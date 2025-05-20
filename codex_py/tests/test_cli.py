import json
import os
from typer.testing import CliRunner

from codex_py.cli import app
import codex_py.config as cfg
import subprocess

runner = CliRunner()

def test_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Codex Python CLI" in result.output

def test_view(tmp_path):
    file = tmp_path / "rollout.json"
    file.write_text("hello")
    result = runner.invoke(app, ["--view", str(file)])
    assert result.exit_code == 0
    assert "hello" in result.output


def test_completion():
    result = runner.invoke(app, ["--completion", "bash"])
    assert result.exit_code == 0
    assert "bash completion for codex" in result.output


def test_config_opens_editor(tmp_path, monkeypatch):
    called = []
    instr = tmp_path / "instructions.md"
    monkeypatch.setattr(cfg, "INSTRUCTIONS_FILEPATH", instr)
    def fake_run(args, *a, **k):
        called.append(args)
    monkeypatch.setattr(subprocess, "run", fake_run)
    result = runner.invoke(app, ["--config"])
    assert result.exit_code == 0
    assert called
    assert instr.exists()

