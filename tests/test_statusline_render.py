import sys

from repo import ROOT

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
