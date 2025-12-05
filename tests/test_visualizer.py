"""Unit tests for the visualizer module."""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from json_explorer.visualizer import JSONVisualizer, visualize_json


@pytest.fixture
def sample_data():
    """Sample JSON data for testing."""
    return {
        "users": [
            {"id": 1, "name": "Alice", "age": 30, "active": True},
            {"id": 2, "name": "Bob", "age": 25, "active": False},
            {"id": 3, "name": "Charlie", "age": 35, "active": True},
        ],
        "metadata": {"total": 3, "created": "2024-01-01", "tags": ["test", "sample"]},
    }


@pytest.fixture
def simple_data():
    """Simple data for basic tests."""
    return {"value": 42, "text": "hello", "flag": True}


@pytest.fixture
def visualizer():
    """Create a JSONVisualizer instance."""
    return JSONVisualizer()


class TestVisualizerInitialization:
    """Test visualizer initialization."""

    def test_init(self, visualizer):
        """Test basic initialization."""
        assert visualizer.stats is None
        assert visualizer.colors is not None
        assert "primary" in visualizer.colors
        assert "secondary" in visualizer.colors

    def test_color_scheme(self, visualizer):
        """Test color scheme is properly defined."""
        required_colors = ["primary", "secondary", "success", "warning", "info"]
        for color in required_colors:
            assert color in visualizer.colors
            assert isinstance(visualizer.colors[color], str)


class TestTerminalVisualization:
    """Test terminal visualization output."""

    @patch("json_explorer.visualizer.CURSES_AVAILABLE", False)
    def test_terminal_fallback(self, visualizer, simple_data, capsys):
        """Test terminal fallback when curses unavailable."""
        visualizer.visualize(simple_data, output="terminal")

        captured = capsys.readouterr()
        assert "JSON DATA VISUALIZATION" in captured.out or captured.err
        assert "DATA TYPES DISTRIBUTION" in captured.out

    @patch("json_explorer.visualizer.CURSES_AVAILABLE", False)
    def test_terminal_fallback_detailed(self, visualizer, sample_data, capsys):
        """Test detailed terminal fallback."""
        visualizer.visualize(sample_data, output="terminal", detailed=True)

        captured = capsys.readouterr()
        assert "QUALITY METRICS" in captured.out

    @patch("json_explorer.visualizer.CURSES_AVAILABLE", True)
    @patch("json_explorer.visualizer.curses")
    def test_curses_visualization(self, mock_curses, visualizer, simple_data):
        """Test curses visualization when available."""
        mock_stdscr = MagicMock()
        mock_stdscr.getmaxyx.return_value = (50, 100)
        mock_stdscr.getch.return_value = ord("q")
        mock_curses.wrapper.side_effect = lambda f, detailed: f(mock_stdscr, detailed)

        visualizer.visualize(simple_data, output="terminal")

        # Verify curses was used
        assert mock_stdscr.clear.called
        assert mock_stdscr.refresh.called


class TestPlotlyVisualization:
    """Test Plotly visualization output."""

    @patch("json_explorer.visualizer.PLOTLY_AVAILABLE", False)
    def test_plotly_unavailable(self, visualizer, simple_data):
        """Test error when Plotly unavailable."""
        with pytest.raises(RuntimeError, match="Plotly not available"):
            visualizer.visualize(simple_data, output="html")

    @patch("json_explorer.visualizer.PLOTLY_AVAILABLE", True)
    @patch("json_explorer.visualizer.make_subplots")
    @patch("json_explorer.visualizer.webbrowser")
    def test_html_output(self, mock_browser, mock_subplots, visualizer, sample_data):
        """Test HTML output generation."""
        mock_fig = MagicMock()
        mock_subplots.return_value = mock_fig

        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as f:
            output_path = f.name

        try:
            visualizer.visualize(
                sample_data, output="html", save_path=output_path, open_browser=False
            )

            assert mock_fig.write_html.called
            assert Path(output_path).exists()
        finally:
            Path(output_path).unlink(missing_ok=True)

    @patch("json_explorer.visualizer.PLOTLY_AVAILABLE", True)
    @patch("json_explorer.visualizer.make_subplots")
    @patch("json_explorer.visualizer.webbrowser.open")
    def test_html_open_browser(
        self, mock_browser_open, mock_subplots, visualizer, simple_data
    ):
        """Test browser auto-open functionality."""
        mock_fig = MagicMock()
        mock_subplots.return_value = mock_fig

        visualizer.visualize(simple_data, output="html", open_browser=True)

        assert mock_browser_open.called

    @patch("json_explorer.visualizer.PLOTLY_AVAILABLE", True)
    @patch("json_explorer.visualizer.make_subplots")
    def test_html_detailed(self, mock_subplots, visualizer, sample_data):
        """Test detailed HTML visualization."""
        mock_fig = MagicMock()
        mock_subplots.return_value = mock_fig

        visualizer.visualize(
            sample_data, output="html", detailed=True, open_browser=False
        )

        # Detailed mode should have more subplots
        call_args = mock_subplots.call_args
        assert call_args is not None


class TestOutputFormats:
    """Test different output format handling."""

    def test_invalid_output_format(self, visualizer, simple_data):
        """Test invalid output format raises error."""
        with pytest.raises(ValueError, match="Unknown output format"):
            visualizer.visualize(simple_data, output="invalid_format")

    @patch("json_explorer.visualizer.CURSES_AVAILABLE", False)
    @patch("json_explorer.visualizer.PLOTLY_AVAILABLE", True)
    @patch("json_explorer.visualizer.make_subplots")
    def test_all_format(self, mock_subplots, visualizer, simple_data, capsys):
        """Test 'all' format generates both outputs."""
        mock_fig = MagicMock()
        mock_subplots.return_value = mock_fig

        visualizer.visualize(simple_data, output="all", open_browser=False)

        # Check terminal output
        captured = capsys.readouterr()
        assert "DATA TYPES DISTRIBUTION" in captured.out

        # Check HTML generation
        assert mock_fig.write_html.called


class TestStatisticsGeneration:
    """Test statistics generation for visualization."""

    def test_stats_generated(self, visualizer, sample_data):
        """Test that statistics are generated."""
        assert visualizer.stats is None

        with patch("json_explorer.visualizer.CURSES_AVAILABLE", False):
            visualizer.visualize(sample_data, output="terminal")

        assert visualizer.stats is not None
        assert "total_values" in visualizer.stats
        assert "data_types" in visualizer.stats

    def test_stats_structure(self, visualizer, sample_data):
        """Test generated statistics structure."""
        with patch("json_explorer.visualizer.CURSES_AVAILABLE", False):
            visualizer.visualize(sample_data, output="terminal")

        stats = visualizer.stats
        assert stats["total_values"] > 0
        assert "max_depth" in stats
        assert "depth_histogram" in stats
        assert "value_patterns" in stats
        assert "computed_insights" in stats


class TestChartGeneration:
    """Test individual chart generation methods."""

    @patch("json_explorer.visualizer.PLOTLY_AVAILABLE", True)
    @patch("json_explorer.visualizer.go")
    def test_data_types_chart(self, mock_go, visualizer, sample_data):
        """Test data types chart generation."""
        from json_explorer.stats import DataStatsAnalyzer

        analyzer = DataStatsAnalyzer()
        visualizer.stats = analyzer.generate_stats(sample_data)

        mock_fig = MagicMock()
        visualizer._add_data_types_chart(mock_fig, 1, 1)

        assert mock_fig.add_trace.called

    @patch("json_explorer.visualizer.PLOTLY_AVAILABLE", True)
    @patch("json_explorer.visualizer.go")
    def test_depth_chart(self, mock_go, visualizer, sample_data):
        """Test depth distribution chart generation."""
        from json_explorer.stats import DataStatsAnalyzer

        analyzer = DataStatsAnalyzer()
        visualizer.stats = analyzer.generate_stats(sample_data)

        mock_fig = MagicMock()
        visualizer._add_depth_chart(mock_fig, 1, 1)

        assert mock_fig.add_trace.called

    @patch("json_explorer.visualizer.PLOTLY_AVAILABLE", True)
    @patch("json_explorer.visualizer.go")
    def test_quality_metrics_chart(self, mock_go, visualizer, sample_data):
        """Test quality metrics chart generation."""
        from json_explorer.stats import DataStatsAnalyzer

        analyzer = DataStatsAnalyzer()
        visualizer.stats = analyzer.generate_stats(sample_data)

        mock_fig = MagicMock()
        visualizer._add_quality_metrics(mock_fig, 1, 1)

        assert mock_fig.add_trace.called


class TestEdgeCases:
    """Test edge cases and special scenarios."""

    @patch("json_explorer.visualizer.CURSES_AVAILABLE", False)
    def test_empty_data(self, visualizer, capsys):
        """Test visualization of empty data."""
        visualizer.visualize({}, output="terminal")

        captured = capsys.readouterr()
        assert "DATA TYPES DISTRIBUTION" in captured.out

    @patch("json_explorer.visualizer.CURSES_AVAILABLE", False)
    def test_simple_scalar(self, visualizer, capsys):
        """Test visualization of simple scalar value."""
        visualizer.visualize(42, output="terminal")

        captured = capsys.readouterr()
        assert "DATA TYPES DISTRIBUTION" in captured.out

    @patch("json_explorer.visualizer.CURSES_AVAILABLE", False)
    def test_list_data(self, visualizer, capsys):
        """Test visualization of list data."""
        data = [1, 2, 3, 4, 5]
        visualizer.visualize(data, output="terminal")

        captured = capsys.readouterr()
        assert "DATA TYPES DISTRIBUTION" in captured.out

    @patch("json_explorer.visualizer.CURSES_AVAILABLE", False)
    def test_deeply_nested_data(self, visualizer, capsys):
        """Test visualization of deeply nested data."""
        data = {"level1": {"level2": {"level3": {"level4": {"value": 42}}}}}
        visualizer.visualize(data, output="terminal")

        captured = capsys.readouterr()
        assert "DATA TYPES DISTRIBUTION" in captured.out

    @patch("json_explorer.visualizer.CURSES_AVAILABLE", False)
    def test_null_values(self, visualizer, capsys):
        """Test visualization with null values."""
        data = {"field1": None, "field2": "value", "field3": None}
        visualizer.visualize(data, output="terminal")

        captured = capsys.readouterr()
        assert "QUALITY METRICS" in captured.out or "DATA TYPES" in captured.out


class TestSavePathHandling:
    """Test save path handling for HTML output."""

    @patch("json_explorer.visualizer.PLOTLY_AVAILABLE", True)
    @patch("json_explorer.visualizer.make_subplots")
    def test_save_path_without_extension(self, mock_subplots, visualizer, simple_data):
        """Test save path without .html extension."""
        mock_fig = MagicMock()
        mock_subplots.return_value = mock_fig

        with tempfile.TemporaryDirectory() as tmpdir:
            save_path = Path(tmpdir) / "output"
            visualizer.visualize(
                simple_data, output="html", save_path=str(save_path), open_browser=False
            )

            # Should add .html extension
            call_args = mock_fig.write_html.call_args
            assert call_args is not None
            assert call_args[0][0].endswith(".html")

    @patch("json_explorer.visualizer.PLOTLY_AVAILABLE", True)
    @patch("json_explorer.visualizer.make_subplots")
    def test_save_path_with_extension(self, mock_subplots, visualizer, simple_data):
        """Test save path with .html extension."""
        mock_fig = MagicMock()
        mock_subplots.return_value = mock_fig

        with tempfile.TemporaryDirectory() as tmpdir:
            save_path = Path(tmpdir) / "output.html"
            visualizer.visualize(
                simple_data, output="html", save_path=str(save_path), open_browser=False
            )

            call_args = mock_fig.write_html.call_args
            assert call_args is not None
            assert str(save_path) in call_args[0][0]


class TestConvenienceFunction:
    """Test the convenience function."""

    @patch("json_explorer.visualizer.CURSES_AVAILABLE", False)
    def test_visualize_json_function(self, simple_data, capsys):
        """Test visualize_json convenience function."""
        visualize_json(simple_data, output="terminal", detailed=True)

        # Verify it produces output
        captured = capsys.readouterr()
        assert "DATA TYPES DISTRIBUTION" in captured.out or captured.err


class TestTerminalCharts:
    """Test terminal chart generation methods."""

    @patch("json_explorer.visualizer.CURSES_AVAILABLE", False)
    def test_terminal_data_types_chart(self, visualizer, sample_data, capsys):
        """Test terminal data types chart."""
        from json_explorer.stats import DataStatsAnalyzer

        analyzer = DataStatsAnalyzer()
        visualizer.stats = analyzer.generate_stats(sample_data)

        visualizer._terminal_data_types_chart()

        captured = capsys.readouterr()
        assert "DATA TYPES DISTRIBUTION" in captured.out

    @patch("json_explorer.visualizer.CURSES_AVAILABLE", False)
    def test_terminal_depth_histogram(self, visualizer, sample_data, capsys):
        """Test terminal depth histogram."""
        from json_explorer.stats import DataStatsAnalyzer

        analyzer = DataStatsAnalyzer()
        visualizer.stats = analyzer.generate_stats(sample_data)

        visualizer._terminal_depth_histogram()

        captured = capsys.readouterr()
        assert "DEPTH DISTRIBUTION" in captured.out

    @patch("json_explorer.visualizer.CURSES_AVAILABLE", False)
    def test_terminal_quality_metrics(self, visualizer, sample_data, capsys):
        """Test terminal quality metrics."""
        from json_explorer.stats import DataStatsAnalyzer

        analyzer = DataStatsAnalyzer()
        visualizer.stats = analyzer.generate_stats(sample_data)

        visualizer._terminal_quality_metrics()

        captured = capsys.readouterr()
        assert "QUALITY METRICS" in captured.out


class TestDataWithVariousPatterns:
    """Test visualization with various data patterns."""

    @patch("json_explorer.visualizer.CURSES_AVAILABLE", False)
    def test_data_with_arrays(self, visualizer, capsys):
        """Test data containing arrays."""
        data = {"items": [1, 2, 3], "tags": ["a", "b", "c"], "matrix": [[1, 2], [3, 4]]}
        visualizer.visualize(data, output="terminal")

        captured = capsys.readouterr()
        assert "DATA TYPES DISTRIBUTION" in captured.out

    @patch("json_explorer.visualizer.CURSES_AVAILABLE", False)
    def test_data_with_mixed_types(self, visualizer, capsys):
        """Test data with mixed types."""
        data = {
            "string": "text",
            "number": 42,
            "float": 3.14,
            "bool": True,
            "null": None,
            "array": [1, 2, 3],
            "object": {"nested": "value"},
        }
        visualizer.visualize(data, output="terminal")

        captured = capsys.readouterr()
        assert "DATA TYPES DISTRIBUTION" in captured.out

    @patch("json_explorer.visualizer.CURSES_AVAILABLE", False)
    def test_data_with_empty_collections(self, visualizer, capsys):
        """Test data with empty collections."""
        data = {
            "empty_list": [],
            "empty_dict": {},
            "empty_string": "",
            "normal": "value",
        }
        visualizer.visualize(data, output="terminal", detailed=True)

        captured = capsys.readouterr()
        assert "QUALITY METRICS" in captured.out or "DATA TYPES" in captured.out
