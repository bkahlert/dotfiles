import shutil
import subprocess

import pytest

from repo import HOME_SOURCE, SYSTEM_PATH, isolated_env

# The sandbox guards `chezmoi`, so the real one is resolved here; the lint-and-unit CI job has none and skips.
CHEZMOI = shutil.which("chezmoi")
LOGIN_HOOK = [".startup", ".startup.log", "Library/LaunchAgents/com.user.startup.plist"]


@pytest.mark.skipif(CHEZMOI is None, reason="chezmoi is not installed")
class TestChezmoiremove:
    def test_should_remove_the_retired_login_hook_from_a_machine_that_still_has_it(self, tmp_path):
        home = tmp_path / "home"
        env = isolated_env(home, list(SYSTEM_PATH))
        for target in LOGIN_HOOK:
            (home / target).parent.mkdir(parents=True, exist_ok=True)
            (home / target).write_text("left over from a machine that applied the old dotfiles\n")
        config = tmp_path / "chezmoi.toml"
        config.write_text('[data]\n  email = "test@example.com"\n  name = "Test User"\n  company = ""\n')
        result = subprocess.run(
            [CHEZMOI, "apply", "--config", str(config), "--source", str(HOME_SOURCE), "--destination", str(home),
             "--exclude=scripts,templates", "--no-tty"],
            env=env, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=120)
        assert result.returncode == 0, result.stderr
        assert [target for target in LOGIN_HOOK if (home / target).exists()] == []
