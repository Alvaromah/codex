from __future__ import annotations
import json
import os
from pathlib import Path
from typing import Any, Dict

CONFIG_DIR = Path.home() / ".codex"
CONFIG_JSON_FILEPATH = CONFIG_DIR / "config.json"
CONFIG_YAML_FILEPATH = CONFIG_DIR / "config.yaml"
CONFIG_YML_FILEPATH = CONFIG_DIR / "config.yml"
INSTRUCTIONS_FILEPATH = CONFIG_DIR / "instructions.md"

DEFAULT_AGENTIC_MODEL = "codex-mini-latest"
DEFAULT_FULL_CONTEXT_MODEL = "gpt-4.1"


def _load_yaml(path: Path) -> Dict[str, Any]:
    try:
        import yaml
    except Exception:
        return {}
    try:
        with path.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}


EMPTY_STORED_CONFIG = {"model": ""}


class AppConfig(Dict[str, Any]):
    pass


def load_config(
    config_path: Path | None = None,
    instructions_path: Path | None = None,
    *,
    is_full_context: bool = False,
) -> AppConfig:
    config_path = config_path or CONFIG_JSON_FILEPATH
    if not config_path.exists():
        if config_path == CONFIG_JSON_FILEPATH:
            if CONFIG_YAML_FILEPATH.exists():
                config_path = CONFIG_YAML_FILEPATH
            elif CONFIG_YML_FILEPATH.exists():
                config_path = CONFIG_YML_FILEPATH
    stored: Dict[str, Any] = {}
    if config_path.exists():
        ext = config_path.suffix.lower()
        try:
            if ext in {".yaml", ".yml"}:
                stored = _load_yaml(config_path)
            else:
                stored = json.loads(config_path.read_text("utf-8"))
        except Exception:
            stored = {}
    instructions_path = instructions_path or INSTRUCTIONS_FILEPATH
    instructions = instructions_path.read_text("utf-8") if instructions_path.exists() else ""
    model = (stored.get("model") or "").strip() or (
        DEFAULT_FULL_CONTEXT_MODEL if is_full_context else DEFAULT_AGENTIC_MODEL
    )
    cfg: AppConfig = AppConfig(
        model=model,
        provider=stored.get("provider"),
        instructions=instructions,
    )
    cfg.update(stored)

    # bootstrap minimal config on first run
    if not config_path.exists():
        try:
            config_path.parent.mkdir(parents=True, exist_ok=True)
            if config_path.suffix.lower() in {".yaml", ".yml"}:
                try:
                    import yaml
                except Exception:
                    config_path.write_text(json.dumps(EMPTY_STORED_CONFIG, indent=2), "utf-8")
                else:
                    config_path.write_text(yaml.safe_dump(EMPTY_STORED_CONFIG), "utf-8")
            else:
                config_path.write_text(json.dumps(EMPTY_STORED_CONFIG, indent=2), "utf-8")
        except Exception:
            pass
    if not instructions_path.exists():
        try:
            instructions_path.parent.mkdir(parents=True, exist_ok=True)
            instructions_path.write_text(instructions, "utf-8")
        except Exception:
            pass
    return cfg
