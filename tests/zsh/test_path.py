import shlex

import pytest

from repo import module_path

START_PATH = "/usr/bin:/bin"


@pytest.fixture(autouse=True)
def bare(sandbox):
    sandbox.only_tools("zsh")


def path_after(zsh, start=START_PATH):
    """The PATH entries, one per line, after the module ran on a shell whose PATH was `start`."""
    return zsh(f"PATH={start}\nsource {shlex.quote(str(module_path('09-path.zsh')))}\nprint -l -- $path")


class TestPath:
    def test_should_put_local_bin_and_usr_local_sbin_in_front_of_the_existing_path(self, zsh, sandbox):
        result = path_after(zsh)
        assert (result.stdout.splitlines(), result.stderr) == (
            [f"{sandbox.home}/.local/bin", "/usr/local/sbin", "/usr/bin", "/bin"], "")

    def test_should_list_an_entry_it_would_add_twice_once_and_in_front(self, zsh, sandbox):
        result = path_after(zsh, f"/usr/bin:{sandbox.home}/.local/bin:/bin:/usr/local/sbin")
        assert result.stdout.splitlines() == [f"{sandbox.home}/.local/bin", "/usr/local/sbin", "/usr/bin", "/bin"]

    def test_should_drop_duplicates_the_path_already_had(self, zsh, sandbox):
        result = path_after(zsh, "/usr/bin:/bin:/usr/bin")
        assert result.stdout.splitlines() == [f"{sandbox.home}/.local/bin", "/usr/local/sbin", "/usr/bin", "/bin"]
