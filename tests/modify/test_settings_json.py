import json

import pytest

from repo import HOME_SOURCE

SCRIPT = HOME_SOURCE / "private_dot_claude" / "modify_settings.json"
OWNED_BY_THE_MACHINE = ("model", "effortLevel", "modelSettings")


class TestModifySettingsJson:
    class TestOnKeysClaudeCodeChangesItself:
        @pytest.mark.parametrize("key", OWNED_BY_THE_MACHINE)
        def test_should_keep_the_live_value_over_the_source_one(self, apply, key):
            result = apply({key: "from source", "theme": "dark"}, {key: "from live"})
            assert result[key] == "from live"

        @pytest.mark.parametrize("key", OWNED_BY_THE_MACHINE)
        def test_should_drop_the_key_when_the_machine_has_none(self, apply, key):
            result = apply({key: "from source", "theme": "dark"}, {"theme": "light"})
            assert key not in result

        def test_should_take_everything_else_from_the_source(self, apply):
            result = apply({"theme": "dark", "env": {"A": "1"}}, {"theme": "light", "env": {"B": "2"}})
            assert result == {"theme": "dark", "env": {"A": "1"}}

    @pytest.mark.parametrize("key", ("enabledPlugins", "extraKnownMarketplaces"))
    class TestOnMachineLocalEntries:
        def test_should_keep_entries_only_the_machine_has(self, apply, key):
            result = apply({key: {"shared": 1}}, {key: {"local-only": 2}})
            assert result[key] == {"local-only": 2, "shared": 1}

        def test_should_let_the_source_win_per_entry(self, apply, key):
            result = apply({key: {"shared": "source"}}, {key: {"shared": "live", "local-only": 2}})
            assert result[key]["shared"] == "source"

        def test_should_add_nothing_when_neither_side_has_the_key(self, apply, key):
            assert key not in apply({"theme": "dark"}, {"theme": "light"})

    class TestOnKeyOrder:
        def test_should_follow_the_live_file_and_append_new_source_keys(self, apply):
            result = apply({"a": 1, "b": 2, "c": 3}, {"c": 0, "x": 0, "a": 0})
            assert list(result) == ["c", "a", "b"]

        def test_should_leave_an_unchanged_file_byte_identical(self, modify, source):
            settings = {"a": 1, "model": "m", "enabledPlugins": {"p": True}}
            first = modify(source(settings), "")
            second = modify(source(settings), first.stdout)
            assert second.stdout == first.stdout

    class TestOnNoCurrentFile:
        @pytest.mark.parametrize("current", ("", "\n"), ids=("empty", "newline"))
        def test_should_render_the_source_without_the_machine_keys(self, modify, source, current):
            result = modify(source({"a": 1, "model": "m"}), current)
            assert (result.returncode, json.loads(result.stdout)) == (0, {"a": 1})

    class TestOnInvalidJson:
        def test_should_fail_and_print_no_content_for_chezmoi_to_write(self, modify, source):
            result = modify(source({"a": 1}), "{ not json")
            assert result.returncode != 0
            assert result.stdout == ""

    class TestOnTheRealSourceState:
        def test_should_render_valid_json_that_keeps_the_machine_choices(self, modify):
            result = modify(SCRIPT, json.dumps({"model": "opus", "effortLevel": "high"}))
            rendered = json.loads(result.stdout)
            assert (result.returncode, rendered["model"], rendered["effortLevel"]) == (0, "opus", "high")
            assert rendered["statusLine"] == {"type": "command", "command": "~/.claude/statusline"}
            assert rendered["env"]["CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS"] == "1"
            assert rendered["enabledPlugins"]["superpowers@claude-plugins-official"] is True

        def test_should_leave_the_real_defaults_byte_identical_on_repeated_apply(self, modify):
            first = modify(SCRIPT, "")
            second = modify(SCRIPT, first.stdout)
            assert first.returncode == second.returncode == 0
            assert first.stdout == second.stdout


@pytest.fixture
def source(tmp_path):
    """A copy of the modifier with fixture defaults in its heredoc."""
    def make(settings):
        script = tmp_path / "modify_settings.json"
        prefix, defaults = SCRIPT.read_text().split("<<'SETTINGS'\n", 1)
        _, suffix = defaults.split("\nSETTINGS", 1)
        script.write_text(prefix + "<<'SETTINGS'\n" + json.dumps(settings) + "\nSETTINGS" + suffix)
        return script
    return make


@pytest.fixture
def apply(modify, source):
    def run(from_source, live):
        result = modify(source(from_source), json.dumps(live))
        assert result.returncode == 0, result.stderr
        return json.loads(result.stdout)
    return run
