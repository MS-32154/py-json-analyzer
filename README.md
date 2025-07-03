# 🔍 JSON Explorer

**JSON Explorer** is a powerful CLI and Python library for analyzing, visualizing, and exploring JSON data from files, URLs, or Python objects.

---

## 📦 Features

- View JSON as a tree (compact, raw, or analytical)
- Search by key, value, key-value pairs, or custom filter expressions
- Generate statistical summaries and insights
- Create visualizations in terminal, browser, or matplotlib
- Interactive terminal exploration mode
- Usable as a Python library with modular components

---

## 📦 Requirements

- Python ≥ 3.7

- The following Python packages:

```
numpy==2.3.1
requests==2.32.4
rich==14.0.0
setuptools==80.9.0
matplotlib==3.10.3
```

> 💡 On Windows, the `windows-curses` package will be installed automatically to enable terminal UI features.

---

## 📥 Installation

### 🔹 From PyPI

```bash
pip install py-json-analyzer
```

Upgrade to the latest version:

```bash
pip install --upgrade py-json-analyzer
```

### 🔹 From Source

```bash
git clone https://github.com/MS-32154/py-json-analyzer
cd json_explorer
pip install .
```

### 🔹 Development Mode

```bash
pip install -e .
```

---

## 🧪 Running Tests

```bash
pytest
```

---

## 🚀 CLI Usage

```
json_explorer  [-h] [--url URL] [--interactive] [--tree {compact,analysis,raw}] [--search SEARCH] [--search-type {key,value,pair,filter}]
               [--search-value SEARCH_VALUE] [--search-mode {exact,contains,regex,startswith,endswith,case_insensitive}] [--tree-results] [--stats]
               [--detailed] [--plot] [--plot-format {terminal,matplotlib,browser,all}] [--save-path SAVE_PATH] [--no-browser]
               [file]

🔍 JSON Explorer - Analyze, visualize, and explore JSON data

positional arguments:
  file                  Path to JSON file

options:
  -h, --help            show this help message and exit
  --url URL             URL to fetch JSON from
  --interactive, -i     Run in interactive mode
  --tree {compact,analysis,raw}
                        Display JSON tree structure

search options:
  --search SEARCH       Search query or filter expression
  --search-type {key,value,pair,filter}
                        Type of search to perform
  --search-value SEARCH_VALUE
                        Value to search for (used with --search-type pair)
  --search-mode {exact,contains,regex,startswith,endswith,case_insensitive}
                        Search mode
  --tree-results        Display search results in tree format

analysis options:
  --stats               Show statistics
  --detailed            Show detailed analysis/statistics

visualization options:
  --plot                Generate visualizations
  --plot-format {terminal,matplotlib,browser,all}
                        Visualization format
  --save-path SAVE_PATH
                        Path to save visualizations
  --no-browser          Don't open browser for HTML visualizations

Examples:
  json_explorer data.json --interactive
  json_explorer data.json --tree compact --stats
  json_explorer data.json --search "name" --search-type key
  json_explorer data.json --search "isinstance(value, int) and value > 10" --search-type filter
  json_explorer --url https://api.example.com/data --plot --tree-results
```

### Interactive-mode Preview

![interactive-mode](/screenshots/screenshots.gif)

---

## 📚 Library Usage

Use `json_explorer` as a Python module:

```python
test_data = {
    "users": [
        {
            "id": 1,
            "name": "Alice",
            "profile": {
                "age": 30,
                "settings": {"theme": "dark", "notifications": True},
            },
            "tags": ["admin", "user"],
        },
        {
            "id": 2,
            "name": "Bob",
            "profile": {
                "age": 25,
                "settings": {
                    "theme": "light",
                    "notifications": False,
                    "language": "en",
                },
            },
            "tags": ["user"],
            "email": "bob@example.com",
        },
    ],
    "metadata": {"total": 2, "created": "2024-01-01"},
}
```

### Stats Analysis

```python
# Displays statistical summaries and structural analysis
from json_explorer.stats import DataStatsAnalyzer

analyzer = DataStatsAnalyzer()
analyzer.print_summary(test_data, detailed=True)
```

### Structure Inference

```python
# Generates a JSON Schema based on the first 20 instances of the largest top-level entity
from json_explorer.analyzer import analyze_json

summary = analyze_json(test_data)
print(summary)
```

### Search Features

```python
from json_explorer.search import JsonSearcher, SearchMode

searcher = JsonSearcher()

# Search keys containing "settings"
results = searcher.search_keys(test_data, "settings", SearchMode.CONTAINS)
searcher.print_results(results)

# Search for values containing '@':"
results = searcher.search_values(test_data, "@", SearchMode.CONTAINS, value_types={str})
searcher.print_results(results)

# Searching for 'key' = 'tags' and values containing 'user':"
results = searcher.search_key_value_pairs(
    test_data,
    key_pattern="tags",
    value_pattern="user",
    value_mode=SearchMode.CONTAINS,
)
searcher.print_results(results, mode=SearchMode.CONTAINS)

# Filter values > 10
results = searcher.search_with_filter(
    test_data,
    lambda k, v, d: isinstance(v, (int, float)) and v > 10
)
searcher.print_results(results, show_tree=True)
```

### Tree View

```python
# Renders a tree view of the inferred JSON structure
# If show_raw is enabled, it also displays the raw JSON Schema
from json_explorer.tree_view import print_json_analysis, print_compact_tree

print_json_analysis(test_data, "Sample Data", show_raw=True)
print_compact_tree(test_data, "Sample Data (Compact)")
```

### Visualizations

```python
Generates visual representations of statistics and insights
from json_explorer.visualizer import JSONVisualizer

visualizer = JSONVisualizer()
visualizer.visualize(test_data, output="terminal", detailed=True)
visualizer.visualize(test_data, output="matplotlib", detailed=True)
visualizer.visualize(test_data, output="browser", detailed=True)
```

---

## 📄 License

MIT License. See `LICENSE` for details.
