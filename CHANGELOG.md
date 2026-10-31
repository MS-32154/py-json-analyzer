# Changelog

All notable changes to this project are documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- Prompt history is stored in the user state directory (`$XDG_STATE_HOME/json_explorer`,
  `~/Library/Application Support/json_explorer`, or `%LOCALAPPDATA%\json_explorer`) instead of
  the current directory.
- `--verbose-logging` is the documented spelling; `--verbose_logging` still works.
- `RegistryError` is exported from `json_explorer.codegen`.
- Logging follows library best practice: importing json_explorer no longer prints INFO logs to stderr.
  The package logger only has a `NullHandler` and propagates to the root logger; the CLI calls
  `configure_logging()`. Logger names are no longer doubled (`json_explorer.cli`, not
  `json_explorer.json_explorer.cli`), and CLI errors are no longer printed twice.
- Requires Python 3.15+ (3.14+ on Windows, where `windows-curses` has no 3.15 wheels yet).
- Project managed with uv (`uv.lock`, `.python-version`); `requirements.txt` removed.
- `__version__` is now read from package metadata (single source: `pyproject.toml`).
- License metadata uses the SPDX expression `MIT` (PEP 639).
- Lint and format with ruff (replaces black, isort and flake8).

### Added
- Compile tests for generated code: Python output is executed and its annotations resolved;
  Go output is checked with `go vet` (run in CI on Linux).
- `JsonExplorerError` base class (exported from `json_explorer`): all package errors (`JSONLoaderError`,
  `GeneratorError`, `RegistryError`, `ConfigError`, `TemplateError`, `CLIError`) now derive from it.
- CI workflow: tests on Ubuntu, macOS and Windows; ruff lint job.
- Publish workflow: runs CI first, checks the tag matches the version, verifies and smoke-tests the built distributions.
- `py.typed` marker: type information is now shipped with the package.

### Fixed
- `--plot` failed with "Unknown output format: interactive" unless `--plot-format` was given.
- `--generate` without `--output` wrapped the code in a Rich header and padding, so redirecting
  it to a file produced invalid code. Piped output is now the raw code; status messages, warnings
  and metadata go to stderr. The analysis spinner no longer writes to stdout or to non-terminals.
- Generated dataclasses raised `TypeError` on import when an optional field (with a default) came
  before a required one. Optional fields now follow required ones (unless `kw_only` is set).
- A file containing an empty `{}` or `[]` was reported as "No data loaded".
- Missing file/URL errors are printed to stderr; the dead "file or URL required" check was fixed.
- Go `time` import detection for combined pointer/slice types (e.g. `[]*time.Time`).
- `codegen.create_config(language)` ignored `language`: it now applies the language's defaults
  (snake_case fields for Python) and rejects unsupported languages.

### Removed
- **Breaking:** the `dev` and `all` extras. `pip install py-json-analyzer[dev]` no longer works;
  development tools are now a PEP 735 `dev` dependency group (`uv sync`, or `pip install --group dev`
  with pip >= 25.1).

## [0.4.0] - 2025-12-05
JMESPath integration and enhanced architecture: JMESPath-based search, Plotly visualizations, centralized logging.

## [0.3.0] - 2025-11-22
Python generator (dataclasses, Pydantic v2, TypedDict) and smarter type resolution.

## [0.2.0] - 2025-08-20
Code generation from JSON data (Go).

## [0.1.3] - 2025-07-03
Initial release series.

## [0.1.2] - 2025-06-28
Initial release series.

[Unreleased]: https://github.com/MS-32154/py-json-analyzer/compare/v0.4.0...HEAD
[0.4.0]: https://github.com/MS-32154/py-json-analyzer/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/MS-32154/py-json-analyzer/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/MS-32154/py-json-analyzer/compare/v0.1.3...v0.2.0
[0.1.3]: https://github.com/MS-32154/py-json-analyzer/compare/v0.1.2...v0.1.3
[0.1.2]: https://github.com/MS-32154/py-json-analyzer/releases/tag/v0.1.2
