import subprocess

import pytest

# macOS ships bash 3.2 and the Brewfile installs a newer one; a script that needs it must say so
# instead of dying on an unbound array or an unknown option halfway through.
NEEDS_BASH_4_4 = ("cleanup",)
SYSTEM_BASH = "/bin/bash"


def system_bash_major():
    return int(subprocess.run([SYSTEM_BASH, "-c", "echo ${BASH_VERSINFO[0]}"], capture_output=True, text=True).stdout)


@pytest.mark.skipif(system_bash_major() >= 4, reason="this system's /bin/bash is new enough")
class TestOnOldBash:
    @pytest.mark.parametrize("name", NEEDS_BASH_4_4)
    def test_should_exit_1_and_name_the_fix(self, run, bin_links, name):
        result = run(SYSTEM_BASH, str(bin_links / name), "--help")
        assert result.returncode == 1
        assert result.stdout == ""
        assert result.stderr.startswith(f"{name}: needs bash 4.4 or newer, found 3.")
        assert result.stderr.endswith("; install it with: brew install bash\n")
