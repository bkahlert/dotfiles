import shlex

import pytest

from repo import module_path

START_PATH = "/usr/bin:/bin"


@pytest.fixture(autouse=True)
def bare(sandbox):
    sandbox.only_tools("zsh")


@pytest.fixture
def user_python(sandbox):
    """~/Library/Python as pip --user leaves it: one directory per version, scripts in its bin."""
    root = sandbox.home / "Library" / "Python"

    def install(*versions, without_bin=(), bin_as_file=()):
        for version in versions:
            (root / version).mkdir(parents=True)
            if version in bin_as_file:
                (root / version / "bin").write_text("")
            elif version not in without_bin:
                (root / version / "bin").mkdir()
        return root
    return install


def path_after(zsh, ostype="darwin24.0"):
    """The PATH entries, one per line, after the module ran on a shell of the given OSTYPE."""
    return zsh(f"OSTYPE={ostype}\nPATH={START_PATH}\nsource {shlex.quote(str(module_path('10-python.zsh')))}\nprint -l -- $path")


class TestPython:
    class TestOnMacOS:
        def test_should_put_the_bin_directory_of_the_highest_python_version_in_front(self, zsh, user_python):
            root = user_python("3.9", "3.12", "3.10")
            result = path_after(zsh)
            assert (result.stdout.splitlines(), result.stderr) == ([f"{root}/3.12/bin", "/usr/bin", "/bin"], "")

        def test_should_skip_versions_whose_bin_is_missing_or_not_a_directory(self, zsh, user_python):
            root = user_python("3.11", "3.13", "3.14", without_bin=["3.13"], bin_as_file=["3.14"])
            result = path_after(zsh)
            assert result.stdout.splitlines() == [f"{root}/3.11/bin", "/usr/bin", "/bin"]

        def test_should_leave_the_path_alone_when_no_python_is_installed(self, zsh):
            result = path_after(zsh)
            assert (result.stdout.splitlines(), result.stderr) == (["/usr/bin", "/bin"], "")

    class TestOnLinux:
        def test_should_leave_the_path_alone_even_when_the_directory_exists(self, zsh, user_python):
            user_python("3.12")
            result = path_after(zsh, "linux-gnu")
            assert (result.stdout.splitlines(), result.stderr) == (["/usr/bin", "/bin"], "")
