from collections import Counter


def analyze_json(data):
    def analyze_node(node):
        if isinstance(node, dict):
            children = {}
            for key, val in node.items():
                children[key] = analyze_node(val)
            return {"type": "object", "children": children}
        elif isinstance(node, list):
            # Skip empty or null-only lists
            non_empty_items = [item for item in node if item not in (None, {}, [], "")]
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
                # Merge list structures recursively
                merged_list = merge_list_summaries(element_summaries)
                return {
                    "type": "list",
                    "child": merged_list,
                }

            return {"type": "list", "child_type": "mixed"}
        else:
            return {"type": type(node).__name__}

    def merge_object_summaries(summaries):
        key_structures = {}
        key_counts = Counter()
        total = len(summaries)

        for summary in summaries:
            for key, val in summary.get("children", {}).items():
                key_counts[key] += 1
                if key not in key_structures:
                    key_structures[key] = []
                key_structures[key].append(val)

        merged = {}
        conflicts = {}

        for key, structures in key_structures.items():
            count = key_counts[key]
            optional = count < total

            # Get unique types for this key
            types = {s["type"] for s in structures}

            if len(types) == 1:
                # All structures have the same type
                structure_type = list(types)[0]

                if structure_type == "object":
                    # Recursively merge object structures
                    merged_children, child_conflicts = merge_object_summaries(
                        structures
                    )
                    merged[key] = {
                        "type": "object",
                        "children": merged_children,
                        "optional": optional,
                    }
                    if child_conflicts:
                        merged[key]["conflicts"] = child_conflicts

                elif structure_type == "list":
                    # Merge list structures
                    merged_list = merge_list_summaries(structures)
                    merged[key] = {
                        "type": "list",
                        "optional": optional,
                        **{k: v for k, v in merged_list.items() if k != "type"},
                    }

                else:
                    # Primitive type
                    merged[key] = {"type": structure_type, "optional": optional}
            else:
                # Type conflict
                merged[key] = {"type": "conflict", "optional": optional}
                conflicts[key] = list(types)

        return merged, conflicts

    def merge_list_summaries(summaries):
        child_types = set()
        child_structures = []

        for summary in summaries:
            if "child_type" in summary:
                child_types.add(summary["child_type"])
            elif "child" in summary:
                child_structures.append(summary["child"])

        if child_structures:
            # All lists contain complex structures
            structure_types = {s["type"] for s in child_structures}

            if len(structure_types) == 1:
                structure_type = list(structure_types)[0]

                if structure_type == "object":
                    # Merge object structures within lists
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
                    # Nested lists
                    merged_nested = merge_list_summaries(child_structures)
                    return {"type": "list", "child": merged_nested}

            return {"type": "list", "child_type": "mixed_complex"}

        elif child_types:
            # Simple child types
            if len(child_types) == 1:
                return {"type": "list", "child_type": list(child_types)[0]}
            else:
                return {
                    "type": "list",
                    "child_type": f"mixed: {', '.join(sorted(child_types))}",
                }

        return {"type": "list", "child_type": "unknown"}

    return analyze_node(data)


if __name__ == "__main__":
    from rich import print as rprint
    from rich.pretty import pretty_repr

    test_data = {
        "users": [
            {
                "id": 1,
                "name": "Alice",
                "profile": {
                    "age": 30,
                    "settings": {"theme": "dark", "notifications": True},
                },
                "tags": ["admin", "user"],
            },
            {
                "id": 2,
                "name": "Bob",
                "profile": {
                    "age": 25,
                    "settings": {
                        "theme": "light",
                        "notifications": False,
                        "language": "en",
                    },
                },
                "tags": ["user"],
                "email": "bob@example.com",
            },
        ],
        "metadata": {"total": 2, "created": "2024-01-01"},
    }

    summary = analyze_json(test_data)
    rprint(pretty_repr(summary))
