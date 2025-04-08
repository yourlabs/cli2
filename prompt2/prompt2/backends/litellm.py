import litellm
import os

from prompt2.backend import BackendPlugin


class LiteLLMBackend(BackendPlugin):
    def __init__(self, model_name, **model_kwargs):
        self.model_name = model_name
        self.model_kwargs = model_kwargs

    async def completion(self, messages):
        if os.getenv('DEBUG'):
            litellm._turn_on_debug()
        stream = await litellm.acompletion(
            messages=messages,
            stream=True,
            model=self.model_name,
            **self.model_kwargs,
        )

        full_content = ""
        async for chunk in stream:
            if hasattr(chunk, 'choices') and chunk.choices:
                delta = chunk.choices[0].delta
                if hasattr(delta, 'content') and delta.content is not None:
                    full_content += delta.content

        return full_content
