"""Modern data visualization using Plotly for interactive charts.

This module provides multi-format visualization capabilities using Plotly
for both terminal (ASCII) and interactive browser-based visualizations.
"""

import tempfile
import webbrowser
from pathlib import Path
from typing import Any, Literal

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from .logging_config import get_logger
from .stats import DataStatsAnalyzer

logger = get_logger(__name__)

OutputFormat = Literal["terminal", "html", "all"]


class JSONVisualizer:
    """Multi-format visualizer using Plotly for modern, interactive charts.

    Outputs: text charts in the terminal, and an interactive HTML report
    (Plotly) opened in the browser.
    """

    def __init__(self) -> None:
        """Initialize the visualizer."""
        self.stats: dict[str, Any] = {}
        self.colors = {
            "primary": "#2E86AB",
            "secondary": "#A23B72",
            "success": "#F18F01",
            "warning": "#C73E1D",
            "info": "#7209B7",
            "light": "#F5F5F5",
            "dark": "#2D3748",
        }
        logger.debug("JSONVisualizer initialized")

    def visualize(
        self,
        data: Any,
        output: OutputFormat | str = "terminal",
        save_path: str | Path | None = None,
        detailed: bool = False,
        open_browser: bool = True,
    ) -> None:
        """Create visualizations for JSON data statistics.

        Args:
            data: JSON data to analyze and visualize.
            output: 'terminal', 'html' or 'all' (both).
            save_path: Path to save files (for HTML outputs).
            detailed: Whether to show detailed visualizations.
            open_browser: Whether to automatically open browser for HTML output.

        """
        logger.info("Creating %s visualization (detailed=%s)", output, detailed)

        # Generate statistics
        analyzer = DataStatsAnalyzer()
        self.stats = analyzer.generate_stats(data)

        if output not in ("terminal", "html", "all"):
            raise ValueError(f"Unknown output format: {output}")
        if output in ("terminal", "all"):
            self._terminal_view(detailed)
        if output in ("html", "all"):
            self._visualize_plotly(save_path, detailed, open_browser)

    def _visualize_plotly(
        self,
        save_path: str | Path | None,
        detailed: bool,
        open_browser: bool,
    ) -> None:
        """Create Plotly visualizations.

        Args:
            save_path: Optional path to save HTML file.
            detailed: Whether to create detailed visualizations.
            open_browser: Whether to open in browser.
        """

        # Create subplots
        if detailed:
            fig = make_subplots(
                rows=3,
                cols=2,
                subplot_titles=(
                    "Data Types Distribution",
                    "Depth Distribution",
                    "Quality Metrics",
                    "Most Common Keys",
                    "Array Sizes",
                    "Complexity Score",
                ),
                specs=[
                    [{"type": "pie"}, {"type": "bar"}],
                    [{"type": "bar"}, {"type": "bar"}],
                    [{"type": "scatter"}, {"type": "indicator"}],
                ],
                vertical_spacing=0.12,
                horizontal_spacing=0.1,
            )
        else:
            fig = make_subplots(
                rows=1,
                cols=3,
                subplot_titles=(
                    "Data Types Distribution",
                    "Depth Distribution",
                    "Quality Metrics",
                ),
                specs=[[{"type": "pie"}, {"type": "bar"}, {"type": "bar"}]],
                horizontal_spacing=0.15,
            )

        if not detailed:
            # Plot 1: Data Types (Pie Chart)
            self._add_data_types_chart(fig, row=1, col=1)

            # Plot 2: Depth Distribution
            self._add_depth_chart(fig, row=1, col=2)

            # Plot 3: Quality Metrics
            self._add_quality_metrics(fig, row=1, col=3)

        else:
            # Plot 1: Data Types (Pie Chart)
            self._add_data_types_chart(fig, row=1, col=1)

            # Plot 2: Depth Distribution
            self._add_depth_chart(fig, row=1, col=2)

            # Plot 3: Quality Metrics
            self._add_quality_metrics(fig, row=2, col=1)

            # Plot 4: Key Frequency
            self._add_key_frequency(fig, row=2, col=2)

            # Plot 5: Array Sizes
            self._add_array_sizes(fig, row=3, col=1)

            # Plot 6: Complexity Score
            self._add_complexity_gauge(fig, row=3, col=2)

        # Update layout
        title = (
            "JSON Data Analysis - Detailed View" if detailed else "JSON Data Analysis"
        )
        fig.update_layout(
            title_text=title,
            title_font_size=20,
            showlegend=True,
            height=1200 if detailed else 500,
            template="plotly_white",
        )

        # Write the report (to save_path or a temporary file) and open it
        if save_path:
            output_path = Path(save_path).with_suffix(".html")
            print(f"📊 HTML report saved to: {output_path}")
        else:
            output_path = Path(tempfile.gettempdir()) / "json_analysis.html"
        fig.write_html(str(output_path))
        if open_browser:
            webbrowser.open(output_path.absolute().as_uri())
            print("🌐 Opening visualization in browser...")

    def _add_data_types_chart(self, fig: go.Figure, row: int, col: int) -> None:
        """Add data types pie chart to figure."""
        data_types = self.stats["data_types"]
        if not data_types:
            return

        labels = list(data_types.keys())
        values = list(data_types.values())

        fig.add_trace(
            go.Pie(
                labels=labels,
                values=values,
                marker={
                    "colors": [
                        self.colors["primary"],
                        self.colors["secondary"],
                        self.colors["success"],
                        self.colors["warning"],
                        self.colors["info"],
                    ]
                },
            ),
            row=row,
            col=col,
        )

    def _add_depth_chart(self, fig: go.Figure, row: int, col: int) -> None:
        """Add depth distribution bar chart."""
        depth_hist = self.stats["depth_histogram"]
        if not depth_hist:
            return

        depths = sorted(depth_hist.keys())
        counts = [depth_hist[d] for d in depths]

        fig.add_trace(
            go.Bar(
                x=[f"Depth {d}" for d in depths],
                y=counts,
                marker_color=self.colors["primary"],
                text=counts,
                textposition="outside",
            ),
            row=row,
            col=col,
        )

    def _add_quality_metrics(self, fig: go.Figure, row: int, col: int) -> None:
        """Add quality metrics bar chart."""
        patterns = self.stats["value_patterns"]
        total = self.stats["total_values"]

        if total == 0:
            return

        metrics = [
            ("Null Values", (patterns["null_count"] / total) * 100),
            ("Empty Strings", (patterns["empty_strings"] / total) * 100),
            ("Empty Collections", (patterns["empty_collections"] / total) * 100),
        ]

        labels, values = zip(*metrics, strict=False)
        colors = [self.colors["warning"], self.colors["secondary"], self.colors["info"]]

        fig.add_trace(
            go.Bar(
                y=labels,
                x=values,
                orientation="h",
                marker_color=colors,
                text=[f"{v:.1f}%" for v in values],
                textposition="outside",
            ),
            row=row,
            col=col,
        )

    def _add_key_frequency(self, fig: go.Figure, row: int, col: int) -> None:
        """Add key frequency bar chart."""
        key_freq = self.stats["key_frequency"]
        if not key_freq:
            return

        top_keys = key_freq.most_common(10)
        keys, counts = zip(*top_keys, strict=False)

        fig.add_trace(
            go.Bar(
                y=keys,
                x=counts,
                orientation="h",
                marker_color=self.colors["success"],
                text=counts,
                textposition="outside",
            ),
            row=row,
            col=col,
        )

    def _add_array_sizes(self, fig: go.Figure, row: int, col: int) -> None:
        """Add array sizes scatter plot."""
        array_sizes = self.stats["structure_insights"]["array_sizes"]
        if not array_sizes:
            return

        sizes = list(array_sizes.keys())
        counts = list(array_sizes.values())

        fig.add_trace(
            go.Scatter(
                x=sizes,
                y=counts,
                mode="markers",
                marker={"size": 12, "color": self.colors["primary"]},
                text=[
                    f"Size: {s}, Count: {c}"
                    for s, c in zip(sizes, counts, strict=False)
                ],
                hoverinfo="text",
            ),
            row=row,
            col=col,
        )

    def _add_complexity_gauge(self, fig: go.Figure, row: int, col: int) -> None:
        """Add complexity score gauge."""
        score = self.stats["computed_insights"]["complexity_score"]

        fig.add_trace(
            go.Indicator(
                mode="gauge+number",
                value=score,
                gauge={
                    "axis": {"range": [0, 100]},
                    "bar": {"color": self.colors["primary"]},
                    "steps": [
                        {"range": [0, 30], "color": "lightgreen"},
                        {"range": [30, 70], "color": "yellow"},
                        {"range": [70, 100], "color": "lightcoral"},
                    ],
                    "threshold": {
                        "line": {"color": "red", "width": 4},
                        "thickness": 0.75,
                        "value": 90,
                    },
                },
            ),
            row=row,
            col=col,
        )

    def _terminal_view(self, detailed: bool = False) -> None:
        """Text charts in the terminal."""
        print("\n" + "=" * 60)
        print("🎨 JSON DATA VISUALIZATION - TERMINAL VIEW")
        print("=" * 60)

        self._terminal_data_types_chart()
        self._terminal_depth_histogram()

        if detailed:
            self._terminal_quality_metrics()

    def _terminal_data_types_chart(self) -> None:
        """Create ASCII bar chart for data types."""
        print("\n📈 DATA TYPES DISTRIBUTION")
        print("-" * 40)

        data_types = self.stats["data_types"]
        if not data_types:
            print("No data types found.")
            return

        total = sum(data_types.values())
        max_count = max(data_types.values())
        bar_width = 30

        for dtype, count in data_types.most_common():
            percentage = (count / total) * 100
            bar_length = int((count / max_count) * bar_width)
            bar = "█" * bar_length + "░" * (bar_width - bar_length)
            print(f"{dtype:12} │{bar}│ {count:>6} ({percentage:4.1f}%)")

    def _terminal_depth_histogram(self) -> None:
        """Create ASCII histogram for depth distribution."""
        print("\n📊 DEPTH DISTRIBUTION")
        print("-" * 35)

        depth_hist = self.stats["depth_histogram"]
        if not depth_hist:
            return

        max_count = max(depth_hist.values())
        bar_height = 20

        for depth in sorted(depth_hist.keys()):
            count = depth_hist[depth]
            bar_length = int((count / max_count) * bar_height)
            bar = "▌" * bar_length
            print(f"Depth {depth:2d} │{bar:<20}│ {count}")

    def _terminal_quality_metrics(self) -> None:
        """Display data quality metrics."""
        print("\n🎯 QUALITY METRICS")
        print("-" * 25)

        patterns = self.stats["value_patterns"]
        total = self.stats["total_values"]

        if total > 0:
            null_rate = (patterns["null_count"] / total) * 100
            empty_str_rate = (patterns["empty_strings"] / total) * 100
            empty_col_rate = (patterns["empty_collections"] / total) * 100

            print(f"Null values:        {null_rate:5.1f}%")
            print(f"Empty strings:      {empty_str_rate:5.1f}%")
            print(f"Empty collections:  {empty_col_rate:5.1f}%")

        if patterns["string_lengths"]["avg"] > 0:
            print(f"Avg string length:  {patterns['string_lengths']['avg']:5.1f}")

        numeric_ranges = patterns["numeric_ranges"]
        if numeric_ranges["min"] is not None:
            print(
                f"Numeric range:      {numeric_ranges['min']} - {numeric_ranges['max']}"
            )


def visualize_json(
    data: Any,
    output: OutputFormat | str = "terminal",
    save_path: str | Path | None = None,
    detailed: bool = False,
    open_browser: bool = True,
) -> None:
    """Convenience function to visualize JSON data statistics.

    Args:
        data: JSON data to analyze and visualize.
        output: 'terminal', 'html' or 'all' (both).
        save_path: Path to save files (for HTML outputs).
        detailed: Whether to show detailed visualizations.
        open_browser: Whether to automatically open browser for HTML output.
    """
    visualizer = JSONVisualizer()
    visualizer.visualize(data, output, save_path, detailed, open_browser)
