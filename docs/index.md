# JSON Explorer API Documentation

## Table of Contents

- [Overview](#overview)
- [Core Modules](#core-modules)
  - [Analyzer Module](#1-analyzer-module)
  - [Search Module (JMESPath)](#2-search-module-jmespath)
  - [Statistics Module](#3-statistics-module)
  - [Visualization Module](#4-visualization-module)
  - [Tree View Module](#5-tree-view-module)
  - [Utils Module](#6-utils-module)
  - [Terminal UI Module](#7-terminal-ui-module)
- [JSON Schema Export](#json-schema-export)
- [Code Generation](#code-generation)
  - [Core Generator Interface](#1-core-generator-interface)
  - [Registry and Plugins](#2-registry-and-plugins)
  - [High-Level API](#3-high-level-api)
  - [Go Generator](#4-go-generator)
  - [Python Generator](#5-python-generator)
  - [TypeScript Generator](#6-typescript-generator)
  - [Rust Generator](#7-rust-generator)
  - [Schema System](#8-schema-system)
- [CLI Usage](#cli-usage)
- [Examples](#examples)
- [Configuration Best Practices](#configuration-best-practices)
- [Error Handling](#error-handling)

---

## Overview

JSON Explorer is a comprehensive Python library and CLI tool for analyzing, searching, visualizing, and generating code from JSON data. It features a modern, modular architecture with JMESPath-powered search capabilities and multi-language code generation.

### Key Features

- **Deep Structural Analysis**: Type detection, optional field inference, and conflict resolution
- **JMESPath Search**: Industry-standard query language for powerful JSON querying
- **Comprehensive Statistics**: Data quality metrics, depth analysis, and structural insights
- **Visualization**: text charts in the terminal, an interactive HTML report (Plotly), or both
- **Code Generation**: Generate Go structs, Python dataclasses/Pydantic/TypedDict from JSON
- **Terminal UI**: a full-screen app (Textual) with the data, its structure, live JMESPath search,
  statistics and code generation with a live preview, side by side in tabs
- **Extensible Architecture**: Plugin-based generator system for custom languages

---

## Core Modules

### 1. Analyzer Module

The analyzer module performs deep structural analysis of JSON data with intelligent type detection and conflict resolution.

#### `analyze_json(data)`

Describes the structure of JSON data as a tree of `Node` objects: one node per
position, merged over **every** value seen there (all array elements are used).

**Returns:** `Node` with

- `kind`: `object`, `array`, `string`, `integer`, `float`, `boolean`, `null` or `mixed`
- `optional`: the key is missing from some objects
- `nullable`: `null` was seen
- `fields`: for objects, the node of each key
- `items`: for arrays, the merged node of all elements (`None` if only empty arrays were seen)
- `kinds`: for `mixed`, the kinds seen
- `format`: for strings, the standard format every value follows (see below)

`node.to_dict()` gives a plain-dict form for printing or JSON.

**Example:**

```python
from json_explorer import analyze_json

data = {
    "users": [
        {"id": 1, "name": "Alice", "email": "alice@example.com"},
        {"id": 2, "name": "Bob"},  # email missing
    ]
}

analyze_json(data).to_dict()
# {'kind': 'object', 'fields': {'users': {'kind': 'array', 'items': {
#     'kind': 'object', 'fields': {
#         'id': {'kind': 'integer'},
#         'name': {'kind': 'string'},
#         'email': {'kind': 'string', 'optional': True}}}}}}
```

#### Merging rules

- **Missing keys** make a node optional, **`null` values** make it nullable:
  `[{"value": None}, {"value": 42}]` → `value: integer (nullable)`;
  `[{"value": 42}, {}]` → `value: integer (optional)`
- **Integers and floats** merge to float: `[1, 2.5]` → `float`
- **Other different kinds** give `mixed`, recorded in `kinds` (generated code uses `Any`/`any`):
  `[{"value": 42}, {"value": "text"}]` → `value: mixed (integer, string)`

#### String formats

Strings are given a format only if **every** value follows the same standard
format (RFC 3339, the formats JSON Schema uses):

| Format | Example | Go | Pydantic | dataclass / TypedDict |
|---|---|---|---|---|
| `date-time` | `2024-01-01T10:00:00Z` | `time.Time` | `datetime` | `str` |
| `local-date-time` | `2024-01-01T10:00:00` | `string` | `datetime` | `str` |
| `date` | `2024-01-01` | `string` | `date` | `str` |
| `time` | `10:30:00`, `10:30:00Z` | `string` | `time` | `str` |
| `duration` | `P1DT4H30M` | `string` | `timedelta` | `str` |

Natural-language dates (`"March"`, `"1 hour ago"`), ISO 8601 forms outside RFC 3339
(`20240101T100000Z`, `2024-W01-1`) and invalid dates stay plain strings.

```python
from json_explorer.analyzer import detect_format

detect_format("2024-01-01T12:00:00Z")  # Format.DATE_TIME
detect_format("2024-01-01")  # Format.DATE
detect_format("not a date")  # None
```

---

### 2. Search Module (JMESPath)

The search module provides powerful JSON querying using [JMESPath](https://jmespath.org/), an industry-standard query language for JSON.

#### `JsonSearcher` Class

JMESPath-based JSON search utility with rich output formatting.

**Constructor:**

```python
JsonSearcher(console=None)
```

**Parameters:**

- `console` (Console, optional): Rich console for formatted output

#### Core Methods

##### `search(data, query)`

Execute a JMESPath query on JSON data.

**Parameters:**

- `data` (Any): JSON data to search
- `query` (str): JMESPath query expression

**Returns:**

- `SearchResult | None`: Result object or None if query returns nothing

**Example:**

```python
from json_explorer import JsonSearcher

searcher = JsonSearcher()

# Simple path
result = searcher.search(data, "users[0].name")

# Filter with condition
result = searcher.search(data, "users[?age > `30`]")

# Projection
result = searcher.search(data, "users[*].email")

# Complex query with functions
result = searcher.search(data, "sort_by(users, &age)[0].name")
```

##### `validate_query(query)`

Validate a JMESPath query without executing it.

**Parameters:**

- `query` (str): JMESPath query expression

**Returns:**

- `tuple[bool, str | None]`: (is_valid, error_message)

**Example:**

```python
valid, error = searcher.validate_query("users[*].name")
if not valid:
    print(f"Invalid query: {error}")
```

##### `print_result(result, show_tree=False, max_display_length=100)`

Display search results in formatted output.

**Parameters:**

- `result` (SearchResult | None): Result to display
- `show_tree` (bool): Display as tree structure vs table
- `max_display_length` (int): Maximum length for displayed values

**Example:**

```python
result = searcher.search(data, "users[*].{name: name, age: age}")
searcher.print_result(result, show_tree=True)
```

##### `get_query_examples()`

Get common JMESPath query patterns with descriptions.

**Returns:**

- `dict[str, str]`: Mapping of descriptions to example queries

##### `print_examples()`

Display formatted table of JMESPath query examples.

#### `SearchResult` Dataclass

Represents a search result with metadata.

**Attributes:**

- `path` (str): JSON path expression used
- `value` (Any): The value(s) found
- `query` (str): Original JMESPath query
- `data_type` (str): Type name of the value

#### JMESPath Query Examples

```python
# Basic access
"users"  # Get users array

"users[0]"  # First user
"users[-1]"  # Last user
"users[*].name"  # All user names

# Filtering
"users[?age > `30`]"  # Filter by age
"users[?active == `true`]"  # Filter by boolean
"users[?age > `30` && active == `true`]"  # Multiple conditions

# Projections (field selection)
"users[*].{name: name, email: email}"  # Select specific fields
"users[?age > `30`].name"  # Filter then project

# Functions
"length(users)"  # Count items
"sort_by(users, &age)"  # Sort by field
"max_by(users, &age)"  # Item with max value
"min_by(users, &score)"  # Item with min value
"contains(name, 'John')"  # Check if contains

# Nested access
"user.profile.settings.theme"  # Deep nested access
"users[*].tags[]"  # Flatten nested arrays

# Slicing
"users[0:3]"  # First 3 users
"users[-2:]"  # Last 2 users
"users[::2]"  # Every other user
```

**Resources:**

- [JMESPath Tutorial](https://jmespath.org/tutorial.html)
- [JMESPath Specification](https://jmespath.org/specification.html)
- [JMESPath Playground](https://jmespath.org/)

---

### 3. Statistics Module

Comprehensive data structure analysis with quality metrics and insights.

#### `DataStatsAnalyzer` Class

Analyzes JSON structures and generates detailed statistics about types, patterns, and quality.

**Constructor:**

```python
DataStatsAnalyzer()
```

#### Methods

##### `generate_stats(data)`

Generate comprehensive statistics for nested data structures.

**Parameters:**

- `data` (Any): Data structure to analyze

**Returns:**

- `dict[str, Any]`: Detailed statistics including:
  - `total_keys` (int): Total number of keys
  - `total_values` (int): Total number of values
  - `data_types` (Counter): Distribution of data types
  - `key_frequency` (Counter): Most common keys
  - `max_depth` (int): Maximum nesting depth
  - `depth_histogram` (Counter): Distribution of depths
  - `value_patterns` (dict): Null counts, empty strings, numeric ranges, etc.
  - `structure_insights` (dict): Repeated structures, array sizes, naming patterns
  - `computed_insights` (dict): Complexity score, uniformity, quality issues

**Example:**

```python
from json_explorer import DataStatsAnalyzer

analyzer = DataStatsAnalyzer()
stats = analyzer.generate_stats(data)

print(f"Total values: {stats['total_values']}")
print(f"Max depth: {stats['max_depth']}")
print(f"Complexity: {stats['computed_insights']['complexity_score']}/100")
print(f"Data types: {stats['data_types']}")
```

##### `print_summary(data, detailed=False)`

Print formatted summary of statistics.

**Parameters:**

- `data` (Any): Data to analyze
- `detailed` (bool): Show detailed breakdown

**Example:**

```python
analyzer.print_summary(data, detailed=True)
# Outputs:
# 📊 Data Structure Analysis Summary
# ========================================
# Total Values: 1,234
# Total Keys: 45
# Max Depth: 5
# Complexity Score: 67/100
# ...
```

#### Statistics Output Structure

```python
# generate_stats(data) for a small document (Counters abbreviated)
{
    "total_keys": 45,
    "total_values": 1234,
    "data_types": Counter({"str": 500, "int": 300, "dict": 100, "bool": 20}),
    "key_frequency": Counter({"id": 10, "name": 10, "email": 8}),
    "max_depth": 5,
    "depth_histogram": Counter({0: 1, 1: 10, 2: 20}),
    "value_patterns": {
        "null_count": 15,
        "empty_strings": 5,
        "empty_collections": 3,
        "numeric_ranges": {"min": 0, "max": 1000},  # booleans are not numbers
        "string_lengths": {"min": 0, "max": 100, "avg": 25.5},
    },
    "structure_insights": {
        "repeated_structures": Counter({("int", "str", "str"): 10}),
        "array_sizes": Counter({5: 10, 10: 5}),
        "key_naming_patterns": Counter({"snake_case": 30, "camelCase": 15}),
    },
    "computed_insights": {
        "complexity_score": 67,
        "most_common_type": ("str", 500),
        "structure_uniformity": "moderately_uniform",
        "data_quality_issues": ["high_null_rate (12.2%)"],
    },
}
```

#### Convenience Function

```python
from json_explorer import generate_stats

stats = generate_stats(data)
```

---

### 4. Visualization Module

Multi-format data visualization with terminal, Plotly, and combined outputs.

#### `JSONVisualizer` Class

Creates visualizations for JSON data statistics in multiple formats.

**Constructor:**

```python
JSONVisualizer()
```

#### Main Method

##### `visualize(data, output="terminal", save_path=None, detailed=False, open_browser=True)`

Create visualizations for JSON data statistics.

**Parameters:**

- `data` (dict | list): JSON data to visualize
- `output` (str): Output format:
  - `"terminal"`: text bar charts in the terminal
  - `"html"`: interactive Plotly report (saved to `save_path` or a temporary file, opened in the browser unless `open_browser=False`)
  - `"all"`: both
- `save_path` (str | Path, optional): Path to save HTML file
- `detailed` (bool): Generate detailed visualizations
- `open_browser` (bool): Auto-open browser for HTML output

**Example:**

```python
from json_explorer import JSONVisualizer

visualizer = JSONVisualizer()

# Terminal visualization
visualizer.visualize(data, output="terminal", detailed=True)

# Interactive HTML
visualizer.visualize(
    data, output="html", save_path="report.html", detailed=True, open_browser=True
)

# Both formats
visualizer.visualize(data, output="all", detailed=True)
```

#### Visualization Types

**Standard Visualizations:**

1. **Data Types Distribution** (Pie chart)
2. **Depth Distribution** (Bar chart)
3. **Quality Metrics** (Horizontal bar chart)

**Detailed Visualizations (when `detailed=True`):**

4. **Key Frequency** (Horizontal bar chart)
5. **Array Sizes** (Scatter plot)
6. **Complexity Gauge** (Gauge chart)

#### Terminal Output

Terminal mode prints text bar charts (data types, depth distribution and, with
`detailed=True`, quality metrics). It works in any terminal, including on Windows.

#### HTML Output (Plotly)

Interactive HTML charts with:

- Hover tooltips
- Zoom and pan
- Export to PNG
- Responsive layout
- Modern color scheme

#### Convenience Function

```python
from json_explorer import visualize_json

visualize_json(data, output="html", save_path="analysis.html", detailed=True)
```

---

### 5. Tree View Module

Rich tree visualization of JSON structures with type annotations and conflict highlighting.

#### Functions

##### `print_json_tree(data, source="JSON", **kwargs)`

Print Rich tree visualization of JSON structure.

**Parameters:**

- `data` (Any): JSON data to visualize
- `source` (str): Name or source for root label
- `**kwargs`: Options for `JsonTreeBuilder`
  - `show_conflicts` (bool): Display conflict information
  - `show_optional` (bool): Display optional annotations

**Example:**

```python
from json_explorer.tree_view import print_json_tree

print_json_tree(data, source="API Response", show_conflicts=True)
```

##### `print_json_analysis(data, source="JSON", show_raw=False)`

Print tree visualization and optionally raw analysis.

**Parameters:**

- `data` (Any): JSON data to analyze
- `source` (str): Name or source
- `show_raw` (bool): Also print raw analysis dictionary

**Example:**

```python
from json_explorer.tree_view import print_json_analysis

print_json_analysis(data, source="Config File", show_raw=True)
```

##### `print_compact_tree(data, source="JSON")`

Print tree without optional/conflict annotations for cleaner view.

**Parameters:**

- `data` (Any): JSON data to visualize
- `source` (str): Name or source

**Example:**

```python
from json_explorer.tree_view import print_compact_tree

print_compact_tree(data, source="Simple View")
```

#### `JsonTreeBuilder` Class

Builds Rich tree visualizations with customizable display options.

**Constructor:**

```python
JsonTreeBuilder(show_conflicts=True, show_optional=True)
```

**Methods:**

- `build_tree(node, parent, name="root")`: Add an `analyze_json()` node (and everything below it)
  to a Rich `Tree`
- `format_label(node, name)`: The label for one node, e.g. `email (string) (nullable)`

Labels show the kind (plus the string format, e.g. `string, date-time`), `(optional)` for keys
missing from some objects, `(nullable)` for values that can be `null`, and the kinds of a
`mixed` value. Colors per kind are in `JsonTreeBuilder.KIND_COLORS`.

---

### 6. Utils Module

Utility functions for loading JSON from files and URLs with validation.

#### Functions

##### `load_json(file_path=None, url=None, timeout=30)`

Load JSON data from either a file or URL.

**Parameters:**

- `file_path` (str | Path, optional): Path to local JSON file
- `url` (str, optional): URL to fetch JSON from
- `timeout` (int): Request timeout in seconds (URLs only)

**Returns:**

- `tuple[str, Any]`: (source_description, parsed_json_data)

**Raises:**

- `JSONLoaderError`: If loading fails
- `FileNotFoundError`: If file doesn't exist

**Example:**

```python
from json_explorer import load_json

# Load from file
source, data = load_json("data.json")

# Load from URL
source, data = load_json(url="https://api.example.com/data")

# With custom timeout
source, data = load_json(url="https://slow-api.com/data", timeout=60)
```

##### `load_json_from_file(file_path)`

Load JSON from a local file.

**Parameters:**

- `file_path` (str | Path): Path to JSON file

**Returns:**

- `tuple[str, Any]`: (source, data)

##### `load_json_from_url(url, timeout=30)`

Load JSON from a URL.

**Parameters:**

- `url` (str): URL to fetch from
- `timeout` (int): Request timeout

**Returns:**

- `tuple[str, Any]`: (source, data)

#### Custom Exception

##### `JSONLoaderError`

Custom exception for JSON loading errors.

```python
from json_explorer.utils import JSONLoaderError

try:
    source, data = load_json("invalid.json")
except JSONLoaderError as e:
    print(f"Failed to load JSON: {e}")
```

### 7. Terminal UI Module

#### `run_tui(data, source="JSON")`

Open the terminal UI (Textual) for already-loaded data and block until the user quits. It needs a
terminal; the CLI checks for one before calling it.

**Parameters:**

- `data` (Any): The JSON data
- `source` (str): Shown in the header and as the root of the data tree

**Returns:**

- `int`: Exit code (0)

```python
from json_explorer.tui import run_tui
from json_explorer.utils import load_json

source, data = load_json("data.json")
run_tui(data, source)
```

See [Terminal UI](#terminal-ui) for the tabs and keys.

---

## JSON Schema Export

`json_explorer.json_schema` turns the analysis into a JSON Schema (draft 2020-12) that describes the
whole document (an array root stays an array).

#### `json_schema(data, title=None)`

Analyze `data` and return its schema as a dict.

#### `to_json_schema(node, title=None)`

Schema for an existing `analyze_json()` result.

**What the schema says:**

- keys present in every object are `required`; a value seen as `null` allows `"null"`
- integers merged with floats are `"number"`; mixed values list every type
- `format` is set for `date-time`, `date` and `duration` strings; times and date-times without a
  UTC offset (which JSON Schema's `time`/`date-time` formats require) get a `description` instead
- additional properties stay allowed: a sample shows which keys exist, not which may never appear

```python
from json_explorer import json_schema

json_schema([{"id": 1, "email": None}, {"id": 2, "email": "a@b.c"}], title="Users")
# {'$schema': 'https://json-schema.org/draft/2020-12/schema', 'title': 'Users',
#  'type': 'array', 'items': {'type': 'object',
#   'properties': {'id': {'type': 'integer'}, 'email': {'type': ['string', 'null']}},
#   'required': ['id', 'email']}}
```

```bash
json_explorer data.json --json-schema > data.schema.json
```

---

## Code Generation

The codegen module provides multi-language code generation from JSON schemas with extensible architecture.

### 1. Core Generator Interface

#### `CodeGenerator` (abstract base class)

Base class for language generators (`json_explorer.codegen.core`).

**Class attributes:**

- `language_name` (str): e.g. `"go"`
- `file_extension` (str): e.g. `".go"`
- `template_dir` (Path): directory with the generator's Jinja2 templates

**Abstract method:**

- `generate(schemas, root_schema_name) -> str`: the source code for all schemas

**Provided:** `render_template(name, context)`, `dependency_order(schemas)` (nested types
first), `validate_schemas(schemas)` (warnings), `format_code(code)`.

Per-run state (names, imports) belongs in `generate()`'s locals, so a generator instance can be
reused. Use `plan_names()` (`json_explorer.codegen.core.naming`) to give every type and field its
identifier once.

**Example:**

```python
from pathlib import Path

from json_explorer.codegen.core import CodeGenerator


class MyGenerator(CodeGenerator):
    language_name = "mylang"
    file_extension = ".ml"
    template_dir = Path(__file__).parent / "templates"

    def generate(self, schemas, root_schema_name):
        return self.render_template("file.ml.j2", {"schemas": list(schemas.values())})
```

---

### 2. Registry and Plugins

Each language is a `LanguagePlugin`: its generator, aliases, CLI flags
(`CliOption`) and usage examples. Built-in plugins are registered on first use; other packages can
provide one through the `json_explorer.languages` entry-point group.

```python
from json_explorer.codegen import (
    CliOption,
    LanguagePlugin,
    create_generator,
    get_language_info,
    is_supported,
    list_languages,
    register,
)

list_languages()  # ['go', 'python']
is_supported("golang")  # True (alias)
get_language_info("py")
# {'name': 'python', 'class': 'PythonGenerator', 'file_extension': '.py',
#  'aliases': ['py'], 'module': 'json_explorer.codegen.languages.python.generator'}

generator = create_generator("go", {"use_pointers_for_optional": False})

# Registering a language
register(
    LanguagePlugin(
        name="mylang",
        generator=MyGenerator,
        aliases=("ml",),
        cli_options=(CliOption("--ml-strict", "strict", "Strict mode"),),
        examples=(("Generate", "--generate mylang"),),
    )
)
```

`create_generator(language, config)` accepts a `GeneratorConfig`, an options dict, a path to a JSON
config file, or `None` (defaults). Unknown or invalid options raise `ConfigError` with the valid
choices. Unknown languages raise `RegistryError`.

---

### 3. High-Level API

#### `generate_from_analysis(analyzer_result, language="go", config=None, root_name="Root")`

Generate code from analyzer output.

**Parameters:**

- `analyzer_result` (dict): Output from `analyze_json()`
- `language` (str): Target language ("go", "python")
- `config` (GeneratorConfig | dict | str, optional): Configuration
- `root_name` (str): Name for root schema

**Returns:**

- `GenerationResult`: Generated code and metadata

**Example:**

```python
from json_explorer import analyze_json
from json_explorer.codegen import generate_from_analysis, create_config

data = {"user_id": 123, "name": "Alice"}
analysis = analyze_json(data)

config = create_config(language="go", package_name="models", add_comments=True)

result = generate_from_analysis(analysis, "go", config, "User")

if result.success:
    print(result.code)
    if result.warnings:
        for warning in result.warnings:
            print(f"Warning: {warning}")
else:
    print(f"Error: {result.error_message}")
```

#### `quick_generate(json_data, language="go", **options)`

Quick code generation from JSON data in one call.

**Parameters:**

- `json_data` (dict | list): JSON data
- `language` (str): Target language
- `**options`: Configuration options as keyword arguments

**Returns:**

- `str`: Generated code

**Example:**

```python
from json_explorer.codegen import quick_generate

data = {"user_id": 123, "name": "Alice", "tags": ["python", "coding"]}

# Generate Go
go_code = quick_generate(data, language="go", package_name="models", root_name="User")

# Generate Python dataclass
python_code = quick_generate(
    data, language="python", style="dataclass", package_name="models"
)

# Generate Pydantic model
pydantic_code = quick_generate(
    data,
    language="python",
    style="pydantic",
)
```

#### `create_config(language, **options)`

Create a configuration object.

**Parameters:**

- `language` (str): Target language
- `**options`: Configuration options

**Returns:**

- `GeneratorConfig`: Configuration object

#### `load_config(config_file=None, custom_config=None)`

Build a configuration from the defaults, a JSON config file, and overrides (later wins).

**Parameters:**

- `config_file` (str | Path, optional): Path to a JSON config file
- `custom_config` (dict, optional): Options that override the file

Unknown or invalid options raise `ConfigError`; options removed in 0.5.0 are ignored with a warning.

**Returns:**

- `GeneratorConfig`: Configuration object

---

### 4. Go Generator

Specialized Go struct generation with JSON tags and pointer handling.

#### Features

- Exported PascalCase fields; `json` tags with the original keys (keys Go can't express as a tag
  are left out with a comment)
- Pointers for optional fields (`use_pointers_for_optional`), `omitempty` (`json_tag_omitempty`)
- Configurable `int_type` (`int`, `int32`, `int64`), `float_type` (`float32`, `float64`) and
  `time_type` (`time.Time` or `string`, for RFC 3339 date-times)
- `any` for unknown or mixed values; imports added as needed; gofmt-clean output

#### Configuration Options

```python
from json_explorer.codegen import GeneratorConfig

config = GeneratorConfig(
    package_name="models",
    json_tag_omitempty=True,
    add_comments=True,
    language_config={
        "use_pointers_for_optional": True,
        "int_type": "int64",  # "int", "int64", "int32"
        "float_type": "float64",  # "float64", "float32"
        "time_type": "time.Time",  # or "string"
    },
)
```

#### Creating generators

```python
from json_explorer.codegen import create_generator

# Defaults: pointers for optional fields, omitempty
generator = create_generator("go")

# Value types only, no omitempty
strict_generator = create_generator(
    "go", {"json_tag_omitempty": False, "use_pointers_for_optional": False}
)
```

#### Pointer Handling

The Go generator intelligently handles pointers:

**Add pointer when:**

- Field is optional primitive type AND `use_pointers_for_optional=True`

```go
Email *string `json:"email,omitempty"`
Age   *int64  `json:"age,omitempty"`
```

**Never add pointer for:**

- `any` (already accepts nil)
- Arrays/slices
- Non-optional fields

```go
UnknownField any `json:"unknown_field"`  // No pointer
Tags         []string    `json:"tags"`            // No pointer
Name         string      `json:"name"`            // Required, no pointer
```

#### Example Output

For this input (`--root-name User --package-name models`):

```json
[
  {"userId": 1, "name": "Alice", "email": null, "tags": ["admin"]},
  {"userId": 2, "name": "Bob", "email": "bob@example.com", "tags": []}
]
```

```go
// Code generated by json_explorer. DO NOT EDIT.

package models

type User struct {
	UserId int64    `json:"userId"`
	Name   string   `json:"name"`
	Email  *string  `json:"email,omitempty"`
	Tags   []string `json:"tags"`
}
```

---

### 5. Python Generator

Specialized Python code generation with multiple styles and modern type hints.

#### Supported Styles

1. **Dataclass**: Standard Python dataclasses with slots
2. **Pydantic**: Pydantic v2 models with validation
3. **TypedDict**: Typed dictionaries for type checking

#### Configuration Options

```python
from json_explorer.codegen import GeneratorConfig

# Dataclass configuration
dataclass_config = GeneratorConfig(
    package_name="models",
    add_comments=True,
    language_config={
        "style": "dataclass",
        "dataclass_slots": True,
        "dataclass_frozen": False,
        "dataclass_kw_only": True,
    },
)

# Pydantic configuration
pydantic_config = GeneratorConfig(
    package_name="models",
    add_comments=True,
    language_config={
        "style": "pydantic",
        "pydantic_config_dict": True,
        "pydantic_extra_forbid": False,
    },
)

# TypedDict configuration
typeddict_config = GeneratorConfig(
    package_name="types",
    add_comments=True,
    language_config={
        "style": "typeddict",
    },
)
```

#### Creating generators

```python
from json_explorer.codegen import create_generator

dc_generator = create_generator(
    "python", {"style": "dataclass", "dataclass_frozen": True}
)
pydantic_generator = create_generator("python", {"style": "pydantic"})
td_generator = create_generator("python", {"style": "typeddict"})
```

#### Field Case Convention

Python generator defaults to Python conventions:

- **Class names**: PascalCase
- **Field names**: snake_case

```python
# Input: {"userId": 1, "userName": "Alice"}

# Generated output:
# Code generated by json_explorer. DO NOT EDIT.
"""Generated dataclasses from JSON schema."""

from dataclasses import dataclass


@dataclass(slots=True, kw_only=True)
class Root:
    user_id: int
    user_name: str
```

#### Pydantic Field() Usage

`Field()` is generated only when needed:

**Generated when:**

- Alias needed (field name differs from JSON key)
- Has description
- Optional field with default

```python
user_id: int = Field(alias="userId")
name: str = Field(description="User's full name")
email: str | None = Field(default=None)
```

**Not generated when:**

- Field matches all defaults

```python
user_id: int  # No Field() needed
```

#### Example Outputs

For the same input as the Go example:

**Dataclass** (keyword-only; dataclasses don't parse values, so formatted strings stay `str`):

```python
# Code generated by json_explorer. DO NOT EDIT.
"""Generated dataclasses from JSON schema."""

from dataclasses import dataclass


@dataclass(slots=True, kw_only=True)
class User:
    user_id: int
    name: str
    email: str | None = None
    tags: list[str]
```

**Pydantic** (aliases map fields to JSON keys):

```python
# Code generated by json_explorer. DO NOT EDIT.
"""Generated Pydantic models from JSON schema."""

from pydantic import BaseModel, Field, ConfigDict


class User(BaseModel):
    model_config = ConfigDict(
        extra="ignore",
        populate_by_name=True,
    )
    user_id: int = Field(alias="userId")
    name: str
    email: str | None = Field(default=None)
    tags: list[str]
```

**TypedDict** (original keys; `| None` for null values, `NotRequired` for keys that can be missing):

```python
# Code generated by json_explorer. DO NOT EDIT.
"""Generated TypedDict classes from JSON schema."""

from typing import TypedDict


class User(TypedDict):
    userId: int
    name: str
    email: str | None
    tags: list[str]
```

---

### 6. TypeScript Generator

Interfaces (default) or Zod 4 schemas with inferred types (`--ts-style zod`,
`{"style": "zod"}`).

#### Features

- Keys stay exactly as in the JSON; keys that aren't identifiers are quoted
- A key that can be missing is `key?: T` (Zod: `.optional()`); a value that can be `null` is
  `T | null` (Zod: `.nullable()`)
- Mixed values become unions (`number | string`; Zod: `z.union([...])`)
- Date/time strings stay `string` in interfaces (`JSON.parse` doesn't convert them) with a doc
  comment; Zod validates them: `z.iso.datetime({ offset: true })`, `z.iso.datetime({ local: true })`,
  `z.iso.date()`, `z.iso.duration()` (times stay `z.string()`: `z.iso.time()` rejects offsets)
- Integers are `z.number().int()` in Zod
- Output is Prettier-formatted (long lines are not wrapped)

```python
from json_explorer.codegen import quick_generate

data = [{"id": 1, "email": None, "nick": "a"}, {"id": 2, "email": "b@x.io"}]
quick_generate(data, "typescript")
# export interface Root {
#   id: number;
#   email: string | null;
#   nick?: string;
# }
quick_generate(data, "typescript", style="zod")
# export const Root = z.object({
#   id: z.number().int(),
#   email: z.string().nullable(),
#   nick: z.string().optional(),
# });
# export type Root = z.infer<typeof Root>;
```

### 7. Rust Generator

Structs with serde derives (`--generate rust`, alias `rs`). Add `serde` (with the `derive` feature)
and, when mixed or unknown values occur, `serde_json` to your crate.

#### Features

- Fields are ASCII snake_case; `#[serde(rename = "...")]` keeps the JSON key when it differs
- Keywords become raw identifiers (`r#type`); `self`, `super` and `crate` get a `_` suffix
- A key that can be missing or a value that can be `null` is `Option<T>`; keys that can be missing
  are also skipped when serializing `None`, so serializing reproduces the input's shape
- Mixed and unknown values are `serde_json::Value`; nullable array elements are `Vec<Option<T>>`
- Date/time strings stay `String`, with a doc comment naming the format
- `--rust-deny-unknown` / `{"deny_unknown_fields": true}` adds `#[serde(deny_unknown_fields)]`
- Output is rustfmt-clean

For `[{"userId": 1, "email": null, "type": "admin", "nick": "a"}, {"userId": 2, "email": "b@x.io", "type": "user"}]`:

```rust
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Root {
    #[serde(rename = "userId")]
    pub user_id: i64,
    pub email: Option<String>,
    pub r#type: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub nick: Option<String>,
}
```

### 8. Schema System

Internal schema representation for code generation.

#### `Schema` Class

Represents a data structure schema.

**Attributes:**

- `name` (str): Type name (unique within one run)
- `original_name` (str): The name it was derived from
- `fields` (list[Field]): List of fields
- `description` (str, optional): Schema description

**Methods:**

- `add_field(field)`: Add a field to schema

#### `Field` Class

Represents an individual field in a schema.

**Attributes:**

- `name` / `original_name` (str): The JSON key
- `type` (FieldType): Field type
- `optional` (bool): Missing from some objects or `null` somewhere
- `missing` (bool) / `nullable` (bool): The two cases separately (TypedDict uses them)
- `description` (str, optional): Note for unknown or mixed types
- `nested_schema` (Schema, optional): For object types
- `array_element_type` (FieldType, optional) / `array_element_schema` (Schema, optional): The
  innermost array element
- `array_dimensions` (int): 1 for `list[T]`, 2 for `list[list[T]]`, ...
- `array_element_nullable` (bool): `null` seen among the elements
- `conflicting_types` (list[FieldType]): For `CONFLICT`

#### `FieldType` Enum

Supported field types:

- `STRING`: String values
- `INTEGER`: Integer numbers
- `FLOAT`: Floating-point numbers
- `BOOLEAN`: Boolean values
- `DATE_TIME`, `LOCAL_DATE_TIME`, `DATE`, `TIME`, `DURATION`: strings in a standard format
- `OBJECT`: Nested objects
- `ARRAY`: Arrays/lists
- `UNKNOWN`: Unknown type (null only)
- `CONFLICT`: Multiple conflicting types

**Example:**

```python
from json_explorer.codegen.core.schema import Schema, Field, FieldType

# Usually built from data: convert_analyzer_output(analyze_json(data), "User")
user_schema = Schema(name="User", original_name="User", description="User data")

user_schema.add_field(
    Field(name="user_id", original_name="user_id", type=FieldType.INTEGER)
)
user_schema.add_field(
    Field(name="email", original_name="email", type=FieldType.STRING, optional=True)
)
user_schema.add_field(
    Field(
        name="tags",
        original_name="tags",
        type=FieldType.ARRAY,
        array_element_type=FieldType.STRING,
    )
)
```

---

## CLI Usage

### Basic Commands

```bash
# Terminal UI (the default when no action is given)
json_explorer data.json

# Tree visualization
json_explorer data.json --tree compact

# Statistics
json_explorer data.json --stats --detailed

# Visualizations
json_explorer data.json --plot --plot-format html
```

### Terminal UI

`json_explorer data.json` (or `--interactive`) opens a full-screen terminal UI with five tabs:

| Tab | Key | Shows |
|---|---|---|
| Data | `1` | The document as a tree; large containers expand on demand |
| Structure | `2` | The inferred types: optional keys, nullable values, formats, mixed kinds |
| Search | `3` | JMESPath queries, checked as you type, with the result as JSON and examples |
| Statistics | `4` | Size, depth, complexity and quality issues; opens the HTML report |
| Code | `5` | Every language and JSON Schema with a live preview; options come from each language's flags |

Other keys: `/` search, `Esc` leave a text box, `Ctrl+S` save the generated code, `Ctrl+Y` copy it,
`q` quit.
The UI needs a terminal; in scripts and pipes use the flags below.

### JMESPath Search

```bash
# Basic queries
json_explorer data.json --search "users[*].name"
json_explorer data.json --search "users[0]"

# Filtering
json_explorer data.json --search "users[?age > \`30\`]"
json_explorer data.json --search "users[?active == \`true\`]"

# Functions
json_explorer data.json --search "length(users)"
json_explorer data.json --search "sort_by(users, &age)"

# Display options
json_explorer data.json --search "users[*].name" --tree-results
json_explorer --show-examples
```

### Code Generation

```bash
# List languages
json_explorer --list-languages

# Language info
json_explorer --language-info go
json_explorer --language-info python

# Generate Go
json_explorer data.json --generate go --output models.go \
  --package-name models --root-name User

# Generate Python dataclass
json_explorer data.json --generate python --output models.py \
  --package-name models

# Generate Pydantic
json_explorer data.json --generate python \
  --python-style pydantic --output models.py

# With configuration file
json_explorer data.json --generate go --config config.json
```

---

## Examples

### 1. Complete Analysis Workflow

```python
from json_explorer import (
    DataStatsAnalyzer,
    JSONVisualizer,
    JsonSearcher,
    analyze_json,
    load_json,
)
from json_explorer.codegen import quick_generate

# Load data
source, data = load_json("data.json")

# Analyze structure
analysis = analyze_json(data)
print(f"Analysis complete: {analysis.kind}")

# JMESPath search
searcher = JsonSearcher()
emails = searcher.search(data, "users[*].email")
searcher.print_result(emails)

# Statistics
analyzer = DataStatsAnalyzer()
analyzer.print_summary(data, detailed=True)

# Visualizations
visualizer = JSONVisualizer()
visualizer.visualize(data, output="html", detailed=True)

# Generate code
go_code = quick_generate(data, "go", package_name="models")
python_code = quick_generate(data, "python", style="pydantic")
```

### 2. Advanced JMESPath Queries

```python
from json_explorer import JsonSearcher

data = {
    "users": [
        {"id": 1, "name": "Alice", "age": 30, "active": True},
        {"id": 2, "name": "Bob", "age": 25, "active": False},
        {"id": 3, "name": "Charlie", "age": 35, "active": True},
    ]
}

searcher = JsonSearcher()

# Complex filtering
result = searcher.search(
    data, "users[?age > `25` && active == `true`].{name: name, age: age}"
)

# Sorting and selection
result = searcher.search(data, "sort_by(users, &age)[-1].name")

# Aggregations
result = searcher.search(data, "length(users[?active == `true`])")

# Several queries
queries = ["users[*].name", "max_by(users, &age).name", "length(users)"]
results = {q: searcher.search(data, q) for q in queries}
```

### 3. Custom Go Generation

```python
from json_explorer import analyze_json
from json_explorer.codegen import GeneratorConfig, generate_from_analysis

data = {"user_profile": {"name": "Alice", "settings": {"theme": "dark"}}}

analysis = analyze_json(data)

config = GeneratorConfig(
    package_name="api",
    json_tag_omitempty=True,
    add_comments=True,
    language_config={"use_pointers_for_optional": True, "int_type": "int64"},
)

result = generate_from_analysis(analysis, "go", config, "UserProfile")

if result.success:
    print(result.code)
    if result.warnings:
        for w in result.warnings:
            print(f"Warning: {w}")
```

### 4. Multiple Python Styles

```python
from json_explorer import analyze_json
from json_explorer.codegen import GeneratorConfig, generate_from_analysis

data = {"user_id": 123, "name": "Alice", "email": None, "tags": ["python"]}

analysis = analyze_json(data)

# Dataclass
dc_config = GeneratorConfig(
    package_name="models",
    language_config={"style": "dataclass", "dataclass_slots": True},
)
dc_result = generate_from_analysis(analysis, "python", dc_config, "User")

# Pydantic
pydantic_config = GeneratorConfig(
    package_name="models",
    language_config={"style": "pydantic", "pydantic_config_dict": True},
)
pydantic_result = generate_from_analysis(analysis, "python", pydantic_config, "User")

# TypedDict
td_config = GeneratorConfig(
    package_name="types", language_config={"style": "typeddict"}
)
td_result = generate_from_analysis(analysis, "python", td_config, "User")
```

### 5. Handling Optional Fields

```python
from json_explorer.codegen import quick_generate

data = [
    {"name": "John", "email": None, "age": 30},
    {"name": "Jane", "email": "jane@example.com", "age": 25},
]

# Go with pointers
go_code = quick_generate(data, language="go")
# Output:
# type Root struct {
#     Name  string  `json:"name"`
#     Email *string `json:"email,omitempty"` // Optional
#     Age   int64   `json:"age"`
# }

# Python with None defaults
python_code = quick_generate(data, language="python")
# Output:
# @dataclass(slots=True, kw_only=True)
# class Root:
#     name: str
#     email: str | None = None  # Optional
#     age: int
```

---

## Configuration Best Practices

### Language-Specific Defaults

**Go:**

- Type and field names: PascalCase (fields must be exported)
- `use_pointers_for_optional`: true

**Python:**

- Class names: PascalCase; field names: snake_case
- `dataclass_slots`: true

### Recommended Configurations

**REST APIs (Go):**

```json
{
  "package_name": "api",
  "language_config": {
    "use_pointers_for_optional": true,
    "int_type": "int64"
  },
  "json_tag_omitempty": true
}
```

**Data Validation (Python Pydantic):**

```json
{
  "package_name": "models",
  "language_config": {
    "style": "pydantic",
    "pydantic_extra_forbid": true
  }
}
```

---

## Error Handling

### Common Exceptions

All derive from `JsonExplorerError` (`from json_explorer import JsonExplorerError`):

- `JSONLoaderError`: JSON loading/parsing errors
- `GeneratorError`: Code generation errors
- `RegistryError`: Unknown language or invalid plugin registration
- `TemplateError`: Template rendering errors
- `ConfigError`: Unknown or invalid configuration options
- `CLIError`: Command-line errors (e.g. an unreadable config file)

### Best Practices

```python
from json_explorer import load_json
from json_explorer.codegen import generate_from_analysis
from json_explorer.utils import JSONLoaderError
from json_explorer.codegen import load_config
from json_explorer.codegen.core import ConfigError

# Handle file loading
try:
    source, data = load_json("data.json")
except FileNotFoundError:
    print("File not found")
except JSONLoaderError as e:
    print(f"JSON error: {e}")

# Check generation results
result = generate_from_analysis(analysis, "go", config)
if not result.success:
    print(f"Generation failed: {result.error_message}")
    if result.exception:
        raise result.exception

# Validate configurations
try:
    config = load_config("config.json")
except ConfigError as e:
    print(f"Config error: {e}")
```

---

## Additional Resources

- **GitHub**: [https://github.com/MS-32154/py-json-analyzer](https://github.com/MS-32154/py-json-analyzer)
- **PyPI**: [https://pypi.org/project/py-json-analyzer/](https://pypi.org/project/py-json-analyzer/)
- **JMESPath**: [https://jmespath.org/](https://jmespath.org/)

---

**JSON Explorer** – © 2025 MS-32154. All rights reserved.
