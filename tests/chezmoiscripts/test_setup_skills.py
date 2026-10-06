import pytest

AGENTS = {
    "bkahlert": ["claude-code"],
    "ista": ["claude-code", "gemini-cli", "github-copilot"],
}
SKILLS = ("grill-me", "grilling", "handoff")
# `fnm env` as far as the script needs it: it puts the default Node.js's bin on PATH.
FNM_ENV = 'export PATH="$HOME/node/bin:$PATH"'


@pytest.fixture(autouse=True)
def fnm(sandbox):
    sandbox.fake_bin("fnm", stdout=FNM_ENV)


class TestSetupSkills:
    class TestOnProfile:
        @pytest.mark.parametrize("company", AGENTS)
        def test_should_install_every_skill_for_the_profile(self, script, fake_bin, calls, company):
            fake_bin("npx")
            result = script("setup-skills", company=company)
            assert result.returncode == 0, result.stderr
            assert installs(calls("npx")) == [(skill, AGENTS[company]) for skill in SKILLS]

        @pytest.mark.parametrize("company", ["", "other"])
        def test_should_install_nothing_without_a_supported_profile(self, script, fake_bin, calls, company):
            fake_bin("npx")
            result = script("setup-skills", company=company)
            assert result.returncode == 0
            assert calls("npx") == []

    class TestOnFailedInstall:
        def test_should_fail_and_not_go_on(self, script, fake_bin, calls):
            fake_bin("npx", exit_code=1)
            result = script("setup-skills", company="ista")
            assert result.returncode == 1
            assert len(calls("npx")) == 1

    class TestOnNodeFromFnm:
        def test_should_run_the_npx_of_fnm_s_default_node(self, script, sandbox, calls):
            sandbox.only_tools()
            node_bin = sandbox.home / "node" / "bin"
            node_bin.mkdir(parents=True)
            (node_bin / "npx").write_text('#!/bin/sh\necho "$*" >> "$HOME/npx-calls"\n')
            (node_bin / "npx").chmod(0o755)
            result = script("setup-skills", company="bkahlert")
            assert result.returncode == 0, result.stderr
            assert len((sandbox.home / "npx-calls").read_text().splitlines()) == len(SKILLS)
            assert calls("fnm") == [["env", "--shell", "bash"]]

    class TestOnMissingFnm:
        @pytest.mark.parametrize("context", AGENTS)
        def test_should_fail_and_name_the_script_that_installs_it(self, script, fake_bin, calls, sandbox, tmp_path,
                                                                  context):
            fake_bin("npx")
            (sandbox.fakes / "fnm").unlink()
            result = script("setup-skills", company=context, prefix_root=tmp_path)
            assert (result.returncode, calls("npx")) == (1, [])
            assert result.stderr == "fnm not found; run_once_before_01-install-packages installs it\n"


def installs(npx_calls):
    return [(call[4].partition("#")[0].rsplit("/", 1)[-1], call[call.index("--agent") + 1:-1]) for call in npx_calls]
