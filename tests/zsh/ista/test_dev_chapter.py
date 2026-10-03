MODULES = ["08-print.zsh", "ista/10-dev-chapter.zsh"]
REPO = "Development/istaexpress/dev-chapter"
REMOTE = "git@gitlab.com:ista-se/cas/ista-express/shared/dev-chapter-time/dev-chapter.git"


class TestDevChapter:
    class TestOnMissingSshAgent:
        def test_should_stay_silent_and_not_clone(self, zsh, fake_bin, calls):
            fake_bin("git", exit_code=128)
            result = zsh("true", modules=MODULES)
            assert (result.returncode, result.stdout, result.stderr) == (0, "", "")
            assert calls("git") == []

        def test_should_add_existing_tools_to_path_without_pulling(self, zsh, fake_bin, calls, sandbox):
            (sandbox.home / REPO / ".git").mkdir(parents=True)
            (sandbox.home / REPO / "tools").mkdir()
            fake_bin("git")
            result = zsh("print -r -- ${path[1]}", modules=MODULES)
            assert result.stdout == f"{sandbox.home}/{REPO}/tools\n"
            assert calls("git") == []

    class TestOnSshAgent:
        def test_should_clone_the_repository(self, zsh, fake_bin, calls, sandbox):
            sandbox.env["SSH_AUTH_SOCK"] = str(sandbox.home / "agent.sock")
            fake_bin("git")
            result = zsh("true", modules=MODULES)
            assert result.returncode == 0
            assert calls("git")[0][:2] == ["clone", REMOTE]
