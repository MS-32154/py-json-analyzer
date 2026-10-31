"""End-to-end tests for the command-line interface (json_explorer.main)."""

import json
import logging
import sys
import tempfile
from pathlib import Path
from unittest import mock

import pytest
from json_explorer.logging_config import PACKAGE_LOGGER_NAME
from json_explorer.main import main

SAMPLES = Path(__file__).parent.parent / "data_samples"
FLAT_SAMPLE = SAMPLES / "003_sample_project.json"


@pytest.fixture(autouse=True)
def _restore_logging():
    """main() configures the package logger; undo it after each test."""
    pkg = logging.getLogger(PACKAGE_LOGGER_NAME)
    saved = (list(pkg.handlers), pkg.level, pkg.propagate)
    yield
    pkg.handlers[:], pkg.level, pkg.propagate = saved


@pytest.fixture
def run(monkeypatch):
    """Run the CLI with the given arguments and return its exit code."""

    def _run(*argv: str) -> int:
        monkeypatch.setattr(sys, "argv", ["json_explorer", *map(str, argv)])
        return main()

    return _run


@pytest.fixture
def no_browser(monkeypatch, tmp_path):
    """Never open a real browser; keep temporary HTML reports in tmp_path."""
    opened = mock.Mock()
    monkeypatch.setattr("webbrowser.open", opened)
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    return opened


def write_json(tmp_path: Path, data) -> Path:
    path = tmp_path / "data.json"
    path.write_text(json.dumps(data))
    return path


# ---------------------------------------------------------------------------
# #3: --plot works with its default format
# ---------------------------------------------------------------------------


def test_plot_with_default_format_succeeds(run, no_browser, tmp_path, capsys):
    assert run(FLAT_SAMPLE, "--plot", "--no-browser") == 0
    out = capsys.readouterr()
    assert "Unknown output format" not in out.out + out.err
    assert (tmp_path / "json_analysis.html").exists()
    no_browser.assert_not_called()


def test_plot_interactive_opens_saved_report(run, no_browser, tmp_path):
    report = tmp_path / "report.html"
    assert run(FLAT_SAMPLE, "--plot", "--save-path", report) == 0
    assert report.exists()
    no_browser.assert_called_once()


# ---------------------------------------------------------------------------
# #4: generated code on stdout is raw when piped; diagnostics go to stderr
# ---------------------------------------------------------------------------


def test_generate_go_to_stdout_is_raw(run, capsys):
    assert run(FLAT_SAMPLE, "--generate", "go") == 0
    out = capsys.readouterr()
    assert out.out.startswith("package main\n")
    assert "Generated Go Code" not in out.out  # no Rich header
    assert "📄" not in out.out


def test_generate_python_to_stdout_is_valid_python(run, capsys):
    assert run(FLAT_SAMPLE, "--generate", "python") == 0
    code = capsys.readouterr().out
    compile(code, "<stdout>", "exec")  # raises SyntaxError if decorated


def test_generate_warnings_go_to_stderr(run, tmp_path, capsys):
    data = write_json(tmp_path, {"value": None})  # unknown type -> warning
    assert run(data, "--generate", "go") == 0
    out = capsys.readouterr()
    assert "Warnings" in out.err
    assert "Warnings" not in out.out


def test_generate_to_file_reports_on_stderr(run, tmp_path, capsys):
    target = tmp_path / "models.go"
    assert run(FLAT_SAMPLE, "--generate", "go", "--output", target) == 0
    assert target.read_text().startswith("package main\n")
    out = capsys.readouterr()
    assert out.out == ""
    assert "saved to" in out.err


# ---------------------------------------------------------------------------
# #17: empty JSON documents are valid data
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("data", [{}, []], ids=["empty-object", "empty-array"])
@pytest.mark.parametrize("action", ["--stats", "--tree"])
def test_empty_documents_are_accepted(run, tmp_path, capsys, data, action):
    args = [action, "compact"] if action == "--tree" else [action]
    assert run(write_json(tmp_path, data), *args) == 0
    out = capsys.readouterr()
    assert "No data loaded" not in out.out + out.err


# ---------------------------------------------------------------------------
# #18: argument handling
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("argv", "message"),
    [
        (["--stats"], "You must provide a file path or --url"),
        (["--generate", "go"], "Code generation requires a file path or --url"),
    ],
)
def test_missing_input_is_reported_on_stderr(run, capsys, argv, message):
    assert run(*argv) == 1
    out = capsys.readouterr()
    assert message in out.err
    assert message not in out.out


@pytest.mark.parametrize("flag", ["--verbose-logging", "--verbose_logging", "-vl"])
def test_verbose_logging_flag_spellings(run, flag):
    assert run(FLAT_SAMPLE, "--stats", flag) == 0
    assert logging.getLogger(PACKAGE_LOGGER_NAME).level == logging.DEBUG


def test_generate_ignores_force_color_when_piped(run, monkeypatch, capsys):
    monkeypatch.setenv("FORCE_COLOR", "1")
    assert run(FLAT_SAMPLE, "--generate", "go") == 0
    assert capsys.readouterr().out.startswith("package main\n")


def test_generated_code_is_utf8_on_non_utf8_pipe(monkeypatch):
    import io

    from json_explorer.codegen.cli_integration import _display_to_stdout

    raw = io.BytesIO()
    monkeypatch.setattr(sys, "stdout", io.TextIOWrapper(raw, encoding="cp1252"))
    _display_to_stdout("// ◉ Generated\n", "go")
    assert raw.getvalue().decode("utf-8") == "// ◉ Generated\n"
