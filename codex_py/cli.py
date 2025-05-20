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

app = typer.Typer(add_help_option=False)


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
    history: bool = typer.Option(False, "--history", help="Browse history"),
    login: bool = typer.Option(False, "--login", help="Login to Codex"),
    quiet: bool = typer.Option(False, "-q", "--quiet", help="Quiet mode"),
    full_context: bool = typer.Option(False, "-f", "--full-context", help="Use larger model"),
    auto_edit: bool = typer.Option(False, "--auto-edit", help="Automatically approve edits"),
    full_auto: bool = typer.Option(False, "--full-auto", help="Run without confirmations"),
    approval_mode: str = typer.Option("suggest", "--approval-mode", help="Approval policy"),
    image: Optional[str] = typer.Option(None, "--image", help="Image prompt"),
):
    """Codex Python CLI"""
    config = load_config(is_full_context=full_context)
    if model:
        config["model"] = model
    if provider:
        config["provider"] = provider

    api_key = os.environ.get("OPENAI_API_KEY", "")
    if login or not api_key:
        api_key = login_flow()
        os.environ["OPENAI_API_KEY"] = api_key
        (pathlib.Path.home() / ".codex" / "auth.json").write_text(
            json.dumps({"OPENAI_API_KEY": api_key})
        )

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

    if not prompt:
        typer.echo("No prompt supplied", err=True)
        raise typer.Exit(1)

    buffer = []

    def on_item(it):
        if quiet:
            if isinstance(it, dict) and "choices" in it:
                content = it["choices"][0]["delta"].get("content")
                if content:
                    buffer.append(content)
        else:
            typer.echo(json.dumps(it))

    # simple approval handling
    def on_command(command: list[str]) -> bool:
        mode = "full-auto" if full_auto else "auto-edit" if auto_edit else approval_mode
        assessment = can_auto_approve(command, mode)
        if assessment.type == "auto-approve":
            return True
        result = ReviewApp.run(command)
        return result == "yes"

    agent = AgentLoop(model=config["model"], api_key=api_key, instructions=config.get("instructions", ""), on_item=on_item, on_command=on_command)
    messages = [{"role": "user", "content": prompt}]
    if image:
        try:
            import base64
            data = pathlib.Path(image).read_bytes()
            b64 = base64.b64encode(data).decode()
            messages.append({"role": "user", "image": b64})
        except Exception:
            pass
    agent.run(messages)
    if quiet:
        typer.echo("".join(buffer))

