import json
import os
import shlex
import subprocess
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


class TestStatusline:
    class TestOnPreview:
        def test_should_render_the_copilot_sample_from_the_dotfiles_repo(
            self, run, fake_bin, calls, sandbox):
            (sandbox.home / "dotfiles/home").mkdir(parents=True)
            fake_bin("chezmoi", stdout=f"{sandbox.home}/dotfiles/home")
            fake_bin("uv", script=(
                f'pwd > "$HOME/uv.cwd"\nprintf %s {shlex.quote(json.dumps(session_payload()))}\n'))

            result = run("copilot-statusline", "--preview", "--no-nerd-fonts")

            assert result.returncode == 0
            assert result.stdout == preview_output()
            assert calls("chezmoi") == [["source-path"]]
            assert calls("uv") == [["run", "--locked", "tests/copilot/test_statusline.py", "--print-input"]]
            assert (sandbox.home / "uv.cwd").read_text() == f"{sandbox.home}/dotfiles\n"
            assert dump_path(sandbox).read_text() == json.dumps(session_payload())

        def test_should_print_the_same_sample_used_by_preview(self, run):
            printed = subprocess.run(
                [sys.executable, __file__, "--print-input"],
                capture_output=True,
                text=True,
                check=True,
            ).stdout

            result = run("copilot-statusline", "--no-nerd-fonts", stdin=printed)

            assert result.returncode == 0
            assert result.stdout == preview_output()

    class TestOnHelp:
        def test_should_print_usage_and_preview_documentation(self, run):
            result = run("copilot-statusline", "--help")

            assert result.returncode == 0
            assert result.stdout.startswith("Purpose:")
            assert "--preview" in result.stdout
            assert "--nerd-fonts" in result.stdout
            assert "--no-nerd-fonts" in result.stdout
            assert "Render the Copilot status line from the session JSON on stdin." in result.stdout
            assert "tests/copilot/test_statusline.py" in result.stdout
            assert "Examples:\n" in result.stdout
            assert "statusline --preview --nerd-fonts      # the sample session with Nerd Font icons" in result.stdout
            assert "statusline --preview --no-nerd-fonts   # the same with emoji fallbacks" in result.stdout

    class TestOnNerdFonts:
        def test_should_render_nerd_font_icons_and_a_segment_bar_when_forced(self, sandbox):
            result = render(sandbox, session_payload(), "--nerd-fonts")

            assert result.returncode == 0, result.stderr
            assert result.stdout == preview_output(nerd_fonts=True)

        def test_should_render_unicode_fallbacks_when_forced(self, sandbox):
            result = render(sandbox, session_payload(), "--no-nerd-fonts")

            assert result.returncode == 0, result.stderr
            assert result.stdout == preview_output()

    class TestOnAutoDetection:
        def test_should_cache_the_probe_and_render_accordingly(self, run, sandbox):
            result = run("copilot-statusline", stdin=json.dumps(session_payload()))

            cached = (sandbox.home / ".cache/agent-statusline/nerd-font-support").read_text()
            assert cached in ("0", "1")
            assert result.returncode == 0, result.stderr
            assert result.stdout == preview_output(nerd_fonts=cached == "1")

        def test_should_trust_a_cached_result(self, run, sandbox):
            cache_detection(sandbox, "1\n")

            result = run("copilot-statusline", stdin=json.dumps(session_payload()))

            assert result.returncode == 0, result.stderr
            assert result.stdout == preview_output(nerd_fonts=True)

        def test_should_let_the_environment_override_the_cache(self, run, sandbox):
            cache_detection(sandbox, "1")

            result = run("env", "NERD_FONTS=0", "copilot-statusline",
                         stdin=json.dumps(session_payload()))

            assert result.returncode == 0, result.stderr
            assert result.stdout == preview_output()

        @pytest.mark.parametrize("flag,environment,nerd_fonts", [
            ("--nerd-fonts", "0", True),
            ("--no-nerd-fonts", "1", False),
        ])
        def test_should_let_the_flag_override_the_environment(
            self, run, flag, environment, nerd_fonts):
            result = run("env", f"NERD_FONTS={environment}", "copilot-statusline", flag,
                         stdin=json.dumps(session_payload()))

            assert result.returncode == 0, result.stderr
            assert result.stdout == preview_output(nerd_fonts=nerd_fonts)

        @pytest.mark.parametrize("family", ["", "JetBrainsMono"],
                                 ids=["top-level", "family-subdirectory"])
        def test_should_probe_again_after_a_font_install(
            self, run, sandbox, fake_bin, family):
            fonts = sandbox.home / (
                "Library/Fonts" if sys.platform == "darwin" else ".local/share/fonts") / family
            fonts.mkdir(parents=True)
            cache = cache_detection(sandbox, "0")
            hour_ago = time.time() - 3600
            os.utime(cache, (hour_ago, hour_ago))
            for directory in {fonts, fonts.parent} if family else {fonts}:
                os.utime(directory, (hour_ago, hour_ago))
            (fonts / "JetBrainsMonoNerdFont-Regular.ttf").write_text("")
            fake_bin("fc-list", stdout=(
                f"{fonts}/JetBrainsMonoNerdFont-Regular.ttf: JetBrainsMono Nerd Font\n"))

            result = run("copilot-statusline", stdin=json.dumps(session_payload()))

            assert result.returncode == 0, result.stderr
            assert (result.stdout, cache.read_text()) == (preview_output(nerd_fonts=True), "1")

        def test_should_still_render_on_an_unwritable_cache(self, run, sandbox):
            (sandbox.home / ".cache/agent-statusline").write_text("")

            result = run("copilot-statusline", stdin=json.dumps(session_payload()))

            assert result.returncode == 0, result.stderr
            assert result.stdout in (preview_output(), preview_output(nerd_fonts=True))

    class TestOnContext:
        def test_should_prefer_the_current_context_over_last_call_metrics(self, sandbox):
            payload = session_payload()
            payload["context_window"].update(
                used_percentage=78.8, context_window_size=272000)

            result = render(sandbox, payload)

            assert result.returncode == 0, result.stderr
            assert result.stdout == preview_output()

        def test_should_preserve_a_zero_current_percentage(self, sandbox):
            payload = session_payload()
            payload["context_window"].update(
                used_percentage=78.8, current_context_used_percentage=0)

            result = render(sandbox, payload)

            assert result.returncode == 0, result.stderr
            assert f"{DIM}○ 0%{RESET} {DIM}╱200k{RESET}" in result.stdout

        def test_should_fall_back_to_legacy_metrics_on_missing_current_values(self, sandbox):
            payload = session_payload()
            payload["context_window"].update(
                current_context_used_percentage=None, displayed_context_limit=None,
                used_percentage=28.8, context_window_size=1000000)

            result = render(sandbox, payload)

            assert result.returncode == 0, result.stderr
            assert f"{DIM}◔ 28%{RESET} {DIM}╱1m{RESET}" in result.stdout

        @pytest.mark.parametrize("percentage,expected", [
            (49.9, "\033[2m◑ 49%\033[0m"),
            (50, "\033[33m◑ 50%\033[0m"),
            (74.9, "\033[33m◕ 74%\033[0m"),
            (75, "\033[31m◕ 75%\033[0m"),
        ])
        def test_should_use_claude_thresholds(self, sandbox, percentage, expected):
            payload = session_payload()
            payload["context_window"]["current_context_used_percentage"] = percentage

            result = render(sandbox, payload)

            assert result.returncode == 0, result.stderr
            assert expected in result.stdout

    class TestOnModel:
        @pytest.mark.parametrize("display_name,model_id", [
            (None, "sonnet"), ("", "sonnet"), (42, "sonnet"),
            ("displayed", "sonnet"), (None, None), ("", ""), (None, 42),
        ])
        def test_should_omit_model_data(
            self, sandbox, display_name, model_id
        ):
            payload = session_payload()
            payload["model"] = {"display_name": display_name, "id": model_id}

            result = render(sandbox, payload)

            assert result.returncode == 0, result.stderr
            assert result.stdout == preview_output()

        def test_should_omit_the_incoming_display_name_and_effort(self, sandbox):
            payload = session_payload()
            payload["model"].update(id="gpt-6.1-sol", display_name="gpt-6.1-sol · high")

            result = render(sandbox, payload)

            assert result.returncode == 0, result.stderr
            assert result.stdout == preview_output()

    class TestOnAiUsed:
        @pytest.mark.parametrize("nano_aiu,expected", [
            (0, "\033[2m$0.00\033[0m"),
            (320414850, "\033[2m$0.00\033[0m"),
            (499990000000, "\033[2m$5.00\033[0m"),
            (500000000000, "\033[33m$5.00\033[0m"),
            (999990000000, "\033[33m$10.00\033[0m"),
            (1000000000000, "\033[31m$10.00\033[0m"),
        ])
        def test_should_convert_raw_credits_to_dollars_with_provider_thresholds(self, sandbox, nano_aiu, expected):
            payload = session_payload()
            payload["ai_used"] = {"total_nano_aiu": nano_aiu, "formatted": "ignored"}

            result = render(sandbox, payload)

            assert result.returncode == 0, result.stderr
            assert expected in result.stdout
            assert "ignored" not in result.stdout

        @pytest.mark.parametrize("nano_aiu", [None, False, "320414850"])
        def test_should_omit_missing_or_invalid_raw_credits(self, sandbox, nano_aiu):
            payload = session_payload()
            payload["ai_used"] = {"total_nano_aiu": nano_aiu, "formatted": "0.32"}

            result = render(sandbox, payload)

            assert result.returncode == 0, result.stderr
            assert "$" not in result.stdout

    class TestOnIndicators:
        @pytest.mark.parametrize("flag", ["--nerd-fonts", "--no-nerd-fonts"])
        def test_should_omit_remote_state_and_icons(self, sandbox, flag):
            payload = session_payload()
            payload["remote"] = {
                "connected": True,
                "indicator": "remote",
                "task_id": "remote-task",
                "task_name": "Conduct Testing Session",
                "task_type": "pull_request",
                "repository": "bkahlert/dotfiles",
                "pull_request_number": 42,
            }

            result = render(sandbox, payload, flag)

            assert result.returncode == 0, result.stderr
            assert len(result.stdout.splitlines()) == 1
            assert result.stdout == preview_output(nerd_fonts=flag == "--nerd-fonts")
            assert "remote" not in result.stdout
            assert "\uf0ac" not in result.stdout
            assert "↗" not in result.stdout

        @pytest.mark.parametrize("flag", ["--nerd-fonts", "--no-nerd-fonts"])
        def test_should_omit_allow_all_state_and_icons(self, sandbox, flag):
            result = render(sandbox, session_payload(), flag)

            assert result.returncode == 0, result.stderr
            assert "YOLO" not in result.stdout
            assert "\uf071" not in result.stdout
            assert "⚠" not in result.stdout

        @pytest.mark.parametrize("enabled", [False, None, "true", 1])
        def test_should_omit_states_that_are_not_enabled(self, sandbox, enabled):
            payload = session_payload()
            payload["remote"]["connected"] = enabled

            result = render(sandbox, payload)

            assert result.returncode == 0, result.stderr
            assert "remote" not in result.stdout
            assert "YOLO" not in result.stdout

    class TestOnClaudeParity:
        @pytest.mark.parametrize("flag", ["--nerd-fonts", "--no-nerd-fonts"])
        def test_should_match_shared_parts_including_ansi_styles(self, run, flag):
            payload = {
                "session_id": "abc123def456",
                "session_name": "my-session",
                "transcript_path": "/tmp/transcript.jsonl",
                "model": {"id": "gpt-6.1-sol", "display_name": "gpt-6.1-sol"},
                "context_window": {"used_percentage": 78.8, "context_window_size": 200000},
            }

            copilot = run("copilot-statusline", flag, stdin=json.dumps(payload))
            claude = run("statusline", flag, stdin=json.dumps(payload))

            assert copilot.returncode == claude.returncode == 0
            claude_parts = claude.stdout.split(" · ")
            assert copilot.stdout == " · ".join([claude_parts[0], *claude_parts[2:]])

    class TestOnInputDump:
        def test_should_store_raw_input_with_owner_only_permissions(self, run, sandbox):
            raw = json.dumps(session_payload(), indent=2) + "\n"

            result = run("copilot-statusline", "--no-nerd-fonts", stdin=raw)

            assert result.returncode == 0, result.stderr
            assert dump_path(sandbox).read_text() == raw
            assert dump_path(sandbox).stat().st_mode & 0o777 == 0o600
            assert result.stdout == preview_output()

        def test_should_replace_the_previous_dump(self, run, sandbox):
            first = run("copilot-statusline", "--no-nerd-fonts", stdin='{"session_id":"first"}')
            second = run("copilot-statusline", "--no-nerd-fonts", stdin='{"session_id":"second"}')

            assert first.returncode == second.returncode == 0
            assert dump_path(sandbox).read_text() == '{"session_id":"second"}'

        def test_should_dump_malformed_input_before_parsing(self, run, sandbox):
            result = run("copilot-statusline", "--no-nerd-fonts", stdin="not json\n")

            assert result.returncode == 0, result.stderr
            assert dump_path(sandbox).read_text() == "not json\n"

        def test_should_replace_a_symlink_without_touching_its_target(self, run, sandbox):
            target = sandbox.home / "untouched.json"
            target.write_text("untouched")
            dump_path(sandbox).symlink_to(target)

            result = run("copilot-statusline", "--no-nerd-fonts", stdin="{}")

            assert result.returncode == 0, result.stderr
            assert target.read_text() == "untouched"
            assert not dump_path(sandbox).is_symlink()
            assert dump_path(sandbox).read_text() == "{}"
            assert dump_path(sandbox).stat().st_mode & 0o777 == 0o600

    class TestOnBadArguments:
        def test_should_reject_unknown_options(self, run):
            result = run("copilot-statusline", "--unknown")

            assert result.returncode == 2
            assert result.stderr == (
                "copilot-statusline: unknown option: --unknown\n"
                "See 'copilot-statusline --help'\n"
            )

        def test_should_reject_positional_arguments(self, run):
            result = run("copilot-statusline", "unexpected")

            assert result.returncode == 2
            assert result.stderr == (
                "copilot-statusline: unexpected argument: unexpected\n"
                "See 'copilot-statusline --help'\n"
            )

    def test_should_render_the_captured_session_as_one_claude_style_row(self, sandbox):
        result = render(sandbox, session_payload())

        assert result.returncode == 0, result.stderr
        assert result.stdout == preview_output()
        assert "premium requests" not in result.stdout
        assert "@bkahlert" not in result.stdout

    def test_should_render_only_session_data_when_copilot_details_are_absent(self, sandbox):
        result = render(sandbox, {
            "model": {"id": "gpt-5-mini"},
            "context_window": {"used_percentage": 0},
        })

        assert result.returncode == 0, result.stderr
        assert result.stdout == f"{DIM}○ 0%{RESET}\n"


def render(sandbox, payload, *args):
    return subprocess.run(
        ["copilot-statusline", *(args or ("--no-nerd-fonts",))],
        env=sandbox.env,
        cwd=sandbox.home,
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=10,
    )


def session_payload():
    return {
        "cwd": str(ROOT),
        "session_id": "abc123def456",
        "session_name": "my-session",
        "transcript_path": str(Path.home() / ".copilot/session-state/abc123def456"),
        "model": {
            "id": "claude-sonnet-4-6",
            "display_name": "claude-sonnet-4-6",
            "auto_tier": None,
            "pending_auto_tier": None,
        },
        "workspace": {"current_dir": str(ROOT), "project_dir": str(ROOT), "added_dirs": []},
        "username": "bkahlert",
        "remote": {"connected": False},
        "version": "1.0.93",
        "cost": {
            "total_api_duration_ms": 2300,
            "total_lines_added": 156,
            "total_lines_removed": 23,
            "total_duration_ms": 45000,
            "total_premium_requests": 3,
        },
        "context_window": {
            "total_input_tokens": 15234,
            "total_output_tokens": 4521,
            "total_cache_read_tokens": 61234,
            "total_cache_write_tokens": 22485,
            "total_reasoning_tokens": 215,
            "total_tokens": 84003,
            "context_window_size": None,
            "used_percentage": None,
            "remaining_percentage": None,
            "remaining_tokens": None,
            "last_call_input_tokens": 21352,
            "last_call_output_tokens": 21,
            "current_context_tokens": 22663,
            "displayed_context_limit": 200000,
            "current_context_used_percentage": 28,
        },
        "ai_used": {"total_nano_aiu": 521000414850, "formatted": "521.00"},
        "allow_all_enabled": True,
    }


def preview_output(*, nerd_fonts=False):
    session, gauge = (
        ("", "\uee03" + "\uee04" * 2 + "\uee01" * 6 + "\uee02")
        if nerd_fonts else ("#", "◔"))
    return " · ".join([
        f"{session} " + link(
            f"file://{Path.home()}/.copilot/session-state/abc123def456",
            "abc123de",
        ) + " \033[3mmy-session\033[0m",
        f"{DIM}{gauge} 28%{RESET} {DIM}╱200k{RESET}",
        f"\033[33m$5.21{RESET}",
    ]) + "\n"


def cache_detection(sandbox, value):
    cache = sandbox.home / ".cache/agent-statusline/nerd-font-support"
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(value)
    return cache


def dump_path(sandbox):
    return Path(sandbox.env["TMPDIR"]) / "copilot-statusline-input.json"


def link(url, text):
    return f"\033]8;;{url}\033\\{text}\033]8;;\033\\"


DIM, YELLOW, RED, RESET = "\033[2m", "\033[33m", "\033[31m", "\033[0m"

if __name__ == "__main__":
    if sys.argv[1:] != ["--print-input"]:
        sys.exit(f"usage: {ROOT / 'tests/copilot/test_statusline.py'} --print-input")
    print(json.dumps(session_payload(), indent=2))
