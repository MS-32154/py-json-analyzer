"""Full-screen terminal UI (Textual) for exploring JSON and generating code.

Tabs: the data itself, its inferred structure, JMESPath search, statistics
(with the HTML report), and code generation with a live preview for every
registered language and JSON Schema. Code options come from each language
plugin's CLI options, so new languages appear without UI code.
"""

import json
from pathlib import Path
from typing import Any, ClassVar

import jmespath
from jmespath.exceptions import JMESPathError
from rich.json import JSON as RichJSON
from rich.syntax import Syntax
from rich.text import Text
from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    Select,
    Static,
    Switch,
    TabbedContent,
    TabPane,
    Tree,
)
from textual.widgets.tree import TreeNode

from .analyzer import Kind, Node, analyze_json
from .codegen import all_plugins, generate_from_analysis, get_plugin
from .codegen.core.plugin import CliOption
from .json_schema import to_json_schema
from .search import JsonSearcher
from .stats import DataStatsAnalyzer
from .tree_view import JsonTreeBuilder
from .visualizer import JSONVisualizer

JSON_SCHEMA = "jsonschema"
MAX_CHILDREN = 500  # per tree node; the rest is summarized
LEXERS = {"go": "go", "python": "python", "typescript": "typescript", "rust": "rust"}


def _preview(value: Any) -> Text:
    """One-line summary of a JSON value for the data tree."""
    match value:
        case dict():
            return Text(f"{{{len(value)} keys}}", style="dim")
        case list():
            return Text(f"[{len(value)} items]", style="dim")
        case str():
            shown = value if len(value) <= 80 else value[:77] + "..."
            return Text(json.dumps(shown, ensure_ascii=False), style="green")
        case bool() | None:
            return Text(json.dumps(value), style="yellow")
        case _:
            return Text(str(value), style="dark_orange")


class DataTree(Tree[Any]):
    """The JSON document itself; children are created when a node is expanded."""

    def __init__(self, data: Any, label: str) -> None:
        super().__init__(Text(label, style="bold"), data=data, id="data-tree")

    def on_mount(self) -> None:
        if isinstance(self.root.data, dict | list):
            self._fill(self.root)
        self.root.expand()

    def _fill(self, node: TreeNode[Any]) -> None:
        value: Any = node.data
        items = (
            list(value.items()) if isinstance(value, dict) else list(enumerate(value))
        )
        for key, child in items[:MAX_CHILDREN]:
            label = Text(
                f"{key}" if isinstance(value, dict) else f"[{key}]", style="cyan"
            )
            label.append(": ").append_text(_preview(child))
            if isinstance(child, dict | list) and child:
                node.add(label, data=child)
            else:
                node.add_leaf(label, data=child)
        if len(items) > MAX_CHILDREN:
            node.add_leaf(Text(f"... {len(items) - MAX_CHILDREN} more", style="dim"))

    @on(Tree.NodeExpanded)
    def _expand(self, event: Tree.NodeExpanded[Any]) -> None:
        if not event.node.children and isinstance(event.node.data, dict | list):
            self._fill(event.node)


class StructureTree(Tree[Node]):
    """The inferred structure: kinds, formats, optional/nullable, mixed kinds."""

    def __init__(self, analysis: Node) -> None:
        self._labels = JsonTreeBuilder()
        super().__init__(
            self._label(analysis, "root"), data=analysis, id="structure-tree"
        )

    def _label(self, node: Node | None, name: str) -> Text:
        return Text.from_markup(self._labels.format_label(node, name))

    def on_mount(self) -> None:
        self._grow(self.root, self.root.data)
        self.root.expand_all()

    def _grow(self, parent: TreeNode[Node], node: Node | None) -> None:
        if node is None:
            return
        if node.kind == Kind.OBJECT:
            children: list[tuple[str, Node | None]] = list(node.fields.items())
        elif node.kind == Kind.ARRAY:
            children = [("item", node.items)]
        else:
            return
        for name, child in children:
            branch = parent.add(self._label(child, name), data=child)
            if child is not None and child.kind in (Kind.OBJECT, Kind.ARRAY):
                self._grow(branch, child)
            else:
                branch.allow_expand = False


class SaveScreen(ModalScreen[Path | None]):
    """Ask for a file name; dismisses with the path, or None if cancelled."""

    def __init__(self, default: str) -> None:
        super().__init__()
        self.default = default

    def compose(self) -> ComposeResult:
        with Vertical(id="save-dialog"):
            yield Label("Save generated code to:")
            yield Input(self.default, id="save-path")
            yield Label("", id="save-warning")
            with Horizontal(id="save-buttons"):
                yield Button("Save", variant="primary", id="save")
                yield Button("Cancel", id="cancel")

    def on_mount(self) -> None:
        self._check(self.default)

    @on(Input.Changed, "#save-path")
    def _changed(self, event: Input.Changed) -> None:
        self._check(event.value)

    def _check(self, value: str) -> None:
        exists = value and Path(value).exists()
        self.query_one("#save-warning", Label).update(
            "[yellow]The file exists and will be overwritten.[/yellow]"
            if exists
            else ""
        )

    @on(Button.Pressed, "#save")
    @on(Input.Submitted, "#save-path")
    def _save(self) -> None:
        value = self.query_one("#save-path", Input).value.strip()
        self.dismiss(Path(value) if value else None)

    @on(Button.Pressed, "#cancel")
    def _cancel(self) -> None:
        self.dismiss(None)


class ExplorerApp(App[None]):
    """JSON Explorer TUI."""

    TITLE = "JSON Explorer"
    CSS = """
    #search-pane, #stats-pane { padding: 0 1; }
    #query { margin-bottom: 1; }
    #search-status, #code-status { height: auto; margin-bottom: 1; }
    #examples { color: $text-muted; margin-top: 1; }
    #stats-table { height: auto; max-height: 60%; }
    #issues { margin-top: 1; height: auto; }
    #report { margin-top: 1; }
    #code-options { width: 42; padding: 0 1; border-right: solid $primary; }
    #code-options Label { margin-top: 1; }
    #code-options Select, #code-options Input { margin-bottom: 0; }
    .switch-row { height: auto; margin-top: 1; }
    .switch-row Label { margin: 1 0 0 1; width: 1fr; }
    #code-buttons { height: auto; margin-top: 1; }
    #code-preview { padding: 0 1; }
    SaveScreen { align: center middle; }
    #save-dialog { width: 70; height: auto; padding: 1 2; border: thick $primary; background: $surface; }
    #save-buttons { height: auto; margin-top: 1; }
    """
    BINDINGS: ClassVar[list[Binding | tuple[str, str] | tuple[str, str, str]]] = [
        Binding("q", "quit", "Quit"),
        Binding("1", "show_tab('data')", "Data", show=False),
        Binding("2", "show_tab('structure')", "Structure", show=False),
        Binding("3", "show_tab('search')", "Search", show=False),
        Binding("4", "show_tab('stats')", "Statistics", show=False),
        Binding("5", "show_tab('code')", "Code", show=False),
        Binding("slash", "focus_search", "Search"),
        Binding("escape", "leave_input", "Leave input", show=False),
        Binding("ctrl+s", "save_code", "Save code"),
        Binding("ctrl+y", "copy_code", "Copy code"),
    ]

    def __init__(self, data: Any, source: str = "JSON") -> None:
        super().__init__()
        self.data = data
        self.source = source
        self.analysis = analyze_json(data)
        self.code = ""
        self.extension = ""

    # -- layout --------------------------------------------------------------

    def compose(self) -> ComposeResult:
        yield Header()
        with TabbedContent(initial="data", id="tabs"):
            with TabPane("Data [1]", id="data"):
                yield DataTree(self.data, self.source)
            with TabPane("Structure [2]", id="structure"):
                yield StructureTree(self.analysis)
            with TabPane("Search [3]", id="search"), Vertical(id="search-pane"):
                yield Input(
                    placeholder="JMESPath query, e.g. users[*].name", id="query"
                )
                yield Static("Type a query and press Enter.", id="search-status")
                with VerticalScroll():
                    yield Static(id="search-result")
                    yield Static(self._examples(), id="examples")
            with TabPane("Statistics [4]", id="stats"), VerticalScroll(id="stats-pane"):
                yield DataTable(id="stats-table", show_cursor=False)
                yield Static(id="issues")
                yield Button("Open HTML report", id="report")
            with TabPane("Code [5]", id="code"), Horizontal():
                with VerticalScroll(id="code-options"):
                    yield Label("Language")
                    yield Select(
                        self._languages(), value="go", allow_blank=False, id="language"
                    )
                    yield Label("Root type name")
                    yield Input("Root", id="root-name")
                    yield Label("Package", id="package-label")
                    yield Input("main", id="package-name")
                    with Horizontal(classes="switch-row"):
                        yield Switch(True, id="comments")
                        yield Label("Comments")
                    yield Vertical(id="language-options")
                    with Horizontal(id="code-buttons"):
                        yield Button("Save...", variant="primary", id="save-code")
                        yield Button("Copy", id="copy-code")
                with VerticalScroll(id="code-preview"):
                    yield Static(id="code-status")
                    yield Static(id="code-view")
        yield Footer()

    async def on_mount(self) -> None:
        self.sub_title = self.source
        self._fill_stats()
        await self._build_language_options()

    def action_show_tab(self, tab: str) -> None:
        self.query_one("#tabs", TabbedContent).active = tab

    def action_leave_input(self) -> None:
        """Esc leaves a text box so the number keys switch tabs again."""
        if isinstance(self.focused, Input):
            self.set_focus(None)

    def action_focus_search(self) -> None:
        self.action_show_tab("search")
        self.query_one("#query", Input).focus()

    # -- search --------------------------------------------------------------

    @staticmethod
    def _examples() -> Text:
        text = Text("Examples\n", style="bold")
        for description, query in JsonSearcher().get_query_examples().items():
            text.append(f"  {query:<38}", style="green").append(f"{description}\n")
        return text

    @on(Input.Changed, "#query")
    def _query_changed(self, event: Input.Changed) -> None:
        status = self.query_one("#search-status", Static)
        if not event.value.strip():
            status.update("Type a query and press Enter.")
            return
        try:
            jmespath.compile(event.value)
        except JMESPathError as e:
            status.update(Text(f"Invalid query: {e}", style="red"))
        else:
            status.update(Text("Valid query: press Enter to run it.", style="green"))

    @on(Input.Submitted, "#query")
    def _run_query(self, event: Input.Submitted) -> None:
        status = self.query_one("#search-status", Static)
        result = self.query_one("#search-result", Static)
        try:
            value = jmespath.search(event.value, self.data)
        except JMESPathError as e:
            status.update(Text(f"Query error: {e}", style="red"))
            result.update("")
            return
        if value is None:
            status.update(Text("No results.", style="yellow"))
            result.update("")
            return
        count = (
            f"{len(value)} items" if isinstance(value, list) else type(value).__name__
        )
        status.update(Text(f"Result: {count}", style="green"))
        result.update(RichJSON.from_data(value, ensure_ascii=False))

    # -- statistics ----------------------------------------------------------

    def _fill_stats(self) -> None:
        stats = DataStatsAnalyzer().generate_stats(self.data)
        insights = stats["computed_insights"]
        table = self.query_one("#stats-table", DataTable)
        table.add_columns("Metric", "Value")
        rows = [
            ("Total values", stats["total_values"]),
            ("Total keys", stats["total_keys"]),
            ("Max depth", stats["max_depth"]),
            ("Complexity score", f"{insights['complexity_score']}/100"),
            ("Structure", insights["structure_uniformity"].replace("_", " ")),
        ]
        rows += [
            (f"  {kind}", count) for kind, count in stats["data_types"].most_common()
        ]
        for metric, value in rows:
            table.add_row(metric, str(value))
        issues = insights["data_quality_issues"]
        self.query_one("#issues", Static).update(
            Text("Quality issues: " + ", ".join(issues), style="yellow")
            if issues
            else Text("No quality issues found.", style="green")
        )

    @on(Button.Pressed, "#report")
    def _open_report(self) -> None:
        try:
            JSONVisualizer().visualize(self.data, output="html", detailed=True)
        except (OSError, ValueError) as e:
            self.notify(f"Report failed: {e}", severity="error")
        else:
            self.notify("HTML report opened in the browser.")

    # -- code generation -----------------------------------------------------

    @staticmethod
    def _languages() -> list[tuple[str, str]]:
        return [(p.title, p.name) for p in all_plugins()] + [
            ("JSON Schema", JSON_SCHEMA)
        ]

    def _language(self) -> str:
        return str(self.query_one("#language", Select).value)

    def _options(self) -> tuple[CliOption, ...]:
        language = self._language()
        return () if language == JSON_SCHEMA else get_plugin(language).cli_options

    async def _build_language_options(self) -> None:
        container = self.query_one("#language-options", Vertical)
        await container.remove_children()
        go = self._language() == "go"  # the only language with packages
        self.query_one("#package-label").display = go
        self.query_one("#package-name").display = go
        widgets: list[Any] = []
        for i, option in enumerate(self._options()):
            if option.choices:
                widgets.append(Label(option.help))
                widgets.append(
                    Select(
                        [(c, c) for c in option.choices],
                        prompt="default",
                        id=f"option-{i}",
                        classes="language-option",
                    )
                )
            else:
                widgets.append(
                    Horizontal(
                        Switch(False, id=f"option-{i}", classes="language-option"),
                        Label(option.help),
                        classes="switch-row",
                    )
                )
        await container.mount_all(widgets)
        self.regenerate()

    @on(Select.Changed, "#language")
    async def _language_changed(self) -> None:
        await self._build_language_options()

    @on(Select.Changed, ".language-option")
    @on(Switch.Changed)
    @on(Input.Changed, "#root-name")
    @on(Input.Changed, "#package-name")
    def _options_changed(self) -> None:
        self.regenerate()

    def _config(self) -> dict[str, Any]:
        config: dict[str, Any] = {
            "add_comments": self.query_one("#comments", Switch).value,
            "package_name": self.query_one("#package-name", Input).value.strip()
            or "main",
        }
        for i, option in enumerate(self._options()):
            widgets = self.query(f"#option-{i}")
            if not widgets:
                return config  # options are being rebuilt
            widget = widgets.first()
            if isinstance(widget, Switch) and widget.value:
                config[option.option] = option.value
            elif isinstance(widget, Select) and widget.value is not Select.NULL:
                config[option.option] = widget.value
        return config

    def regenerate(self) -> None:
        language = self._language()
        root = self.query_one("#root-name", Input).value.strip() or "Root"
        status = self.query_one("#code-status", Static)
        view = self.query_one("#code-view", Static)
        if language == JSON_SCHEMA:
            schema = to_json_schema(self.analysis, title=root)
            self.code = json.dumps(schema, indent=2, ensure_ascii=False) + "\n"
            self.extension = ".schema.json"
            status.update(Text("JSON Schema (draft 2020-12)", style="green"))
            view.update(Syntax(self.code, "json", theme="monokai"))
            return
        result = generate_from_analysis(self.analysis, language, self._config(), root)
        if not result.success:
            self.code = ""
            status.update(
                Text(result.error_message or "Generation failed", style="red")
            )
            view.update("")
            return
        self.code = result.code
        self.extension = get_plugin(language).generator.file_extension
        warnings = "\n".join(f"⚠ {w}" for w in result.warnings)
        status.update(Text(warnings, style="yellow") if warnings else "")
        view.update(Syntax(self.code, LEXERS.get(language, "text"), theme="monokai"))

    @on(Button.Pressed, "#save-code")
    def action_save_code(self) -> None:
        if not self.code:
            self.notify("Nothing to save.", severity="warning")
            return
        root = self.query_one("#root-name", Input).value.strip() or "Root"
        self.push_screen(
            SaveScreen(f"{root.lower()}{self.extension}"), self._write_code
        )

    def _write_code(self, path: Path | None) -> None:
        if path is None:
            return
        try:
            path.write_text(self.code, encoding="utf-8", newline="\n")
        except OSError as e:
            self.notify(f"Could not save: {e}", severity="error")
        else:
            self.notify(f"Saved {path}")

    @on(Button.Pressed, "#copy-code")
    def action_copy_code(self) -> None:
        if self.code:
            self.copy_to_clipboard(self.code)
            self.notify("Code copied to the clipboard.")


def run_tui(data: Any, source: str = "JSON") -> int:
    """Run the TUI until the user quits; returns the exit code."""
    ExplorerApp(data, source).run()
    return 0
