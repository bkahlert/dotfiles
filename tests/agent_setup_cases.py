import pytest

AGENTS = {"claude": "claude-code", "copilot": "github-copilot", "gemini": "gemini-cli"}


class AgentSetupCases:
    @pytest.mark.parametrize("company", ["", "bkahlert", "ista", "other"])
    def test_should_install_skills_only_for_its_agent(self, script, fake_bin, calls, tmp_path, company):
        for agent in AGENTS:
            fake_bin(agent, script='[[ $2 == marketplace && $3 == list ]] && printf "[]\\n"\nexit 0\n')
        fake_bin("fnm", stdout='export PATH="$HOME/node/bin:$PATH"')
        fake_bin("npx")
        result = script(f"setup-{self.agent}", prefix_root=tmp_path, company=company)
        assert result.returncode == 0, result.stderr
        assert calls("npx") == skill_calls(self.agent)
        assert all(calls(agent) == [] for agent in AGENTS if agent != self.agent)

    @pytest.mark.parametrize("os", ["Darwin", "Linux"])
    def test_should_skip_without_its_agent_or_node(self, script, sandbox, tmp_path, os):
        sandbox.only_tools()
        result = script(f"setup-{self.agent}", prefix_root=tmp_path, uname=os)
        assert (result.returncode, result.stdout, result.stderr) == (0, "", "")

    def test_should_fail_when_fnm_is_missing(self, script, fake_bin, calls, tmp_path):
        fake_bin(self.agent)
        result = script(f"setup-{self.agent}", prefix_root=tmp_path)
        assert result.returncode == 1
        assert "fnm not found" in result.stderr
        assert calls(self.agent) == []

    def test_should_surface_fnm_initialization_failure(self, script, fake_bin, calls, tmp_path):
        fake_bin(self.agent)
        fake_bin("fnm", exit_code=3, stderr="fnm failed\n")
        result = script(f"setup-{self.agent}", prefix_root=tmp_path)
        assert (result.returncode, result.stderr) == (3, "fnm failed\n")
        assert calls(self.agent) == []

    def test_should_stop_after_the_first_failed_skill_install(self, script, fake_bin, calls, tmp_path):
        fake_bin(self.agent, script='[[ $2 == marketplace && $3 == list ]] && printf "[]\\n"\nexit 0\n')
        fake_bin("fnm")
        fake_bin("npx", exit_code=4)
        result = script(f"setup-{self.agent}", prefix_root=tmp_path)
        assert result.returncode == 4
        assert len(calls("npx")) == 1

    @pytest.mark.parametrize("prefix", ["/opt/homebrew", "/usr/local", ".local", "node"])
    def test_should_find_the_agent_and_npx_off_path(self, script, sandbox, tmp_path, prefix):
        sandbox.only_tools("jq")
        sandbox.fake_bin("fnm", stdout='export PATH="$HOME/node/bin:$PATH"')
        bin_dir = ((sandbox.home / prefix) if prefix in (".local", "node")
                   else tmp_path / prefix.lstrip("/")) / "bin"
        bin_dir.mkdir(parents=True)
        (bin_dir / self.agent).write_text(
            '#!/bin/sh\n[ "$3" = list ] && printf "[]\\n"\nexit 0\n')
        (bin_dir / self.agent).chmod(0o755)
        node_bin = sandbox.home / "node" / "bin"
        node_bin.mkdir(parents=True, exist_ok=True)
        (node_bin / "npx").write_text('#!/bin/sh\nprintf "%s\\n" "$*" >> "$HOME/npx-calls"\n')
        (node_bin / "npx").chmod(0o755)
        result = script(f"setup-{self.agent}", prefix_root=tmp_path)
        assert result.returncode == 0, result.stderr
        assert len((sandbox.home / "npx-calls").read_text().splitlines()) == 3


def skill_calls(agent):
    return [["--yes", "skills", "add", "-g", f"mattpocock/skills/skills/productivity/{skill}",
             "--agent", AGENTS[agent], "-y"] for skill in ("grill-me", "grilling", "handoff")]
