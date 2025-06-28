import pytest
from unittest.mock import patch, MagicMock
import collections

from json_explorer.visualizer import JSONVisualizer, visualize_json


@pytest.fixture
def sample_data():
    return {"key": "value", "list": [1, 2, 3], "nested": {"a": None, "b": ""}}


@pytest.fixture
def mocked_stats():
    return {
        "data_types": collections.Counter({"int": 3, "str": 2}),
        "depth_histogram": {1: 2, 2: 3},
        "key_frequency": collections.Counter({"key": 2, "list": 1}),
        "structure_insights": {"array_sizes": {3: 1}},
        "value_patterns": {
            "null_count": 1,
            "empty_strings": 1,
            "empty_collections": 0,
            "string_lengths": {"avg": 3.2},
            "numeric_ranges": {"min": 1, "max": 100},
        },
        "total_values": 10,
        "total_keys": 5,
        "max_depth": 3,
        "computed_insights": {
            "complexity_score": 42,
            "structure_uniformity": "semi_structured",
            "most_common_type": ("int", 4),
            "data_quality_issues": ["High null count"],
        },
    }


@patch("json_explorer.visualizer.DataStatsAnalyzer")
def test_visualize_terminal(mock_analyzer, sample_data, mocked_stats):
    mock_analyzer.return_value.generate_stats.return_value = mocked_stats
    visualizer = JSONVisualizer()

    with patch("builtins.print") as mock_print:
        visualizer.visualize(sample_data, output="terminal", detailed=False)
        assert visualizer.stats["total_values"] == 10
        mock_print.assert_any_call("\n" + "=" * 60)


@patch("json_explorer.visualizer.DataStatsAnalyzer")
@patch("json_explorer.visualizer.webbrowser.open")
def test_visualize_browser(mock_webbrowser, mock_analyzer, sample_data, mocked_stats):
    mock_analyzer.return_value.generate_stats.return_value = mocked_stats
    visualizer = JSONVisualizer()

    with patch("builtins.print") as mock_print:
        visualizer.visualize(sample_data, output="browser", detailed=False)
        mock_webbrowser.assert_called_once()
        mock_print.assert_any_call("\n🌐 Generating browser visualization...")


@patch("json_explorer.visualizer.DataStatsAnalyzer")
@patch("json_explorer.visualizer.plt")
def test_visualize_matplotlib(mock_plt, mock_analyzer, sample_data, mocked_stats):
    mock_analyzer.return_value.generate_stats.return_value = mocked_stats

    mock_fig = MagicMock()
    mock_ax1 = MagicMock()
    mock_ax2 = MagicMock()
    mock_ax3 = MagicMock()

    mock_ax1.pie.return_value = ("wedges", "texts", "autotexts")

    mock_ax2.bar.return_value = [
        MagicMock(get_height=lambda: 10, get_x=lambda: 0, get_width=lambda: 1)
    ]
    mock_ax3.barh.return_value = [
        MagicMock(get_width=lambda: 50, get_y=lambda: 0, get_height=lambda: 1)
    ]

    mock_plt.subplots.return_value = (mock_fig, [mock_ax1, mock_ax2, mock_ax3])

    visualizer = JSONVisualizer()

    with patch("builtins.print"):
        visualizer.visualize(sample_data, output="matplotlib", detailed=False)

    mock_plt.show.assert_called_once()
    mock_plt.subplots.assert_called_once()


@patch("json_explorer.visualizer.JSONVisualizer.visualize")
def test_visualize_json_function(mock_vis):
    data = {"key": "value"}
    visualize_json(data, output="all")
    mock_vis.assert_called_once()
