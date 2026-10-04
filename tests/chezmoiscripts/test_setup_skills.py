import pytest

AGENTS = {
    "bkahlert": ["claude-code"],
    "ista": ["claude-code", "gemini-cli", "github-copilot"],
}
SKILLS = ("grill-me", "handoff")
# nvm.sh as far as the script needs it: `nvm use default` puts the default node's bin on PATH, and, like the real
# one, it does not survive set -u and fails to load on an ~/.nvmrc naming an uninstalled version unless told --no-use.
NVM_SH = """\
: "$NVM_SH_NEEDS_UNSET_VARIABLES"
[[ " $* " == *" --no-use "* || ! -f $HOME/.nvmrc ]] || return 3
nvm() { [[ "$*" == "use default" ]] && export PATH="$HOME/node/bin:$PATH"; }
"""


@pytest.fixture(autouse=True)
def nvm(sandbox):
    nvm_dir = sandbox.home / ".nvm"
    nvm_dir.mkdir()
    (nvm_dir / "nvm.sh").write_text(NVM_SH)
    return nvm_dir


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

    class TestOnNodeFromNvm:
        def test_should_run_the_npx_of_nvm_s_default_node(self, script, sandbox):
            sandbox.only_tools()
            node_bin = sandbox.home / "node" / "bin"
            node_bin.mkdir(parents=True)
            (node_bin / "npx").write_text('#!/bin/sh\necho "$*" >> "$HOME/npx-calls"\n')
            (node_bin / "npx").chmod(0o755)
            result = script("setup-skills", env={"DOTFILES_CONTEXT": "bkahlert"})
            assert result.returncode == 0, result.stderr
            assert len((sandbox.home / "npx-calls").read_text().splitlines()) == len(SKILLS)

        def test_should_use_the_default_on_an_nvmrc_naming_an_uninstalled_version(self, script, sandbox):
            sandbox.only_tools()
            node_bin = sandbox.home / "node" / "bin"
            node_bin.mkdir(parents=True)
            (node_bin / "npx").write_text('#!/bin/sh\necho "$*" >> "$HOME/npx-calls"\n')
            (node_bin / "npx").chmod(0o755)
            (sandbox.home / ".nvmrc").write_text("18\n")
            result = script("setup-skills", env={"DOTFILES_CONTEXT": "bkahlert"})
            assert result.returncode == 0, result.stderr
            assert len((sandbox.home / "npx-calls").read_text().splitlines()) == len(SKILLS)

    class TestOnMissingNvm:
        @pytest.mark.parametrize("context", AGENTS)
        def test_should_fail_and_name_the_script_that_installs_it(self, script, fake_bin, calls, nvm, context):
            fake_bin("npx")
            (nvm / "nvm.sh").unlink()
            result = script("setup-skills", env={"DOTFILES_CONTEXT": context})
            assert (result.returncode, calls("npx")) == (1, [])
            assert result.stderr == f"nvm not found in {nvm}; run_once_before_02-install-nvm installs it\n"

def installs(npx_calls):
    return [(call[4].partition("#")[0].rsplit("/", 1)[-1], call[call.index("--agent") + 1:-1]) for call in npx_calls]
