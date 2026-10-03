import subprocess

import pytest

from repo import chezmoiscripts

SOURCES = dict(chezmoiscripts())


@pytest.fixture
def script(sandbox, fake_bin):
    def run(key, *args, uname="Darwin", stdin=None, env=None, timeout=30):
        if uname:
            fake_bin("uname", stdout=f"{uname}\n")
        feed = {"input": stdin} if stdin is not None else {"stdin": subprocess.DEVNULL}
        return subprocess.run(["bash", str(SOURCES[key]), *args], env={**sandbox.env, **(env or {})},
                              cwd=sandbox.home, **feed, capture_output=True, text=True, timeout=timeout)
    return run
