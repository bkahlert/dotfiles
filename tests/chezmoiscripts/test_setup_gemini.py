from agent_setup_cases import AgentSetupCases, skill_calls


class TestSetupGemini(AgentSetupCases):
    agent = "gemini"

    def test_should_only_install_skills_without_configuring_servers(self, script, fake_bin, calls, tmp_path):
        fake_bin("fnm")
        fake_bin("gemini")
        fake_bin("npx")
        result = script("setup-gemini", prefix_root=tmp_path)
        assert result.returncode == 0, result.stderr
        assert calls("gemini") == []
        assert calls("npx") == skill_calls("gemini")
