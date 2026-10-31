[![PyPI version](https://img.shields.io/pypi/v/py-json-analyzer.svg)](https://pypi.org/project/py-json-analyzer/)
[![Python 3.15+ (3.14+ on Windows)](https://img.shields.io/badge/python-3.15+%20%7C%203.14+%20Windows-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

# JSON Explorer

**JSON Explorer** is a powerful CLI and Python library for analyzing, visualizing, exploring, and generating code from JSON data. Built with modern Python practices and featuring JMESPath-powered search capabilities.

---

## Features

### Analysis & Exploration

- **Structural Analysis**: infers one type per position from every value seen (optional keys, nullable
  values, int/float widening, mixed types) and detects standard string formats (RFC 3339 date-times,
  dates, times, durations)
- **JMESPath Search**: Industry-standard query language for powerful JSON searching and filtering
- **Tree Visualization**: Multiple view modes (compact, analytical, raw) with rich terminal output
- **Statistical Analysis**: Comprehensive data quality metrics and structural insights
- **Visualization**: text charts in the terminal, an interactive HTML report (Plotly), or both
- **JSON Schema export**: a draft 2020-12 schema of the data (`--json-schema`) for validation or for
  other code generators
- **Interactive Mode**: Full-featured terminal UI for exploration and analysis

### Code Generation

- **Go**: structs with JSON tags, pointers for optional fields, `time.Time` for RFC 3339 date-times;
  gofmt-clean output
- **Python**: dataclasses, Pydantic v2 models (aliases for renamed keys, `datetime`/`date`/`time`/
  `timedelta`) or TypedDicts (original keys); ruff/black-formatted output
- **TypeScript**: interfaces, or Zod 4 schemas with inferred types; keys kept as in the JSON,
  `key?:` for missing keys, `| null` for null values, unions for mixed values; Prettier-formatted
- **Correct names**: types named after their keys (`TeamLead`, `Project`), every name planned once so
  declarations and references agree, keys escaped or mapped with aliases
- **Verified output**: the test suite compiles the generated code and decodes the source data with it
- **Configuration**: JSON config file, CLI flags, or guided interactive setup with presets;
  invalid options fail with a clear message

### Library Features

- **Modular Architecture**: Use individual components independently
- **Language plugins**: add a target language as a package (or install one through the
  `json_explorer.languages` entry point)
- **Typed**: ships `py.typed`; type-checks cleanly with mypy
- **Quiet as a library**: logs only when the application configures logging

---

## Requirements

- **Python**: 3.15 or higher (Linux/macOS); 3.14 or higher on Windows

### Core Dependencies

```
jmespath>=1.0.1          # JMESPath query language
jinja2>=3.0.0            # Template engine for code generation
plotly>=5.0.0            # Interactive, browser-based graphing
prompt-toolkit>=3.0.0    # Interactive input with autocomplete
requests>=2.32.0         # HTTP requests for URL loading
rich>=13.0.0             # Rich terminal formatting
```

### Development Dependencies (`dev` dependency group)

```
pytest>=7.0.0
pytest-cov>=4.0.0
ruff>=0.17.0
mypy>=1.0.0
types-requests>=2.31.0
```

---

## Installation

### From PyPI (Recommended)

```bash
pip install py-json-analyzer
```

Upgrade to the latest version:

```bash
pip install --upgrade py-json-analyzer
```

### From Source

```bash
git clone https://github.com/MS-32154/py-json-analyzer
cd py-json-analyzer
uv sync              # or: pip install -e .
```

For development with all optional dependencies:

```bash
uv sync              # installs the dev group; or (pip >= 25.1): pip install -e . --group dev
```

---

## Quick Start

### Command Line

```bash
# Interactive mode (recommended for first-time users)
json_explorer data.json --interactive

# Quick analysis
json_explorer data.json --tree compact --stats

# JMESPath search
json_explorer data.json --search "users[*].email"

# Generate Go code
json_explorer data.json --generate go --output models.go

# Generate Pydantic models
json_explorer data.json --generate python --python-style pydantic --output models.py

# Create visualizations
json_explorer data.json --plot --plot-format html
```

### Python Library

```python
from json_explorer import analyze_json, JsonSearcher
from json_explorer.codegen import quick_generate

# Analyze structure
data = {"users": [{"id": 1, "name": "Alice", "email": "alice@example.com"}]}
analysis = analyze_json(data)
print(analysis)

# JMESPath search
searcher = JsonSearcher()
result = searcher.search(data, "users[*].email")
searcher.print_result(result)

# Generate code
go_code = quick_generate(data, language="go", package_name="models")
python_code = quick_generate(data, language="python", style="pydantic")
```

---

## CLI Usage

### Basic Commands

```bash
json_explorer [FILE] [OPTIONS]

# Data Sources
json_explorer data.json              # Load from file
json_explorer --url https://api.example.com/data  # Load from URL

# Display Modes
--interactive, -i                    # Interactive mode (full UI)
--tree {compact,analysis,raw}        # Display tree structure
--stats                              # Show statistics
--detailed                           # Show detailed information
--plot                               # Generate visualizations
```

### JMESPath Search

The search functionality now uses [JMESPath](https://jmespath.org/), an industry-standard query language for JSON:

```bash
# Basic path expressions
json_explorer data.json --search "users"              # Get users array
json_explorer data.json --search "users[0]"           # First user
json_explorer data.json --search "users[*].name"      # All names

# Filtering
json_explorer data.json --search "users[?age > \`30\`]"           # Filter by age
json_explorer data.json --search "users[?active == \`true\`]"     # Filter by boolean

# Functions
json_explorer data.json --search "length(users)"                  # Count users
json_explorer data.json --search "sort_by(users, &age)"          # Sort by field
json_explorer data.json --search "max_by(users, &age).name"      # Get name of oldest

# Projections (field selection)
json_explorer data.json --search "users[*].{name: name, email: email}"

# Complex queries
json_explorer data.json --search "users[?age > \`30\` && active == \`true\`].name"

# Display options
--tree-results                       # Show results as tree
--show-examples                      # Display JMESPath examples
```

**JMESPath Resources:**

- [Tutorial](https://jmespath.org/tutorial.html)
- [Specification](https://jmespath.org/specification.html)
- [Online Playground](https://jmespath.org/)

### Code Generation

```bash
# List supported languages
json_explorer --list-languages

# Get language details
json_explorer --language-info go
json_explorer --language-info python

# Generate Go code
json_explorer data.json --generate go \
  --output models.go \
  --package-name models \
  --root-name User

# Go-specific options
--no-pointers                        # Don't use pointers for optional fields

# Generate Python code
json_explorer data.json --generate python \
  --output models.py \
  --python-style {dataclass,pydantic,typeddict}

# Python-specific options
--frozen                             # Make dataclasses immutable
--no-slots                           # Don't use __slots__
--no-kw-only                         # Positional fields (default: keyword-only)
--pydantic-forbid-extra              # Forbid extra fields in Pydantic

# TypeScript-specific options
--ts-style {interface,zod}           # Interfaces (default) or Zod schemas

# Common options
--config config.json                 # Load configuration from file
--no-comments                        # Don't generate comments
--verbose                            # Show detailed generation info
```

### JSON Schema

```bash
# Print a JSON Schema (draft 2020-12) of the data
json_explorer data.json --json-schema > data.schema.json
json_explorer data.json --json-schema --output data.schema.json --root-name Users
```

### Visualization

```bash
# Terminal visualization (text charts)
json_explorer data.json --plot --plot-format terminal

# Interactive HTML (Plotly)
json_explorer data.json --plot --plot-format html

# All formats
json_explorer data.json --plot --plot-format all

# Options
--detailed                           # Generate detailed charts
--save-path output.html              # Save to specific file
--no-browser                         # Don't auto-open browser
```

### Logging

```bash
--log-level {DEBUG,INFO,WARNING,ERROR}
--log-file output.log
```

---

## Python API

### Core Analysis

```python
from json_explorer import analyze_json, load_json

# Load data
source, data = load_json("data.json")
# or
source, data = load_json(url="https://api.example.com/data")

# Analyze structure
analysis = analyze_json(data)
print(f"Kind: {analysis.kind}")          # object, array, string, ...
print(f"Fields: {list(analysis.fields)}")  # for objects
print(analysis.to_dict())                  # plain-dict form
```

### JMESPath Search

```python
from json_explorer import JsonSearcher

searcher = JsonSearcher()

# Basic search
result = searcher.search(data, "users[*].email")
if result:
    searcher.print_result(result)

# Several queries
results = {q: searcher.search(data, q) for q in ["users[*].name", "length(users)"]}

# Validate query before executing
valid, error = searcher.validate_query("users[*].invalid...")
if valid:
    result = searcher.search(data, query)

# Get example queries
examples = searcher.get_query_examples()
searcher.print_examples()
```

### JSON Schema

```python
from json_explorer import json_schema

schema = json_schema(data, title="Users")  # dict, draft 2020-12
```

### Statistics & Analysis

```python
from json_explorer import DataStatsAnalyzer, generate_stats

# Generate statistics
analyzer = DataStatsAnalyzer()
stats = analyzer.generate_stats(data)

# Print formatted summary
analyzer.print_summary(data, detailed=True)

# Or use convenience function
stats = generate_stats(data)
print(f"Total values: {stats['total_values']}")
print(f"Max depth: {stats['max_depth']}")
print(f"Complexity: {stats['computed_insights']['complexity_score']}")
```

### Visualization

```python
from json_explorer import JSONVisualizer, visualize_json

# Create visualizer
visualizer = JSONVisualizer()

# Terminal visualization
visualizer.visualize(data, output="terminal", detailed=True)

# HTML visualization
visualizer.visualize(
    data,
    output="html",
    save_path="report.html",
    detailed=True,
    open_browser=True
)

# Or use convenience function
visualize_json(data, output="html", detailed=True)
```

### Tree Display

```python
from json_explorer.tree_view import print_compact_tree, print_json_analysis

# Full analysis with tree
print_json_analysis(data, source="API Response", show_raw=False)

# Compact tree (no annotations)
print_compact_tree(data, source="Config File")

# Custom tree builder
from json_explorer.tree_view import JsonTreeBuilder

builder = JsonTreeBuilder(show_conflicts=True, show_optional=True)
# ... use builder for custom visualization
```

### Code Generation

```python
from json_explorer.codegen import (
    quick_generate,
    generate_from_analysis,
    create_config,
    list_languages,
    get_language_info
)

# Quick generation
go_code = quick_generate(
    data,
    language="go",
    package_name="models",
    root_name="User"
)

python_code = quick_generate(
    data,
    language="python",
    style="pydantic",
    package_name="models"
)

# Detailed workflow
analysis = analyze_json(data)
config = create_config(
    language="go",
    package_name="api",
    add_comments=True,
    language_config={
        "use_pointers_for_optional": True,
        "int_type": "int64"
    }
)

result = generate_from_analysis(analysis, "go", config, "User")
if result.success:
    print(result.code)
    with open("models.go", "w") as f:
        f.write(result.code)
else:
    print(f"Error: {result.error_message}")

# Discover capabilities
languages = list_languages()
print(f"Supported: {languages}")

info = get_language_info("python")
print(f"Python styles: {info.get('styles', [])}")
```

### Interactive Mode

```python
from json_explorer.interactive import InteractiveHandler

handler = InteractiveHandler()
handler.set_data(data, source="my_data.json")
exit_code = handler.run()  # Launches interactive UI
```

---

## Configuration

### Configuration File Format

JSON Explorer uses JSON configuration files for code generation:

```json
{
  "package_name": "models",
  "add_comments": true,
  "json_tag_omitempty": true,
  "language_config": {
    "use_pointers_for_optional": true,
    "int_type": "int64",
    "float_type": "float64"
  }
}
```

### Language-Specific Examples

#### Go Configuration

```json
{
  "package_name": "api",
  "add_comments": true,
  "json_tag_omitempty": true,
  "language_config": {
    "use_pointers_for_optional": true,
    "int_type": "int64",
    "float_type": "float64"
  }
}
```

#### Python Dataclass Configuration

```json
{
  "package_name": "models",
  "add_comments": true,
  "language_config": {
    "style": "dataclass",
    "dataclass_slots": true,
    "dataclass_frozen": false,
    "dataclass_kw_only": true
  }
}
```

#### Python Pydantic Configuration

```json
{
  "package_name": "models",
  "add_comments": true,
  "language_config": {
    "style": "pydantic",
    "pydantic_config_dict": true,
    "pydantic_extra_forbid": false
  }
}
```

Load configuration:

```bash
json_explorer data.json --generate go --config go_config.json
```

```python
from json_explorer.codegen import load_config, generate_from_analysis

config = load_config("go_config.json")
result = generate_from_analysis(analysis, "go", config, "User")
```

---

## Architecture

### Project Structure

```
json_explorer/
├── __init__.py              # Public API exports
├── __main__.py              # Entry point for `python -m json_explorer`
├── main.py                  # CLI application coordinator
├── cli.py                   # CLI command handler
├── interactive.py           # Interactive mode handler
│
├── analyzer.py              # JSON structure analysis
├── search.py                # JMESPath-based search
├── stats.py                 # Statistical analysis
├── tree_view.py             # Tree visualization
├── visualizer.py            # Terminal text charts and Plotly HTML report
├── utils.py                 # File/URL loading
├── ui.py                    # Prompts and shared terminal helpers
├── errors.py                # JsonExplorerError base exception
├── logging_config.py        # Logging setup (silent unless configured)
│
└── codegen/
    ├── __init__.py          # Code generation API
    ├── registry.py          # Generator registry system
    ├── cli_integration.py   # CLI integration
    ├── interactive.py       # Interactive codegen UI
    │
    ├── core/                # Core codegen infrastructure
    │   ├── naming.py        # Word splitting and the name plan
    │   ├── config.py        # Configuration and option validation
    │   ├── templates.py     # Jinja2 rendering
    │   ├── schema.py        # Schema built from the analysis
    │   ├── plugin.py        # LanguagePlugin / CliOption
    │   └── generator.py     # Base generator
    │
    └── languages/           # Language-specific generators
        ├── go/
        │   ├── plugin.py    # Registration, CLI flags, examples
        │   ├── generator.py
        │   ├── config.py
        │   ├── naming.py
        │   ├── interactive.py
        │   └── templates/   # Jinja2 templates
        │
        ├── python/
        │   ├── plugin.py
        │   ├── generator.py
        │   ├── config.py
        │   ├── naming.py
        │   ├── interactive.py
        │   └── templates/   # Jinja2 templates
        │
        └── typescript/      # Interfaces and Zod schemas
            ├── plugin.py
            ├── generator.py
            ├── config.py
            ├── naming.py
            └── templates/
```

### Key Design Patterns

- **Typed analysis**: `analyze_json()` returns `Node` trees merged by one rule
- **Name plan**: every type and field is named once before rendering
- **Language plugins**: each language is one `LanguagePlugin` (generator, flags, examples, interactive
  handler), registered by the registry or an entry point

---

## Testing

Run the test suite:

```bash
pytest
```

Run with coverage:

```bash
pytest --cov=json_explorer --cov-report=html
```

Test categories:

- **Core modules**: analyzer, search, stats, tree_view, visualizer
- **Codegen core**: naming, schema, config, templates, registry/plugins
- **Generators**: Go and Python (all styles)
- **Compile and decode tests** (`test_codegen_compiles.py`): generated Python is executed and must be
  ruff-format clean; generated Go must pass `go vet` and `gofmt`; Go and Pydantic must decode the
  source data. Go checks are skipped when Go isn't installed (`JSON_EXPLORER_GO` can point to one)
- **CLI**: end-to-end runs of `json_explorer` (`test_cli.py`)

---

## Supported Languages

| Language       | Status          | Features                                                 |
| -------------- | --------------- | -------------------------------------------------------- |
| **Go**         | ✅ Full Support | Structs, JSON tags, pointers, configurable int/float/time types |
| **Python**     | ✅ Full Support | Dataclasses, Pydantic v2, TypedDict, modern type hints   |
| **TypeScript** | ✅ Full Support | Interfaces, Zod 4 schemas, optional/nullable keys, unions |

Other languages can be added as plugins (see below).

---

## Documentation

- **API Documentation**: [https://ms-32154.github.io/py-json-analyzer/](https://ms-32154.github.io/py-json-analyzer/)
- **GitHub Repository**: [https://github.com/MS-32154/py-json-analyzer](https://github.com/MS-32154/py-json-analyzer)
- **Issue Tracker**: [https://github.com/MS-32154/py-json-analyzer/issues](https://github.com/MS-32154/py-json-analyzer/issues)

---

## Contributing

Contributions are welcome! Here's how to get started:

1. **Fork** the repository
2. **Clone** your fork: `git clone https://github.com/YOUR_USERNAME/py-json-analyzer`
3. **Create** a feature branch: `git checkout -b feature/amazing-feature`
4. **Make** your changes and add tests
5. **Run** tests: `pytest`
6. **Commit**: `git commit -m 'Add amazing feature'`
7. **Push**: `git push origin feature/amazing-feature`
8. **Open** a Pull Request

### Development Setup

```bash
# Clone and setup
git clone https://github.com/MS-32154/py-json-analyzer
cd py-json-analyzer
uv sync

# Run tests
uv run pytest

# Lint and format code
uv run ruff check --fix json_explorer/ tests/
uv run ruff format json_explorer/ tests/

# Type checking
uv run mypy json_explorer/
```

### Adding a New Language Generator

1. Create a package with a generator extending `CodeGenerator` (set `language_name`,
   `file_extension`, `template_dir`; implement `generate()`) and its Jinja2 templates
2. Define `PLUGIN = LanguagePlugin(name=..., generator=..., aliases=..., cli_options=..., examples=...)`
3. Register it: built-in languages are listed in `_BUILTIN_PLUGINS` in
   `json_explorer/codegen/registry.py`; external packages declare an entry point in the
   `json_explorer.languages` group that points to the plugin
4. Add the language to `tests/test_codegen_compiles.py` so its output is compiled and checked

---

## Support

### Getting Help

- **Documentation**: Check the [API docs](https://ms-32154.github.io/py-json-analyzer/)
- **Examples**: See the examples section above
- **Issues**: [GitHub Issues](https://github.com/MS-32154/py-json-analyzer/issues)

### Reporting Issues

When reporting issues, please include:

1. **Python version**: `python --version`
2. **Package version**: `pip show py-json-analyzer`
3. **Operating system**
4. **Minimal reproducible example**
5. **Full error traceback**
6. **Expected vs actual behavior**

### Feature Requests

We welcome feature requests! Please open an issue with:

- Clear description of the feature
- Use cases and benefits
- Example of how it would work
- Any relevant mockups or examples

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Acknowledgments

- **JMESPath**: Powerful JSON query language
- **Rich**: Beautiful terminal formatting
- **Plotly**: Interactive visualizations
- **Jinja2**: Flexible template engine

---

## Author

**MS-32154**

- GitHub: [@MS-32154](https://github.com/MS-32154)
- Email: msttoffg@gmail.com

---

**JSON Explorer** – © 2025 MS-32154. All rights reserved.
