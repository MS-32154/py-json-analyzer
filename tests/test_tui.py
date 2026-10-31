"""Tests for the Textual TUI, driven headlessly with Textual's pilot."""

import asyncio
import json
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

import pytest
from json_explorer.tui import JSON_SCHEMA, MAX_CHILDREN, ExplorerApp
from textual.pilot import Pilot
from textual.widgets import DataTable, Input, Select, Static, Switch, Tree

DATA = {
    "users": [
        {"id": 1, "name": "Ann", "email": None, "joined": "2024-01-01T10:00:00Z"},
        {"id": 2, "name": "Bob", "email": "b@x", "joined": "2024-02-01T10:00:00Z"},
    ],
    "meta": {"total": 2},
}

type Scenario = Callable[[ExplorerApp, Pilot[None]], Awaitable[None]]


def drive(scenario: Scenario, data: Any = DATA) -> ExplorerApp:
    """Run the app headlessly, play the scenario, return the app."""
    app = ExplorerApp(data, "test.json")

    async def run() -> None:
        async with app.run_test(size=(140, 45)) as pilot:
            await pilot.pause()
            await scenario(app, pilot)

    asyncio.run(run())
    return app


def text(app: ExplorerApp, selector: str) -> str:
    return str(app.query_one(selector, Static).render())


async def choose(app: ExplorerApp, pilot: Pilot[None], language: str) -> None:
    app.query_one("#language", Select).value = language
    await pilot.pause()
    await pilot.pause()


class TestData:
    def test_tree_lazily_expands(self):
        async def scenario(app, pilot):
            tree = app.query_one("#data-tree", Tree)
            users = tree.root.children[0]
            assert str(users.label) == "users: [2 items]"
            assert not users.children  # filled on expand
            users.expand()
            await pilot.pause()
            assert str(users.children[0].label) == "[0]: {4 keys}"

        drive(scenario)

    def test_long_lists_are_capped(self):
        async def scenario(app, pilot):
            root = app.query_one("#data-tree", Tree).root
            assert len(root.children) == MAX_CHILDREN + 1
            assert str(root.children[-1].label) == "... 10 more"

        drive(scenario, list(range(MAX_CHILDREN + 10)))

    def test_scalar_document(self):
        async def scenario(app, pilot):
            assert not app.query_one("#data-tree", Tree).root.children

        drive(scenario, 42)


class TestStructure:
    def test_shows_inferred_fields(self):
        async def scenario(app, pilot):
            root = app.query_one("#structure-tree", Tree).root
            names = [str(child.label).split()[0] for child in root.children]
            assert names == ["users", "meta"]
            item = root.children[0].children[0]
            fields = " ".join(str(f.label) for f in item.children)
            assert "email" in fields
            assert "date-time" in fields

        drive(scenario)


class TestSearch:
    @pytest.mark.parametrize(
        ("query", "status"),
        [
            ("users[*].name", "Valid query"),
            ("users[", "Invalid query"),
        ],
    )
    def test_validates_while_typing(self, query, status):
        async def scenario(app, pilot):
            await pilot.press("slash")
            assert app.focused is app.query_one("#query", Input)
            app.query_one("#query", Input).value = query
            await pilot.pause()
            assert status in text(app, "#search-status")

        drive(scenario)

    def test_runs_query(self):
        async def scenario(app, pilot):
            await pilot.press("slash")
            await pilot.press(*"users[*].name", "enter")
            assert "Result: 2 items" in text(app, "#search-status")
            assert '"Ann"' in text(app, "#search-result")

        drive(scenario)

    def test_no_results(self):
        async def scenario(app, pilot):
            await pilot.press("slash")
            await pilot.press(*"missing", "enter")
            assert "No results" in text(app, "#search-status")

        drive(scenario)


class TestStatistics:
    def test_table_and_issues(self):
        async def scenario(app, pilot):
            table = app.query_one("#stats-table", DataTable)
            rows = {
                table.get_row_at(i)[0]: table.get_row_at(i)[1]
                for i in range(table.row_count)
            }
            assert rows["Max depth"] == "3"
            assert "quality issues" in text(app, "#issues").lower()

        drive(scenario)


class TestCode:
    @pytest.mark.parametrize(
        ("language", "expected"),
        [
            ("go", "type Root struct {"),
            ("python", "class Root:"),
            ("typescript", "export interface Root {"),
            ("rust", "pub struct Root {"),
        ],
    )
    def test_languages(self, language, expected):
        async def scenario(app, pilot):
            await choose(app, pilot, language)
            assert expected in app.code

        drive(scenario)

    def test_json_schema(self):
        async def scenario(app, pilot):
            await choose(app, pilot, JSON_SCHEMA)
            assert json.loads(app.code)["title"] == "Root"
            assert app.extension == ".schema.json"
            assert not app.query("#language-options > *")

        drive(scenario)

    def test_options_come_from_the_plugin(self):
        async def scenario(app, pilot):
            await choose(app, pilot, "python")
            style = app.query_one("#option-0", Select)
            style.value = "pydantic"
            await pilot.pause()
            assert "class Root(BaseModel):" in app.code
            await choose(app, pilot, "go")
            assert "*string" in app.code
            app.query_one("#option-0", Switch).value = True  # --no-pointers
            await pilot.pause()
            assert "*string" not in app.code

        drive(scenario)

    def test_root_name_and_comments(self):
        async def scenario(app, pilot):
            await choose(app, pilot, "typescript")
            assert "/** RFC 3339 date-time */" in app.code
            app.query_one("#comments", Switch).value = False
            app.query_one("#root-name", Input).value = "Payload"
            await pilot.pause()
            assert "export interface Payload {" in app.code
            assert "/**" not in app.code

        drive(scenario)

    def test_go_package(self):
        async def scenario(app, pilot):
            app.query_one("#package-name", Input).value = "models"
            await pilot.pause()
            assert "package models" in app.code
            await choose(app, pilot, "python")
            assert not app.query_one("#package-name", Input).display

        drive(scenario)

    def test_save(self, tmp_path: Path):
        target = tmp_path / "out" / "model.go"
        target.parent.mkdir()

        async def scenario(app, pilot):
            await pilot.press("ctrl+s")
            await pilot.pause()
            path = app.screen.query_one("#save-path", Input)
            assert path.value == "root.go"
            path.value = str(target)
            await pilot.press("enter")
            await pilot.pause()

        app = drive(scenario)
        assert target.read_text() == app.code

    def test_save_cancelled(self, tmp_path: Path):
        async def scenario(app, pilot):
            await pilot.press("ctrl+s")
            await pilot.pause()
            await pilot.click("#cancel")
            await pilot.pause()
            assert app.screen is app.screen_stack[0]

        drive(scenario)

    def test_copy(self, monkeypatch):
        copied = []
        monkeypatch.setattr(
            ExplorerApp, "copy_to_clipboard", lambda self, t: copied.append(t)
        )

        async def scenario(app, pilot):
            await pilot.press("ctrl+y")

        app = drive(scenario)
        assert copied == [app.code]


def test_number_keys_switch_tabs():
    async def scenario(app, pilot):
        for key, tab in zip(
            "12345", ["data", "structure", "search", "stats", "code"], strict=True
        ):
            await pilot.press(key)
            assert app.query_one("#tabs").active == tab

    drive(scenario)


def test_escape_leaves_the_search_box():
    async def scenario(app, pilot):
        await pilot.press("slash", "4")
        assert app.query_one("#query", Input).value == "4"  # typed, not a tab switch
        await pilot.press("escape", "4")
        assert app.query_one("#tabs").active == "stats"

    drive(scenario)
