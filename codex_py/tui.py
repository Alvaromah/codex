from __future__ import annotations
import json
from pathlib import Path
from textual.app import App, ComposeResult
from textual.widgets import Static


class HistoryApp(App[str]):
    def __init__(self, history_dir: Path) -> None:
        super().__init__()
        self.history_dir = history_dir
        self.selection: str | None = None

    def compose(self) -> ComposeResult:
        for p in sorted(self.history_dir.glob("*.json")):
            yield Static(p.name)

    def on_key(self, event) -> None:  # type: ignore
        if event.key == "q":
            self.exit(None)
        if event.key == "enter":
            focused = self.focused
            if isinstance(focused, Static):
                self.exit((self.history_dir / focused.renderable).read_text())


class ReviewApp(App[str]):
    def __init__(self, command: list[str]) -> None:
        super().__init__()
        self.command = command
        self.result = "no"

    def compose(self) -> ComposeResult:
        yield Static("Run command: " + " ".join(self.command))
        yield Static("[y]es/[n]o")

    def on_key(self, event) -> None:  # type: ignore
        if event.key.lower() == "y":
            self.exit("yes")
        if event.key.lower() == "n":
            self.exit("no")
