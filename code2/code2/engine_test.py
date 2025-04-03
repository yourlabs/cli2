import sys
from pathlib import Path
import datetime
async def main():
    from code2.cli import Engine
    dt = datetime.datetime.now().timestamp()
    path = Path(__file__).parent.parent.parent / 'tests/code2/test_story'
    with path.open('r') as f:
        response = f.read()
    await Engine().handle_response(response.replace('{dt}', str(int(dt))))


import asyncio
asyncio.run(main())
