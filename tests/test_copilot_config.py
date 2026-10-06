import json
import stat
import subprocess

import pytest

from repo import CONTEXTS, HOME_SOURCE, SYSTEM_PATH, isolated_env, require_chezmoi


class TestCopilotConfig:
    @pytest.mark.parametrize("company", CONTEXTS, ids=lambda company: company or "none")
    def test_should_apply_instructions_and_settings_without_owning_other_copilot_state(self, tmp_path, company):
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
             "--override-data", json.dumps({"company": company}), "apply", "--exclude=scripts", str(copilot)],
            env=env, cwd=home, capture_output=True, text=True, timeout=30)
        assert result.returncode == 0, result.stderr
        source = HOME_SOURCE / "private_dot_copilot"
        assert (copilot / "copilot-instructions.md").read_bytes() == (source / "copilot-instructions.md").read_bytes()
        assert (copilot / "settings.json").read_bytes() == (source / "private_settings.json").read_bytes()
        assert json.loads((copilot / "settings.json").read_text())["model"] == "auto"
        assert stat.S_IMODE(copilot.stat().st_mode) == 0o700
        assert stat.S_IMODE((copilot / "settings.json").stat().st_mode) == 0o600
        assert (copilot / "mcp-config.json").read_text() == '{"mcpServers":{}}'
