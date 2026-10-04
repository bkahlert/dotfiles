import subprocess

from repo import HOME_SOURCE, SYSTEM_PATH, isolated_env, require_chezmoi

LOGIN_HOOK = [".startup", ".startup.log", "Library/LaunchAgents/com.user.startup.plist"]


class TestChezmoiremove:
    def test_should_remove_the_retired_login_hook_from_a_machine_that_still_has_it(self, tmp_path):
        chezmoi = require_chezmoi()
        home = tmp_path / "home"
        env = isolated_env(home, list(SYSTEM_PATH))
        for target in LOGIN_HOOK:
            (home / target).parent.mkdir(parents=True, exist_ok=True)
            (home / target).write_text("left over from a machine that applied the old dotfiles\n")
        config = tmp_path / "chezmoi.toml"
        config.write_text('[data]\n  email = "test@example.com"\n  name = "Test User"\n  company = ""\n')
        result = subprocess.run(
            [chezmoi, "apply", "--config", str(config), "--source", str(HOME_SOURCE), "--destination", str(home),
             "--exclude=scripts,templates", "--no-tty"],
            env=env, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=120)
        assert result.returncode == 0, result.stderr
        assert [target for target in LOGIN_HOOK if (home / target).exists()] == []
