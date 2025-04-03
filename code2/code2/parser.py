# coding_assistant.py
import re


class Parser:
    def __init__(self):
        self.talk_pattern = r'\[TALK\](.*?)\[/TALK\]'
        self.run_pattern = r'\[RUN\](.*?)\[/RUN\]'
        self.code_pattern = r'\[CODE\](.*?)\[/CODE\]'

    def parse(self, response: str):
        """Parse LLM response into a list of operations in order."""
        operations = []

        # Split response into sections while preserving order
        pattern = r'(\[TALK\].*?\[/TALK\]|\[RUN\].*?\[/RUN\]|\[CODE\].*?\[/CODE\])'
        sections = re.split(pattern, response, flags=re.DOTALL)

        for section in sections:
            section = section.strip()
            if not section:
                continue

            # Handle TALK
            talk_match = re.match(self.talk_pattern, section, re.DOTALL)
            if talk_match:
                operations.append({
                    'type': 'talk',
                    'content': talk_match.group(1).strip()
                })
                continue

            # Handle RUN
            run_match = re.match(self.run_pattern, section, re.DOTALL)
            if run_match:
                operations.append({
                    'type': 'run',
                    'command': run_match.group(1).strip()
                })
                continue

            # Handle CODE
            code_match = re.match(self.code_pattern, section, re.DOTALL)
            if code_match:
                content = code_match.group(1).strip()
                lines = content.split('\n')
                if len(lines) < 3:
                    continue

                file_path = lines[0].strip()
                before_content = ""
                after_content = ""
                current_section = None
                has_before = False
                has_after = False

                for line in lines[1:]:
                    line = line.rstrip()
                    if line == "~~~before":
                        current_section = "before"
                        has_before = True
                        continue
                    elif line == "~~~after":
                        current_section = "after"
                        has_after = True
                        continue
                    elif line == "~~~":
                        current_section = None
                        continue

                    if current_section == "before":
                        before_content += line + "\n" if line else ""
                    elif current_section == "after":
                        after_content += line + "\n" if line else ""

                if has_before and has_after:
                    operations.append({
                        'type': 'code',
                        'file_path': file_path,
                        'before': before_content.rstrip(),
                        'after': after_content.rstrip()
                    })

        return operations

    def execute(self, response: str):
        """Execute the parsed response (simulated)."""
        operations = self.parse(response)

        for op in operations:
            if op['type'] == 'talk':
                print(f"Talking to user: {op['content']}")
            elif op['type'] == 'run':
                print(f"Running command: {op['command']}")
            elif op['type'] == 'code':
                print(f"Modifying {op['file_path']}:")
                print(f"Before:\n{op['before']}")
                print(f"After:\n{op['after']}")

# Example usage
if __name__ == "__main__":
    sample_response = """
    [TALK]
    Let's modify a Python file
    [/TALK]

    [RUN]
    mkdir test_dir
    [/RUN]

    [CODE]
    test.py
    ~~~before
    print("Hi")
    ~~~
    ~~~after
    def hello():
        print("Hello, World!")
    ~~~
    [/CODE]
    """

    parser = Parser()
    parser.execute(sample_response)
