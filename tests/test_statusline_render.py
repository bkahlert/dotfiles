import shutil
import sys

import pytest

from repo import HOME_SOURCE, ROOT

sys.path.insert(0, str(ROOT / "home" / "dot_local" / "share"))

from statusline_render import render_parts


class TestStatuslineRender:
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
    @pytest.mark.parametrize("command", ["statusline", "copilot-statusline"])
    def test_should_fail_visibly_when_the_shared_module_is_missing(self, command, run, sandbox):
        module = sandbox.home / ".local/share/statusline_render.py"
        module.unlink(missing_ok=True)

        result = run(command, "--no-nerd-fonts", stdin="{}")

        assert result.returncode != 0
        assert "statusline_render" in result.stderr

    class TestOnSourceExecution:
        @pytest.mark.parametrize("provider", ["claude", "copilot"])
        @pytest.mark.parametrize("preview", [False, True])
        def test_should_render_without_an_applied_module(
            self, provider, preview, run, sandbox, fake_bin
        ):
            (sandbox.home / ".local/share/statusline_render.py").unlink()
            fake_bin("chezmoi", stdout=f"{HOME_SOURCE}\n")
            fake_bin("uv", stdout="{}")
            script = HOME_SOURCE / f"private_dot_{provider}" / "executable_statusline"
            args = ["--no-nerd-fonts", *(["--preview"] if preview else [])]

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
            assert (sandbox.home / ".local/share/statusline_render.py").is_file()

            result = run(str(script), "--no-nerd-fonts", stdin="{}")

            assert result.returncode != 0
            assert "statusline_render" in result.stderr
