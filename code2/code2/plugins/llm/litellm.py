"""
Model DSN:
"""

from litellm import completion

from code2.plugins.llm.base import LLMPlugin


class LiteLLM(LLMPlugin):
    def __init__(self, model_name, **model_kwargs):
        self.model_name = model_name
        self.model_kwargs = model_kwargs

    def completion(self, messages):
        stream = completion(
            messages=messages,
            stream=True,
            model=self.model_name,
            **self.model_kwargs,
        )

        full_content = ""
        for chunk in stream:
            if hasattr(chunk, 'choices') and chunk.choices:
                delta = chunk.choices[0].delta
                if hasattr(delta, 'content') and delta.content is not None:
                    full_content += delta.content

        return full_content
