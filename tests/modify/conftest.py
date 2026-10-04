import subprocess

import pytest


@pytest.fixture
def modify(sandbox):
    """Run a modify_ script the way chezmoi does: the current target on stdin, the new content on stdout."""
    def run(script, current, **env):
        return subprocess.run(["bash", str(script)], input=current, env={**sandbox.env, **env}, cwd=sandbox.home,
                              capture_output=True, text=True, timeout=10)
    return run
