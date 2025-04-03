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
    def __init__(self, old_filename, new_filename, hunks, strip_count=0):
        self.old_filename = old_filename
        self.new_filename = new_filename
        self.hunks = hunks
        # strip_count indicates how many leading path components should be stripped when patching.
        self.strip_count = strip_count

    def __repr__(self):
        return (f"UnifiedDiff(old_filename={self.old_filename}, "
                f"new_filename={self.new_filename}, strip_count={self.strip_count}, "
                f"hunks={self.hunks})")

def parse_unified_diff(diff_text):
    """
    Parses a unified diff string, recalculates hunk counts from the actual hunk lines,
    and returns a UnifiedDiff instance. Also converts Windows CRLF to Unix LF.
    Additionally, it discards hunks that do not effect any change.
    For non-new-file diffs, the original header counts are preserved.
    It also analyzes the file header paths to suggest a -p flag for patch.
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
            # Parse hunk header and capture original counts.
            m = re.match(r'@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@', line)
            if not m:
                raise ValueError("Invalid hunk header: " + line)
            old_start = int(m.group(1))
            original_old_count = int(m.group(2)) if m.group(2) else 1
            new_start = int(m.group(3))
            original_new_count = int(m.group(4)) if m.group(4) else 1
            i += 1
            hunk_lines = []
            while i < len(lines) and not (lines[i].startswith('@@') or lines[i].startswith('--- ') or lines[i].startswith('+++ ')):
                hunk_lines.append(lines[i])
                i += 1

            # Recalculate counts from hunk lines.
            calculated_old_count = sum(1 for l in hunk_lines if l and l[0] in (' ', '-'))
            calculated_new_count = sum(1 for l in hunk_lines if l and l[0] in (' ', '+'))
            if old_filename == "/dev/null":
                calculated_old_count = 0

            # Compute effective content (ignoring the diff markers):
            def effective_content(lines, allowed_prefixes):
                return [l[1:] for l in lines if l and l[0] in allowed_prefixes]

            old_effective = effective_content(hunk_lines, (' ', '-'))
            new_effective = effective_content(hunk_lines, (' ', '+'))
            # If the effective content is the same, this hunk is a no-op.
            if old_effective == new_effective:
                continue

            # For new file diffs, use recalculated counts; otherwise, preserve original counts.
            if old_filename == "/dev/null":
                hunk_old_count = calculated_old_count
                hunk_new_count = calculated_new_count
            else:
                hunk_old_count = original_old_count
                hunk_new_count = original_new_count

            hunks.append(Hunk(old_start, hunk_old_count, new_start, hunk_new_count, hunk_lines))
        else:
            i += 1

    if old_filename is None or new_filename is None:
        raise ValueError("Diff does not contain valid file header information.")

    # Determine if we should suggest a -p flag.
    strip_count = 0
    if old_filename.startswith("a/") and new_filename.startswith("b/"):
        strip_count = 1

    return UnifiedDiff(old_filename, new_filename, hunks, strip_count=strip_count)

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
    return "\n".join(parts) + "\n"

