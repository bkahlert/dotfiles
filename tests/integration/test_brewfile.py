import os
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
        # brew info neither taps a third-party tap nor loads its formulae untrusted; brew bundle does both for an
        # entry marked trusted, so the check taps and lifts the trust requirement for itself.
        for tap in {name.rsplit("/", 1)[0] for name in names if name.count("/") == 2}:
            subprocess.run(["brew", "tap", tap], check=True, capture_output=True, text=True, timeout=300)
        result = subprocess.run(["brew", "info", "--json=v2", f"--{'formula' if kind == 'brew' else 'cask'}", *names],
                                env={**os.environ, "HOMEBREW_NO_REQUIRE_TAP_TRUST": "1"},
                                capture_output=True, text=True, timeout=300)
        assert result.returncode == 0, f"brew does not know one of {names}:\n{result.stderr}"
