import pytest


@pytest.fixture
def playbook(tmp_path, request):
    from cansible.playbook import Playbook
    return Playbook(tmp_path, name=request.node.originalname)
