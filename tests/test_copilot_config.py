import json
import stat
import subprocess

from repo import HOME_SOURCE, SYSTEM_PATH, isolated_env, require_chezmoi


class TestCopilotConfig:
    def test_should_apply_instructions_and_settings_without_owning_other_copilot_state(self, tmp_path):
        home = tmp_path / "home"
        env = isolated_env(home, list(SYSTEM_PATH))
        copilot = home / ".copilot"
        copilot.mkdir()
        (copilot / "settings.json").write_text('{"model":"local-choice"}')
        (copilot / "mcp-config.json").write_text('{"mcpServers":{}}')
        result = subprocess.run(
            [require_chezmoi(), "--source", str(HOME_SOURCE), "--destination", str(home),
             "--config", "/dev/null", "--config-format", "toml",
             "--persistent-state", str(tmp_path / "state.boltdb"),
             "apply", "--exclude=scripts", str(copilot)],
            env=env, cwd=home, capture_output=True, text=True, timeout=30)
        assert result.returncode == 0, result.stderr
        source = HOME_SOURCE / "private_dot_copilot"
        assert (copilot / "copilot-instructions.md").read_bytes() == (source / "copilot-instructions.md").read_bytes()
        assert (copilot / "settings.json").read_bytes() == (source / "private_settings.json").read_bytes()
        settings = json.loads((copilot / "settings.json").read_text())
        assert settings["model"] == "auto"
        assert settings["statusLine"] == {
            "type": "command",
            "command": "~/.copilot/statusline",
        }
        assert settings["footer"] == {
            "showAgent": True,
            "showAiUsed": True,
            "showContextWindow": True,
            "showModelEffort": True,
            "showQuota": True,
            "showYolo": True,
            "showCiStatus": True,
            "showBranch": True,
            "showPullRequest": True,
            "showDirectory": True,
            "showCodeChanges": True,
            "showUsername": True,
            "showSandbox": True,
            "showCustom": True,
        }
        assert stat.S_IMODE(copilot.stat().st_mode) == 0o700
        assert stat.S_IMODE((copilot / "settings.json").stat().st_mode) == 0o600
        assert (copilot / "mcp-config.json").read_text() == '{"mcpServers":{}}'

    def test_should_keep_superpowers_enabled_across_repeated_apply(self, tmp_path):
        home = tmp_path / "home"
        env = isolated_env(home, list(SYSTEM_PATH))
        copilot = home / ".copilot"
        copilot.mkdir()
        installed = {
            "enabledPlugins": {"superpowers@superpowers-marketplace": True},
            "extraKnownMarketplaces": {
                "superpowers-marketplace": {
                    "source": {"source": "github", "repo": "obra/superpowers-marketplace"},
                },
            },
        }
        (copilot / "settings.json").write_text(json.dumps(installed))
        command = [
            require_chezmoi(), "--source", str(HOME_SOURCE), "--destination", str(home),
            "--config", "/dev/null", "--config-format", "toml",
            "--persistent-state", str(tmp_path / "state.boltdb"),
            "apply", "--exclude=scripts", str(copilot),
        ]
        for _ in range(2):
            result = subprocess.run(command, env=env, cwd=home, capture_output=True, text=True, timeout=30)
            assert result.returncode == 0, result.stderr
            settings = json.loads((copilot / "settings.json").read_text())
            assert settings["enabledPlugins"] == installed["enabledPlugins"]
            assert settings["extraKnownMarketplaces"] == installed["extraKnownMarketplaces"]
