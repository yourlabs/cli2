import litellm
from prompt2.plugin import Plugin
import os
import cli2
import sys


class LiteLLMPlugin(Plugin):
    def __init__(self, model_name, **model_kwargs):
        self.model_name = model_name
        self.model_kwargs = model_kwargs

    async def completion(self, messages, stream=False):
        if os.getenv('LITELLM_DEBUG'):
            litellm._turn_on_debug()
        stream = await litellm.acompletion(
            messages=messages,
            stream=True,
            model=self.model_name,
            **self.model_kwargs,
        )

        full_content = ""
        printed_lines = 0
        full_reasoning = ''
        reasoning_printed = False
        code_open = False
        async for chunk in stream:
            if hasattr(chunk, 'choices') and chunk.choices:
                delta = chunk.choices[0].delta
                if reasoning := getattr(delta, 'reasoning_content', None):
                    if stream:
                        if not reasoning_printed:
                            print(cli2.t.o.b('REASONING'), file=sys.stderr)
                            reasoning_printed = True
                        print(
                            cli2.t.G(delta.reasoning_content),
                            end='',
                            flush=True,
                            file=sys.stderr,
                        )
                    full_reasoning += reasoning

                if content := getattr(delta, 'content', ''):
                    if reasoning_printed:
                        # separate reasoning output visually
                        print('\n', file=sys.stderr)
                        reasoning_printed = False

                    full_content += content
                    if not content.endswith('\n'):
                        continue

                    new_lines = full_content.split('\n')[printed_lines:]
                    for new_line in new_lines:
                        if new_line.strip().startswith('```'):
                            code_open = not code_open

                    if not new_lines:
                        continue

                    highlight_content = full_content
                    if code_open:
                        # manuall close code block for pygments to highlight
                        if not highlight_content.endswith('\n'):
                            highlight_content += '\n'
                        highlight_content += '```'

                    highlighted = cli2.highlight(highlight_content, 'Markdown')
                    highlighted_lines = highlighted.split('\n')

                    if code_open:
                        highlighted_lines = highlighted_lines[:-1]

                    print(
                        '\n'.join(highlighted_lines[printed_lines:]),
                        flush=True,
                        file=sys.stderr,
                    )
                    printed_lines = len(highlighted_lines)

        new_lines = full_content.split('\n')[printed_lines:]
        for new_line in new_lines:
            if new_line.strip().startswith('```'):
                code_open = not code_open

        highlight_content = full_content
        if code_open:
            # manuall close code block for pygments to highlight code
            if not highlight_content.endswith('\n'):
                highlight_content += '\n'
            highlight_content += '```'

        highlighted = cli2.highlight(highlight_content, 'Markdown')
        highlighted_lines = highlighted.split('\n')

        if code_open:
            highlighted_lines = highlighted_lines[:-1]

        print(
            '\n'.join(highlighted_lines[printed_lines:]),
            flush=True,
            file=sys.stderr,
        )
        printed_lines = len(highlighted_lines)

        return full_content or full_reasoning

    def __str__(self):
        return (
            f'litellm {self.model_name} '
            + ' '.join([
                f'{k}={v}' for k, v in self.model_kwargs.items()
            ])
        ).strip()
