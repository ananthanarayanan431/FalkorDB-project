from types import SimpleNamespace


class FakeLLM:
    """Stands in for a chat model. `structured` maps schema class -> response object."""

    def __init__(self, structured=None, text="Why does it behave that way?"):
        self.structured = structured or {}
        self.text = text

    def with_structured_output(self, schema):
        return SimpleNamespace(invoke=lambda _msgs: self.structured[schema])

    def invoke(self, _msgs):
        return SimpleNamespace(content=self.text)
