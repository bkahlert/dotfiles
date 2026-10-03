import pytest

MODULE = "20-claude.zsh"


@pytest.fixture(autouse=True)
def bare(sandbox):
    sandbox.only_tools("zsh", "cat", "chmod")


def fake_installer(sandbox):
    """A curl fake that serves an installer script, which drops a `claude` on the PATH."""
    claude = sandbox.fakes / "claude"
    sandbox.fake_bin("curl", script=(
        "cat <<'INSTALLER'\n"
        f"printf '#!/bin/sh\\necho installed-claude \"$@\"\\n' > {claude}\n"
        f"chmod +x {claude}\n"
        "INSTALLER\n"))


class TestClaude:
    def test_should_pass_every_argument_on_to_claude(self, zsh, fake_bin, calls):
        fake_bin("claude", stdout="ok")
        result = zsh("claude -p 'two words'", modules=[MODULE])
        assert (result.stdout, result.returncode) == ("ok", 0)
        assert calls("claude") == [["-p", "two words"]]
        assert calls("curl") == []

    def test_should_alias_clauded_to_claude_without_permission_prompts(self, zsh, fake_bin, calls):
        fake_bin("claude")
        # zsh -c parses the whole script before sourcing the module; eval parses the alias use afterward.
        zsh("eval 'clauded fix it'", modules=[MODULE])
        assert calls("claude") == [["--dangerously-skip-permissions", "fix", "it"]]

    class TestOnMissingClaude:
        def test_should_run_the_official_installer_and_then_claude(self, zsh, sandbox, calls):
            fake_installer(sandbox)
            result = zsh("claude --version", modules=[MODULE])
            assert (result.stdout, result.returncode) == ("installed-claude --version\n", 0)
            assert result.stderr == "Claude not found. Installing...\n"
            assert calls("curl") == [["-fsSL", "https://claude.ai/install.sh"]]

        def test_should_fail_when_the_installer_provides_no_claude(self, zsh, fake_bin):
            fake_bin("curl", exit_code=22)
            result = zsh("claude --version", modules=[MODULE])
            assert result.returncode != 0
            assert "installed-claude" not in result.stdout
