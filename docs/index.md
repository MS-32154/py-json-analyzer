# JSON Explorer API Documentation

## Table of Contents

- [Overview](#overview)
- [Core Modules](#core-modules)
- [Code Generation](#code-generation)
- [CLI Usage](#cli-usage)
- [Examples](#examples)

## Overview

JSON Explorer is a comprehensive tool for analyzing, visualizing, and generating code from JSON data. It provides both programmatic APIs and command-line interfaces for various JSON processing tasks.

### Key Features

- **JSON Analysis**: Deep structural analysis with type detection and conflict resolution
- **Search & Filter**: Advanced search capabilities with custom filter expressions
- **Visualization**: Multiple output formats (terminal, matplotlib, browser)
- **Code Generation**: Multi-language code generation from JSON schemas
- **Statistics**: Comprehensive data quality and structure metrics

---

## Core Modules

### 1. Analyzer Module

The analyzer module provides deep structural analysis of JSON data.

#### `analyze_json(data)`

Analyzes JSON structure and returns detailed metadata.

**Parameters:**

- `data` (dict|list|any): JSON data to analyze

**Returns:**

- `dict`: Analysis summary with structure, types, and conflicts

**Example:**

```python
from json_explorer.analyzer import analyze_json

data = {"users": [{"id": 1, "name": "Alice"}]}
analysis = analyze_json(data)
print(analysis)
# Returns structured analysis with types, optional fields, conflicts
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
    register_generator,
    get_generator,
    list_supported_languages,
    get_language_info
)

# List available languages
languages = list_supported_languages()

# Get generator instance
generator = get_generator("go", config)

# Get language information
info = get_language_info("go")
```

### 3. High-Level API

#### `generate_from_analysis(analyzer_result, language="go", config=None, root_name="Root")`

Generate code from analyzer output.

**Parameters:**

- `analyzer_result`: Output from `analyze_json()`
- `language` (str): Target language
- `config` (GeneratorConfig|dict|str): Configuration
- `root_name` (str): Name for root schema

**Returns:**

- `GenerationResult`: Generated code and metadata

#### `quick_generate(json_data, language="go", **options)`

Quick code generation from JSON data.

**Example:**

```python
from json_explorer.codegen import quick_generate

data = {"user_id": 123, "name": "Alice"}
go_code = quick_generate(data, language="go", package_name="models")
print(go_code)
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

### 5. Schema System

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

### 6. Interactive Handler

Interactive code generation interface.

#### `CodegenInteractiveHandler` Class

```python
from json_explorer.codegen.interactive import CodegenInteractiveHandler

handler = CodegenInteractiveHandler(data, console)
handler.run_interactive()
```

**Features:**

- Language selection
- Configuration templates
- Advanced options
- Real-time preview

---

## CLI Usage

### Basic Commands

```bash
# Analyze JSON structure
json-explorer data.json --tree compact

# Search for keys
json-explorer data.json --search "user" --search-type key

# Generate statistics
json-explorer data.json --stats --detailed

# Create visualizations
json-explorer data.json --plot --plot-format matplotlib

# Interactive mode
json-explorer data.json --interactive
```

### Code Generation Commands

```bash
# Generate Go structs
json-explorer data.json --generate go --output models.go

# With custom configuration
json-explorer data.json --generate go --package-name models --root-name User

# List available languages
json-explorer --list-languages

# Get language information
json-explorer --language-info go
```

### Advanced Search

```bash
# Filter search with expressions
json-explorer data.json --search "isinstance(value, int) and value > 10" --search-type filter

# Search with tree results
json-explorer data.json --search "email" --search-type value --tree-results
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

# Generate code
go_code = quick_generate(data, "go", package_name="models")
with open('models.go', 'w') as f:
    f.write(go_code)
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

### 3. Advanced Code Generation

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

### 4. Interactive Usage

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

## Error Handling

### Common Exceptions

- `JSONLoaderError`: JSON loading/parsing errors
- `GeneratorError`: Code generation errors
- `RegistryError`: Generator registry errors
- `TemplateError`: Template rendering errors
- `ConfigError`: Configuration errors

### Best Practices

1. **Always handle file loading errors**:

```python
try:
    from json_explorer.utils import load_json
    source, data = load_json("data.json")
except FileNotFoundError:
    print("File not found")
except JSONLoaderError as e:
    print(f"JSON loading error: {e}")
```

2. **Check generation results**:

```python
result = generate_from_analysis(analysis, "go", config)
if not result.success:
    print(f"Generation failed: {result.error_message}")
    if result.exception:
        raise result.exception
```

3. **Validate configurations**:

```python
from json_explorer.codegen import load_config

try:
    config = load_config("config.json")
except ConfigError as e:
    print(f"Configuration error: {e}")
```
