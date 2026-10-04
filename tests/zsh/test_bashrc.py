import shlex

import pytest

from repo import HOME_SOURCE

BASHRC = shlex.quote(str(HOME_SOURCE / "dot_bashrc"))


@pytest.fixture(autouse=True)
def bare(sandbox):
    sandbox.only_tools()


class TestBashrc:
    def test_should_init_starship(self, sandbox, fake_bin):
        fake_bin("starship", stdout="echo starship-prompt\n")
        result = sandbox.run("bash", "--norc", "-c", f"source {BASHRC}")
        assert (result.stdout, result.stderr) == ("starship-prompt\n", "")

    class TestOnMissingStarship:
        def test_should_stay_silent(self, sandbox):
            result = sandbox.run("bash", "--norc", "-c", f"source {BASHRC}")
            assert (result.returncode, result.stdout, result.stderr) == (0, "", "")
