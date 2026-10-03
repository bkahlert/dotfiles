class TestSandbox:
    class TestRun:
        def test_should_resolve_scripts_by_their_target_name(self, run):
            result = run("gh-latest", "--help")
            assert result.returncode == 0
            assert result.stdout.startswith("Purpose:")

        def test_should_keep_the_real_home_out_of_reach(self, run, sandbox):
            result = run("sh", "-c", 'echo "$HOME" "$XDG_CONFIG_HOME"')
            assert result.stdout.split() == [str(sandbox.home), str(sandbox.home / ".config")]

        def test_should_fail_loudly_on_a_guarded_tool(self, run):
            result = run("op", "read", "op://x/y/z")
            assert result.returncode == 127
            assert result.stderr == "op: not faked in this test\n"

    class TestFakeBin:
        def test_should_record_every_call_with_its_arguments(self, run, fake_bin, calls):
            fake_bin("gh")
            run("gh", "pr", "view", "--json", "title and body")
            run("gh", "")
            run("gh")
            assert calls("gh") == [["pr", "view", "--json", "title and body"], [""], []]

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

    class TestZsh:
        def test_should_autoload_a_function_from_the_source_tree(self, zsh):
            result = zsh("whence -w zsh-scratch", function="zsh-scratch")
            assert result.stdout == "zsh-scratch: function\n"

        def test_should_source_modules_in_order(self, zsh):
            result = zsh("whence -w printf_info", modules=["08-print.zsh"])
            assert result.stdout == "printf_info: function\n"
