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
import tokenize
import os # Import os for path operations


class TracebackFormatter:
    """Custom traceback formatter with context lines, locals, and colors."""

    def __init__(self):
        self.output = []

    @staticmethod
    def display_value(value):
        """Truncate long values for display."""
        try:
            value = str(value)
        except Exception:
            try:
                value = repr(value)
            except Exception:
                value = f'{type(value)} instance (unrepresentable)'
        if len(value) > 75:
            value = value[:72] + '...' # Adjusted length to fit ellipsis
        return value

    @staticmethod
    def get_function_signature(source):
        """Extract function signature from source code."""
        try:
            tree = ast.parse(source)
            # Handle cases where the source might not start with a function
            if tree.body and isinstance(tree.body[0], ast.FunctionDef):
                func_def = tree.body[0]
                func_name = func_def.name
                args = [t.c(arg.arg) for arg in func_def.args.args]
                return f"{t.y.b(func_name)}({', '.join(args)})"
        except Exception: # Catch broad exceptions during parsing
            return None
        return None # Return None if no function definition found

    def format_frame(self, frame, is_last=False, frame_number=1, total_frames=1):
        """Format a single traceback frame."""
        code = frame.f_code
        filename = code.co_filename
        lineno = frame.f_lineno
        name = code.co_name

        from pathlib import Path
        relative = False
        colored_filename = t.G(filename) # Default color
        colored_lineno = t.G(lineno)     # Default color
        sig_color = t.G                # Default color
        try:
            # Check if path is relative only if it's likely a file path
            if filename and '<' not in filename and '>' not in filename:
                path = Path(filename)
                # Check if file exists and is relative to cwd
                if path.exists() and path.is_relative_to(os.getcwd()):
                    relative = True
                    # Use relative path for display
                    try:
                        display_path = path.relative_to(os.getcwd())
                    except ValueError: # pragma: no cover
                        # Should not happen if is_relative_to is True, but be safe
                        display_path = path
                    colored_filename = t.p.b(display_path)
                    colored_lineno = t.y.b(lineno)
                    sig_color = t.p.b
        except (ValueError, OSError): # Handle potential issues with path operations
            pass # Keep default non-relative coloring

        output = []
        header = f"\n  {colored_filename}:{colored_lineno} {sig_color(name)}" # Default header

        try:
            lines, firstlineno = [], 1 # Default values
            source_found = False
            try:
                # Attempt to get source lines using inspect
                lines, firstlineno = inspect.getsourcelines(frame)
                if lines and firstlineno >= 1:
                    source_found = True
                    signature = self.get_function_signature(textwrap.dedent('\n'.join(lines)))
                    header = f"\n  {colored_filename}:{colored_lineno} {sig_color(signature or name)}"
                else:
                    # inspect.getsourcelines might return empty list or invalid lineno
                    raise OSError("Could not get valid source lines from inspect.")
            except (OSError, TypeError, tokenize.TokenError):
                # Fallback: Try reading the file directly if source couldn't be obtained via inspect
                # This helps with non-Python files or edge cases.
                try:
                    # Check if filename seems like a real path
                    if filename and '<' not in filename and '>' not in filename and os.path.exists(filename):
                        with open(filename, 'r', encoding='utf-8', errors='replace') as f:
                            lines = f.readlines()
                        firstlineno = 1 # Assume file content starts at line 1
                        source_found = True
                        # Header uses function name as signature is unavailable
                        header = f"\n  {colored_filename}:{colored_lineno} {sig_color(name)}"
                except Exception:
                    # If reading file also fails, proceed without source lines
                    lines = [] # Ensure lines is empty
                    firstlineno = lineno # Point to the error line number directly

            output.append(header)

            # Process lines only if source was found
            if source_found and lines:
                # Calculate the 0-based index of the error line within the 'lines' list
                # Ensure lineno is not smaller than firstlineno
                if lineno >= firstlineno:
                    error_index = lineno - firstlineno
                else:
                    # Defensive: If lineno is unexpectedly smaller, point to the start
                    error_index = 0

                # Clamp error_index to valid range within the lines list
                error_index = max(0, min(error_index, len(lines) - 1))

                # Define context window sizes
                context_lines = 4  # Standard context lines before/after
                more_context = 10  # Extra context for the final frame

                # Determine context window based on frame type/position
                if not relative: # Non-project code (library etc.)
                    # Minimal context: error line +/- 1
                    start = max(0, error_index - 1)
                    end = min(len(lines), error_index + 2)
                elif is_last and frame_number == total_frames: # Last frame (error origin)
                    # More context
                    start = max(0, error_index - more_context)
                    end = min(len(lines), error_index + more_context + 1)
                else: # Intermediate frame in project code
                    # Standard context
                    start = max(0, error_index - context_lines)
                    end = min(len(lines), error_index + context_lines + 1)

                # Ensure start index is not greater than end index
                start = min(start, end)

                # Format and append lines within the context window
                for i in range(start, end):
                    # Basic safety check, although start/end calculation should be robust
                    if 0 <= i < len(lines):
                        line = lines[i].rstrip()
                        is_error_line = (i == error_index)
                        # Use red bold marker for the error line
                        prefix = t.r.b(">>> ") if is_error_line else "    "
                        # Optional: Add line number display for clarity
                        # current_line_no = firstlineno + i
                        # output.append(f"{current_line_no:5d}{prefix}{highlight(line, 'Python')}")
                        output.append(f"{prefix}{highlight(line, 'Python')}")

            # If source couldn't be found/read, 'lines' is empty, loop won't run. Header is already added.

        except Exception as e:
            # Fallback if any unexpected error occurs during frame formatting
            output.append(f"\n  {t.r('Error formatting frame:')} {type(e).__name__}: {e}")
            # Ensure basic location info is still present
            if header not in output: # Avoid duplicate header
                 output.append(header)


        # Add locals display only for relative paths (project code)
        if relative:
            try:
                # Filter out modules and internal variables for cleaner output
                filtered_locals = {
                    k: v for k, v in frame.f_locals.items()
                    if not k.startswith('__') and not inspect.ismodule(v)
                }
                if filtered_locals: # Only add locals section if there's something to show
                    locals_str = " ".join(
                        f"{t.c.b(k)}={t.g(self.display_value(v))}"
                        for k, v in filtered_locals.items()
                    )
                    output.append(f"    {t.g.b('Locals')}: {locals_str}")
            except Exception as e:
                 # Avoid crashing traceback formatting due to locals issues
                 output.append(f"    {t.r.i('(Error displaying locals)')} {type(e).__name__}")


        return output

    def parse(self, etype, value, tb):
        """Parse the exception and traceback into formatted lines."""
        # Reset output for each new traceback
        self.output = [f"{t.bold('Traceback')} (most recent call last):"]

        frames = []
        while tb:
            frames.append(tb.tb_frame)
            tb = tb.tb_next

        total_frames = len(frames)
        for number, frame in enumerate(frames, 1):
            try:
                frame_output = self.format_frame(
                    frame,
                    is_last=(number == total_frames),
                    frame_number=number,
                    total_frames=total_frames
                )
                self.output.extend(frame_output) # Use extend for list of lines
            except Exception as e:
                # If format_frame fails catastrophically, add a minimal error message
                self.output.append(f"\n  {t.r('Failed to format frame')} #{number}: {type(e).__name__}")

        # Add the final exception line
        self.output.append(f"\n{t.r.b(etype.__name__)}: {t.c(value)}")

    def excepthook(self, etype, value, tb):
        """Custom exception hook implementation."""
        try:
            self.parse(etype, value, tb)
            print('\n'.join(self.output))
        except Exception:
            # Ultimate fallback: use standard traceback printer if our formatter fails
            sys.__excepthook__(etype, value, tb)


    def enable(self):
        """Set this formatter as the system exception hook."""
        sys.excepthook = self.excepthook

# Global instance and enable function
_formatter = TracebackFormatter()

def enable():
    """Enable the custom traceback formatter."""
    _formatter.enable()

# Optional: Function to disable and restore original hook
def disable():
    """Restore the default system exception hook."""
    sys.excepthook = sys.__excepthook__