[![PyPI version](https://img.shields.io/pypi/v/py-json-analyzer.svg)](https://pypi.org/project/py-json-analyzer/)
[![Python 3.9+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

# JSON Explorer

**JSON Explorer** is a powerful CLI and Python library for analyzing, visualizing, exploring, and generating code from JSON data.

---

## Features

### Analysis & Exploration

- View JSON as a tree (compact, raw, or analytical)
- Search by key, value, key-value pairs, or custom filter expressions
- Generate statistical summaries and insights
- Create visualizations in terminal, browser, or matplotlib
- Interactive terminal exploration mode

### Code Generation

- Generate strongly-typed data structures from JSON
- Multiple language support (Go, with Python, TypeScript, Rust coming soon)
- Smart type detection and conflict resolution
- Configurable naming conventions and templates
- JSON serialization tags and annotations
- Interactive configuration and preview

### Library Features

- Usable as a Python library with modular components
- Extensible architecture for custom generators
- Template-based code generation
- Configuration profiles and validation

---

## Requirements

- Python >= 3.9

Required packages:

```
numpy==2.3.2
requests==2.32.5
rich==14.1.0
setuptools==80.9.0
matplotlib==3.10.5
dateparser==1.2.2
jinja2>=3.0.0
```

> Note: On Windows, the `windows-curses` package will be installed automatically to enable terminal UI features.

---

## Installation

### From PyPI

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
cd json_explorer
pip install .
```

### Development Mode

```bash
pip install -e .
```

---

## Running Tests

```bash
pytest
```

---

## CLI Usage

```
json_explorer [-h] [--url URL] [--interactive] [--tree {compact,analysis,raw}]
              [--search SEARCH] [--search-type {key,value,pair,filter}]
              [--search-value SEARCH_VALUE] [--search-mode {exact,contains,regex,startswith,endswith,case_insensitive}]
              [--tree-results] [--stats] [--detailed] [--plot] [--plot-format {terminal,matplotlib,browser,all}]
              [--save-path SAVE_PATH] [--no-browser]
              [--generate LANGUAGE] [--output FILE] [--config FILE] [--package-name NAME] [--root-name NAME]
              [--list-languages] [--language-info LANGUAGE] [--verbose]
              [file]

JSON Explorer - Analyze, visualize, explore, and generate code from JSON data

positional arguments:
  file                  Path to JSON file

options:
  -h, --help            show this help message and exit
  --url URL             URL to fetch JSON from
  --interactive, -i     Run in interactive mode

analysis options:
  --tree {compact,analysis,raw}
                        Display JSON tree structure
  --stats               Show statistics
  --detailed            Show detailed analysis/statistics

search options:
  --search SEARCH       Search query or filter expression
  --search-type {key,value,pair,filter}
                        Type of search to perform
  --search-value SEARCH_VALUE
                        Value to search for (used with --search-type pair)
  --search-mode {exact,contains,regex,startswith,endswith,case_insensitive}
                        Search mode
  --tree-results        Display search results in tree format

visualization options:
  --plot                Generate visualizations
  --plot-format {terminal,matplotlib,browser,all}
                        Visualization format
  --save-path SAVE_PATH
                        Path to save visualizations
  --no-browser          Don't open browser for HTML visualizations

code generation options:
  --generate LANGUAGE, -g LANGUAGE
                        Generate code in specified language
  --output FILE, -o FILE
                        Output file for generated code (default: stdout)
  --config FILE         JSON configuration file for code generation
  --package-name NAME   Package/namespace name for generated code
  --root-name NAME      Name for the root data structure (default: Root)
  --list-languages      List supported target languages and exit
  --language-info LANGUAGE
                        Show detailed information about a specific language
  --verbose             Show generation result metadata

common generation options:
  --no-comments         Don't generate comments in output code
  --struct-case {pascal,camel,snake}
                        Case style for struct/class names
  --field-case {pascal,camel,snake}
                        Case style for field names

Go-specific options:
  --no-pointers         Don't use pointers for optional fields in Go
  --no-json-tags        Don't generate JSON struct tags in Go
  --no-omitempty        Don't add omitempty to JSON tags in Go
  --json-tag-case {original,snake,camel}
                        Case style for JSON tag names in Go
```

### Examples

**Basic Analysis:**

```bash
json_explorer data.json --interactive
json_explorer data.json --tree compact --stats
json_explorer --url https://api.example.com/data --plot
```

**Search Examples:**

```bash
json_explorer data.json --search "name" --search-type key
json_explorer data.json --search "isinstance(value, int) and value > 10" --search-type filter
```

**Code Generation Examples:**

```bash
# List supported languages
json_explorer --list-languages

# Generate Go structs
json_explorer data.json --generate go

# Generate with custom configuration
json_explorer data.json --generate go --output models.go --package-name models

# Interactive code generation
json_explorer data.json --interactive  # Then select code generation menu
```

### Screenshots

**Main Interactive Mode:**
![interactive-mode](/screenshots/main.gif)

**Code Generation Interface:**
![code generation interface - Go](/screenshots/codegen_go.gif)

---

## Library Usage

### Analysis & Exploration

```python
from json_explorer.stats import DataStatsAnalyzer
from json_explorer.analyzer import analyze_json
from json_explorer.search import JsonSearcher, SearchMode
from json_explorer.tree_view import print_json_analysis
from json_explorer.visualizer import JSONVisualizer

test_data = {
    "users": [
        {
            "id": 1,
            "name": "Alice",
            "profile": {"age": 30, "settings": {"theme": "dark"}},
            "tags": ["admin", "user"]
        }
    ],
    "metadata": {"total": 1, "created": "2024-01-01"}
}

# Statistical analysis
analyzer = DataStatsAnalyzer()
analyzer.print_summary(test_data, detailed=True)

# Structure inference
summary = analyze_json(test_data)
print(summary)

# Search functionality
searcher = JsonSearcher()

results = searcher.search_keys(test_data, "settings", SearchMode.CONTAINS) # Search keys containing "settings"

results = searcher.search_values(test_data, "@", SearchMode.CONTAINS, value_types={str}) # Search for values containing '@'

results = searcher.search_key_value_pairs(
    test_data,
    key_pattern="tags",
    value_pattern="user",
    value_mode=SearchMode.CONTAINS,
) # Searching for 'key' = 'tags' and values containing 'user'

results = searcher.search_with_filter(
    test_data,
    lambda k, v, d: isinstance(v, (int, float)) and v > 10
) # Filter values > 10
searcher.print_results(results, show_tree=True)

# Tree visualization
print_json_analysis(test_data, "Sample Data", show_raw=True)

# Data visualizations
visualizer = JSONVisualizer()
visualizer.visualize(test_data, output="terminal", detailed=True)  # 'terminal', 'matplotlib', or 'browser' output
```

### Code Generation

```python
from json_explorer.codegen import (
    generate_from_analysis,
    quick_generate,
    list_supported_languages,
    get_language_info,
    create_config
)
from json_explorer.analyzer import analyze_json

# Quick generation
go_code = quick_generate(test_data, language="go")
print(go_code)

# Detailed generation workflow
analysis = analyze_json(test_data)
config = create_config(
    language="go",
    package_name="models",
    add_comments=True
)
result = generate_from_analysis(analysis, "go", config, "User")

if result.success:
    print(result.code)
    if result.warnings:
        print("Warnings:", result.warnings)

# List available languages and info
languages = list_supported_languages()
print("Supported languages:", languages)

go_info = get_language_info("go")
print("Go generator info:", go_info)

# Interactive code generation
from json_explorer.codegen import create_interactive_handler

handler = create_interactive_handler(test_data)
handler.run_interactive()  # Launches interactive interface
```

### Supported Languages

| Language       | Status          | Features                                         |
| -------------- | --------------- | ------------------------------------------------ |
| **Go**         | ✅ Full Support | Structs, JSON tags, pointers, configurable types |
| **Python**     | 🚧 Coming Soon  | Dataclasses, Pydantic models, type hints         |
| **TypeScript** | 🚧 Coming Soon  | Interfaces, types, optional properties           |
| **Rust**       | 🚧 Coming Soon  | Structs, Serde annotations, Option types         |

### Code Generation Features

- **Smart Type Detection**: Handles mixed types, conflicts, and unknown values
- **Configurable Output**: Multiple templates and naming conventions
- **Language-Specific Options**: Tailored features for each target language
- **Validation & Warnings**: Comprehensive validation with helpful warnings
- **Template System**: Extensible Jinja2-based template architecture
- **Interactive Configuration**: Guided setup with preview and validation

---

## Configuration

### Code Generation Config Example

```json
{
  "package_name": "models",
  "add_comments": true,
  "generate_json_tags": true,
  "json_tag_omitempty": true,
  "struct_case": "pascal",
  "field_case": "pascal",
  "use_pointers_for_optional": true,
  "int_type": "int64",
  "float_type": "float64"
}
```

Load configuration:

```bash
json_explorer data.json --generate go --config config.json
```

---

## API Reference

For the complete API reference got to [JSON Explorer API Documentation](https://ms-32154.github.io/py-json-analyzer/) or see the source code.

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## Support

If you encounter any issues or have questions, please:

1. Check the [examples](#examples) section
2. Search existing [GitHub Issues](https://github.com/MS-32154/py-json-analyzer/issues)
3. Create a new issue with:
   - Python version
   - Operating system
   - Minimal code example reproducing the issue
   - Full error traceback (if applicable)

---

**JSON Explorer** – © 2025 MS-32154. All rights reserved.
