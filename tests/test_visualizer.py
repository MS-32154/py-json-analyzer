"""Tests for the visualizer (terminal text charts and Plotly HTML report)."""

from unittest.mock import patch

import pytest
from json_explorer.visualizer import JSONVisualizer, visualize_json


@pytest.fixture
def sample_data():
    return {
        "users": [
            {"id": 1, "name": "Alice", "email": None, "tags": ["a", "b"]},
            {"id": 2, "name": "Bob", "email": "bob@example.com", "tags": []},
        ],
        "meta": {"count": 2, "ratio": 0.5},
    }


@pytest.fixture
def no_browser():
    with patch("webbrowser.open") as opened:
        yield opened


@pytest.fixture(autouse=True)
def temp_reports(tmp_path, monkeypatch):
    """Temporary HTML reports go to tmp_path."""
    import tempfile

    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))


class TestTerminal:
    def test_charts(self, sample_data, capsys):
        JSONVisualizer().visualize(sample_data, output="terminal")
        out = capsys.readouterr().out
        assert "DATA TYPES DISTRIBUTION" in out
        assert "DEPTH DISTRIBUTION" in out
        assert "QUALITY METRICS" not in out

    def test_detailed_adds_quality_metrics(self, sample_data, capsys):
        JSONVisualizer().visualize(sample_data, output="terminal", detailed=True)
        out = capsys.readouterr().out
        assert "QUALITY METRICS" in out
        assert "Null values" in out

    @pytest.mark.parametrize("data", [{}, [], 42, None, {"a": {"b": {"c": [1]}}}])
    def test_edge_cases(self, data, capsys):
        JSONVisualizer().visualize(data, output="terminal", detailed=True)
        assert "DATA TYPES DISTRIBUTION" in capsys.readouterr().out


class TestHtml:
    def test_temporary_report_opened(self, sample_data, tmp_path, no_browser):
        JSONVisualizer().visualize(sample_data, output="html")
        report = tmp_path / "json_analysis.html"
        assert report.exists()
        no_browser.assert_called_once_with(report.absolute().as_uri())

    def test_saved_report_opened(self, sample_data, tmp_path, no_browser):
        target = tmp_path / "report.html"
        JSONVisualizer().visualize(sample_data, output="html", save_path=target)
        assert target.exists()
        no_browser.assert_called_once()

    def test_no_browser(self, sample_data, tmp_path, no_browser):
        JSONVisualizer().visualize(
            sample_data,
            output="html",
            save_path=tmp_path / "r.html",
            open_browser=False,
        )
        no_browser.assert_not_called()

    def test_html_suffix_added(self, sample_data, tmp_path, no_browser):
        JSONVisualizer().visualize(
            sample_data, output="html", save_path=tmp_path / "report"
        )
        assert (tmp_path / "report.html").exists()

    def test_detailed_report(self, sample_data, tmp_path, no_browser):
        target = tmp_path / "detailed.html"
        JSONVisualizer().visualize(
            sample_data, output="html", detailed=True, save_path=target
        )
        assert "Complexity Score" in target.read_text(encoding="utf-8")


class TestFormats:
    def test_all_writes_both(self, sample_data, tmp_path, no_browser, capsys):
        JSONVisualizer().visualize(
            sample_data, output="all", save_path=tmp_path / "r.html"
        )
        assert "DATA TYPES DISTRIBUTION" in capsys.readouterr().out
        assert (tmp_path / "r.html").exists()

    @pytest.mark.parametrize("output", ["interactive", "png", ""])
    def test_unknown_format(self, sample_data, output):
        with pytest.raises(ValueError, match="Unknown output format"):
            JSONVisualizer().visualize(sample_data, output=output)

    def test_stats_kept_on_instance(self, sample_data, capsys):
        visualizer = JSONVisualizer()
        visualizer.visualize(sample_data, output="terminal")
        assert visualizer.stats["max_depth"] >= 3


def test_visualize_json_function(sample_data, capsys):
    visualize_json(sample_data, output="terminal")
    assert "DATA TYPES DISTRIBUTION" in capsys.readouterr().out
