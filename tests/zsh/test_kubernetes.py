import shlex

import pytest

from repo import module_path


@pytest.fixture(autouse=True)
def bare(sandbox):
    sandbox.only_tools("zsh")


class TestKubernetes:
    def test_should_leave_kubectl_to_editor(self, zsh):
        result = zsh(f"source {shlex.quote(str(module_path('10-kubernetes.zsh')))}\nprint -r -- \"${{KUBE_EDITOR-unset}}\"")
        assert result.stdout == "unset\n"
