from types import SimpleNamespace


class FakeLLM:
    """Stands in for an async chat model. `structured` maps schema class -> response object."""

    def __init__(self, structured=None, text="Why does it behave that way?"):
        self.structured = structured or {}
        self.text = text

    def with_structured_output(self, schema):
        async def ainvoke(_msgs):
            return self.structured[schema]
        return SimpleNamespace(ainvoke=ainvoke)

    async def ainvoke(self, _msgs):
        return SimpleNamespace(content=self.text)
