import json

import pytest


class TestStatusline:
    class TestOnNerdFonts:
        def test_should_render_glyphs_and_a_segment_bar(self, run, clock):
            result = run("statusline", "--nerd-fonts", stdin=json.dumps(INPUT))
            assert result.returncode == 0
            assert result.stdout == NERD

    class TestOnNoNerdFonts:
        def test_should_render_text_variant_emoji(self, run, clock):
            result = run("statusline", "--no-nerd-fonts", stdin=json.dumps(INPUT))
            assert result.returncode == 0
            assert result.stdout == FALLBACK

    class TestOnAutoDetection:
        def test_should_cache_the_probe_and_render_accordingly(self, run, clock, sandbox):
            result = run("statusline", stdin=json.dumps(INPUT))
            cached = (sandbox.home / ".cache/claude/nerd-font-support").read_text()
            assert cached in ("0", "1")
            assert result.stdout == {"1": NERD, "0": FALLBACK}[cached]

        def test_should_trust_a_cached_result(self, run, clock, sandbox):
            cache_detection(sandbox, "1")
            result = run("statusline", stdin=json.dumps(INPUT))
            assert result.stdout == NERD

        def test_should_let_the_environment_override_the_cache(self, run, clock, sandbox):
            cache_detection(sandbox, "1")
            result = run("env", "NERD_FONTS=0", "statusline", stdin=json.dumps(INPUT))
            assert result.stdout == FALLBACK

    class TestOnConfiguredModel:
        def test_should_dim_a_model_that_matches_the_settings(self, run, clock, sandbox):
            configure_model(sandbox, "settings.json", "sonnet")
            result = render(run, INPUT)
            assert f"{DIM}⚙︎ claude-sonnet-4-6{RESET}" in result.stdout

        def test_should_highlight_a_model_that_differs_from_the_settings(self, run, clock, sandbox):
            configure_model(sandbox, "settings.json", "opus")
            result = render(run, INPUT)
            assert f"{YELLOW}⚙︎ claude-sonnet-4-6{RESET}" in result.stdout

        def test_should_prefer_the_local_settings(self, run, clock, sandbox):
            configure_model(sandbox, "settings.json", "opus")
            configure_model(sandbox, "settings.local.json", "sonnet")
            result = render(run, INPUT)
            assert f"{DIM}⚙︎ claude-sonnet-4-6{RESET}" in result.stdout

    class TestOnThresholds:
        def test_should_colour_the_cost_yellow_from_5_dollars(self, run, clock):
            result = render(run, {"cost": {"total_cost_usd": 5.0}})
            assert f"{YELLOW}$5.00{RESET}" in result.stdout

        def test_should_colour_the_cost_red_from_10_dollars(self, run, clock):
            result = render(run, {"cost": {"total_cost_usd": 10}})
            assert f"{RED}$10.00{RESET}" in result.stdout

        def test_should_colour_the_context_red_from_75_percent(self, run, clock):
            result = render(run, {"context_window": {"used_percentage": 75.9}})
            assert f"{RED}◕ 75%{RESET}" in result.stdout

        def test_should_mark_an_expired_rate_limit_window(self, run, clock):
            result = render(run, {"rate_limits": {"five_hour": {"used_percentage": 3, "resets_at": 1893399000}}})
            assert link(LIMITS, f"{DIM}⏱︎ 3% ᵉˣᵖⁱʳᵉᵈ{RESET}") in result.stdout

    class TestOnSparseInput:
        def test_should_render_only_the_model_and_the_context(self, run, clock):
            result = render(run, {})
            assert result.returncode == 0
            assert result.stdout == f"⚙︎ ? · {DIM}○ 0%{RESET}\n"


def render(run, fields):
    return run("statusline", "--no-nerd-fonts", stdin=json.dumps(fields))


def cache_detection(sandbox, value):
    cache = sandbox.home / ".cache/claude/nerd-font-support"
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(value)


def configure_model(sandbox, name, model):
    (sandbox.home / ".claude").mkdir(exist_ok=True)
    (sandbox.home / ".claude" / name).write_text(json.dumps({"model": model}))


def link(url, text):
    return f"\x1b]8;;{url}\x1b\\{text}\x1b]8;;\x1b\\"


@pytest.fixture
def clock(fake_bin):
    fake_bin("date", stdout="1893400000")


DIM, YELLOW, RED, RESET = "\x1b[2m", "\x1b[33m", "\x1b[31m", "\x1b[0m"
LIMITS = "https://console.anthropic.com/settings/limits"
TRANSCRIPT = "file:///Users/bkahlert/.claude/transcripts/abc123def456.jsonl"
EMPTY_SEGMENTS = "" * 6

INPUT = {
    "cwd": "/Users/bkahlert/Development/com.bkahlert/dotfiles",
    "session_id": "abc123def456",
    "session_name": "my-session",
    "transcript_path": "/Users/bkahlert/.claude/transcripts/abc123def456.jsonl",
    "model": {"id": "claude-sonnet-4-6", "display_name": "Sonnet"},
    "workspace": {
        "current_dir": "/Users/bkahlert/Development/com.bkahlert/dotfiles",
        "project_dir": "/Users/bkahlert/Development/com.bkahlert/dotfiles",
        "added_dirs": [],
    },
    "version": "2.1.90",
    "output_style": {"name": "default"},
    "cost": {
        "total_cost_usd": 0.01234,
        "total_duration_ms": 45000,
        "total_api_duration_ms": 2300,
        "total_lines_added": 156,
        "total_lines_removed": 23,
    },
    "context_window": {
        "total_input_tokens": 15234,
        "total_output_tokens": 4521,
        "context_window_size": 200000,
        "used_percentage": 28,
        "remaining_percentage": 92,
        "current_usage": {
            "input_tokens": 8500,
            "output_tokens": 1200,
            "cache_creation_input_tokens": 5000,
            "cache_read_input_tokens": 2000,
        },
    },
    "agent": {"name": "security-reviewer"},
    "exceeds_200k_tokens": False,
    "rate_limits": {
        "five_hour": {"used_percentage": 28.5, "resets_at": 1893465000},
        "seven_day": {"used_percentage": 92.2, "resets_at": 1893758400},
    },
}

NERD = " · ".join([
    link(TRANSCRIPT, " abc123de:my-session"),
    " claude-sonnet-4-6",
    "\U000f06a9 security-reviewer",
    f"{DIM}{EMPTY_SEGMENTS} 28%{RESET} {DIM}╱200k{RESET}",
    f"{DIM}$0.01{RESET}",
    link(LIMITS, f"{DIM} 28% ¹⁸·¹ʰ{RESET}"),
    link(LIMITS, f"{RED} 92% ⁴·¹ᵈ{RESET}"),
]) + "\n"

FALLBACK = " · ".join([
    link(TRANSCRIPT, "# abc123de:my-session"),
    "⚙︎ claude-sonnet-4-6",
    "웃 security-reviewer",
    f"{DIM}◔ 28%{RESET} {DIM}╱200k{RESET}",
    f"{DIM}$0.01{RESET}",
    link(LIMITS, f"{DIM}⏱︎ 28% ¹⁸·¹ʰ{RESET}"),
    link(LIMITS, f"{RED}⧗︎ 92% ⁴·¹ᵈ{RESET}"),
]) + "\n"
