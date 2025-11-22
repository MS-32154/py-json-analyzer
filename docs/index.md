# JSON Explorer API Documentation

## Table of Contents

- [Overview](#overview)
- [Core Modules](#core-modules)
- [Code Generation](#code-generation)
- [CLI Usage](#cli-usage)
- [Examples](#examples)
- [Configuration Best Practices](#configuration-best-practices)
- [Error Handling](#error-handling)

---

## Overview

JSON Explorer is a comprehensive tool for analyzing, visualizing, and generating code from JSON data. It provides both programmatic APIs and command-line interfaces for various JSON processing tasks.

### Key Features

- **JSON Analysis**: Deep structural analysis with type detection and conflict resolution
- **Search & Filter**: Advanced search capabilities with custom filter expressions
- **Visualization**: Multiple output formats (terminal, matplotlib, browser)
- **Code Generation**: Multi-language code generation from JSON schemas (Go, Python)
- **Statistics**: Comprehensive data quality and structure metrics

---

## Core Modules

### 1. Analyzer Module

The analyzer module provides deep structural analysis of JSON data.

#### `analyze_json(data)`

Analyzes JSON structure and returns detailed metadata.

**Parameters:**

- `data (dict|list|any)`: JSON data to analyze

**Returns:**

- `dict`: Analysis summary with structure, types, and conflicts

**Structure of returned dict:**

```python
{
    "type": "object",           # Root type: "object", "list", or primitive
    "children": {               # For objects: field definitions
        "field_name": {
            "type": "str",      # Field type
            "optional": False   # Whether field is optional
        }
    },
    "conflicts": {              # Type conflicts detected
        "field_name": ["str", "int"]
    }
}
```

**Example output:**

```python
{
    "type": "object",
    "children": {
        "user_id": {"type": "int", "optional": False},
        "name": {"type": "str", "optional": False},
        "email": {"type": "str", "optional": True},
        "tags": {
            "type": "list",
            "child_type": "str",
            "optional": False
        }
    },
    "conflicts": {}
}
```

**Example:**

```python
from json_explorer.analyzer import analyze_json

data = {"users": [{"id": 1, "name": "Alice"}]}
analysis = analyze_json(data)
print(analysis)
# Returns structured analysis with types, optional fields, conflicts
```

#### Optional Field Detection

The analyzer marks fields as optional in two cases:

1. **Missing from some objects**: Field doesn't appear in all objects

```python
   [
        {"name": "John"},
        {"name": "Jane", "email": "jane@example.com"}
   ]
   # email is optional (missing from first object)
```

2. **Has None values**: Field has `None` in some objects

```python
   [
        {"name": "John", "email": None},
        {"name": "Jane", "email": "jane@example.com"}
   ]
   # email is optional (None in first object)
```

#### Type Conflict Resolution

When a field has mixed types, the analyzer uses smart resolution:

- **None + Single Type** → Optional field of that type

```python
  [{"value": None}, {"value": "text"}]
  # Result: value: str (optional) ✅
```

- **None + Multiple Types** → Real conflict (uses `Any` or `interface{}`)

```python
  [{"value": None}, {"value": 1}, {"value": "text"}]
  # Result: value: Any (conflict) ⚠️
```

- **Multiple Types (no None)** → Real conflict

```python
  [{"value": 1}, {"value": "text"}]
  # Result: value: Any (conflict) ⚠️
```

### 2. Search Module

Advanced search functionality with multiple search modes and filter expressions.

#### `JsonSearcher` Class

**Constructor:**

```python
JsonSearcher(console=None)
```

**Methods:**

##### `search_keys(data, target_key, mode=SearchMode.EXACT, max_results=None, min_depth=0, max_depth=None)`

Search for keys in JSON data.

**Parameters:**

- `data`: JSON data to search
- `target_key` (str): Key pattern to search for
- `mode` (SearchMode): Search mode (EXACT, CONTAINS, REGEX, etc.)
- `max_results` (int, optional): Limit number of results
- `min_depth` (int): Minimum depth to search
- `max_depth` (int, optional): Maximum depth to search

**Returns:**

- `List[SearchResult]`: List of search results

**Example:**

```python
from json_explorer.search import JsonSearcher, SearchMode

searcher = JsonSearcher()
results = searcher.search_keys(data, "user", SearchMode.CONTAINS)
searcher.print_results(results)
```

##### `search_values(data, target_value, mode=SearchMode.EXACT, value_types=None, **kwargs)`

Search for values in JSON data.

##### `search_with_filter(data, filter_func)`

Search using custom filter functions.

**Example:**

```python
# Find all integer values greater than 10
def filter_func(key, value, depth):
    return isinstance(value, int) and value > 10

results = searcher.search_with_filter(data, filter_func)
```

#### `SearchMode` Enum

Available search modes:

- `EXACT`: Exact match
- `CONTAINS`: Contains substring
- `REGEX`: Regular expression
- `STARTSWITH`: Starts with pattern
- `ENDSWITH`: Ends with pattern
- `CASE_INSENSITIVE`: Case-insensitive match

### 3. Statistics Module

Comprehensive data analysis and quality metrics.

#### `DataStatsAnalyzer` Class

**Methods:**

##### `generate_stats(data)`

Generate comprehensive statistics for data structure.

**Returns:**

- `dict`: Detailed statistics including:
  - Total keys/values
  - Data type distribution
  - Depth analysis
  - Quality metrics
  - Structure insights

**Example:**

```python
from json_explorer.stats import DataStatsAnalyzer

analyzer = DataStatsAnalyzer()
stats = analyzer.generate_stats(data)
analyzer.print_summary(data, detailed=True)
```

### 4. Visualization Module

Multi-format data visualization capabilities.

#### `JSONVisualizer` Class

##### `visualize(data, output="terminal", save_path=None, detailed=False, open_browser=True)`

Create visualizations for JSON data statistics.

**Parameters:**

- `data`: JSON data to visualize
- `output` (str): Output format ('terminal', 'matplotlib', 'browser', 'all')
- `save_path` (str, optional): Path to save files
- `detailed` (bool): Show detailed visualizations
- `open_browser` (bool): Auto-open browser for HTML output

**Example:**

```python
from json_explorer.visualizer import JSONVisualizer

visualizer = JSONVisualizer()
visualizer.visualize(data, output="matplotlib", detailed=True)
```

### 5. Filter Parser Module

Safe expression parsing for advanced filtering.

#### `FilterExpressionParser` Class

##### `parse_filter(expression)`

Parse and compile filter expressions safely.

**Parameters:**

- `expression` (str): Filter expression string

**Returns:**

- `callable`: Filter function

**Example:**

```python
from json_explorer.filter_parser import FilterExpressionParser

# Create filter for numeric values > 10
filter_func = FilterExpressionParser.parse_filter(
    "isinstance(value, (int, float)) and value > 10"
)
```

**Supported in expressions:**

- Variables: `key`, `value`, `depth`
- Functions: `isinstance()`, `len()`, `str()`, `int()`, `float()`
- Operators: `==`, `!=`, `<`, `>`, `and`, `or`, `not`, `in`

---

## Code Generation

The codegen module provides multi-language code generation from JSON schemas.

### 1. Core Generator Interface

#### `CodeGenerator` (Abstract Base Class)

Base class for all language generators.

**Abstract Methods:**

- `language_name`: Property returning language name
- `file_extension`: Property returning file extension
- `generate(schemas, root_schema_name)`: Generate code for schemas

### 2. Registry System

#### `GeneratorRegistry` Class

Manages available code generators.

##### `register(language, generator_class, aliases=None)`

Register a new generator.

##### `create_generator(language, config=None)`

Create generator instance with configuration.

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

# Get generator instance
generator = get_generator("go", config)
generator = get_generator("python", config)

# Get language information
info = get_language_info("go")
info = get_language_info("python")
```

### 3. High-Level API

#### `generate_from_analysis(analyzer_result, language="go", config=None, root_name="Root")`

Generate code from analyzer output.

**Parameters:**

- `analyzer_result`: Output from `analyze_json()`
- `language` (str): Target language ('go', 'python')
- `config (GeneratorConfig|dict|str)`: Configuration
- `root_name` (str): Name for root schema

**Returns:**

- `GenerationResult`: Generated code and metadata

#### `quick_generate(json_data, language="go", **options)`

Quick code generation from JSON data.

**Example:**

```python
from json_explorer.codegen import quick_generate

data = {"user_id": 123, "name": "Alice"}

# Generate Go
go_code = quick_generate(data, language="go", package_name="models")
print(go_code)

# Generate Python dataclass
python_code = quick_generate(data, language="python", style="dataclass")
print(python_code)

# Generate Pydantic model
pydantic_code = quick_generate(data, language="python", style="pydantic")
print(pydantic_code)
```

### 4. Go Generator

Specialized Go struct generation with JSON tags.

#### Features

- Configurable type mappings
- Pointer usage for optional fields
- JSON tag generation
- Package and import management
- Naming convention handling

#### Configuration Options

```python
from json_explorer.codegen import GeneratorConfig

config = GeneratorConfig(
    package_name="models",
    generate_json_tags=True,
    json_tag_omitempty=True,
    add_comments=True,
    language_config={
        "int_type": "int64",
        "float_type": "float64",
        "use_pointers_for_optional": True
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

# Optimized for web APIs
api_generator = create_web_api_generator()

# Strict types (no pointers)
strict_generator = create_strict_generator()
```

#### Pointer Handling

The Go generator intelligently handles pointers:

- **Optional primitive types** → Add pointer when `use_pointers_for_optional=True`

```go
  Email *string `json:"email,omitempty"`
```

- **interface{} and any** → Never add pointer (already accepts nil)

```go
  UnknownField interface{} `json:"unknown_field"`  // No pointer
```

- **Arrays** → Never add pointer

```go
  Tags []string `json:"tags"`  // No pointer on slice
```

### 5. Python Generator

Specialized Python code generation with multiple styles.

#### Features

- Dataclass generation
- Pydantic v2 model generation
- TypedDict generation
- Type hints with modern syntax (T | None)
- Field aliases and metadata
- Configurable options per style

#### Configuration Options

```python
from json_explorer.codegen import GeneratorConfig

# Dataclass configuration
config = GeneratorConfig(
    package_name="models",
    add_comments=True,
    struct_case="pascal",
    field_case="snake",
    language_config={
        "style": "dataclass",
        "dataclass_slots": True,
        "dataclass_frozen": False,
        "use_optional": True
    }
)

# Pydantic configuration
pydantic_config = GeneratorConfig(
    package_name="models",
    add_comments=True,
    language_config={
        "style": "pydantic",
        "pydantic_use_field": True,
        "pydantic_use_alias": True,
        "pydantic_config_dict": True
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

# Dataclass generator
dc_generator = create_dataclass_generator()

# Pydantic v2 generator
pydantic_generator = create_pydantic_generator()

# TypedDict generator
td_generator = create_typeddict_generator()
```

#### Field Case Convention

Python generator defaults to Python conventions:

- **Class names**: PascalCase (`struct_case="pascal"`)
- **Field names**: snake_case (`field_case="snake"`)

This is automatically applied unless explicitly overridden:

```python
# Input: {"userId": 1, "userName": "Alice"}

# Generated output:
@dataclass
class Root:
    user_id: int      # ✅ Converted to snake_case
    user_name: str    # ✅ Converted to snake_case
```

#### Pydantic Field() Usage

`Field()` is only generated when needed:

- **Alias needed** (field name differs from JSON key)

```python
  user_id: int = Field(alias="userId")
```

- **Has description**

```python
  name: str = Field(description="User's full name")
```

- **Optional field**

```python
  email: str | None = Field(default=None)
```

If none of these apply, no `Field()` is generated:

```python
user_id: int  # No Field() needed
```

### 6. Schema System

Internal schema representation for code generation.

#### `Schema` Class

Represents data structure schema.

**Properties:**

- `name` (str): Schema name
- `fields` (List[Field]): List of fields
- `description` (str, optional): Schema description

#### `Field` Class

Represents individual field in schema.

**Properties:**

- `name` (str): Field name
- `type` (FieldType): Field type
- `optional` (bool): Whether field is optional
- `nested_schema` (Schema, optional): For object types
- `array_element_type` (FieldType, optional): For array types

#### `FieldType` Enum

Supported field types:

- `STRING`, `INTEGER`, `FLOAT`, `BOOLEAN`
- `TIMESTAMP`, `OBJECT`, `ARRAY`
- `UNKNOWN`, `CONFLICT`

### 7. Interactive Handler

Interactive code generation interface.

#### `CodegenInteractiveHandler` Class

```python
from json_explorer.codegen.interactive import CodegenInteractiveHandler

handler = CodegenInteractiveHandler(data, console)
handler.run_interactive()
```

**Features:**

- Language selection (Go, Python)
- Configuration templates
- Style selection (for Python)
- Advanced options
- Real-time preview

---

## CLI Usage

### Basic Commands

```bash
# Analyze JSON structure
json_explorer data.json --tree compact

# Search for keys
json_explorer data.json --search "user" --search-type key

# Generate statistics
json_explorer data.json --stats --detailed

# Create visualizations
json_explorer data.json --plot --plot-format matplotlib

# Interactive mode
json_explorer data.json --interactive
```

### Code Generation Commands

```bash
# List available languages
json_explorer --list-languages

# Get language information
json_explorer --language-info go
json_explorer --language-info python

# Generate Go structs
json_explorer data.json --generate go --output models.go

# Generate Python dataclasses
json_explorer data.json --generate python --output models.py

# Generate Pydantic models
json_explorer data.json --generate python --python-style pydantic --output models.py

# Generate TypedDict
json_explorer data.json --generate python --python-style typeddict --output types.py

# With custom configuration
json_explorer data.json --generate go --package-name models --root-name User

# Python with frozen dataclass
json_explorer data.json --generate python --frozen --output models.py
```

### Advanced Search

```bash
# Filter search with expressions
json_explorer data.json --search "isinstance(value, int) and value > 10" --search-type filter

# Search with tree results
json_explorer data.json --search "email" --search-type value --tree-results
```

---

## Examples

### 1. Complete Analysis Workflow

```python
import json
from json_explorer.analyzer import analyze_json
from json_explorer.search import JsonSearcher, SearchMode
from json_explorer.stats import DataStatsAnalyzer
from json_explorer.visualizer import JSONVisualizer
from json_explorer.codegen import quick_generate

# Load data
with open('data.json') as f:
    data = json.load(f)

# Analyze structure
analysis = analyze_json(data)
print("Structure analysis complete")

# Search for patterns
searcher = JsonSearcher()
email_fields = searcher.search_keys(data, "email", SearchMode.CONTAINS)
print(f"Found {len(email_fields)} email-related fields")

# Generate statistics
analyzer = DataStatsAnalyzer()
analyzer.print_summary(data, detailed=True)

# Create visualizations
visualizer = JSONVisualizer()
visualizer.visualize(data, output="browser", detailed=True)

# Generate Go code
go_code = quick_generate(data, "go", package_name="models")
with open('models.go', 'w') as f:
    f.write(go_code)

# Generate Python code
python_code = quick_generate(data, "python", style="pydantic")
with open('models.py', 'w') as f:
    f.write(python_code)
```

### 2. Custom Filter Expressions

```python
from json_explorer.search import JsonSearcher
from json_explorer.filter_parser import FilterExpressionParser

data = {
    "users": [
        {"id": 1, "age": 25, "email": "user@example.com"},
        {"id": 2, "age": 30, "email": None},
        {"id": 3, "age": 35, "active": True}
    ]
}

searcher = JsonSearcher()

# Find adult users
adult_filter = FilterExpressionParser.parse_filter(
    "key == 'age' and isinstance(value, int) and value >= 18"
)
results = searcher.search_with_filter(data, adult_filter)

# Find email addresses
email_filter = FilterExpressionParser.parse_filter(
    "'@' in str(value) and isinstance(value, str)"
)
email_results = searcher.search_with_filter(data, email_filter)
```

### 3. Advanced Go Code Generation

```python
from json_explorer.analyzer import analyze_json
from json_explorer.codegen import (
    GeneratorConfig,
    get_generator,
    generate_from_analysis
)

# Analyze JSON
data = {"user_profile": {"name": "Alice", "settings": {"theme": "dark"}}}
analysis = analyze_json(data)

# Create custom configuration
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

# Generate code
result = generate_from_analysis(analysis, "go", config, "UserProfile")

if result.success:
    print("Generated Go code:")
    print(result.code)

    if result.warnings:
        print("\nWarnings:")
        for warning in result.warnings:
            print(f"  - {warning}")
else:
    print(f"Generation failed: {result.error_message}")
```

### 4. Advanced Python Code Generation

```python
from json_explorer.analyzer import analyze_json
from json_explorer.codegen import (
    GeneratorConfig,
    generate_from_analysis
)

# Analyze JSON
data = {
    "user_id": 123,
    "name": "Alice",
    "email": None,
    "tags": ["python", "coding"]
}
analysis = analyze_json(data)

# Generate dataclass
dataclass_config = GeneratorConfig(
    package_name="models",
    add_comments=True,
    language_config={
        "style": "dataclass",
        "dataclass_slots": True,
        "dataclass_frozen": False,
        "use_optional": True
    }
)

result = generate_from_analysis(analysis, "python", dataclass_config, "User")
print("Dataclass:")
print(result.code)

# Generate Pydantic model
pydantic_config = GeneratorConfig(
    package_name="models",
    add_comments=True,
    language_config={
        "style": "pydantic",
        "pydantic_use_field": True,
        "pydantic_use_alias": True,
        "pydantic_config_dict": True
    }
)

result = generate_from_analysis(analysis, "python", pydantic_config, "User")
print("\nPydantic model:")
print(result.code)
```

### 5. Interactive Usage

```python
from json_explorer.interactive import InteractiveHandler

# Create handler
handler = InteractiveHandler()

# Load data
handler.set_data(data, "sample_data.json")

# Run interactive mode
handler.run()
```

This provides a comprehensive menu-driven interface for all JSON Explorer features.

---

### 6. Handling Optional Fields with None

```python
from json_explorer.codegen import quick_generate

# Data with None values
data = [
    {"name": "John", "email": None, "age": 30},
    {"name": "Jane", "email": "jane@example.com", "age": 25}
]

# Generate Go
go_code = quick_generate(data, language="go")
print(go_code)
# Output:
# type RootItem struct {
#     Name  string  `json:"name"`
#     Email *string `json:"email,omitempty"`  // ✅ Optional pointer
#     Age   int64   `json:"age"`
# }

# Generate Python
python_code = quick_generate(data, language="python")
print(python_code)
# Output:
# @dataclass(slots=True)
# class RootItem:
#     name: str
#     email: str | None = None  // ✅ Optional with default
#     age: int
```

---

## Configuration Best Practices

### Language-Specific Defaults

Each language has sensible defaults that follow community conventions:

**Go:**

- `struct_case`: "pascal" (Go convention)
- `field_case`: "pascal" (Go convention)
- `use_pointers_for_optional`: true

**Python:**

- `struct_case`: "pascal" (PEP 8)
- `field_case`: "snake" (PEP 8)
- `dataclass_slots`: true (memory optimization)

### Override Priority

Configuration is applied in this order (highest priority first):

1. CLI arguments: `--field-case snake`
2. Config file: `config.json`
3. Language defaults: Automatic per language
4. Core defaults: Fallback values

Example:

```bash
# Uses Python default (snake_case for fields)
json_explorer data.json --generate python

# Override to pascal case
json_explorer data.json --generate python --field-case pascal
```

### Recommended Configurations

**For REST APIs (Go):**

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

**For Data Validation (Python Pydantic):**

```json
{
  "package_name": "models",
  "field_case": "snake",
  "language_config": {
    "style": "pydantic",
    "pydantic_use_field": true,
    "pydantic_use_alias": true,
    "pydantic_extra_forbid": true
  }
}
```

**For Type Checking (Python TypedDict):**

```json
{
  "package_name": "types",
  "field_case": "snake",
  "language_config": {
    "style": "typeddict",
    "typeddict_total": false
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

#### 1. **Always handle file loading errors**:

```python
try:
    from json_explorer.utils import load_json
    source, data = load_json("data.json")
except FileNotFoundError:
    print("File not found")
except JSONLoaderError as e:
    print(f"JSON loading error: {e}")
```

#### 2. **Check generation results**:

```python
result = generate_from_analysis(analysis, "go", config)
if not result.success:
    print(f"Generation failed: {result.error_message}")
    if result.exception:
        raise result.exception
```

#### 3. **Validate configurations**:

```python
from json_explorer.codegen import load_config

try:
    config = load_config("config.json")
except ConfigError as e:
    print(f"Configuration error: {e}")
```
