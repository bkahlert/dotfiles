import json
import shutil
import sys

import pytest

from repo import HOME_SOURCE, ROOT

sys.path.insert(0, str(ROOT / "home" / "dot_local" / "share"))

import agent_statusline
from agent_statusline import render_parts


class TestAgentStatusline:
    class TestOnModel:
        @pytest.mark.parametrize("override,environment,icon", [
            ("1", "0", "\ue28c"), ("0", "1", "⚙\ufe0e"),
            (None, "1", "\ue28c"), (None, "0", "⚙\ufe0e"),
        ])
        @pytest.mark.parametrize("model,configured,expected", [
            ("claude-sonnet-4-6", None, "{icon} claude-sonnet-4-6"),
            (None, None, "{icon} ?"),
            ("", None, "{icon} "),
            ("Auto → GPT-6 Luna", "", "{icon} Auto → GPT-6 Luna"),
            ("claude-sonnet-4-6", "sonnet", "\033[2m{icon} claude-sonnet-4-6\033[0m"),
            ("sonnet", "claude-sonnet-4-6", "\033[2m{icon} sonnet\033[0m"),
            ("CLAUDE-SONNET-4-6", "Sonnet", "\033[2m{icon} CLAUDE-SONNET-4-6\033[0m"),
            ("claude-sonnet-4-6", "opus", "\033[33m{icon} claude-sonnet-4-6\033[0m"),
            (None, "sonnet", "\033[33m{icon} ?\033[0m"),
        ])
        def test_should_render_the_model_and_select_its_own_icon(
            self, monkeypatch, override, environment, icon, model, configured, expected
        ):
            monkeypatch.setenv("NERD_FONTS", environment)

            result = agent_statusline.part_model(model, configured, override=override)

            assert result == expected.format(icon=icon)

    class TestOnJsonInput:
        @pytest.mark.parametrize("text,expected", [
            ('{"session_id":"abc","nested":{"used":0}}', {"session_id": "abc", "nested": {"used": 0}}),
            ("{}", {}), ("", {}), ("not json", {}), ("null", {}),
            ("[]", {}), ('"session"', {}), ("42", {}), ("true", {}),
        ])
        def test_should_read_only_json_objects(self, text, expected):
            assert agent_statusline.read_json(text) == expected

        @pytest.mark.parametrize("value,path,expected", [
            ({"nested": {"used": 0}}, ("nested", "used"), 0),
            ({"nested": {"used": False}}, ("nested", "used"), False),
            ({"nested": {"used": ""}}, ("nested", "used"), ""),
            ({"nested": {}}, ("nested", "used"), None),
            ({"nested": []}, ("nested", "used"), None),
            (None, ("nested", "used"), None),
            ({"used": 2}, (), {"used": 2}),
        ])
        def test_should_read_nested_fields_without_losing_falsey_values(self, value, path, expected):
            assert agent_statusline.field(value, *path) == expected

        @pytest.mark.parametrize("value,expected", [
            (0, 0), (2, 2), (-1, -1), (0.5, 0.5),
            (True, None), (False, None), ("2", None), (None, None), ({}, None),
        ])
        def test_should_accept_numbers_but_not_booleans(self, value, expected):
            assert agent_statusline.number(value) == expected

    class TestOnInputDump:
        def test_should_replace_raw_input_with_owner_only_permissions(self, tmp_path, monkeypatch):
            monkeypatch.setattr("tempfile.gettempdir", lambda: str(tmp_path))
            destination = tmp_path / "sample-input.json"
            destination.write_text("previous")
            destination.chmod(0o644)
            raw = '{"session_name":"caf\u00e9"}\n'

            agent_statusline.dump_input(raw, "sample-input.json")

            assert destination.read_text() == raw
            assert destination.stat().st_mode & 0o777 == 0o600
            assert list(tmp_path.iterdir()) == [destination]

        def test_should_surface_write_errors_and_clean_up_the_temporary_file(self, tmp_path, monkeypatch):
            monkeypatch.setattr("tempfile.gettempdir", lambda: str(tmp_path))
            destination = tmp_path / "sample-input.json"
            destination.mkdir()

            with pytest.raises(OSError):
                agent_statusline.dump_input("raw", "sample-input.json")

            assert list(tmp_path.iterdir()) == [destination]

    class TestOnSession:
        @pytest.mark.parametrize("override,environment,icon", [
            ("1", "0", "\uf292"), ("0", "1", "#"),
            (None, "1", "\uf292"), (None, "0", "#"),
        ])
        @pytest.mark.parametrize("session_id,name,url,expected", [
            ("abc123def456", "my-session", "file:///tmp/session.jsonl",
             "{icon} \033]8;;file:///tmp/session.jsonl\033\\abc123de\033]8;;\033\\ \033[3mmy-session\033[0m"),
            ("abc123def456", "my-session", None,
             "{icon} abc123de \033[3mmy-session\033[0m"),
            ("abc123def456", None, "file:///tmp/session.jsonl",
             "{icon} \033]8;;file:///tmp/session.jsonl\033\\abc123de\033]8;;\033\\"),
            ("abc", None, None, "{icon} abc"),
            (None, "my-session", "file:///tmp/session.jsonl", "\033[3mmy-session\033[0m"),
            (None, "my-session", None, "\033[3mmy-session\033[0m"),
            (None, None, "file:///tmp/session.jsonl", ""),
            (None, None, None, ""),
            ("", "", "", ""),
        ])
        def test_should_render_optional_fields_and_select_its_own_icon(
            self, monkeypatch, override, environment, icon, session_id, name, url, expected
        ):
            monkeypatch.setenv("NERD_FONTS", environment)

            result = agent_statusline.part_session(session_id, name, url, override=override)

            assert result == expected.format(icon=icon)

        def test_should_allow_all_fields_to_be_omitted(self):
            assert agent_statusline.part_session() == ""

    class TestOnLinks:
        def test_should_wrap_only_the_supplied_text(self):
            result = agent_statusline.link("file:///tmp/transcript.jsonl", "abc123de")

            assert result == (
                "\033]8;;file:///tmp/transcript.jsonl\033\\abc123de\033]8;;\033\\"
            )

    class TestOnIconSelection:
        @pytest.mark.parametrize("override,environment,session,model,remote,yolo", [
            ("1", "0", "\uf292", "\ue28c", "\uf0ac", "\uf071"),
            ("0", "1", "#", "⚙\ufe0e", "↗", "⚠\ufe0e"),
            (None, "1", "\uf292", "\ue28c", "\uf0ac", "\uf071"),
            (None, "0", "#", "⚙\ufe0e", "↗", "⚠\ufe0e"),
        ])
        def test_should_select_semantic_icons_with_flag_precedence(
            self, monkeypatch, override, environment, session, model, remote, yolo
        ):
            monkeypatch.setenv("NERD_FONTS", environment)

            result = agent_statusline.select_icons(override)

            assert (result.session, result.model, result.remote, result.yolo) == (
                session, model, remote, yolo
            )

        @pytest.mark.parametrize("percentage,expected", [
            (0, "○"), (11, "○"), (12, "◔"), (36, "◔"), (37, "◑"),
            (61, "◑"), (62, "◕"), (86, "◕"), (87, "●"), (100, "●"),
        ])
        def test_should_select_a_circle_at_each_boundary(self, percentage, expected):
            icons = agent_statusline.select_icons("0")

            result = icons.gauge(percentage)

            assert result == expected

        @pytest.mark.parametrize("percentage,expected", [
            (0, "\uee00" + "\uee01" * 8 + "\uee02"),
            (4, "\uee00" + "\uee01" * 8 + "\uee02"),
            (5, "\uee03" + "\uee01" * 8 + "\uee02"),
            (94, "\uee03" + "\uee04" * 8 + "\uee02"),
            (95, "\uee03" + "\uee04" * 8 + "\uee05"),
            (100, "\uee03" + "\uee04" * 8 + "\uee05"),
        ])
        def test_should_fill_bar_segments_at_their_midpoints(self, percentage, expected):
            icons = agent_statusline.select_icons("1")

            result = icons.gauge(percentage)

            assert result == expected

    def test_should_join_parts_with_the_default_separator(self):
        result = render_parts(["model", "context"])
        assert result == "model · context"

    def test_should_omit_empty_parts_without_leaving_separators(self):
        result = render_parts(["", "model", "", "context", ""])
        assert result == "model · context"

    def test_should_use_a_custom_separator(self):
        result = render_parts(["model", "context"], " | ")
        assert result == "model | context"

    def test_should_return_empty_string_for_no_parts(self):
        result = render_parts([])
        assert result == ""

    def test_should_preserve_part_text_verbatim(self):
        ansi = "\033[2mtext\033[0m"
        hyperlink = "\033]8;;file:///tmp/session\033\\session\033]8;;\033\\"
        result = render_parts([ansi, hyperlink])
        assert result == f"{ansi} · {hyperlink}"


class TestStatuslineCommands:
    class TestOnSession:
        @pytest.mark.parametrize("command", ["statusline", "copilot-statusline"])
        @pytest.mark.parametrize("flag,icon", [
            ("--nerd-fonts", "\uf292"), ("--no-nerd-fonts", "#"),
        ])
        @pytest.mark.parametrize("session_id,name,transcript,expected", [
            ("abc123def456", "my-session", "/tmp/session.jsonl",
             "{icon} \033]8;;file:///tmp/session.jsonl\033\\abc123de\033]8;;\033\\ \033[3mmy-session\033[0m"),
            ("abc123def456", "my-session", None,
             "{icon} abc123de \033[3mmy-session\033[0m"),
            ("abc123def456", None, "/tmp/session.jsonl",
             "{icon} \033]8;;file:///tmp/session.jsonl\033\\abc123de\033]8;;\033\\"),
            (None, "my-session", "/tmp/session.jsonl",
             "\033[3mmy-session\033[0m"),
            (None, None, "/tmp/session.jsonl", ""),
        ])
        def test_should_render_id_and_name_independently(
            self, command, flag, icon, session_id, name, transcript, expected, run
        ):
            payload = {"session_id": session_id, "session_name": name,
                       "transcript_path": transcript}

            result = run(command, flag, stdin=json.dumps(payload))

            assert result.returncode == 0, result.stderr
            assert result.stdout.split(" · ")[0] == (
                expected.format(icon=icon) if expected else
                ("\ue28c ?" if flag == "--nerd-fonts" else "⚙\ufe0e ?")
            )

    @pytest.mark.parametrize("command", ["statusline", "copilot-statusline"])
    def test_should_use_the_shared_cache_under_xdg_cache_home(
        self, command, run, sandbox, tmp_path
    ):
        cache_home = tmp_path / "cache"
        cache = cache_home / "agent-statusline/nerd-font-support"
        cache.parent.mkdir(parents=True)
        cache.write_text("1\n")

        result = run("env", f"XDG_CACHE_HOME={cache_home}", command, stdin="{}")

        assert result.returncode == 0, result.stderr
        assert result.stdout.startswith("\ue28c ?")

    @pytest.mark.parametrize("command", ["statusline", "copilot-statusline"])
    def test_should_fail_visibly_when_the_shared_module_is_missing(self, command, run, sandbox):
        module = sandbox.home / ".local/share/agent_statusline.py"
        module.unlink(missing_ok=True)

        result = run(command, "--no-nerd-fonts", stdin="{}")

        assert result.returncode != 0
        assert "agent_statusline" in result.stderr

    class TestOnSourceExecution:
        @pytest.mark.parametrize("provider", ["claude", "copilot"])
        @pytest.mark.parametrize("preview", [False, True])
        @pytest.mark.parametrize("flag", ["--nerd-fonts", "--no-nerd-fonts"])
        def test_should_render_without_an_applied_module(
            self, provider, preview, flag, run, sandbox, fake_bin
        ):
            (sandbox.home / ".local/share/agent_statusline.py").unlink()
            fake_bin("chezmoi", stdout=f"{HOME_SOURCE}\n")
            fake_bin("uv", stdout="{}")
            script = HOME_SOURCE / f"private_dot_{provider}" / "executable_statusline"
            args = [flag, *(["--preview"] if preview else [])]

            result = run(str(script), *args, stdin="{}")

            assert result.returncode == 0, result.stderr
            assert result.stderr == ""
            assert result.stdout.strip()

        @pytest.mark.parametrize("provider", ["claude", "copilot"])
        def test_should_fail_visibly_on_missing_source_module(
            self, provider, run, sandbox, tmp_path
        ):
            source = tmp_path / "source"
            script = source / f"private_dot_{provider}" / "executable_statusline"
            script.parent.mkdir(parents=True)
            shutil.copy2(HOME_SOURCE / f"private_dot_{provider}" / "executable_statusline", script)
            (source / "dot_local/share").mkdir(parents=True)
            assert (sandbox.home / ".local/share/agent_statusline.py").is_file()

            result = run(str(script), "--no-nerd-fonts", stdin="{}")

            assert result.returncode != 0
            assert "agent_statusline" in result.stderr
