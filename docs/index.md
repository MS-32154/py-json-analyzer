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
- [Code Generation](#code-generation)
  - [Core Generator Interface](#1-core-generator-interface)
  - [Registry System](#2-registry-system)
  - [High-Level API](#3-high-level-api)
  - [Go Generator](#4-go-generator)
  - [Python Generator](#5-python-generator)
  - [Schema System](#6-schema-system)
  - [Interactive Handler](#7-interactive-handler)
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
- **Multi-Format Visualization**: Terminal (curses/ASCII), interactive HTML (Plotly), or combined
- **Code Generation**: Generate Go structs, Python dataclasses/Pydantic/TypedDict from JSON
- **Interactive Mode**: Full-featured terminal UI for exploration and configuration
- **Extensible Architecture**: Plugin-based generator system for custom languages

---

## Core Modules

### 1. Analyzer Module

The analyzer module performs deep structural analysis of JSON data with intelligent type detection and conflict resolution.

#### `analyze_json(data)`

Analyzes JSON structure and returns detailed metadata including types, optional fields, and conflicts.

**Parameters:**

- `data (dict|list|Any)`: JSON data to analyze

**Returns:**

- `dict`: Analysis summary with structure, types, and conflicts

**Return Structure:**

```python
{
    "type": "object",           # Root type: "object", "list", or primitive
    "children": {               # For objects: field definitions
        "field_name": {
            "type": "str",      # Field type
            "optional": False,  # Whether field is optional
            "conflicts": {}     # Type conflicts if any
        }
    },
    "conflicts": {              # Top-level conflicts
        "field_name": ["str", "int"]
    }
}
```

**Example:**

```python
from json_explorer import analyze_json

data = {
    "users": [
        {"id": 1, "name": "Alice", "email": "alice@example.com"},
        {"id": 2, "name": "Bob"}  # email missing
    ]
}

analysis = analyze_json(data)
print(analysis)
# {
#     "type": "object",
#     "children": {
#         "users": {
#             "type": "list",
#             "child": {
#                 "type": "object",
#                 "children": {
#                     "id": {"type": "int", "optional": False},
#                     "name": {"type": "str", "optional": False},
#                     "email": {"type": "str", "optional": True}
#                 }
#             }
#         }
#     }
# }
```

#### Optional Field Detection

Fields are marked as optional when:

1. **Missing from some objects**:

   ```python
   [{"name": "Alice"}, {"name": "Bob", "age": 30}]
   # age is optional
   ```

2. **Contains None values**:
   ```python
   [{"name": "Alice", "email": None}, {"name": "Bob", "email": "bob@example.com"}]
   # email is optional
   ```

#### Type Conflict Resolution

The analyzer intelligently handles mixed types:

- **None + Single Type** → Optional field

  ```python
  [{"value": None}, {"value": 42}]
  # Result: value: int (optional)
  ```

- **None + Multiple Types** → Conflict (uses `Any`/`interface{}`)

  ```python
  [{"value": None}, {"value": 42}, {"value": "text"}]
  # Result: value: conflict (int, str)
  ```

- **Multiple Non-None Types** → Conflict
  ```python
  [{"value": 42}, {"value": "text"}]
  # Result: value: conflict (int, str)
  ```

#### Timestamp Detection

The analyzer automatically detects timestamp strings:

```python
from json_explorer.analyzer import detect_timestamp

detect_timestamp("2024-01-01T12:00:00Z")  # True
detect_timestamp("2024-01-01")  # True
detect_timestamp("not a date")  # False
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

##### `search(data, query, compile_query=False)`

Execute a JMESPath query on JSON data.

**Parameters:**

- `data` (Any): JSON data to search
- `query` (str): JMESPath query expression
- `compile_query` (bool): Compile query for reuse (performance optimization)

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

##### `search_multiple(data, queries)`

Execute multiple JMESPath queries efficiently.

**Parameters:**

- `data` (Any): JSON data to search
- `queries` (list[str]): List of JMESPath query expressions

**Returns:**

- `dict[str, SearchResult]`: Mapping of query strings to results

**Example:**

```python
queries = [
    "users[*].name",
    "users[?age > `30`]",
    "length(users)",
    "max_by(users, &age).name"
]
results = searcher.search_multiple(data, queries)

for query, result in results.items():
    print(f"Query: {query}")
    searcher.print_result(result)
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
"users"                              # Get users array
"users[0]"                          # First user
"users[-1]"                         # Last user
"users[*].name"                     # All user names

# Filtering
"users[?age > `30`]"                # Filter by age
"users[?active == `true`]"          # Filter by boolean
"users[?age > `30` && active == `true`]"  # Multiple conditions

# Projections (field selection)
"users[*].{name: name, email: email}"     # Select specific fields
"users[?age > `30`].name"                 # Filter then project

# Functions
"length(users)"                     # Count items
"sort_by(users, &age)"              # Sort by field
"max_by(users, &age)"               # Item with max value
"min_by(users, &score)"             # Item with min value
"contains(name, 'John')"            # Check if contains

# Nested access
"user.profile.settings.theme"       # Deep nested access
"users[*].tags[]"                   # Flatten nested arrays

# Slicing
"users[0:3]"                        # First 3 users
"users[-2:]"                        # Last 2 users
"users[::2]"                        # Every other user
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
{
    "total_keys": 45,
    "total_values": 1234,
    "data_types": Counter({"str": 500, "int": 300, "dict": 100, ...}),
    "key_frequency": Counter({"id": 10, "name": 10, "email": 8, ...}),
    "max_depth": 5,
    "depth_histogram": Counter({0: 1, 1: 10, 2: 20, ...}),
    "value_patterns": {
        "null_count": 15,
        "empty_strings": 5,
        "empty_collections": 3,
        "numeric_ranges": {"min": 0, "max": 1000},
        "string_lengths": {"min": 0, "max": 100, "avg": 25.5}
    },
    "structure_insights": {
        "repeated_structures": Counter({...}),
        "array_sizes": Counter({5: 10, 10: 5, ...}),
        "key_naming_patterns": Counter({"snake_case": 30, "camelCase": 15})
    },
    "computed_insights": {
        "complexity_score": 67,
        "most_common_type": ("str", 500),
        "structure_uniformity": "moderately_uniform",
        "data_quality_issues": ["high_null_rate (12.2%)"]
    }
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
  - `"terminal"`: ASCII/curses visualization
  - `"html"`: Interactive Plotly charts saved to file
  - `"interactive"`: Same as "html" (legacy alias)
  - `"all"`: Both terminal and HTML
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
    data,
    output="html",
    save_path="report.html",
    detailed=True,
    open_browser=True
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

Terminal mode uses:

- **curses** (when available): Interactive, paginated display with navigation
- **ASCII fallback**: Static ASCII bar charts when curses unavailable

**Terminal Controls:**

- `SPACE`: Next page
- `q`: Quit

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

visualize_json(
    data,
    output="html",
    save_path="analysis.html",
    detailed=True
)
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
from json_explorer import print_json_analysis

print_json_analysis(data, source="Config File", show_raw=True)
```

##### `print_compact_tree(data, source="JSON")`

Print tree without optional/conflict annotations for cleaner view.

**Parameters:**

- `data` (Any): JSON data to visualize
- `source` (str): Name or source

**Example:**

```python
from json_explorer import print_compact_tree

print_compact_tree(data, source="Simple View")
```

#### `JsonTreeBuilder` Class

Builds Rich tree visualizations with customizable display options.

**Constructor:**

```python
JsonTreeBuilder(show_conflicts=True, show_optional=True)
```

**Methods:**

- `build_tree(summary, parent_tree, name="root")`: Recursively build tree from analysis

**Type Colors:**

- `object`: bold blue
- `list`: bold magenta
- `str`: green
- `int`/`float`: dark orange
- `bool`: yellow
- `NoneType`: dim white
- `conflict`: bold red

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

#### Interactive Input Functions

##### `prompt_input(message, default=None, **kwargs)`

User-friendly input with optional choices and autocompletion.

**Parameters:**

- `message` (str): Prompt message
- `default` (str, optional): Default value
- `choices` (list, optional): Valid choices for autocompletion
- `console` (Console, optional): Rich console instance

**Example:**

```python
from json_explorer.utils import prompt_input

language = prompt_input(
    "Select language",
    choices=["go", "python", "typescript"],
    default="go"
)
```

##### `prompt_input_path(message, **kwargs)`

Input for file paths with autocompletion.

**Parameters:**

- `message` (str): Prompt message
- `default` (str): Default path

**Example:**

```python
from json_explorer.utils import prompt_input_path

filepath = prompt_input_path("Enter JSON file path", default="data.json")
```

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

---

## Code Generation

The codegen module provides multi-language code generation from JSON schemas with extensible architecture.

### 1. Core Generator Interface

#### `CodeGenerator` (Abstract Base Class)

Base class for all language generators.

**Abstract Properties:**

- `language_name` (str): Language name (e.g., "go", "python")
- `file_extension` (str): File extension (e.g., ".go", ".py")

**Abstract Methods:**

- `generate(schemas, root_schema_name)`: Generate code for schemas

**Example Implementation:**

```python
from json_explorer.codegen.core import CodeGenerator, GenerationResult

class MyGenerator(CodeGenerator):
    @property
    def language_name(self) -> str:
        return "mylang"

    @property
    def file_extension(self) -> str:
        return ".ml"

    def generate(self, schemas, root_schema_name):
        # Implementation
        code = "..."
        return GenerationResult(
            success=True,
            code=code,
            language="mylang"
        )
```

---

### 2. Registry System

#### `GeneratorRegistry` Class

Manages registration and retrieval of code generators.

##### Class Methods

**`register(language, generator_class, aliases=None)`**

Register a generator class.

**Parameters:**

- `language` (str): Primary language name
- `generator_class` (type): Generator class
- `aliases` (list[str], optional): Alternative names

**`create_generator(language, config=None)`**

Create a generator instance.

**Parameters:**

- `language` (str): Language name or alias
- `config` (GeneratorConfig | dict, optional): Configuration

**Returns:**

- `CodeGenerator`: Generator instance

**`list_languages()`**

Get list of supported languages.

**Returns:**

- `list[str]`: Language names

**`get_generator_info(language)`**

Get information about a generator.

**Returns:**

- `dict`: Generator metadata

#### Global Registry Functions

```python
from json_explorer.codegen import (
    register,
    get_generator,
    list_supported_languages,
    get_language_info
)

# List available languages
languages = list_supported_languages()
print(languages)  # ['go', 'python']

# Get generator
generator = get_generator("go", config)

# Get language info
info = get_language_info("python")
print(info)
# {
#     'name': 'python',
#     'description': 'Python code generator',
#     'styles': ['dataclass', 'pydantic', 'typeddict'],
#     ...
# }
```

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

config = create_config(
    language="go",
    package_name="models",
    add_comments=True
)

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
go_code = quick_generate(
    data,
    language="go",
    package_name="models",
    root_name="User"
)

# Generate Python dataclass
python_code = quick_generate(
    data,
    language="python",
    style="dataclass",
    package_name="models"
)

# Generate Pydantic model
pydantic_code = quick_generate(
    data,
    language="python",
    style="pydantic",
    pydantic_use_field=True
)
```

#### `create_config(language, **options)`

Create a configuration object.

**Parameters:**

- `language` (str): Target language
- `**options`: Configuration options

**Returns:**

- `GeneratorConfig`: Configuration object

#### `load_config(path)`

Load configuration from JSON file.

**Parameters:**

- `path` (str | Path): Path to config file

**Returns:**

- `GeneratorConfig`: Configuration object

---

### 4. Go Generator

Specialized Go struct generation with JSON tags and pointer handling.

#### Features

- Configurable type mappings (`int`, `int64`, `float64`, etc.)
- Smart pointer usage for optional fields
- JSON tag generation with customizable cases
- Package and import management
- Naming convention handling (PascalCase, camelCase, snake_case)
- Conflict resolution with `interface{}`

#### Configuration Options

```python
from json_explorer.codegen import GeneratorConfig

config = GeneratorConfig(
    package_name="models",
    generate_json_tags=True,
    json_tag_omitempty=True,
    json_tag_case="snake",  # "original", "snake", "camel"
    add_comments=True,
    struct_case="pascal",
    field_case="pascal",
    language_config={
        "use_pointers_for_optional": True,
        "int_type": "int64",      # "int", "int64", "int32"
        "float_type": "float64"   # "float64", "float32"
    }
)
```

#### Factory Functions

```python
from json_explorer.codegen.languages.go import (
    create_go_generator,
    create_web_api_generator,
    create_strict_generator
)

# Default Go generator
generator = create_go_generator()

# Optimized for web APIs (pointers, omitempty)
api_generator = create_web_api_generator()

# Strict types (no pointers)
strict_generator = create_strict_generator()
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

- `interface{}` or `any` (already accepts nil)
- Arrays/slices
- Non-optional fields

```go
UnknownField interface{} `json:"unknown_field"`  // No pointer
Tags         []string    `json:"tags"`            // No pointer
Name         string      `json:"name"`            // Required, no pointer
```

#### Example Output

```go
package models

// User represents the root data structure
type User struct {
    UserID int64    `json:"user_id"`
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
    struct_case="pascal",
    field_case="snake",  # Python convention
    language_config={
        "style": "dataclass",
        "dataclass_slots": True,
        "dataclass_frozen": False,
        "dataclass_kw_only": False,
        "use_optional": True
    }
)

# Pydantic configuration
pydantic_config = GeneratorConfig(
    package_name="models",
    add_comments=True,
    struct_case="pascal",
    field_case="snake",
    language_config={
        "style": "pydantic",
        "pydantic_use_field": True,
        "pydantic_use_alias": True,
        "pydantic_config_dict": True,
        "pydantic_extra_forbid": False,
        "use_optional": True
    }
)

# TypedDict configuration
typeddict_config = GeneratorConfig(
    package_name="types",
    add_comments=True,
    struct_case="pascal",
    field_case="snake",
    language_config={
        "style": "typeddict",
        "typeddict_total": False,
        "use_optional": True
    }
)
```

#### Factory Functions

```python
from json_explorer.codegen.languages.python import (
    create_python_generator,
    create_dataclass_generator,
    create_pydantic_generator,
    create_typeddict_generator
)

# Default Python generator (dataclass)
generator = create_python_generator()

# Specific style generators
dc_generator = create_dataclass_generator(slots=True, frozen=False)
pydantic_generator = create_pydantic_generator(use_field=True)
td_generator = create_typeddict_generator(total=False)
```

#### Field Case Convention

Python generator defaults to Python conventions:

- **Class names**: PascalCase (`struct_case="pascal"`)
- **Field names**: snake_case (`field_case="snake"`)

```python
# Input: {"userId": 1, "userName": "Alice"}

# Generated output:
@dataclass(slots=True)
class Root:
    user_id: int      # ✅ Converted to snake_case
    user_name: str    # ✅ Converted to snake_case
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

**Dataclass:**

```python
from dataclasses import dataclass

@dataclass(slots=True)
class User:
    """User represents the root data structure"""
    user_id: int
    name: str
    email: str | None = None
    tags: list[str]
```

**Pydantic:**

```python
from pydantic import BaseModel, Field

class User(BaseModel):
    """User represents the root data structure"""
    user_id: int = Field(alias="userId")
    name: str
    email: str | None = Field(default=None)
    tags: list[str]

    model_config = {"populate_by_name": True}
```

**TypedDict:**

```python
from typing import TypedDict, NotRequired

class User(TypedDict):
    """User represents the root data structure"""
    user_id: int
    name: str
    email: NotRequired[str | None]
    tags: list[str]
```

---

### 6. Schema System

Internal schema representation for code generation.

#### `Schema` Class

Represents a data structure schema.

**Attributes:**

- `name` (str): Schema name
- `fields` (list[Field]): List of fields
- `description` (str, optional): Schema description

**Methods:**

- `add_field(field)`: Add a field to schema
- `get_field(name)`: Get field by name

#### `Field` Class

Represents an individual field in a schema.

**Attributes:**

- `name` (str): Field name
- `type` (FieldType): Field type
- `optional` (bool): Whether field is optional
- `description` (str, optional): Field description
- `nested_schema` (Schema, optional): For object types
- `array_element_type` (FieldType, optional): For array types

#### `FieldType` Enum

Supported field types:

- `STRING`: String values
- `INTEGER`: Integer numbers
- `FLOAT`: Floating-point numbers
- `BOOLEAN`: Boolean values
- `TIMESTAMP`: Datetime/timestamp strings
- `OBJECT`: Nested objects
- `ARRAY`: Arrays/lists
- `UNKNOWN`: Unknown type (null only)
- `CONFLICT`: Multiple conflicting types

**Example:**

```python
from json_explorer.codegen.core.schema import Schema, Field, FieldType

# Create schema
user_schema = Schema(name="User", description="User data")

# Add fields
user_schema.add_field(Field(
    name="user_id",
    type=FieldType.INTEGER,
    optional=False
))

user_schema.add_field(Field(
    name="email",
    type=FieldType.STRING,
    optional=True
))

user_schema.add_field(Field(
    name="tags",
    type=FieldType.ARRAY,
    array_element_type=FieldType.STRING,
    optional=False
))
```

---

### 7. Interactive Handler

Interactive code generation interface with guided configuration.

#### `CodegenInteractiveHandler` Class

Provides menu-driven interface for code generation.

**Constructor:**

```python
CodegenInteractiveHandler(data, console=None)
```

**Parameters:**

- `data` (dict | list): JSON data to generate code from
- `console` (Console, optional): Rich console instance

**Methods:**

##### `run_interactive()`

Launch interactive code generation interface.

**Features:**

- Language selection
- Style selection (for Python)
- Configuration templates
- Advanced options
- Real-time code preview
- Save to file

**Example:**

```python
from json_explorer.codegen.interactive import CodegenInteractiveHandler

handler = CodegenInteractiveHandler(data)
handler.run_interactive()
```

**Interactive Flow:**

1. Select language (Go, Python)
2. Select style (if Python)
3. Choose configuration template or custom
4. Configure advanced options
5. Preview generated code
6. Save to file or clipboard

---

## CLI Usage

### Basic Commands

```bash
# Interactive mode
json_explorer data.json --interactive

# Tree visualization
json_explorer data.json --tree compact

# Statistics
json_explorer data.json --stats --detailed

# Visualizations
json_explorer data.json --plot --plot-format html
```

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
    load_json,
    analyze_json,
    JsonSearcher,
    DataStatsAnalyzer,
    JSONVisualizer,
    quick_generate
)

# Load data
source, data = load_json("data.json")

# Analyze structure
analysis = analyze_json(data)
print(f"Analysis complete: {analysis['type']}")

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
        {"id": 3, "name": "Charlie", "age": 35, "active": True}
    ]
}

searcher = JsonSearcher()

# Complex filtering
result = searcher.search(
    data,
    "users[?age > `25` && active == `true`].{name: name, age: age}"
)

# Sorting and selection
result = searcher.search(data, "sort_by(users, &age)[-1].name")

# Aggregations
result = searcher.search(data, "length(users[?active == `true`])")

# Multiple queries
queries = [
    "users[*].name",
    "max_by(users, &age).name",
    "length(users)"
]
results = searcher.search_multiple(data, queries)
```

### 3. Custom Go Generation

```python
from json_explorer import analyze_json
from json_explorer.codegen import (
    GeneratorConfig,
    generate_from_analysis
)

data = {
    "user_profile": {
        "name": "Alice",
        "settings": {"theme": "dark"}
    }
}

analysis = analyze_json(data)

config = GeneratorConfig(
    package_name="api",
    generate_json_tags=True,
    json_tag_omitempty=True,
    add_comments=True,
    language_config={
        "use_pointers_for_optional": True,
        "int_type": "int64"
    }
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
from json_explorer.codegen import (
    GeneratorConfig,
    generate_from_analysis
)

data = {
    "user_id": 123,
    "name": "Alice",
    "email": None,
    "tags": ["python"]
}

analysis = analyze_json(data)

# Dataclass
dc_config = GeneratorConfig(
    package_name="models",
    language_config={"style": "dataclass", "dataclass_slots": True}
)
dc_result = generate_from_analysis(analysis, "python", dc_config, "User")

# Pydantic
pydantic_config = GeneratorConfig(
    package_name="models",
    language_config={
        "style": "pydantic",
        "pydantic_use_field": True,
        "pydantic_config_dict": True
    }
)
pydantic_result = generate_from_analysis(analysis, "python", pydantic_config, "User")

# TypedDict
td_config = GeneratorConfig(
    package_name="types",
    language_config={"style": "typeddict", "typeddict_total": False}
)
td_result = generate_from_analysis(analysis, "python", td_config, "User")
```

### 5. Handling Optional Fields

```python
from json_explorer.codegen import quick_generate

data = [
    {"name": "John", "email": None, "age": 30},
    {"name": "Jane", "email": "jane@example.com", "age": 25}
]

# Go with pointers
go_code = quick_generate(data, language="go")
# Output:
# type RootItem struct {
#     Name  string  `json:"name"`
#     Email *string `json:"email,omitempty"`  // Optional
#     Age   int64   `json:"age"`
# }

# Python with None defaults
python_code = quick_generate(data, language="python")
# Output:
# @dataclass(slots=True)
# class RootItem:
#     name: str
#     email: str | None = None  // Optional
#     age: int
```

---

## Configuration Best Practices

### Language-Specific Defaults

**Go:**

- `struct_case`: "pascal"
- `field_case`: "pascal"
- `use_pointers_for_optional`: true

**Python:**

- `struct_case`: "pascal"
- `field_case`: "snake"
- `dataclass_slots`: true

### Recommended Configurations

**REST APIs (Go):**

```json
{
  "package_name": "api",
  "language_config": {
    "use_pointers_for_optional": true,
    "int_type": "int64",
    "json_tag_omitempty": true
  }
}
```

**Data Validation (Python Pydantic):**

```json
{
  "package_name": "models",
  "field_case": "snake",
  "language_config": {
    "style": "pydantic",
    "pydantic_use_field": true,
    "pydantic_extra_forbid": true
  }
}
```

---

## Error Handling

### Common Exceptions

- `JSONLoaderError`: JSON loading/parsing errors
- `GeneratorError`: Code generation errors
- `RegistryError`: Generator registry errors
- `TemplateError`: Template rendering errors
- `ConfigError`: Configuration errors

### Best Practices

```python
from json_explorer import load_json, generate_from_analysis
from json_explorer.utils import JSONLoaderError
from json_explorer.codegen import load_config

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
except Exception as e:
    print(f"Config error: {e}")
```

---

## Additional Resources

- **GitHub**: [https://github.com/MS-32154/py-json-analyzer](https://github.com/MS-32154/py-json-analyzer)
- **PyPI**: [https://pypi.org/project/py-json-analyzer/](https://pypi.org/project/py-json-analyzer/)
- **JMESPath**: [https://jmespath.org/](https://jmespath.org/)

---

**JSON Explorer** – © 2025 MS-32154. All rights reserved.
