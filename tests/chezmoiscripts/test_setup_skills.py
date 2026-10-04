import re

import pytest

AGENTS = {
    "bkahlert": ["claude-code"],
    "ista": ["claude-code", "gemini-cli", "github-copilot"],
}
SKILLS = ("grill-me", "handoff")


class TestSetupSkills:
    class TestOnContext:
        @pytest.mark.parametrize("context", AGENTS)
        def test_should_install_every_skill_for_the_agents_of_the_context(self, script, fake_bin, calls, context):
            fake_bin("npx")
            result = script("setup-skills", env={"DOTFILES_CONTEXT": context})
            assert result.returncode == 0, result.stderr
            assert installs(calls("npx")) == [(skill, AGENTS[context]) for skill in SKILLS]

        @pytest.mark.parametrize("context", ["", "other"])
        def test_should_install_nothing_for_an_unknown_context(self, script, fake_bin, calls, context):
            fake_bin("npx")
            result = script("setup-skills", env={"DOTFILES_CONTEXT": context})
            assert result.returncode == 0
            assert calls("npx") == []

        def test_should_install_nothing_without_a_context(self, script, fake_bin, calls):
            fake_bin("npx")
            result = script("setup-skills")
            assert result.returncode == 0
            assert calls("npx") == []

    class TestOnFailedInstall:
        def test_should_fail_and_not_go_on(self, script, fake_bin, calls):
            fake_bin("npx", exit_code=1)
            result = script("setup-skills", env={"DOTFILES_CONTEXT": "ista"})
            assert result.returncode == 1
            assert len(calls("npx")) == 1

    class TestOnMissingNpx:
        @pytest.mark.parametrize("context", AGENTS)
        def test_should_skip_with_a_one_line_notice_and_exit_0(self, script, sandbox, context):
            sandbox.only_tools()
            (sandbox.fakes / "npx").unlink()
            result = script("setup-skills", env={"DOTFILES_CONTEXT": context})
            assert result.returncode == 0, result.stderr
            assert result.stderr == "npx not available; skipping skills install\n"

    class TestPinning:
        def test_should_run_an_exact_version_of_the_skills_cli(self, script, fake_bin, calls):
            fake_bin("npx")
            script("setup-skills", env={"DOTFILES_CONTEXT": "ista"})
            assert all(re.fullmatch(r"skills@\d+\.\d+\.\d+", call[1]) for call in calls("npx"))

        def test_should_install_every_skill_from_a_commit(self, script, fake_bin, calls):
            fake_bin("npx")
            script("setup-skills", env={"DOTFILES_CONTEXT": "ista"})
            assert all(re.fullmatch(r".+#[0-9a-f]{40}", call[4]) for call in calls("npx"))


def installs(npx_calls):
    return [(call[4].partition("#")[0].rsplit("/", 1)[-1], call[call.index("--agent") + 1:-1]) for call in npx_calls]
