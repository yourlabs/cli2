import re

class Hunk:
    def __init__(self, old_start, old_count, new_start, new_count, lines):
        self.old_start = old_start
        self.old_count = old_count
        self.new_start = new_start
        self.new_count = new_count
        self.lines = lines

    def __repr__(self):
        return (f"Hunk(old_start={self.old_start}, old_count={self.old_count}, "
                f"new_start={self.new_start}, new_count={self.new_count}, "
                f"lines={self.lines})")

class UnifiedDiff:
    def __init__(self, old_filename, new_filename, hunks):
        self.old_filename = old_filename
        self.new_filename = new_filename
        self.hunks = hunks

    def __repr__(self):
        return (f"UnifiedDiff(old_filename={self.old_filename}, "
                f"new_filename={self.new_filename}, hunks={self.hunks})")

def parse_unified_diff(diff_text):
    """
    Parses a unified diff string, recalculates hunk counts from the actual hunk lines,
    and returns a UnifiedDiff instance. Also converts Windows CRLF to Unix LF.
    """
    # Convert Windows CRLF to Unix LF.
    diff_text = diff_text.replace("\r\n", "\n")
    lines = diff_text.splitlines()

    old_filename = None
    new_filename = None
    hunks = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith('--- '):
            old_filename = line[4:].strip()
            i += 1
            if i < len(lines) and lines[i].startswith('+++ '):
                new_filename = lines[i][4:].strip()
                i += 1
            else:
                raise ValueError("Diff missing +++ filename after --- filename")
        elif line.startswith('@@'):
            # Parse the hunk header.
            m = re.match(r'@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@', line)
            if not m:
                raise ValueError("Invalid hunk header: " + line)
            old_start = int(m.group(1))
            old_count = int(m.group(2)) if m.group(2) else 1
            new_start = int(m.group(3))
            new_count = int(m.group(4)) if m.group(4) else 1
            i += 1
            hunk_lines = []
            # Collect hunk body lines until we reach the next header.
            while i < len(lines) and not lines[i].startswith('@@') \
                  and not lines[i].startswith('--- ') and not lines[i].startswith('+++ '):
                hunk_lines.append(lines[i])
                i += 1
            # Recalculate counts from the actual hunk lines.
            # For the old file, count lines starting with ' ' or '-'
            calculated_old_count = sum(1 for l in hunk_lines if l and l[0] in (' ', '-'))
            # For the new file, count lines starting with ' ' or '+'
            calculated_new_count = sum(1 for l in hunk_lines if l and l[0] in (' ', '+'))
            # Override parsed counts with recalculated ones.
            old_count = calculated_old_count
            new_count = calculated_new_count
            hunks.append(Hunk(old_start, old_count, new_start, new_count, hunk_lines))
        else:
            # Skip any non-header lines (e.g., metadata)
            i += 1

    if old_filename is None or new_filename is None:
        raise ValueError("Diff does not contain valid file header information.")

    return UnifiedDiff(old_filename, new_filename, hunks)

def reconstruct_unified_diff(unified_diff):
    """
    Reconstructs the unified diff text from a UnifiedDiff instance.
    Always produces Unix LF line endings.
    """
    parts = []
    parts.append(f"--- {unified_diff.old_filename}")
    parts.append(f"+++ {unified_diff.new_filename}")
    for hunk in unified_diff.hunks:
        parts.append(f"@@ -{hunk.old_start},{hunk.old_count} +{hunk.new_start},{hunk.new_count} @@")
        parts.extend(hunk.lines)
    # Ensure the diff ends with a newline.
    return "\n".join(parts) + "\n"

