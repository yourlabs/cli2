"""
Traceback hook with more context lines, locals and colors.

Having more context lines and locals is useful to set context for LLMs, colors
are just cool.

Basied on :py:mod:`cli2.theme`, you can override the color palette with
environment variables.
"""
from cli2.display import highlight
from cli2.theme import t
import ast
import inspect
import sys
import textwrap

class TracebackFormatter:
    """Custom traceback formatter with context lines, locals, and colors."""

    def __init__(self):
        self.output = []

    @staticmethod
    def display_value(value):
        """Truncate long values for display."""
        try:
            value = str(value)
        except:
            try:
                value = repr(value)
            except:
                value = f'{type(value)}'
        if len(value) > 75:
            value = value[:75] + '…'
        return value

    @staticmethod
    def get_function_signature(source):
        """Extract function signature from source code."""
        try:
            tree = ast.parse(source)
            func_def = tree.body[0]
            func_name = func_def.name
            args = [t.c(arg.arg) for arg in func_def.args.args]
            return f"{t.y.b(func_name)}({', '.join(args)})"
        except:
            return None

    def format_frame(self, frame, is_last=False, frame_number=1, total_frames=1):
        """Format a single traceback frame."""
        code = frame.f_code
        filename = code.co_filename
        lineno = frame.f_lineno
        name = code.co_name

        output = []
        try:
            lines, firstlineno = inspect.getsourcelines(frame)
            signature = self.get_function_signature(textwrap.dedent('\n'.join(lines)))
            header = f"\n  {t.p.b(filename)}:{t.c.b(lineno)} {signature or t.y.b(name)}"
            output.append(header)

            error_index = lineno - firstlineno
            start = max(0, error_index - 4)
            end = min(len(lines), error_index + 1)

            if end - start > 10:
                start = end - 10
            if is_last and total_frames == frame_number:
                start = max(0, start - 10)
                end += 10

            for i in range(start, end):
                try:
                    line = lines[i].rstrip()
                    prefix = ">>> " if i == error_index else "    "
                    output.append(f"{prefix}{highlight(line, 'Python')}")
                except IndexError:
                    break
        except OSError:
            output.append(f"\n  {t.p.b(filename)}:{t.c.b(lineno)} {t.y.b(name)}")

        locals_str = " ".join(
            f"{t.c.b(k)}={t.g(self.display_value(v))}"
            for k, v in frame.f_locals.items()
            if not k.startswith('__') and not inspect.ismodule(v)
        )
        if locals_str:
            output.append(f"    {t.g.b('Locals')}: {locals_str}")

        return output

    def parse(self, etype, value, tb):
        """Custom exception hook implementation."""
        self.output.append(f"{t.bold('Traceback')} (most recent call last):")

        frames = []
        while tb:
            frames.append(tb.tb_frame)
            tb = tb.tb_next

        total_frames = len(frames)
        for number, frame in enumerate(frames, 1):
            output = self.format_frame(
                frame,
                is_last=(number == total_frames),
                frame_number=number,
                total_frames=total_frames
            )
            self.output.append("\n".join(output))

        self.output.append(f"{t.r.b(etype.__name__)}: {t.c(value)}")

    def excepthook(self, etype, value, tb):
        """Custom exception hook implementation."""
        self.parse(etype, value, tb)
        print('\n'.join(self.output))

    def enable(self):
        """Set this formatter as the system exception hook."""
        sys.excepthook = self.excepthook

# Usage
def enable():
    formatter = TracebackFormatter()
    formatter.enable()
