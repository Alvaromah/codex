from __future__ import annotations
import json
import os
import pathlib
import typer
import webbrowser
import http.server
import socketserver
from typing import Optional
from .tui import HistoryApp, ReviewApp

from .config import load_config
from .agent_loop import AgentLoop
from .approvals import can_auto_approve

app = typer.Typer(invoke_without_command=True)


def login_flow() -> str:
    token = "dummy-token"

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Logged in")
            nonlocal token
            token = self.path.split("token=")[-1]

    with socketserver.TCPServer(("", 0), Handler) as httpd:
        port = httpd.server_address[1]
        url = f"http://localhost:{port}"
        webbrowser.open(url)
        httpd.handle_request()
    return token


@app.callback()
def main(
    prompt: Optional[str] = typer.Argument(None, help="Prompt"),
    model: Optional[str] = typer.Option(None, "-m", "--model"),
    provider: Optional[str] = typer.Option(None, "-p", "--provider"),
    view: Optional[str] = typer.Option(None, "-v", "--view"),
    history: bool = typer.Option(False, "--history"),
    login: bool = typer.Option(False, "--login"),
    quiet: bool = typer.Option(False, "-q", "--quiet"),
    full_context: bool = typer.Option(False, "-f", "--full-context"),
):
    """Codex Python CLI"""
    config = load_config(is_full_context=full_context)
    if model:
        config["model"] = model
    if provider:
        config["provider"] = provider

    if view:
        path = pathlib.Path(view)
        typer.echo(path.read_text())
        raise typer.Exit()

    if history:
        history_dir = pathlib.Path.home() / ".codex" / "history"
        if history_dir.exists():
            content = HistoryApp.run(history_dir)
            if content:
                typer.echo(content)
        raise typer.Exit()

    api_key = os.environ.get("OPENAI_API_KEY", "")
    if login or not api_key:
        api_key = login_flow()
        os.environ["OPENAI_API_KEY"] = api_key
        (pathlib.Path.home() / ".codex" / "auth.json").write_text(
            json.dumps({"OPENAI_API_KEY": api_key})
        )

    if not prompt:
        typer.echo("No prompt supplied", err=True)
        raise typer.Exit(1)

    def on_item(it):
        if quiet:
            if isinstance(it, dict) and "choices" in it:
                content = it["choices"][0]["delta"].get("content")
                if content:
                    typer.echo(content, nl=False)
        else:
            typer.echo(json.dumps(it))

    # simple approval handling
    def on_command(command: list[str]) -> bool:
        assessment = can_auto_approve(command, "suggest")
        if assessment.type == "auto-approve":
            return True
        result = ReviewApp.run(command)
        return result == "yes"

    agent = AgentLoop(model=config["model"], api_key=api_key, instructions=config.get("instructions", ""), on_item=on_item)
    agent.run([{"role": "user", "content": prompt}])

