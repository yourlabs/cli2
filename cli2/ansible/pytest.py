import pytest

try:
    from .playbook import Playbook
except ImportError:
    pass
else:
    @pytest.fixture
    def playbook(tmp_path, request):
        return Playbook(tmp_path, name=request.node.originalname)
