import flow2
from prompt2 import Model, Parser, Prompt


class PromptPlugin(flow2.Task):
    def __init__(self, name, content, model=None, parser=None, **kwargs):
        self.prompt = Prompt(content=content)
        self.model = Model(model)
        self.parser = parser
        super().__init__(name, **kwargs)

    async def run(self, queue, context=None):
        self.prompt.context.update(context or dict())
        return await self.model(self.prompt, parser=self.parser)
