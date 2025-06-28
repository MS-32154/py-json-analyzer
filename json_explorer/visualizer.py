import json
import tempfile
import webbrowser
from pathlib import Path

try:
    import curses
except ImportError:
    raise RuntimeError(
        "❗ This feature requires curses. On Windows, install windows-curses."
    )


try:
    import matplotlib.pyplot as plt
    import numpy as np

    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

from .stats import DataStatsAnalyzer


class JSONVisualizer:
    """Multi-format visualizer for JSON statistics with terminal, matplotlib, and browser output."""

    def __init__(self):
        self.stats = None
        self.colors = {
            "primary": "#2E86AB",
            "secondary": "#A23B72",
            "success": "#F18F01",
            "warning": "#C73E1D",
            "info": "#7209B7",
            "light": "#F5F5F5",
            "dark": "#2D3748",
        }

    def visualize(
        self,
        data,
        output="terminal",
        save_path=None,
        detailed=False,
        open_browser=True,
    ):
        """
        Create visualizations for JSON data statistics.

        Args:
            data: JSON data to analyze and visualize
            output: Output format ('terminal', 'matplotlib', 'browser', 'all')
            save_path: Path to save files (for matplotlib and browser outputs)
            detailed: Whether to show detailed visualizations
            open_browser: Whether to automatically open browser for HTML output
        """
        analyzer = DataStatsAnalyzer()
        self.stats = analyzer.generate_stats(data)

        if output == "all":
            self._visualize_terminal(detailed)
            if MATPLOTLIB_AVAILABLE:
                self._visualize_matplotlib(save_path, detailed)
            self._visualize_browser(save_path, detailed, open_browser)
        elif output == "terminal":
            self._visualize_terminal(detailed)
        elif output == "matplotlib":
            if MATPLOTLIB_AVAILABLE:
                self._visualize_matplotlib(save_path, detailed)
            else:
                print(
                    "❌ Matplotlib not available. Install with: pip install matplotlib"
                )
        elif output == "browser":
            self._visualize_browser(save_path, detailed, open_browser)
        else:
            raise ValueError(f"Unknown output format: {output}")

    def _visualize_terminal(self, detailed=False):
        """Create terminal-based visualizations using curses when available."""
        try:
            curses.wrapper(self._curses_main, detailed)
        except:
            # Fallback to standard terminal output
            self._terminal_fallback(detailed)

    def _curses_main(self, stdscr, detailed):
        """Main curses interface for terminal visualization."""
        curses.curs_set(0)
        stdscr.clear()

        curses.start_color()
        curses.init_pair(1, curses.COLOR_CYAN, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK)
        curses.init_pair(3, curses.COLOR_YELLOW, curses.COLOR_BLACK)
        curses.init_pair(4, curses.COLOR_RED, curses.COLOR_BLACK)
        curses.init_pair(5, curses.COLOR_MAGENTA, curses.COLOR_BLACK)
        curses.init_pair(6, curses.COLOR_WHITE, curses.COLOR_BLACK)

        height, width = stdscr.getmaxyx()
        current_page = 0
        max_pages = 3 if detailed else 2

        while True:
            stdscr.clear()

            # Header
            title = "🎨 JSON DATA VISUALIZATION - TERMINAL VIEW"
            stdscr.addstr(
                0,
                max(0, (width - len(title)) // 2),
                title,
                curses.color_pair(1) | curses.A_BOLD,
            )
            stdscr.addstr(1, 0, "=" * min(width - 1, 60), curses.color_pair(1))

            if current_page == 0:
                self._draw_data_types_chart(stdscr, 3, width, height)
            elif current_page == 1:
                self._draw_depth_histogram(stdscr, 3, width, height)
            elif current_page == 2 and detailed:
                self._draw_quality_metrics(stdscr, 3, width, height)

            # Navigation
            nav_text = f"Page {current_page + 1}/{max_pages} | SPACE: Next | q: Quit"
            if detailed:
                nav_text += " | d: Toggle detailed"
            stdscr.addstr(height - 2, 0, nav_text, curses.color_pair(6))

            stdscr.refresh()

            key = stdscr.getch()
            if key == ord("q"):
                break
            elif key == ord(" "):
                current_page = (current_page + 1) % max_pages
            elif key == ord("d") and detailed:
                pass

    def _draw_data_types_chart(self, stdscr, start_y, width, height):
        """Draw data types chart using curses."""
        stdscr.addstr(
            start_y,
            2,
            "📊 DATA TYPES DISTRIBUTION",
            curses.color_pair(2) | curses.A_BOLD,
        )

        data_types = self.stats["data_types"]
        if not data_types:
            stdscr.addstr(start_y + 2, 4, "No data types found.", curses.color_pair(4))
            return

        total = sum(data_types.values())
        max_count = max(data_types.values())
        bar_width = min(40, width - 30)

        y = start_y + 2
        colors = [curses.color_pair(i) for i in range(2, 6)]

        for i, (dtype, count) in enumerate(data_types.most_common()):
            if y >= height - 4:
                break

            percentage = (count / total) * 100
            bar_length = int((count / max_count) * bar_width)

            # Type name
            stdscr.addstr(y, 2, f"{dtype:12}", curses.color_pair(6))

            # Bar
            stdscr.addstr(y, 16, "│", curses.color_pair(6))
            color = colors[i % len(colors)]
            stdscr.addstr(y, 17, "█" * bar_length, color)
            stdscr.addstr(
                y, 17 + bar_length, "░" * (bar_width - bar_length), curses.color_pair(6)
            )
            stdscr.addstr(y, 17 + bar_width, "│", curses.color_pair(6))

            # Stats
            stats_text = f" {count:>6} ({percentage:4.1f}%)"
            stdscr.addstr(y, 18 + bar_width, stats_text, curses.color_pair(6))

            y += 1

    def _draw_depth_histogram(self, stdscr, start_y, width, height):
        """Draw depth histogram using curses."""
        stdscr.addstr(
            start_y, 2, "📏 DEPTH DISTRIBUTION", curses.color_pair(3) | curses.A_BOLD
        )

        depth_hist = self.stats["depth_histogram"]
        if not depth_hist:
            stdscr.addstr(start_y + 2, 4, "No depth data found.", curses.color_pair(4))
            return

        max_count = max(depth_hist.values())
        bar_height = min(15, height - start_y - 8)

        y = start_y + 2
        for depth in sorted(depth_hist.keys()):
            if y >= height - 4:
                break

            count = depth_hist[depth]
            bar_length = int((count / max_count) * bar_height)

            stdscr.addstr(y, 2, f"Depth {depth:2d}", curses.color_pair(6))
            stdscr.addstr(y, 12, "│", curses.color_pair(6))
            stdscr.addstr(y, 13, "▌" * bar_length, curses.color_pair(3))
            stdscr.addstr(y, 13 + bar_length, f"│ {count}", curses.color_pair(6))

            y += 1

    def _draw_quality_metrics(self, stdscr, start_y, width, height):
        """Draw quality metrics using curses."""
        stdscr.addstr(
            start_y, 2, "🎯 QUALITY METRICS", curses.color_pair(5) | curses.A_BOLD
        )

        patterns = self.stats["value_patterns"]
        total = self.stats["total_values"]

        if total == 0:
            stdscr.addstr(
                start_y + 2, 4, "No data for quality analysis.", curses.color_pair(4)
            )
            return

        y = start_y + 2

        # Null rate
        null_rate = (patterns["null_count"] / total) * 100
        stdscr.addstr(
            y,
            4,
            f"Null values:        {null_rate:5.1f}%",
            curses.color_pair(4) if null_rate > 10 else curses.color_pair(2),
        )
        y += 1

        # Empty strings
        empty_str_rate = (patterns["empty_strings"] / total) * 100
        stdscr.addstr(
            y,
            4,
            f"Empty strings:      {empty_str_rate:5.1f}%",
            curses.color_pair(4) if empty_str_rate > 10 else curses.color_pair(2),
        )
        y += 1

        # Empty collections
        empty_col_rate = (patterns["empty_collections"] / total) * 100
        stdscr.addstr(
            y,
            4,
            f"Empty collections:  {empty_col_rate:5.1f}%",
            curses.color_pair(4) if empty_col_rate > 10 else curses.color_pair(2),
        )
        y += 2

        # String stats
        if patterns["string_lengths"]["avg"] > 0:
            stdscr.addstr(
                y,
                4,
                f"Avg string length:  {patterns['string_lengths']['avg']:5.1f}",
                curses.color_pair(6),
            )
            y += 1

        # Numeric range
        numeric_ranges = patterns["numeric_ranges"]
        if numeric_ranges["min"] is not None:
            stdscr.addstr(
                y,
                4,
                f"Numeric range:      {numeric_ranges['min']} - {numeric_ranges['max']}",
                curses.color_pair(6),
            )
            y += 1

        # Key insights
        insights = self.stats["computed_insights"]
        stdscr.addstr(
            y + 1,
            4,
            f"Complexity Score:   {insights['complexity_score']}/100",
            curses.color_pair(3),
        )
        y += 1
        stdscr.addstr(
            y + 1,
            4,
            f"Uniformity:         {insights['structure_uniformity'].replace('_', ' ').title()}",
            curses.color_pair(6),
        )

    def _terminal_fallback(self, detailed=False):
        """Fallback terminal visualization without curses."""
        print("\n" + "=" * 60)
        print("🎨 JSON DATA VISUALIZATION - TERMINAL VIEW")
        print("=" * 60)

        self._terminal_data_types_chart()
        self._terminal_depth_histogram()

        if detailed:
            self._terminal_key_frequency()
            self._terminal_array_sizes()
            self._terminal_quality_metrics()

    def _terminal_data_types_chart(self):
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

    def _terminal_depth_histogram(self):
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

    def _terminal_key_frequency(self):
        """Display most common keys."""
        print("\n🔑 MOST COMMON KEYS")
        print("-" * 25)

        key_freq = self.stats["key_frequency"]
        if not key_freq:
            print("No keys found.")
            return

        for i, (key, count) in enumerate(key_freq.most_common(10)):
            print(f"{i+1:2d}. {key:20} ({count:>3})")

    def _terminal_array_sizes(self):
        """Display array size distribution."""
        print("\n📋 ARRAY SIZES")
        print("-" * 20)

        array_sizes = self.stats["structure_insights"]["array_sizes"]
        if not array_sizes:
            print("No arrays found.")
            return

        for size, count in sorted(array_sizes.items()):
            print(f"Size {size:3d}: {count:>3} arrays")

    def _terminal_quality_metrics(self):
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

    def _visualize_matplotlib(self, save_path=None, detailed=False):
        """Create matplotlib visualizations with version validation."""
        if not MATPLOTLIB_AVAILABLE:
            print(
                "❌ Matplotlib not available. Install with: pip install matplotlib numpy"
            )
            return

        # Check matplotlib version
        try:
            import matplotlib

            version = matplotlib.__version__
            major_version = int(version.split(".")[0])
            if major_version < 3:
                print(
                    f"⚠️  Matplotlib version {version} detected. Version 3.0+ recommended for best results."
                )
        except:
            print("⚠️  Could not determine matplotlib version.")

        print(
            f"\n🎨 Generating matplotlib visualizations (v{matplotlib.__version__})..."
        )

        plt.style.use("default")
        plt.rcParams["figure.facecolor"] = "white"
        plt.rcParams["axes.facecolor"] = "white"

        if detailed:
            fig, axes = plt.subplots(2, 3, figsize=(18, 12))
            fig.suptitle(
                "JSON Data Analysis - Detailed View", fontsize=16, fontweight="bold"
            )
        else:
            fig, axes = plt.subplots(1, 3, figsize=(15, 5))
            fig.suptitle(
                "JSON Data Analysis - Overview", fontsize=16, fontweight="bold"
            )

        if not detailed:
            axes = [axes]

        # Plot 1: Data Types Distribution (Pie Chart)
        self._plot_data_types_pie(axes[0][0] if detailed else axes[0][0])

        # Plot 2: Depth Distribution (Bar Chart)
        self._plot_depth_distribution(axes[0][1] if detailed else axes[0][1])

        # Plot 3: Quality Metrics (Bar Chart)
        self._plot_quality_metrics(axes[0][2] if detailed else axes[0][2])

        if detailed:
            # Plot 4: Key Frequency (Horizontal Bar)
            self._plot_key_frequency(axes[1][0])

            # Plot 5: Array Sizes (Scatter)
            self._plot_array_sizes(axes[1][1])

            # Plot 6: Structure Complexity (Gauge-like)
            self._plot_complexity_score(axes[1][2])

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches="tight", facecolor="white")
            print(f"📁 Matplotlib chart saved to: {save_path}")

        plt.show()

    def _plot_data_types_pie(self, ax):
        """Plot data types distribution as pie chart."""
        data_types = self.stats["data_types"]
        if not data_types:
            ax.text(
                0.5, 0.5, "No data", ha="center", va="center", transform=ax.transAxes
            )
            ax.set_title("Data Types Distribution")
            return

        labels, sizes = zip(*data_types.most_common())
        colors = plt.cm.Set3(np.linspace(0, 1, len(labels)))

        wedges, texts, autotexts = ax.pie(
            sizes, labels=labels, colors=colors, autopct="%1.1f%%"
        )
        ax.set_title("Data Types Distribution", fontweight="bold")

    def _plot_depth_distribution(self, ax):
        """Plot depth distribution as bar chart."""
        depth_hist = self.stats["depth_histogram"]
        if not depth_hist:
            ax.text(
                0.5,
                0.5,
                "No depth data",
                ha="center",
                va="center",
                transform=ax.transAxes,
            )
            ax.set_title("Depth Distribution")
            return

        depths = sorted(depth_hist.keys())
        counts = [depth_hist[d] for d in depths]

        bars = ax.bar(depths, counts, color=self.colors["primary"], alpha=0.7)
        ax.set_xlabel("Depth Level")
        ax.set_ylabel("Number of Nodes")
        ax.set_title("Depth Distribution", fontweight="bold")
        ax.grid(True, alpha=0.3)

        # Add value labels on bars
        for bar, count in zip(bars, counts):
            height = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width() / 2.0,
                height,
                f"{count}",
                ha="center",
                va="bottom",
            )

    def _plot_quality_metrics(self, ax):
        """Plot quality metrics as horizontal bar chart."""
        patterns = self.stats["value_patterns"]
        total = self.stats["total_values"]

        if total == 0:
            ax.text(
                0.5, 0.5, "No data", ha="center", va="center", transform=ax.transAxes
            )
            ax.set_title("Quality Metrics")
            return

        metrics = [
            ("Null Values", (patterns["null_count"] / total) * 100),
            ("Empty Strings", (patterns["empty_strings"] / total) * 100),
            ("Empty Collections", (patterns["empty_collections"] / total) * 100),
        ]

        labels, values = zip(*metrics)
        colors = [self.colors["warning"], self.colors["secondary"], self.colors["info"]]

        bars = ax.barh(labels, values, color=colors, alpha=0.7)
        ax.set_xlabel("Percentage (%)")
        ax.set_title("Quality Metrics", fontweight="bold")
        ax.grid(True, axis="x", alpha=0.3)

        # Add value labels
        for bar, value in zip(bars, values):
            width = bar.get_width()
            ax.text(
                width,
                bar.get_y() + bar.get_height() / 2.0,
                f"{value:.1f}%",
                ha="left",
                va="center",
                fontweight="bold",
            )

    def _plot_key_frequency(self, ax):
        """Plot most common keys."""
        key_freq = self.stats["key_frequency"]
        if not key_freq:
            ax.text(
                0.5, 0.5, "No keys", ha="center", va="center", transform=ax.transAxes
            )
            ax.set_title("Key Frequency")
            return

        top_keys = key_freq.most_common(10)
        keys, counts = zip(*top_keys)

        bars = ax.barh(
            range(len(keys)), counts, color=self.colors["success"], alpha=0.7
        )
        ax.set_yticks(range(len(keys)))
        ax.set_yticklabels(keys)
        ax.set_xlabel("Frequency")
        ax.set_title("Most Common Keys", fontweight="bold")
        ax.grid(True, axis="x", alpha=0.3)

    def _plot_array_sizes(self, ax):
        """Plot array sizes distribution."""
        array_sizes = self.stats["structure_insights"]["array_sizes"]
        if not array_sizes:
            ax.text(
                0.5, 0.5, "No arrays", ha="center", va="center", transform=ax.transAxes
            )
            ax.set_title("Array Sizes")
            return

        sizes, counts = zip(*array_sizes.items())

        scatter = ax.scatter(sizes, counts, c=self.colors["primary"], alpha=0.6, s=100)
        ax.set_xlabel("Array Size")
        ax.set_ylabel("Frequency")
        ax.set_title("Array Size Distribution", fontweight="bold")
        ax.grid(True, alpha=0.3)

    def _plot_complexity_score(self, ax):
        """Plot complexity score as gauge."""
        score = self.stats["computed_insights"]["complexity_score"]

        # Create a simple gauge-like visualization
        theta = np.linspace(0, np.pi, 100)
        r = np.ones_like(theta)

        ax.plot(theta, r, "k-", linewidth=8, alpha=0.3)

        # Score arc
        score_theta = np.linspace(0, np.pi * (score / 100), int(score))
        score_r = np.ones_like(score_theta)

        color = (
            self.colors["success"]
            if score < 30
            else self.colors["warning"] if score < 70 else self.colors["warning"]
        )
        ax.plot(score_theta, score_r, color=color, linewidth=8)

        ax.set_ylim(0, 1.2)
        ax.set_xlim(-0.2, np.pi + 0.2)
        ax.text(
            np.pi / 2,
            0.5,
            f"{score}/100",
            ha="center",
            va="center",
            fontsize=20,
            fontweight="bold",
        )
        ax.set_title("Complexity Score", fontweight="bold")
        ax.axis("off")

    def _visualize_browser(self, save_path=None, detailed=False, open_browser=True):
        """Create interactive browser-based visualization."""
        print("\n🌐 Generating browser visualization...")

        html_content = self._generate_html_report(detailed)

        if save_path:
            file_path = Path(save_path)
            if file_path.suffix != ".html":
                file_path = file_path.with_suffix(".html")
        else:
            file_path = Path(tempfile.gettempdir()) / "json_analysis.html"

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        print(f"📁 HTML report saved to: {file_path}")

        if open_browser:
            webbrowser.open(f"file://{file_path.absolute()}")
            print("🌐 Opening in browser...")

    def _generate_html_report(self, detailed=False):
        """Generate comprehensive HTML report with interactive charts."""
        stats = self.stats
        insights = stats["computed_insights"]

        data_types_data = [
            {"name": k, "value": v} for k, v in stats["data_types"].most_common()
        ]
        depth_data = [
            {"depth": k, "count": v}
            for k, v in sorted(stats["depth_histogram"].items())
        ]

        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>JSON Data Analysis Report</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/3.9.1/chart.min.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        
        .header {{
            background: linear-gradient(135deg, {self.colors['primary']} 0%, {self.colors['secondary']} 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }}
        
        .header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }}
        
        .content {{
            padding: 40px;
        }}
        
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }}
        
        .stat-card {{
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            padding: 30px;
            border-radius: 15px;
            text-align: center;
            box-shadow: 0 10px 20px rgba(0,0,0,0.1);
            transition: transform 0.3s ease;
        }}
        
        .stat-card:hover {{
            transform: translateY(-5px);
        }}
        
        .stat-value {{
            font-size: 2.5em;
            font-weight: bold;
            color: {self.colors['primary']};
        }}
        
        .stat-label {{
            color: #666;
            font-size: 1.1em;
            margin-top: 10px;
        }}
        
        .charts-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 30px;
            margin-bottom: 40px;
        }}
        
        .chart-card {{
            background: white;
            border-radius: 15px;
            padding: 20px;
            box-shadow: 0 10px 20px rgba(0,0,0,0.1);
        }}
        
        .chart-title {{
            font-size: 1.3em;
            font-weight: bold;
            margin-bottom: 20px;
            text-align: center;
            color: {self.colors['dark']};
        }}
        
        .insights {{
            background: linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%);
            border-radius: 15px;
            padding: 30px;
            margin-top: 30px;
        }}
        
        .insights h3 {{
            color: {self.colors['dark']};
            margin-bottom: 20px;
        }}
        
        .insight-item {{
            background: rgba(255,255,255,0.7);
            padding: 15px;
            border-radius: 10px;
            margin-bottom: 10px;
        }}
        
        .quality-issues {{
            background: linear-gradient(135deg, #ffeaa7 0%, #fab1a0 100%);
            border-radius: 10px;
            padding: 20px;
            margin-top: 20px;
        }}
        
        .issue {{
            background: rgba(255,255,255,0.8);
            padding: 10px;
            border-radius: 5px;
            margin: 5px 0;
            border-left: 4px solid {self.colors['warning']};
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎨 JSON Data Analysis Report</h1>
            <p>Comprehensive analysis of your data structure</p>
        </div>
        
        <div class="content">
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-value">{stats['total_values']:,}</div>
                    <div class="stat-label">Total Values</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{stats['total_keys']:,}</div>
                    <div class="stat-label">Total Keys</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{stats['max_depth']}</div>
                    <div class="stat-label">Max Depth</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{insights['complexity_score']}/100</div>
                    <div class="stat-label">Complexity Score</div>
                </div>
            </div>
            
            <div class="charts-grid">
                <div class="chart-card">
                    <div class="chart-title">📊 Data Types Distribution</div>
                    <canvas id="dataTypesChart"></canvas>
                </div>
                <div class="chart-card">
                    <div class="chart-title">📏 Depth Distribution</div>
                    <canvas id="depthChart"></canvas>
                </div>
                <div class="chart-card">
                    <div class="chart-title">🎯 Quality Metrics</div>
                    <canvas id="qualityChart"></canvas>
                </div>
            </div>
            
            <div class="insights">
                <h3>🔍 Key Insights</h3>
                <div class="insight-item">
                    <strong>Most Common Type:</strong> {insights['most_common_type'][0] if insights['most_common_type'] else 'N/A'} 
                    ({insights['most_common_type'][1] if insights['most_common_type'] else 0} occurrences)
                </div>
                <div class="insight-item">
                    <strong>Structure Uniformity:</strong> {insights['structure_uniformity'].replace('_', ' ').title()}
                </div>
                
                {f'''
                <div class="quality-issues">
                    <h4>⚠️ Data Quality Issues</h4>
                    {"".join(f'<div class="issue">• {issue}</div>' for issue in insights['data_quality_issues'])}
                </div>
                ''' if insights['data_quality_issues'] else ''}
            </div>
        </div>
    </div>
    
    <script>
        // Data Types Chart
        const dataTypesCtx = document.getElementById('dataTypesChart').getContext('2d');
        new Chart(dataTypesCtx, {{
            type: 'doughnut',
            data: {{
                labels: {json.dumps([item['name'] for item in data_types_data])},
                datasets: [{{
                    data: {json.dumps([item['value'] for item in data_types_data])},
                    backgroundColor: [
                        '{self.colors["primary"]}',
                        '{self.colors["secondary"]}',
                        '{self.colors["success"]}',
                        '{self.colors["warning"]}',
                        '{self.colors["info"]}',
                        '#FF6B6B',
                        '#4ECDC4',
                        '#45B7D1'
                    ]
                }}]
            }},
            options: {{
                responsive: true,
                plugins: {{
                    legend: {{
                        position: 'bottom'
                    }}
                }}
            }}
        }});
        
        // Depth Chart
        const depthCtx = document.getElementById('depthChart').getContext('2d');
        new Chart(depthCtx, {{
            type: 'bar',
            data: {{
                labels: {json.dumps([f"Depth {item['depth']}" for item in depth_data])},
                datasets: [{{
                    label: 'Node Count',
                    data: {json.dumps([item['count'] for item in depth_data])},
                    backgroundColor: '{self.colors["primary"]}',
                    borderColor: '{self.colors["primary"]}',
                    borderWidth: 1
                }}]
            }},
            options: {{
                responsive: true,
                scales: {{
                    y: {{
                        beginAtZero: true
                    }}
                }}
            }}
        }});
        
        // Quality Metrics Chart
        const qualityCtx = document.getElementById('qualityChart').getContext('2d');
        const total = {stats['total_values']};
        
        if (total > 0) {{
            const qualityData = [
                (({stats['value_patterns']['null_count']} / total) * 100),
                (({stats['value_patterns']['empty_strings']} / total) * 100),
                (({stats['value_patterns']['empty_collections']} / total) * 100)
            ];
            
            new Chart(qualityCtx, {{
                type: 'bar',
                data: {{
                    labels: ['Null Values %', 'Empty Strings %', 'Empty Collections %'],
                    datasets: [{{
                        label: 'Percentage',
                        data: qualityData,
                        backgroundColor: [
                            '{self.colors["warning"]}',
                            '{self.colors["secondary"]}',
                            '{self.colors["info"]}'
                        ],
                        borderColor: [
                            '{self.colors["warning"]}',
                            '{self.colors["secondary"]}',
                            '{self.colors["info"]}'
                        ],
                        borderWidth: 1
                    }}]
                }},
                options: {{
                    responsive: true,
                    scales: {{
                        y: {{
                            beginAtZero: true,
                            max: 100,
                            ticks: {{
                                callback: function(value) {{
                                    return value + '%';
                                }}
                            }}
                        }}
                    }},
                    plugins: {{
                        tooltip: {{
                            callbacks: {{
                                label: function(context) {{
                                    return context.dataset.label + ': ' + context.parsed.y.toFixed(1) + '%';
                                }}
                            }}
                        }}
                    }}
                }}
            }});
        }} else {{
            qualityCtx.font = '16px sans-serif';
            qualityCtx.fillStyle = '#666';
            qualityCtx.textAlign = 'center';
            qualityCtx.fillText('No data available', qualityCtx.canvas.width / 2, qualityCtx.canvas.height / 2);
        }};
    </script>
</body>
</html>
        """

        return html


def visualize_json(
    data, output="terminal", save_path=None, detailed=False, open_browser=True
):
    """
    Convenience function to visualize JSON data statistics.

    Args:
        data: JSON data to analyze and visualize
        output: Output format ('terminal', 'matplotlib', 'browser', 'all')
        save_path: Path to save files (for matplotlib and browser outputs)
        detailed: Whether to show detailed visualizations
        open_browser: Whether to automatically open browser for HTML output
    """
    visualizer = JSONVisualizer()
    visualizer.visualize(data, output, save_path, detailed, open_browser)


if __name__ == "__main__":
    sample_data = {
        "users": [
            {
                "id": 1,
                "name": "Alice",
                "email": "alice@example.com",
                "profile": {"age": 30, "city": "NYC"},
                "tags": ["admin", "power-user"],
            },
            {
                "id": 2,
                "name": "Bob",
                "email": None,
                "profile": {"age": 25, "city": "LA"},
                "tags": [],
            },
            {
                "id": 3,
                "name": "",
                "email": "charlie@example.com",
                "profile": None,
                "tags": ["user"],
            },
        ],
        "metadata": {
            "total_count": 3,
            "last_updated": "2025-06-26",
            "settings": {
                "notifications": True,
                "privacy": {"level": "high", "options": ["email", "sms"]},
            },
        },
        "empty_list": [],
        "numbers": [1, 2, 3, 4, 5, 100, 200],
        "tags": ["user", "data", "sample"],
    }

    print("🎨 JSON Visualizer Demo")
    print("Available outputs: terminal, matplotlib, browser, all")

    visualizer = JSONVisualizer()

    visualizer.visualize(sample_data, output="terminal", detailed=True)
    visualizer.visualize(sample_data, output="matplotlib", detailed=True)
    visualizer.visualize(sample_data, output="browser", detailed=True)
