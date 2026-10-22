import stat
import subprocess
import tomllib

import pytest

from repo import HOME_SOURCE, SYSTEM_PATH, isolated_env, require_chezmoi


class TestCodexConfig:
    @pytest.mark.parametrize("command", ["diff", "apply"])
    def test_should_ignore_unrelated_chezmoi_data_in_the_temporary_directory(self, tmp_path, command):
        home = tmp_path / "home"
        env = isolated_env(home, list(SYSTEM_PATH))
        (home / ".codex").mkdir()
        (home / ".codex" / "config.toml").write_text('model = "local-choice"\n')
        (home / "tmp" / ".chezmoidata.toml").write_text("broken = [")
        result = subprocess.run(
            [require_chezmoi(), "--source", str(HOME_SOURCE), "--destination", str(home),
             "--config", "/dev/null", "--config-format", "toml",
             "--persistent-state", str(tmp_path / "state.boltdb"),
             command, "--exclude=scripts", str(home / ".codex" / "config.toml")],
            env=env, cwd=home, capture_output=True, text=True, timeout=30)
        assert result.returncode == 0, result.stderr
        assert list((home / "tmp").iterdir()) == [home / "tmp" / ".chezmoidata.toml"]

    def test_should_apply_instructions_and_preserve_machine_local_state(self, tmp_path):
        home = tmp_path / "home"
        env = isolated_env(home, list(SYSTEM_PATH))
        codex = home / ".codex"
        codex.mkdir()
        (codex / "config.toml").write_text(
            'model = "local-choice"\n[projects."/work"]\ntrust_level = "trusted"\n'
            '[mcp_servers.private]\ncommand = "internal-server"\n'
            '[tui]\nstatus_line_use_colors = false\n'
            '[plugins."superpowers@superpowers-dev"]\nenabled = false\n')
        local = {
            "auth.json": '{"access_token":"test-placeholder"}',
            "history.jsonl": '{"session_id":"local-session"}\n',
        }
        for name, content in local.items():
            (codex / name).write_text(content)
        command = [
            require_chezmoi(), "--source", str(HOME_SOURCE), "--destination", str(home),
            "--config", "/dev/null", "--config-format", "toml",
            "--persistent-state", str(tmp_path / "state.boltdb"),
            "apply", "--exclude=scripts", str(codex),
        ]
        for _ in range(2):
            result = subprocess.run(command, env=env, cwd=home, capture_output=True, text=True, timeout=30)
            assert result.returncode == 0, result.stderr
            assert (codex / "AGENTS.md").read_bytes() == (HOME_SOURCE / "private_dot_codex" / "AGENTS.md").read_bytes()
            assert "~/.config/agents/AGENTS.md" in (codex / "AGENTS.md").read_text()
            assert stat.S_IMODE(codex.stat().st_mode) == 0o700
            assert stat.S_IMODE((codex / "config.toml").stat().st_mode) == 0o600
            settings = tomllib.loads((codex / "config.toml").read_text())
            assert settings["model"] == "local-choice"
            assert settings["projects"] == {"/work": {"trust_level": "trusted"}}
            assert settings["mcp_servers"]["private"] == {"command": "internal-server"}
            assert settings["mcp_servers"]["idea"] == {"url": "http://127.0.0.1:64342/stream"}
            assert settings["tui"]["status_line_use_colors"] is True
            assert settings["plugins"]["superpowers@superpowers-dev"]["enabled"] is True
            assert {name: (codex / name).read_text() for name in local} == local
