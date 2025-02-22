import pytest
from .playbook import Playbook


@pytest.fixture
def playbook(tmp_path, request):
    return Playbook(tmp_path, name=request.node.originalname)
