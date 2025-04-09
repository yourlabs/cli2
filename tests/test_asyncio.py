import cli2
import pytest


@pytest.mark.asyncio
async def test_files_read(tmp_path):
    files = [tmp_path / 'a', tmp_path / 'b', tmp_path / 'c']
    expected = dict()
    for file in files:
        content = f'{file.name}content'
        with file.open('w') as f:
            f.write(content)
        expected[file] = content
    result = await cli2.files_read(*files)
    assert result == expected
