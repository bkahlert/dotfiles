MODULES = ["ista/10-dev-chapter.zsh"]
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

        def test_should_warn_on_stderr_when_the_tools_directory_is_missing(self, zsh, fake_bin, sandbox):
            (sandbox.home / REPO / ".git").mkdir(parents=True)
            fake_bin("git")
            result = zsh("true", modules=MODULES)
            assert (result.stdout, result.stderr) == (
                "", f"! dev-chapter tools directory not found at {sandbox.home}/{REPO}/tools\n")

    class TestOnSshAgent:
        def test_should_clone_the_repository(self, zsh, fake_bin, calls, sandbox):
            sandbox.env["SSH_AUTH_SOCK"] = str(sandbox.home / "agent.sock")
            fake_bin("git")
            result = zsh("true", modules=MODULES)
            assert result.returncode == 0
            assert calls("git")[0][:2] == ["clone", REMOTE]

        def test_should_report_the_clone_on_stdout(self, zsh, fake_bin, sandbox):
            sandbox.env["SSH_AUTH_SOCK"] = str(sandbox.home / "agent.sock")
            fake_bin("git")
            result = zsh("true", modules=MODULES)
            assert result.stdout == f"Cloning dev-chapter repository to {sandbox.home}/{REPO}...\n✔ Repository cloned successfully\n"

        def test_should_report_the_whole_git_failure_on_stderr_when_the_clone_fails(self, zsh, fake_bin, sandbox):
            sandbox.env["SSH_AUTH_SOCK"] = str(sandbox.home / "agent.sock")
            fake_bin("git", stdout="fatal: no route to host", exit_code=128)
            result = zsh("true", modules=MODULES)
            assert result.stderr == "✘ Failed to clone dev-chapter repository:\n✘ fatal: no route to host\n"

        def test_should_warn_on_stderr_and_keep_the_tools_on_path_when_the_pull_fails(self, zsh, fake_bin, calls, sandbox):
            sandbox.env["SSH_AUTH_SOCK"] = str(sandbox.home / "agent.sock")
            (sandbox.home / REPO / ".git").mkdir(parents=True)
            (sandbox.home / REPO / "tools").mkdir()
            fake_bin("git", stdout="fatal: unreachable", exit_code=1)
            result = zsh("print -r -- ${path[1]}", modules=MODULES)
            assert (result.stdout, result.stderr) == (
                f"{sandbox.home}/{REPO}/tools\n",
                "! Failed to update dev-chapter repository:\n! fatal: unreachable\n")
            assert "pull" in calls("git")[0]
