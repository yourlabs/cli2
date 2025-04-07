"""
Functions that will be exposed in Jinja2.

Add yours over the code2_jinja2 entry point plugin!
"""

def read(path):
    with open(path, 'r') as f:
        content = f.read()
    return content
