from __future__ import annotations
import json
import os
import pathlib
import subprocess
import typer
import webbrowser
import http.server
import socketserver
from typing import Optional
from .tui import HistoryApp, ReviewApp

from .config import load_config, INSTRUCTIONS_FILEPATH
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
    ctx: typer.Context,
    prompt: Optional[str] = typer.Argument(None, help="Prompt"),
    model: Optional[str] = typer.Option(None, "-m", "--model"),
    provider: Optional[str] = typer.Option(None, "-p", "--provider"),
    view: Optional[str] = typer.Option(None, "-v", "--view"),
    history: bool = typer.Option(False, "--history"),
    login: bool = typer.Option(False, "--login"),
    config_edit: bool = typer.Option(False, "-c", "--config"),
    completion: Optional[str] = typer.Option(None, "--completion"),
    quiet: bool = typer.Option(False, "-q", "--quiet"),
    full_context: bool = typer.Option(False, "-f", "--full-context"),
):
    """Codex Python CLI"""
    if ctx.invoked_subcommand is not None:
        return
    config = load_config(is_full_context=full_context)
    if model:
        config["model"] = model
    if provider:
        config["provider"] = provider

    if completion:
        scripts = {
            "bash": "# bash completion for codex\n_codex_completion() {\n  local cur\n  cur=\"${COMP_WORDS[COMP_CWORD]}\"\n  COMPREPLY=( $(compgen -o default -o filenames -- \"${cur}\") )\n}\ncomplete -F _codex_completion codex",
            "zsh": "# zsh completion for codex\n#compdef codex\n\n_codex() {\n  _arguments '*:filename:_files'\n}\n_codex",
            "fish": "# fish completion for codex\ncomplete -c codex -a '(__fish_complete_path)' -d 'file path'",
        }
        script = scripts.get(completion)
        if not script:
            typer.echo(f"Unsupported shell: {completion}", err=True)
            raise typer.Exit(1)
        typer.echo(script)
        raise typer.Exit()

    if view:
        path = pathlib.Path(view)
        typer.echo(path.read_text())
        raise typer.Exit()

    if config_edit:
        # Ensure minimal config exists
        load_config()
        editor = os.environ.get("EDITOR", "notepad" if os.name == "nt" else "vi")
        subprocess.run([editor, str(INSTRUCTIONS_FILEPATH)])
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

