"""
Traceback hook with more context lines, locals, colors, and line numbers.

Having more context lines and locals is useful to set context for LLMs, colors
are just cool. Line numbers help pinpoint errors precisely.

Based on :py:mod:`cli2.theme`, you can override the color palette with
environment variables.
"""

from cli2.display import highlight
from cli2.theme import t
from pathlib import Path
import inspect
import math
import os
import sys


class TracebackFormatter:
    """
    Custom traceback formatter with context lines, locals, colors, and line
    numbers.
    """

    # Default width if file lines can't be determined
    DEFAULT_LINE_NUMBER_WIDTH = 4
    # Separator between line number and code
    LINE_NUMBER_SEPARATOR = t.G(" | ")

    def __init__(self):
        self.output = []
        # Cache for file lines (filename -> (lines, total_lines))
        self._source_cache = {}

    def _get_source_lines(self, filename):
        """
        Read source lines from a file, using a cache.

        :return: (lines, total_lines).
        """
        # Not a real file, or special name like <string>
        if not filename or "<" in filename or ">" in filename:
            return None, 0

        cached = self._source_cache.get(filename)
        if cached:
            return cached

        try:
            path = Path(filename)
            # Ensure it exists and is a file before trying to open
            if path.is_file():  # Implicitly checks existence
                with open(
                    filename, "r", encoding="utf-8", errors="replace"
                ) as f:
                    lines = f.readlines()
                total_lines = len(lines)
                self._source_cache[filename] = (lines, total_lines)
                return lines, total_lines
            else:
                # File doesn't exist or is not a regular file
                self._source_cache[filename] = (None, 0)
                return None, 0
        except (OSError, UnicodeDecodeError):  # Catch specific expected errors
            self._source_cache[filename] = (None, 0)  # Cache failure
            return None, 0

    @staticmethod
    def _calculate_lineno_width(total_lines):
        """Calculate the width needed for line numbers."""
        if total_lines <= 0:
            # Handle 0 or negative (shouldn't happen but safe)
            return TracebackFormatter.DEFAULT_LINE_NUMBER_WIDTH
        try:
            # Calculate width based on digits in highest line number
            width = math.ceil(
                math.log10(total_lines + 1)
            )  # +1 handles boundary
            # Ensure minimum width for alignment
            return max(TracebackFormatter.DEFAULT_LINE_NUMBER_WIDTH, width)
        except ValueError:  # Should not happen if total_lines > 0
            return TracebackFormatter.DEFAULT_LINE_NUMBER_WIDTH

    def _format_source_line(
        self, line_content, line_no, total_lines, is_error_line
    ):
        """Format a single line of source code with line number."""

        width = self._calculate_lineno_width(total_lines)
        line_no_str = str(line_no).rjust(width)

        # Choose colors based on whether it's the error line
        num_color = t.y.b if is_error_line else t.G  # Yellow/bold for error

        colored_line = num_color(line_no_str)

        # Keep existing code highlighting
        highlighted_code = highlight(line_content.rstrip("\r\n"), "Python")

        # Combine line number, separator, and highlighted code
        return f"{colored_line}{self.LINE_NUMBER_SEPARATOR}{highlighted_code}"

    @staticmethod
    def display_value(value):
        """Truncate long values for display."""
        try:
            value = str(value)
        except Exception:
            try:
                value = repr(value)
            except Exception:
                value = f"{type(value)} instance (unrepresentable)"
        if len(value) > 75:
            value = value[:72] + "..."  # Adjusted length to fit ellipsis
        return value

    def format_syntax_error(self, etype, value):
        """Format SyntaxError exceptions with line numbers."""
        filename = getattr(value, "filename", "<unknown>")
        lineno = getattr(value, "lineno", 0)
        offset = getattr(value, "offset", None)  # Can be None
        text = getattr(value, "text", None)  # The line text if available
        msg = getattr(value, "msg", str(value))  # Error message

        t.G(filename)  # Default color
        colored_lineno = t.G(lineno)  # Default color
        display_path_str = filename

        if filename and "<" not in filename and ">" not in filename:
            try:
                path = Path(filename)
                # Check existence and relativity together
                cwd = Path(os.getcwd())
                if (
                    path.exists()
                    and path.is_file()
                    and path.is_relative_to(cwd)
                ):
                    display_path = path.relative_to(cwd)
                    display_path_str = str(display_path)
                    t.p.b(display_path_str)  # Use display_path_str
                    colored_lineno = t.y.b(lineno)
            except (ValueError, OSError):
                pass  # Keep default non-relative coloring

        # Header - using standard Python format
        self.output.append(
            f'\n  File "{t.c(display_path_str)}", line {colored_lineno}'
        )

        file_lines, total_lines = self._get_source_lines(filename)
        source_line_content = None

        if text:  # SyntaxError often provides the line directly
            source_line_content = text.rstrip("\r\n")
            # If we couldn't read the file, estimate total lines
            if total_lines == 0:
                total_lines = lineno
        elif file_lines and lineno is not None and 1 <= lineno <= total_lines:
            # Try reading from the fetched file lines
            source_line_content = file_lines[lineno - 1].rstrip("\r\n")

        if source_line_content is not None:
            # Estimate total_lines if we couldn't read the file but have lineno
            if total_lines == 0 and lineno > 0:
                total_lines = lineno  # Best guess for width calculation

            # Format the line with number and marker (always error line)
            formatted_line = self._format_source_line(
                source_line_content, lineno, total_lines, True
            )
            # Indent like standard traceback source line
            self.output.append(f"    {formatted_line}")

            # Add pointer ('^') using offset if available
            if offset is not None:
                # Offset is 1-based column number

                width = self._calculate_lineno_width(total_lines)
                pointer_prefix_len = width + len(self.LINE_NUMBER_SEPARATOR)
                pointer_pos_in_code = max(0, offset - 1)
                pointer_indentation = (
                    " " * pointer_prefix_len + " " * pointer_pos_in_code
                )
                pointer_line = f"    {pointer_indentation}{t.r.b('^')}"
                self.output.append(pointer_line)
        elif filename and "<" not in filename and ">" not in filename:
            # Indicate failure to get source only if we expected to read a file
            self.output.append(
                f"      {t.r.i('(Could not read source or find line)')}"
            )

        # Add the final exception line (standard format, not indented)
        exception_str = f"{t.r.b(etype.__name__)}: {t.c(msg)}"
        self.output.append(exception_str)

    def format_frame(
        self, frame, is_last=False, frame_number=1, total_frames=1
    ):
        """Format a single traceback frame with line numbers."""
        code = frame.f_code
        filename = code.co_filename
        lineno = frame.f_lineno
        name = code.co_name

        relative = False
        t.G(filename)
        colored_lineno = t.G(lineno)
        sig_color = t.G  # Default color

        display_path_str = filename
        try:
            # Check if path is relative only if it's likely a file path
            if filename and "<" not in filename and ">" not in filename:
                path = Path(filename)
                # Check existence and relativity together
                cwd = Path(os.getenv('PROJECT_PATH', os.getcwd()))
                if (
                    path.exists()
                    and path.is_file()
                    and path.is_relative_to(cwd)
                ):
                    relative = True
                    try:
                        display_path = path.relative_to(cwd)
                        display_path_str = str(display_path)
                    except ValueError:  # pragma: no cover
                        display_path_str = str(path)  # Should not happen

                    t.p.b(display_path_str)  # Use relative string
                    colored_lineno = t.y.b(lineno)
                    sig_color = t.p.b
        except (ValueError, OSError):  # Handle potential issues with path ops
            pass  # Keep default non-relative coloring

        output = []
        # Standard Python format: File "...", line ..., in ...
        header = (
            f'\n  File "{t.c(display_path_str)}", line {colored_lineno}, '
            f"in {sig_color(name)}"
        )

        # Append header first
        output.append(header)

        # Get source lines using cache
        file_lines, total_lines = self._get_source_lines(filename)

        # Process lines only if source was found
        if file_lines:
            try:
                # inspect.getblock might be slightly more robust for finding
                # the block but finding the exact start line can be tricky.
                # Let's use lineno. Assume lineno is 1-based index into
                # file_lines.
                error_index = lineno - 1  # 0-based index

                # Bounds check error_index
                if not (0 <= error_index < total_lines):
                    raise IndexError(
                        f"Line number {lineno} out of range (1-{total_lines})"
                    )

                # Define context window sizes

                context_lines = 1  # Context lines above/below
                more_context = 3  # Extra context for final frame in project

                # Determine context window based on frame type/position
                if not relative:  # Non-project code (library etc.)
                    start_index = error_index
                    end_index = error_index + 1  # Just the error line
                elif is_last and frame_number == total_frames:  # Last frame
                    start_index = max(0, error_index - more_context)
                    end_index = min(
                        total_lines, error_index + more_context + 1
                    )
                else:  # Intermediate frame in project code
                    start_index = max(0, error_index - context_lines)
                    end_index = min(
                        total_lines, error_index + context_lines + 1
                    )

                # Format and append lines within the context window
                for i in range(start_index, end_index):
                    # i is 0-based index into file_lines
                    line_content = file_lines[i].rstrip(
                        "\r\n"
                    )  # Strip newlines

                    current_lineno = i + 1  # 1-based line number for display
                    is_error_line_in_context = i == error_index
                    if not line_content:
                        continue

                    formatted_line = self._format_source_line(
                        line_content,
                        current_lineno,
                        total_lines,
                        is_error_line_in_context,
                    )
                    # Add standard indentation ("    ") for source lines in
                    # traceback
                    output.append(f"    {formatted_line}")

            # Specific handling for line number issues
            except IndexError as e:
                # This can happen if lineno reported by frame is outside file
                # bounds
                output.append(
                    '      '
                    + t.r.i('(Error processing source: line number invalid)')
                    + str(e)
                )
            # Catch other errors during line processing
            except Exception as e:
                # Append indication of error processing source lines
                output.append(
                    "      "
                    + t.r.i("(Error processing source lines)")
                    + f"{type(e).__name__}: {e}"
                )

        elif filename and "<" not in filename and ">" not in filename:
            # Indicate failure if it was a real filename we expected to read
            output.append(f"      {t.r.i('(Could not read source file)')}")
        # Note: No 'else' needed for <string> etc., we just don't show source

        # Add locals display for every frame
        try:
            filtered_locals = {
                k: v
                for k, v in frame.f_locals.items()
                if (
                    not k.startswith("__")
                    and not inspect.ismodule(v)
                    and not inspect.isclass(v)
                )
            }
            # Only add locals section if there's something to show
            if filtered_locals:
                # Sort locals by key for consistent output
                sorted_locals = sorted(filtered_locals.items())
                locals_str = " ".join(
                    f"{k}={t.g(self.display_value(v))}"
                    for k, v in sorted_locals
                )

                # Add standard indentation for locals line
                output.append(f"    {t.g.b('Locals')}: {locals_str}")

        except Exception as e:
            output.append(
                "    " + t.r.i("(Error displaying locals)") + type(e).__name__
            )

        return output

    def parse(self, etype, value, tb):
        """Parse the exception and traceback into formatted lines."""
        # Reset output for each new traceback
        self.output = []

        # Handle SyntaxError separately as it doesn't have a typical traceback
        # stack
        if issubclass(etype, SyntaxError):
            self.format_syntax_error(etype, value)
            return  # SyntaxError handled, exit parse

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
                    total_frames=total_frames,
                )
                self.output.extend(frame_output)
            except Exception as e:
                # Minimal error message if format_frame fails
                try:
                    fname = frame.f_code.co_filename
                    lineno = frame.f_lineno
                    location = f'\n File "{fname}", line {lineno}'
                except Exception:
                    location = ""
                # Add standard indentation for error message within frame
                self.output.append(
                    t.r.i(f"(Failed to format frame #{number}{location})")
                    + f" {type(e).__name__}: {e}"
                )

        # Add the final exception line
        try:
            # Get exception type name and value representation
            exc_name = t.r.b(etype.__name__)
            exc_value = t.c(value)
            exception_str = f"{exc_name}: {exc_value}"
        except Exception:
            exception_str = (
                f"{t.r.b(etype.__name__)}: "
                f"{t.c.i('(Error displaying exception value)')}"
            )
        self.output.append(f"{exception_str}")

    def excepthook(self, etype, value, tb):
        """Custom exception hook implementation."""
        try:
            self.parse(etype, value, tb)
            print("\n".join(self.output), file=sys.stderr)
        except Exception as e_hook:
            # Ultimate fallback: use standard traceback printer if our
            # formatter fails
            print(
                f"FATAL: cli2.traceback hook failed: "
                f"{type(e_hook).__name__}: {e_hook}",
                file=sys.stderr,
            )
            sys.__excepthook__(etype, value, tb)

    def enable(self):
        """Set this formatter as the system exception hook."""
        sys.excepthook = self.excepthook


# Global instance and enable function
_formatter = TracebackFormatter()


def enable():
    """Enable the custom traceback formatter."""
    # Defer import to avoid circularity
    from cli2.configuration import cfg

    # Check config if tracebacks should be enabled
    if not bool(cfg.get("CLI2_TRACEBACK_DISABLE")):
        _formatter.enable()


# Optional: Function to disable and restore original hook
def disable():
    """Restore the default system exception hook."""
    sys.excepthook = sys.__excepthook__
