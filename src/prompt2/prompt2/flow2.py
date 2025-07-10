import cli2
import flow2
from prompt2 import Model, Prompt


class PromptPlugin(flow2.Task):
    def __init__(self, name, content, model=None, parser=None, **kwargs):
        self.prompt = Prompt(content=content)
        self.model = Model(model)
        self.parser = parser
        kwargs.setdefault('output', False)
        super().__init__(name, **kwargs)

    async def run(self, context=None):
        self.prompt.context.update(context or dict())
        return await self.model(self.prompt, parser=self.parser)

    def output_result(self, result):
        cli2.print(getattr(result, 'result', result))
