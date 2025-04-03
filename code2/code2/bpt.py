def parse(response):
    operations = []

    # Handle empty input
    if not response.strip():
        return operations

    # Split lines and process manually
    lines = response.split('\n')
    i = 0

    while i < len(lines):
        line = lines[i].strip()
        if not line:  # Skip empty lines between blocks
            i += 1
            continue

        op_type = line.rstrip('>')

        if op_type == 'chat':
            i += 1
            content_lines = []
            while i < len(lines) and lines[i].strip() and not lines[i].endswith('>'):
                content_lines.append(lines[i])
                i += 1
            content = '\n'.join(content_lines).strip()
            operations.append({'type': 'chat', 'content': content})

        elif op_type == 'command':
            i += 1
            if i < len(lines) and lines[i].strip():
                command = lines[i].strip()
                operations.append({'type': 'command', 'command': command})
            else:
                operations.append({'type': 'chat', 'content': 'Error: No command provided after "command>".'})
            i += 1

        elif op_type == 'diff':
            i += 1
            if i >= len(lines) or not lines[i].strip():
                operations.append({'type': 'chat', 'content': 'Error: No file path provided after "diff>".'})
                i += 1
                continue

            path = lines[i].strip()
            i += 1

            # Collect before: and after: sections
            before_lines = []
            after_lines = []
            current_section = None

            while i < len(lines):
                line = lines[i].strip()
                if line.endswith('>') and line != 'before:' and line != 'after:':  # New block starts
                    break
                if line == 'before:':
                    current_section = before_lines
                elif line == 'after:':
                    current_section = after_lines
                elif current_section is not None and line:
                    current_section.append(lines[i])  # Preserve original indentation
                i += 1

            if not before_lines or not after_lines:
                operations.append({'type': 'chat', 'content': 'Error: "diff>" block missing valid "before:" or "after:" sections.'})
                continue

            before_content = '\n'.join(before_lines).strip()
            after_content = '\n'.join(after_lines).strip()

            operations.append({
                'type': 'diff',
                'path': path,
                'before': before_content,
                'after': after_content
            })

        else:
            operations.append({'type': 'chat', 'content': f'Error: Unknown operation type "{op_type}".'})
            i += 1

    return operations
