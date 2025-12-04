"""JSON structure analyzer with type detection and schema inference.

This module analyzes JSON data structures to detect types, optional fields,
conflicts, and generates comprehensive structural summaries.
"""

from collections import Counter
from typing import Any

import dateparser
from rich.progress import Progress, SpinnerColumn, TextColumn

from .logging_config import get_logger

logger = get_logger(__name__)


def detect_timestamp(value: Any) -> bool:
    """Detect if a string value is a timestamp.

    Args:
        value: Value to check.

    Returns:
        True if the value is a parseable timestamp, False otherwise.
    """
    if not isinstance(value, str) or len(value) < 4:
        return False

    try:
        parsed = dateparser.parse(value)
        return parsed is not None
    except Exception:
        return False


def analyze_json(data: Any) -> dict[str, Any]:
    """Analyze JSON structure and return detailed metadata.

    This function performs deep structural analysis of JSON data, identifying:
    - Data types and their distribution
    - Optional and required fields
    - Type conflicts across similar structures
    - Nested object and array patterns

    Args:
        data: JSON data to analyze (dict, list, or primitive type).

    Returns:
        Dictionary containing analysis summary with structure, types, and conflicts.

    Example:
        >>> data = {"users": [{"id": 1, "name": "Alice"}]}
        >>> analysis = analyze_json(data)
        >>> print(analysis['type'])
        'object'
    """
    logger.info("Starting JSON analysis")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=None,
        transient=True,
    ) as progress:
        task = progress.add_task("[cyan]Analyzing JSON...", total=None)

        def analyze_node(node: Any) -> dict[str, Any]:
            """Recursively analyze a node in the JSON structure."""
            if isinstance(node, dict):
                children = {}
                for key, val in node.items():
                    progress.update(task, advance=1)
                    children[key] = analyze_node(val)
                return {"type": "object", "children": children}

            elif isinstance(node, list):
                # Skip empty or null-only lists
                non_empty_items = [
                    item for item in node if item not in (None, {}, [], "")
                ]
                if not non_empty_items:
                    return {"type": "list", "child_type": "unknown"}

                sample = non_empty_items[:20]
                element_summaries = [analyze_node(item) for item in sample]
                types = {e["type"] for e in element_summaries}

                # List of primitives
                if len(types) == 1 and all(
                    e["type"] not in {"object", "list"} for e in element_summaries
                ):
                    return {"type": "list", "child_type": types.pop()}

                # List of objects
                if all(e["type"] == "object" for e in element_summaries):
                    merged, conflicts = merge_object_summaries(element_summaries)
                    return {
                        "type": "list",
                        "child": {
                            "type": "object",
                            "children": merged,
                            "conflicts": conflicts,
                        },
                    }

                # List of lists
                if all(e["type"] == "list" for e in element_summaries):
                    merged_list = merge_list_summaries(element_summaries)
                    return {"type": "list", "child": merged_list}

                return {"type": "list", "child_type": "mixed"}

            elif node is None:
                return {"type": "unknown", "is_none": True}

            else:
                if isinstance(node, str):
                    if detect_timestamp(node):
                        return {"type": "timestamp"}
                    else:
                        return {"type": "str"}
                else:
                    return {"type": type(node).__name__}

        def merge_object_summaries(
            summaries: list[dict[str, Any]],
        ) -> tuple[dict[str, Any], dict[str, list[str]]]:
            """Merge multiple object summaries, detecting optional fields and conflicts."""
            key_structures: dict[str, list] = {}
            key_counts = Counter()
            key_none_counts = Counter()
            total = len(summaries)

            for summary in summaries:
                seen_keys = set()

                for key, val in summary.get("children", {}).items():
                    key_counts[key] += 1
                    seen_keys.add(key)

                    if val.get("type") == "unknown":
                        key_none_counts[key] += 1

                    if key not in key_structures:
                        key_structures[key] = []
                    key_structures[key].append(val)

            merged: dict[str, Any] = {}
            conflicts: dict[str, list[str]] = {}

            for key, structures in key_structures.items():
                count = key_counts[key]
                none_count = key_none_counts[key]

                # Field is optional if missing or has None values
                optional = (count < total) or (none_count > 0)

                # Filter out None/unknown types
                concrete_structures = [
                    s for s in structures if s.get("type") != "unknown"
                ]

                working_structures = (
                    concrete_structures if concrete_structures else structures
                )

                types = {s["type"] for s in working_structures}

                if len(types) == 1:
                    structure_type = list(types)[0]

                    if structure_type == "object":
                        merged_children, child_conflicts = merge_object_summaries(
                            working_structures
                        )
                        merged[key] = {
                            "type": "object",
                            "children": merged_children,
                            "optional": optional,
                        }
                        if child_conflicts:
                            merged[key]["conflicts"] = child_conflicts

                    elif structure_type == "list":
                        merged_list = merge_list_summaries(working_structures)
                        merged[key] = {
                            "type": "list",
                            "optional": optional,
                            **{k: v for k, v in merged_list.items() if k != "type"},
                        }

                    else:
                        merged[key] = {"type": structure_type, "optional": optional}

                elif len(types) > 1:
                    merged[key] = {"type": "conflict", "optional": optional}
                    conflicts[key] = list(types)

                else:
                    merged[key] = {"type": "unknown", "optional": optional}

            return merged, conflicts

        def merge_list_summaries(summaries: list[dict[str, Any]]) -> dict[str, Any]:
            """Merge multiple list summaries."""
            child_types = set()
            child_structures = []

            for summary in summaries:
                if "child_type" in summary:
                    child_types.add(summary["child_type"])
                elif "child" in summary:
                    child_structures.append(summary["child"])

            if child_structures:
                structure_types = {s["type"] for s in child_structures}

                if len(structure_types) == 1:
                    structure_type = list(structure_types)[0]

                    if structure_type == "object":
                        merged_children, child_conflicts = merge_object_summaries(
                            child_structures
                        )
                        return {
                            "type": "list",
                            "child": {
                                "type": "object",
                                "children": merged_children,
                                "conflicts": child_conflicts,
                            },
                        }
                    elif structure_type == "list":
                        merged_nested = merge_list_summaries(child_structures)
                        return {"type": "list", "child": merged_nested}

                return {"type": "list", "child_type": "mixed_complex"}

            elif child_types:
                if len(child_types) == 1:
                    return {"type": "list", "child_type": list(child_types)[0]}
                else:
                    return {
                        "type": "list",
                        "child_type": f"mixed: {', '.join(sorted(child_types))}",
                    }

            return {"type": "list", "child_type": "unknown"}

        result = analyze_node(data)
        logger.info("JSON analysis completed successfully")
        return result
