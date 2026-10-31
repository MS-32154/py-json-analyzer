"""JSON Explorer - Comprehensive JSON analysis and code generation tool."""

from importlib import metadata as _metadata

from .analyzer import analyze_json
from .errors import JsonExplorerError
from .json_schema import json_schema, to_json_schema
from .logging_config import configure_logging, get_logger
from .search import JsonSearcher, SearchResult
from .stats import DataStatsAnalyzer, generate_stats
from .utils import JSONLoaderError, load_json
from .visualizer import JSONVisualizer, visualize_json

try:
    __version__ = _metadata.version("py-json-analyzer")
except _metadata.PackageNotFoundError:  # running from a source tree without install
    __version__ = "0+unknown"

__all__ = [
    "DataStatsAnalyzer",
    "JSONLoaderError",
    "JSONVisualizer",
    "JsonExplorerError",
    "JsonSearcher",
    "SearchResult",
    "analyze_json",
    "configure_logging",
    "generate_stats",
    "get_logger",
    "json_schema",
    "load_json",
    "to_json_schema",
    "visualize_json",
]
