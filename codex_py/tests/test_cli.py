import json
import os
import sys
from pathlib import Path
from typer.testing import CliRunner

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
os.environ.setdefault("OPENAI_API_KEY", "test-key")
from codex_py.cli import app

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
