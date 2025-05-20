from __future__ import annotations
import time
from typing import Any, Callable, Dict, Iterable, List, Optional

try:
    import openai
except Exception:  # pragma: no cover - openai optional
    openai = None


class AgentLoop:
    def __init__(
        self,
        model: str,
        api_key: str | None,
        instructions: str = "",
        on_item: Callable[[Dict[str, Any]], None] | None = None,
        on_loading: Callable[[bool], None] | None = None,
        on_command: Callable[[List[str]], bool] | None = None,
        max_retries: int = 3,
    ) -> None:
        self.model = model
        self.api_key = api_key
        self.instructions = instructions
        self.on_item = on_item or (lambda item: None)
        self.on_loading = on_loading or (lambda b: None)
        self.on_command = on_command or (lambda cmd: True)
        self.max_retries = max_retries

    def run(self, messages: List[Dict[str, str]]) -> None:
        if openai is None:
            raise RuntimeError("openai package required")
        client = openai.OpenAI(api_key=self.api_key) if hasattr(openai, "OpenAI") else openai
        attempt = 0
        while attempt <= self.max_retries:
            attempt += 1
            try:
                stream = client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    stream=True,
                )
                self.on_loading(True)
                for chunk in stream:
                    if isinstance(chunk, dict) and "tool_calls" in chunk.get("choices", [{}])[0].get("delta", {}):
                        tool = chunk["choices"][0]["delta"]["tool_calls"][0]
                        if tool.get("name") == "shell":
                            command = tool["arguments"].get("command", "")
                            parts = command.split()
                            if not self.on_command(parts):
                                return
                    self.on_item(chunk)
                self.on_loading(False)
                return
            except Exception as e:
                if attempt > self.max_retries:
                    raise
                time.sleep(0.5 * attempt)
