"""JSON Explorer - Comprehensive JSON analysis and code generation tool."""

from .analyzer import analyze_json
from .logging_config import configure_logging, get_logger
from .search import JsonSearcher, SearchResult
from .stats import DataStatsAnalyzer, generate_stats
from .utils import JSONLoaderError, load_json
from .visualizer import JSONVisualizer, visualize_json

__version__ = "0.4.0"

__all__ = [
    # Statistics
    "DataStatsAnalyzer",
    # Exceptions
    "JSONLoaderError",
    # Visualization
    "JSONVisualizer",
    # Search (now JMESPath-based)
    "JsonSearcher",
    "SearchResult",
    # Core
    "analyze_json",
    # Logging
    "configure_logging",
    "generate_stats",
    "get_logger",
    "load_json",
    "visualize_json",
]
