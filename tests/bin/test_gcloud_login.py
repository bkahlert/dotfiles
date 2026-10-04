import time

import pytest

NORMAL = "bjoern.kahlert@ista-express.de"
ADMIN = "bjoern.kahlert.admin@ista-express.de"


class TestGcloudLogin:
    class TestOnOptions:
        def test_should_refuse_admin_and_adc_together(self, run):
            result = login(run, "--admin", "--adc")
            assert result.returncode == 1
            assert result.stderr == "✘ gcloud-login: --admin and --adc are mutually exclusive\n"

        @pytest.mark.parametrize("timeout", ["0", "abc"])
        def test_should_require_a_positive_timeout(self, run, timeout):
            result = login(run, f"--timeout={timeout}")
            assert result.returncode == 1
            assert result.stderr.startswith("✘ gcloud-login: --timeout must be a positive integer")

        def test_should_exit_2_on_a_missing_timeout_value(self, run):
            result = login(run, "--timeout")
            assert result.returncode == 2
            assert result.stderr == "✘ gcloud-login: --timeout: missing value (see 'gcloud-login --help')\n"

        def test_should_exit_2_on_an_unknown_option(self, run):
            result = login(run, "--nope")
            assert result.returncode == 2
            assert result.stderr == "✘ gcloud-login: unknown option --nope (see 'gcloud-login --help')\n"

    class TestOutsideTheIstaContext:
        def test_should_refuse_to_run(self, run):
            result = run("gcloud-login")
            assert result.returncode == 1
            assert result.stderr == "✘ gcloud-login: only available in the ista context\n"

    class TestOnStatus:
        def test_should_report_both_identities_and_exit_0_when_valid(self, run, fake_bin):
            fake_bin("gcloud", script=GCLOUD_VALID)
            fake_bin("curl", stdout='{"email":"adc@ista-express.de"}')
            result = login(run, "--status")
            assert result.returncode == 0
            assert result.stdout == "CLI account:  me@ista-express.de (valid)\nADC identity: adc@ista-express.de (valid)\n"

        def test_should_send_the_adc_token_on_stdin_and_keep_it_out_of_curls_argv(self, run, fake_bin, calls, sandbox):
            fake_bin("gcloud", script=GCLOUD_VALID)
            fake_bin("curl", script='cat > "$HOME/curl.stdin"\necho \'{"email":"adc@ista-express.de"}\'\n')
            result = login(run, "--status")
            assert result.returncode == 0
            assert calls("curl") == [["-fsS", "--data-urlencode", "access_token@-", "https://oauth2.googleapis.com/tokeninfo"]]
            assert (sandbox.home / "curl.stdin").read_text() == "tok"

        def test_should_exit_1_when_a_login_is_needed(self, run, fake_bin):
            fake_bin("gcloud", exit_code=1)
            result = login(run, "--status")
            assert result.returncode == 1
            assert result.stdout == "CLI account:  none (needs login)\nADC identity: unknown (needs login)\n"

    class TestOnValidCredentials:
        @pytest.mark.parametrize("args,mode,command", [
            ((), "cli", ["auth", "login", NORMAL, "--quiet"]),
            (("--adc",), "adc", ["auth", "application-default", "login", NORMAL, "--quiet"]),
            (("--admin",), "admin", ["auth", "login", ADMIN, "--quiet"]),
        ], ids=["cli", "adc", "admin"])
        def test_should_do_nothing_and_say_so(self, run, fake_bin, calls, args, mode, command):
            fake_bin("gcloud")
            fake_bin("pkill")
            result = login(run, *args)
            assert result.returncode == 0
            assert result.stderr.endswith(f"✔ Credentials for {command[-2]} are still valid ({mode}); nothing to do\n")
            assert calls("gcloud") == [command]
            assert calls("pkill") == []

    class TestOnGcloudFailingBeforeTheBrowser:
        def test_should_relay_its_output_and_exit_1(self, run, fake_bin):
            fake_bin("gcloud", script='echo "ERROR: boom" >&2\nexit 1\n')
            result = login(run)
            assert result.returncode == 1
            assert result.stderr.endswith("ERROR: boom\n✘ gcloud-login: gcloud failed before opening a browser\n")

        def test_should_exit_2_when_no_url_arrives_in_time(self, run, fake_bin):
            fake_bin("gcloud", script="sleep 5\n")
            result = login(run, "--timeout", "1")
            assert result.returncode == 2
            assert result.stderr.endswith("✘ gcloud-login: gcloud produced no auth url within 1s\n")

    class TestOnTheBrowserFlow:
        def test_should_drive_the_login_with_the_admin_password_from_op_agent(self, run, fake_bin, calls, sandbox):
            browser_tools(fake_bin, sandbox)
            fake_bin("op-agent", script='[[ $1 == status ]] && exit 1\nprintf hunter2\n')
            fake_bin("gcloud-login-driver", script='cat > "$HOME/driver.stdin"\ntouch "$HOME/callback"\nexit 0\n')
            result = login(run, "--admin", timeout=30)
            assert result.returncode == 0
            assert result.stderr.endswith(f"✔ Logged in (admin) as {ADMIN}\n")
            profile = sandbox.home / "Library/Application Support/gcloud-login/admin"
            [driver] = calls("gcloud-login-driver")
            assert driver[:3] == ["--port-file", str(profile / "DevToolsActivePort"), "--url-file"]
            assert driver[4:] == ["--email", ADMIN, "--timeout", "120"]
            assert (sandbox.home / "driver.stdin").read_text() == "hunter2"
            assert calls("op-agent") == [["status"], ["read", "op://Employee/p44thhnd5ylh6zrm6etwozs63a/password"]]
            assert (sandbox.home / "chromium.args").read_text().splitlines() == [
                f"--user-data-dir={profile}", "--remote-debugging-port=0", "--no-first-run",
                "--no-default-browser-check", "--no-startup-window"]

        @pytest.mark.parametrize("args,profile", [((), "normal"), (("--adc",), "normal"), (("--admin",), "admin")],
                                 ids=["cli", "adc", "admin"])
        def test_should_end_a_leftover_chromium_of_that_profile_before_launching_a_new_one(
                self, run, fake_bin, calls, sandbox, args, profile):
            browser_tools(fake_bin, sandbox)
            fake_bin("op-agent", script="printf hunter2\n")
            fake_bin("gcloud-login-driver", script='touch "$HOME/callback"\n')
            # The browser starts in the background, so a pkill that runs after the launch can still beat
            # its first write. Linger, and any browser launched meanwhile shows up.
            fake_bin("pkill", script='sleep 0.3\n[[ -e "$HOME/chromium.args" ]] && touch "$HOME/pkill-after-launch"\nexit 0\n')
            result = login(run, *args, timeout=30)
            assert result.returncode == 0
            expected = f"--user-data-dir={sandbox.home}/Library/Application Support/gcloud-login/{profile}"
            assert calls("pkill") == [["-f", "--", expected]]
            assert not (sandbox.home / "pkill-after-launch").exists()

        @pytest.mark.parametrize("args", [(), ("--adc",)], ids=["cli", "adc"])
        def test_should_not_read_the_admin_password_outside_the_admin_flow(self, run, fake_bin, calls, sandbox, args):
            browser_tools(fake_bin, sandbox)
            fake_bin("op-agent", script="printf hunter2\n")
            fake_bin("gcloud-login-driver", script='cat > "$HOME/driver.stdin"\ntouch "$HOME/callback"\n')
            result = login(run, *args, timeout=30)
            assert result.returncode == 0
            assert calls("op-agent") == []
            assert (sandbox.home / "driver.stdin").read_text() == ""
            [driver] = calls("gcloud-login-driver")
            assert driver[driver.index("--email") + 1] == NORMAL

        def test_should_exit_2_when_the_driver_times_out_and_gcloud_never_finishes(self, run, fake_bin, sandbox):
            browser_tools(fake_bin, sandbox)
            fake_bin("gcloud-login-driver", exit_code=2)
            result = login(run, "--timeout", "1", timeout=30)
            assert result.returncode == 2
            assert ("! gcloud-login: automation stopped (driver exit 2); "
                    "finish the login in the Chromium window or press Ctrl-C\n") in result.stderr
            assert result.stderr.endswith("✘ gcloud-login: browser flow timed out\n")

        def test_should_abort_at_once_and_warn_when_the_driver_refuses_an_unexpected_host(self, run, fake_bin, sandbox):
            browser_tools(fake_bin, sandbox)
            fake_bin("gcloud-login-driver", script=(
                "echo 'gcloud-login-driver: password page on unexpected host evil.test; "
                "not typing the password (https://evil.test/login)' >&2\nexit 4\n"))
            started = time.monotonic()
            result = login(run, "--timeout", "30", timeout=60)
            assert time.monotonic() - started < 15, "waited for the user to finish by hand"
            assert result.returncode == 1
            assert "password page on unexpected host evil.test" in result.stderr
            assert "! gcloud-login: do NOT enter your password on that page\n" in result.stderr
            assert "finish the login in the Chromium window" not in result.stderr
            assert result.stderr.endswith("✘ gcloud-login: the sign-in was redirected to an unexpected host; login aborted\n")

        class TestOnAFailingChromiumInstall:
            def test_should_say_so_and_exit_1(self, run, fake_bin, calls, sandbox):
                fake_bin("gcloud", script=GCLOUD_BROWSER)
                fake_bin("node")
                fake_bin("npx", exit_code=1)
                result = login(run, timeout=30)
                assert result.returncode == 1
                assert result.stderr.endswith("✘ gcloud-login: Chromium install failed\n")
                assert calls("npx") == [["--yes", "@puppeteer/browsers", "install", "chromium@1702741",
                                         "--path", f"{sandbox.home}/.cache/gcloud-login"]]


GCLOUD_VALID = "\n".join([
    'case "$*" in',
    '  "config get-value account") echo me@ista-express.de ;;',
    '  "auth print-access-token --quiet") exit 0 ;;',
    '  "auth application-default print-access-token") echo tok ;;',
    "esac", "exit 0", ""])

GCLOUD_BROWSER = "\n".join([
    'case "$*" in',
    '  "auth login "*|"auth application-default login "*)',
    "    printf 'https://accounts.google.com/o/oauth2/auth?x=1' > \"$GCLOUD_LOGIN_URL_FILE\"",
    '    for ((i = 0; i < 100; i++)); do [[ -e "$HOME/callback" ]] && exit 0; sleep 0.1; done',
    "    exit 1 ;;",
    "esac", "exit 0", ""])

CHROMIUM = "\n".join([
    "#!/usr/bin/env bash",
    'for arg in "$@"; do [[ $arg == --user-data-dir=* ]] && profile=${arg#*=}; done',
    'printf "%s\\n" "$@" > "$HOME/chromium.args"',
    'printf "9222\\n/devtools/browser/x\\n" > "$profile/DevToolsActivePort"',
    "exec sleep 30", ""])


def login(run, *args, **kwargs):
    return run("env", "DOTFILES_CONTEXT=ista", "gcloud-login", *args, **kwargs)


def browser_tools(fake_bin, sandbox):
    fake_bin("gcloud", script=GCLOUD_BROWSER)
    fake_bin("node")
    fake_bin("npx")
    chromium = sandbox.home / ".cache/gcloud-login/chromium/mac_arm-1702741/chrome-mac/Chromium.app/Contents/MacOS/Chromium"
    chromium.parent.mkdir(parents=True)
    chromium.write_text(CHROMIUM)
    chromium.chmod(0o755)
