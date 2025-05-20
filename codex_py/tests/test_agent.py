from codex_py.agent_loop import AgentLoop


class DummyStream(list):
    def __iter__(self):
        yield {"choices": [{"delta": {"content": "hi"}}]}


class DummyClient:
    def __init__(self):
        self.chat = self
        self.completions = self

    def create(self, model, messages, stream):
        return DummyStream()


def test_agent_basic(monkeypatch):
    import codex_py.agent_loop as ag
    monkeypatch.setattr(ag, "openai", type("x", (), {"OpenAI": lambda api_key=None: DummyClient()}))
    items = []
    agent = AgentLoop("test", api_key="key", on_item=items.append)
    agent.run([{"role": "user", "content": "hi"}])
    assert items
