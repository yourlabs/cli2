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
from pathlib import Path # Import Path

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

    def format_syntax_error(self, etype, value):
        """Format SyntaxError exceptions."""
        filename = getattr(value, 'filename', '<unknown>')
        lineno = getattr(value, 'lineno', 0)
        offset = getattr(value, 'offset', None) # Can be None
        text = getattr(value, 'text', None)     # The line text if available
        msg = getattr(value, 'msg', str(value)) # Error message

        # Use similar path logic as format_frame for coloring/relativity
        relative = False
        colored_filename = t.G(filename) # Default color
        colored_lineno = t.G(lineno)     # Default color
        display_path_str = filename

        if filename and '<' not in filename and '>' not in filename:
            try:
                path = Path(filename)
                if path.exists() and path.is_relative_to(os.getcwd()):
                    relative = True
                    display_path = path.relative_to(os.getcwd())
                    display_path_str = str(display_path)
                    colored_filename = t.p.b(display_path)
                    colored_lineno = t.y.b(lineno)
            except (ValueError, OSError):
                 pass # Keep default non-relative coloring

        # Header - using standard Python format: File "...", line ...
        self.output.append(f'  File "{t.c(display_path_str)}", line {colored_lineno}')

        lines = []
        source_found = False
        firstlineno = 0 # Track the starting line number of 'lines'

        if text: # SyntaxError often provides the line directly
            # Ensure text ends with a newline for consistent processing
            lines = [text.rstrip('\r\n') + '\n']
            source_found = True
            firstlineno = lineno # The line number corresponds to this single line
        elif filename and '<' not in filename and '>' not in filename:
            # Fallback: Try reading the file if text wasn't provided
            try:
                with open(filename, 'r', encoding='utf-8', errors='replace') as f:
                    lines = f.readlines()
                firstlineno = 1 # File reading starts at line 1
                source_found = True
            except Exception as e:
                self.output.append(f"    {t.r.i('(Could not read source file)')} {type(e).__name__}")
                lines = [] # Failed to read

        if source_found and lines:
            # Calculate the 0-based index of the error line within the 'lines' list.
            error_index = lineno - firstlineno

            # Bounds check
            if 0 <= error_index < len(lines):
                line = lines[error_index].rstrip('\r\n') # Use the specific line

                # Print the line
                output_line = f"    {highlight(line, 'Python')}" # No prefix needed here
                self.output.append(output_line)

                # Add pointer using offset if available
                if offset is not None:
                    # Offset is 1-based column number. Adjust for 0-based index.
                    # Strip leading whitespace from the line to match offset calculation
                    leading_whitespace = len(line) - len(line.lstrip(' '))
                    effective_offset = offset - 1 # Make offset 0-based

                    # Adjust offset if it includes leading whitespace that we stripped
                    # This heuristic might not be perfect for all cases (e.g., tabs)
                    pointer_pos = effective_offset

                    # Ensure pointer position is non-negative
                    pointer_pos = max(0, pointer_pos)

                    pointer_line = " " * 4 + " " * pointer_pos + t.r.b("^")
                    self.output.append(pointer_line)
            else:
                 self.output.append(f"    {t.r.i('(Could not locate line {lineno} in source)')}")


        # Add the final exception line (standard format)
        exception_str = f"{t.r.b(etype.__name__)}: {t.c(msg)}"
        self.output.append(exception_str) # No leading newline needed here


    def format_frame(self, frame, is_last=False, frame_number=1, total_frames=1):
        """Format a single traceback frame."""
        code = frame.f_code
        filename = code.co_filename
        lineno = frame.f_lineno
        name = code.co_name

        relative = False
        colored_filename = t.G(filename) # Default color
        colored_lineno = t.G(lineno)     # Default color
        sig_color = t.G                # Default color
        display_path_str = filename
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
                        display_path_str = str(display_path)
                    except ValueError: # pragma: no cover
                        # Should not happen if is_relative_to is True, but be safe
                        display_path_str = str(path)

                    colored_filename = t.p.b(display_path_str)
                    colored_lineno = t.y.b(lineno)
                    sig_color = t.p.b
        except (ValueError, OSError): # Handle potential issues with path operations
            pass # Keep default non-relative coloring

        output = []
        # Standard Python format: File "...", line ..., in ...
        header = f'  File "{t.c(display_path_str)}", line {colored_lineno}, in {sig_color(name)}'

        lines = []
        firstlineno = 1 # Default values, assuming line 1 if source not found
        source_found = False
        try:
            # Attempt to get source lines using inspect
            source_lines, start_line = inspect.getsourcelines(frame)
            if source_lines and start_line >= 1:
                lines = source_lines
                firstlineno = start_line
                source_found = True
                # Attempt to extract a more informative signature (optional refinement)
                # try:
                #     signature = self.get_function_signature(textwrap.dedent(''.join(lines)))
                #     header = f'  File "{t.c(display_path_str)}", line {colored_lineno}, in {sig_color(signature or name)}'
                # except Exception: pass # Fallback to original name is fine
            else:
                raise OSError("Could not get valid source lines from inspect.")
        except (OSError, TypeError, tokenize.TokenError, IndentationError):
            # Fallback: Try reading the file directly
            try:
                if filename and '<' not in filename and '>' not in filename and os.path.exists(filename):
                    with open(filename, 'r', encoding='utf-8', errors='replace') as f:
                        lines = f.readlines()
                    firstlineno = 1 # File reading starts at line 1
                    source_found = True
            except Exception:
                lines = [] # Ensure lines is empty
                firstlineno = lineno # Point to the error line number

        # Append header *after* potential signature update
        output.append(header)

        # Process lines only if source was found
        if source_found and lines:
            try:
                # Calculate the 0-based index of the error line within the 'lines' list.
                error_index = lineno - firstlineno

                # Perform bounds checking and clamping for error_index:
                if error_index < 0 or error_index >= len(lines):
                     # If index is invalid, don't show source context
                     raise IndexError("Calculated line index out of bounds.")

                # Define context window sizes
                context_lines = 1  # Show only 1 line of context normally
                more_context = 3   # Show more context for the final frame in project code

                # Determine context window based on frame type/position
                if not relative: # Non-project code (library etc.)
                    start = error_index
                    end = error_index + 1 # Just the error line
                elif is_last and frame_number == total_frames: # Last frame (error origin in project)
                    start = max(0, error_index - more_context)
                    end = min(len(lines), error_index + more_context + 1)
                else: # Intermediate frame in project code
                    start = max(0, error_index - context_lines)
                    end = min(len(lines), error_index + context_lines + 1)

                # Ensure start index is not greater than end index
                start = min(start, end)

                # Format and append lines within the context window
                for i in range(start, end):
                    if 0 <= i < len(lines):
                        line = lines[i].rstrip('\r\n') # Strip only newlines
                        is_error_line = (i == error_index)
                        # Standard traceback format shows just the line, indented
                        # Use red bold marker for the exact error line *if* it's the last frame
                        prefix = t.r.b(">>> ") if (is_error_line and is_last) else "    "
                        output.append(f"{prefix}{highlight(line, 'Python')}")

            except Exception as e: # Catch errors during line processing
                 # Append the header anyway, but indicate source processing error
                 output.append(f"    {t.r.i('(Error processing source lines)')} {type(e).__name__}")
        # If source couldn't be found/read, header is already added.

        # Add locals display only for relative paths (project code) and last frame
        if relative and is_last:
            try:
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
                 output.append(f"    {t.r.i('(Error displaying locals)')} {type(e).__name__}")

        return output

    def parse(self, etype, value, tb):
        """Parse the exception and traceback into formatted lines."""
        # Reset output for each new traceback
        self.output = []

        # Handle SyntaxError separately as it doesn't have a typical traceback stack
        if issubclass(etype, SyntaxError):
            self.format_syntax_error(etype, value)
            return # SyntaxError handled, exit parse

        # --- Standard Traceback Processing ---
        self.output.append(f"{t.bold('Traceback')} (most recent call last):")

        frames = []
        current_tb = tb
        while current_tb:
            frames.append(current_tb.tb_frame)
            current_tb = current_tb.tb_next

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
                # Minimal error message if format_frame fails
                try:
                    fname = frame.f_code.co_filename
                    lineno = frame.f_lineno
                    location = f' File "{fname}", line {lineno}'
                except Exception:
                    location = ""
                self.output.append(f'  {t.r.i(f"(Failed to format frame #{number}{location})")} {type(e).__name__}')

        # Add the final exception line
        try:
             # Get exception type name and value representation
             exc_name = t.r.b(etype.__name__)
             exc_value = t.c(value)
             exception_str = f"{exc_name}: {exc_value}"
        except Exception:
             exception_str = f"{t.r.b(etype.__name__)}: {t.c.i('(Error displaying exception value)')}"
        self.output.append(f"{exception_str}") # No leading newline needed


    def excepthook(self, etype, value, tb):
        """Custom exception hook implementation."""
        try:
            self.parse(etype, value, tb)
            print('\n'.join(self.output), file=sys.stderr) # Print to stderr
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