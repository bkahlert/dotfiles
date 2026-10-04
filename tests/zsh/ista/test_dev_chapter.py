import time

MODULES = ["ista/10-dev-chapter.zsh"]
REPO = "Development/istaexpress/dev-chapter"
REMOTE = "git@gitlab.com:ista-se/cas/ista-express/shared/dev-chapter-time/dev-chapter.git"
CACHE = ".cache/dev-chapter"


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
        class TestOnMissingRepository:
            def test_should_clone_in_the_background(self, zsh, fake_bin, calls, sandbox):
                with_agent(sandbox)
                fake_bin("git")
                result = zsh("true", modules=MODULES)
                assert result.returncode == 0
                eventually(lambda: calls("git"))
                assert calls("git")[0][:2] == ["clone", REMOTE]

            def test_should_stay_silent_on_both_streams_while_cloning(self, zsh, fake_bin, calls, sandbox):
                with_agent(sandbox)
                fake_bin("git")
                result = zsh("true", modules=MODULES)
                eventually(lambda: calls("git"))
                assert (result.stdout, result.stderr) == ("", "")

            def test_should_not_wait_for_the_clone(self, zsh, fake_bin, sandbox):
                with_agent(sandbox)
                fake_bin("git", script=blocks_until_released(sandbox))
                result = zsh(continues_while_git_runs(sandbox), modules=MODULES)
                assert (result.returncode, result.stdout, result.stderr) == (0, "git running, shell continued\n", "")

            def test_should_report_the_whole_git_failure_on_the_next_start(self, zsh, fake_bin, calls, sandbox):
                with_agent(sandbox)
                fake_bin("git", stdout="fatal: no route to host", exit_code=128)
                zsh("true", modules=MODULES)
                eventually(lambda: (sandbox.home / CACHE / "clone-error").exists())
                result = zsh("true", modules=MODULES)
                assert (result.stdout, result.stderr) == (
                    "", "✘ Failed to clone dev-chapter repository:\n✘ fatal: no route to host\n")

        class TestOnExistingRepository:
            def test_should_pull_in_the_background_and_keep_the_tools_on_path(self, zsh, fake_bin, calls, sandbox):
                with_repo(sandbox)
                fake_bin("git")
                result = zsh("print -r -- ${path[1]}", modules=MODULES)
                eventually(lambda: calls("git"))
                assert (result.stdout, result.stderr) == (f"{sandbox.home}/{REPO}/tools\n", "")
                assert calls("git")[0][-2:] == ["pull", "--autostash"]

            def test_should_not_wait_for_the_pull(self, zsh, fake_bin, sandbox):
                with_repo(sandbox)
                fake_bin("git", script=blocks_until_released(sandbox))
                result = zsh(continues_while_git_runs(sandbox), modules=MODULES)
                assert (result.returncode, result.stdout, result.stderr) == (0, "git running, shell continued\n", "")

            def test_should_not_pull_again_within_the_interval(self, zsh, fake_bin, calls, sandbox):
                with_repo(sandbox)
                (sandbox.home / CACHE).mkdir(parents=True)
                (sandbox.home / CACHE / "last_attempt").write_text(f"{int(time.time())}\n")
                fake_bin("git")
                zsh("true", modules=MODULES)
                time.sleep(0.3)
                assert calls("git") == []

            def test_should_report_the_whole_git_failure_once_on_the_next_start(self, zsh, fake_bin, calls, sandbox):
                with_repo(sandbox)
                fake_bin("git", stdout="fatal: unreachable", exit_code=1)
                first = zsh("true", modules=MODULES)
                eventually(lambda: (sandbox.home / CACHE / "update-error").exists())
                second = zsh("true", modules=MODULES)
                third = zsh("true", modules=MODULES)
                assert first.stderr == ""
                assert second.stderr == "! Failed to update dev-chapter repository:\n! fatal: unreachable\n"
                assert third.stderr == ""
                assert len(calls("git")) == 1


def with_agent(sandbox):
    sandbox.env["SSH_AUTH_SOCK"] = str(sandbox.home / "agent.sock")


def with_repo(sandbox):
    with_agent(sandbox)
    (sandbox.home / REPO / ".git").mkdir(parents=True)
    (sandbox.home / REPO / "tools").mkdir()


def eventually(condition, timeout=5):
    deadline = time.monotonic() + timeout
    while not condition():
        assert time.monotonic() < deadline, "background git never ran"
        time.sleep(0.02)


def blocks_until_released(sandbox):
    """A git that signals it started, then hangs until the test releases it (self-releasing after 10 s)."""
    return (f"touch {sandbox.home}/started\n"
            f"for _ in $(seq 200); do [ -e {sandbox.home}/release ] && exit 0; sleep 0.05; done\n")


def continues_while_git_runs(sandbox):
    """Passes only if the shell gets past the module while git is still hanging; a synchronous git would deadlock."""
    return (f"repeat 200 {{ [[ -e {sandbox.home}/started ]] && break; sleep 0.02 }}\n"
            f"[[ -e {sandbox.home}/started && ! -e {sandbox.home}/release ]] && print 'git running, shell continued'\n"
            f"touch {sandbox.home}/release")
