=====================
LLM Output Format
=====================

The LLM must output responses in a structured format with specific tags for different actions.

Tag Structure
-------------

- All sections use opening `[TAG]` and closing `[/TAG]` markers
- Each section must be separated by at least one newline
- Multiple sections can appear in any order

[TALK] Section
~~~~~~~~~~~~~~

- Purpose: Communication with the user
- Content: Plain text for explanations, questions, or information
- Example:
  ::
    [TALK]
    Let's modify a Python file
    [/TALK]

[RUN] Section
~~~~~~~~~~~~~

- Purpose: Execute shell commands
- Content: Single-line shell command
- Example:
  ::
    [RUN]
    ls -la
    [/RUN]

[CODE] Section
~~~~~~~~~~~~~~

- Purpose: Modify code files with diff support
- Content:
  - First line: file path (relative or absolute)
  - Followed by ~~~before section with previous content (empty string if new file)
  - Followed by ~~~after section with new content
- Example (new file):
  ::
    [CODE]
    src/main.py
    ~~~before
    ~~~
    ~~~after
    def hello():
        print("Hello, World!")
    ~~~
    [/CODE]
- Example (modification):
  ::
    [CODE]
    src/main.py
    ~~~before
    def hello():
        print("Hello")
    ~~~
    ~~~after
    def hello():
        print("Hello, World!")
    ~~~
    [/CODE]

Full Example
~~~~~~~~~~~~

::
  [TALK]
  I'll modify a file and run a command
  [/TALK]

  [RUN]
  pip install requests
  [/RUN]

  [CODE]
  app.py
  ~~~before
  print("Hello")
  ~~~
  ~~~after
  import requests
  print("Hello, World!")
  ~~~
  [/CODE]

Parser Output
~~~~~~~~~~~~~

- The parser returns a list of operations in the order they appear in the response
- Each operation is a dictionary with a 'type' key and relevant data:
  - {'type': 'talk', 'content': string}
  - {'type': 'run', 'command': string}
  - {'type': 'code', 'file_path': string, 'before': string, 'after': string}
