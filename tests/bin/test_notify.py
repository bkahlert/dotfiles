import pytest


class TestNotify:
    class TestOnMessage:
        def test_should_pass_message_title_subtitle_and_sound_to_osascript_in_order(self, run, fake_bin, calls):
            fake_bin("osascript")
            result = run("notify", "--title", "Done", "--subtitle", "build", "--sound", "Glass", "Build finished")
            assert result.returncode == 0
            assert calls("osascript") == [["-", "Build finished", "Done", "build", "Glass"]]

        def test_should_default_the_title_and_leave_subtitle_and_sound_empty(self, run, fake_bin, calls):
            fake_bin("osascript")
            run("notify", "hello")
            assert calls("osascript") == [["-", "hello", "Notification", "", ""]]

        def test_should_join_several_words_with_spaces(self, run, fake_bin, calls):
            fake_bin("osascript")
            run("notify", "build", "finished", "ok")
            assert calls("osascript")[0][1] == "build finished ok"

        def test_should_accept_the_equals_form_and_options_after_the_message(self, run, fake_bin, calls):
            fake_bin("osascript")
            run("notify", "hello", "--title=T", "--subtitle=S", "--sound=Purr")
            assert calls("osascript") == [["-", "hello", "T", "S", "Purr"]]

        def test_should_take_a_dashed_message_after_a_double_dash(self, run, fake_bin, calls):
            fake_bin("osascript")
            run("notify", "--", "--not-an-option")
            assert calls("osascript")[0][1] == "--not-an-option"

        def test_should_hand_the_applescript_to_osascript_on_stdin(self, run, fake_bin, sandbox):
            script = sandbox.home / "applescript"
            fake_bin("osascript", script=f'cat > "{script}"\n')
            run("notify", "hello")
            text = script.read_text()
            assert "on run {theNotification, theTitle, theSubtitle, theSound}" in text
            assert "display notification theNotification with title theTitle subtitle theSubtitle" in text

    class TestOnDebug:
        def test_should_log_the_invocation_to_the_notify_log(self, run, fake_bin, sandbox):
            fake_bin("osascript")
            sandbox.env["DEBUG"] = "1"
            run("notify", "hello", "--title", "T")
            assert (sandbox.home / ".notify.log").read_text() == "Invocation: hello --title T\n"

        def test_should_log_nothing_without_debug(self, run, fake_bin, sandbox):
            fake_bin("osascript")
            run("notify", "hello")
            assert not (sandbox.home / ".notify.log").exists()

    class TestOnBadArguments:
        @pytest.mark.parametrize("option", ["--title", "--subtitle", "--sound"])
        def test_should_exit_2_with_a_one_line_hint_on_a_missing_value(self, run, fake_bin, calls, option):
            fake_bin("osascript")
            result = run("notify", "hello", option)
            assert result.returncode == 2
            assert result.stderr == f"notify: {option}: missing value\nSee 'notify --help'\n"
            assert calls("osascript") == []

        def test_should_exit_2_on_an_unknown_option(self, run):
            result = run("notify", "--nope", "hello")
            assert result.returncode == 2
            assert result.stderr == "notify: unknown option: --nope\nSee 'notify --help'\n"

        def test_should_print_the_header_to_stderr_and_exit_2_without_a_message(self, run, fake_bin, calls):
            fake_bin("osascript")
            result = run("notify", "--title", "T")
            assert result.returncode == 2
            assert result.stdout == ""
            assert result.stderr.startswith("Purpose: Send a macOS notification")
            assert calls("osascript") == []

    class TestOnHelp:
        def test_should_print_the_header_to_stdout(self, run):
            result = run("notify", "--help")
            assert result.returncode == 0
            assert result.stdout.startswith("Purpose: Send a macOS notification")
