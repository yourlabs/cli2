from code2 import project
from pathlib import Path
from sqlalchemy import select
import os
from pathlib import Path
from sqlalchemy import select, or_
from sqlalchemy.orm import joinedload
from code2 import db


def paths():
    return [Path(__file__).parent / 'prompts']


async def symbols_src(*symbol_names):
    """
    Retrieve the code snippets for a given list of symbol names from their files.
    Uses project to access the database and project path.

    Args:
        symbol_names: List of symbol names to look up

    Returns:
        List of code strings (None for symbols where code couldn't be retrieved)
    """
    return '\n\n\n'.join(await project.symbols.src(*symbol_names))


# Example usage:
async def main():
    # Assuming project is set
    symbol_names = ["function1", "class2", "variable3"]
    codes = await get_symbol_codes(symbol_names)
    for i, code in enumerate(codes):
        print(f"db.Symbol: {symbol_names[i]}")
        if code:
            print("Code:")
            print(code)
        else:
            print("No code retrieved")
        print("---")

# If you need to run it:
# import asyncio
# asyncio.run(main())
