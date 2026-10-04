import re
import shutil
import subprocess

import pytest

from repo import brewfile_lines

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(shutil.which("brew") is None, reason="needs Homebrew"),
]


class TestBrewfilePackages:
    @pytest.mark.parametrize("kind", ["brew", "cask"])
    def test_should_exist_in_homebrew(self, kind):
        names = [m.group(1) for line in brewfile_lines() if (m := re.match(rf'{kind} "([^"]+)"', line))]
        result = subprocess.run(["brew", "info", "--json=v2", f"--{'formula' if kind == 'brew' else 'cask'}", *names],
                                capture_output=True, text=True, timeout=300)
        assert result.returncode == 0, f"brew does not know one of {names}:\n{result.stderr}"
