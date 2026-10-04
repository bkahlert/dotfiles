import os
import sys

import pytest


class TestSandbox:
    class TestRun:
        def test_should_resolve_scripts_by_their_target_name(self, run):
            result = run("gh-latest", "--help")
            assert result.returncode == 0
            assert result.stdout.startswith("Purpose:")

        def test_should_resolve_a_claude_script_by_its_target_name(self, run):
            result = run("statusline", "--no-nerd-fonts", stdin="{}")
            assert result.returncode == 0
            assert result.stdout.endswith("0%\x1b[0m\n")

        def test_should_give_the_child_no_stdin_even_when_the_parent_has_one(self, run):
            read_end, write_end = os.pipe()
            saved = os.dup(0)
            os.dup2(read_end, 0)
            try:
                result = run("cat", timeout=3)
            finally:
                os.dup2(saved, 0)
                for fd in (saved, read_end, write_end):
                    os.close(fd)
            assert result.stdout == ""

        def test_should_keep_the_real_home_out_of_reach(self, run, sandbox):
            result = run("sh", "-c", 'echo "$HOME" "$XDG_CONFIG_HOME"')
            assert result.stdout.split() == [str(sandbox.home), str(sandbox.home / ".config")]

        def test_should_fail_loudly_on_a_guarded_tool(self, run):
            result = run("op", "read", "op://x/y/z")
            assert result.returncode == 127
            assert result.stderr == "op: not faked in this test\n"

        def test_should_guard_tools_that_change_local_state_too(self, run):
            result = run("git", "--version")
            assert result.returncode == 127
            assert result.stderr == "git: not faked in this test\n"

        @pytest.mark.parametrize("command", [
            ["ssh-keygen", "-l", "-f", "/dev/null"], ["openssl", "version"], ["xcrun", "--version"],
            ["gem", "--version"], ["uv", "--version"], ["yarn", "--version"], ["composer", "--version"],
        ], ids=lambda command: command[0])
        def test_should_guard_the_tools_the_script_tests_fake(self, run, command):
            result = run(*command)
            assert result.returncode == 127
            assert result.stderr == f"{command[0]}: not faked in this test\n"

    class TestFakeBin:
        def test_should_record_every_call_with_its_arguments(self, run, fake_bin, calls):
            fake_bin("gh")
            run("gh", "pr", "view", "--json", "title and body")
            run("gh", "")
            run("gh")
            assert calls("gh") == [["pr", "view", "--json", "title and body"], [""], []]

        def test_should_record_an_argument_that_spans_lines(self, run, fake_bin, calls):
            fake_bin("gh")
            run("gh", "pr", "create", "--body", "line one\nline two")
            assert calls("gh") == [["pr", "create", "--body", "line one\nline two"]]

        def test_should_return_the_canned_output_and_exit_code(self, run, fake_bin):
            fake_bin("gh", stdout="out", stderr="err", exit_code=3)
            result = run("gh")
            assert (result.stdout, result.stderr, result.returncode) == ("out", "err", 3)

        def test_should_run_a_script_body_with_the_arguments(self, run, fake_bin):
            fake_bin("gh", script='[[ $1 == pr ]] && echo yes || echo no\n')
            result = run("gh", "pr")
            assert result.stdout == "yes\n"

        def test_should_replace_a_guard(self, run, fake_bin):
            fake_bin("curl", stdout="{}")
            result = run("curl", "https://example.test")
            assert result.returncode == 0

        def test_should_keep_records_apart_when_two_fakes_share_a_pipeline(self, run, fake_bin, calls):
            fake_bin("tool")
            for _ in range(20):
                run("sh", "-c", "tool a one | tool b two")
            assert sorted(calls("tool")) == sorted([["a", "one"], ["b", "two"]] * 20)

    class TestOnlyTools:
        def test_should_keep_the_named_tools_and_hide_the_rest(self, sandbox, fake_bin):
            fake_bin("faked", stdout="x")
            sandbox.only_tools("zsh", "cat")
            result = sandbox.zsh("print -r -- ${+commands[cat]}${+commands[faked]}${+commands[ls]}${+commands[bash]}")
            assert result.stdout == "1101\n"

    class TestZsh:
        def test_should_autoload_a_function_from_the_source_tree(self, zsh, sandbox, tmp_path, monkeypatch):
            (tmp_path / "greet").write_text("print -r -- hello $1\n")
            monkeypatch.setattr(sys.modules[type(sandbox).__module__], "FUNCTIONS_SOURCE", tmp_path)
            result = zsh("greet world", function="greet")
            assert result.stdout == "hello world\n"

        def test_should_source_a_module_from_the_source_tree(self, zsh):
            result = zsh("whence -w _dc_warn", modules=["ista/10-dev-chapter.zsh"])
            assert result.stdout == "_dc_warn: function\n"
