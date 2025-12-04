"""JSON Explorer - Comprehensive JSON analysis and code generation tool."""

from .logging_config import configure_logging, get_logger
from .analyzer import analyze_json
from .search import JsonSearcher, SearchResult
from .stats import DataStatsAnalyzer, generate_stats
from .visualizer import JSONVisualizer, visualize_json
from .utils import load_json, JSONLoaderError

__version__ = "0.4.0"

__all__ = [
    # Logging
    "configure_logging",
    "get_logger",
    # Core
    "analyze_json",
    "load_json",
    # Search (now JMESPath-based)
    "JsonSearcher",
    "SearchResult",
    # Statistics
    "DataStatsAnalyzer",
    "generate_stats",
    # Visualization
    "JSONVisualizer",
    "visualize_json",
    # Exceptions
    "JSONLoaderError",
]
