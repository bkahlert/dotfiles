import re


class TestGrepr:
    def test_should_remind_to_use_rg(self, run, sandbox):
        (sandbox.home / "a.txt").write_text("needle\n")
        result = run("grepr", "needle", "a.txt")
        assert result.stderr == "grepr: use rg directly\n"

    def test_should_fall_back_to_grep_when_rg_is_unavailable(self, run, sandbox):
        (sandbox.home / "a.txt").write_text("needle\n")
        tools_without_rg = sandbox.home.parent / "tools-without-rg"
        tools_without_rg.mkdir()
        for tool in sandbox.real_tools.iterdir():
            if tool.name != "rg":
                (tools_without_rg / tool.name).symlink_to(tool.resolve())
        sandbox.env["PATH"] = f"{sandbox.fakes}:{sandbox.bin_links}:{tools_without_rg}"
        result = run("grepr", "needle", "a.txt")
        assert result.returncode == 0
        assert result.stdout == "a.txt:1:needle\n"
        assert result.stderr == "grepr: rg unavailable; using grep fallback\n"

    def test_should_print_filename_line_number_and_five_lines_of_context(self, run, sandbox):
        lines = [f"line {n}" for n in range(1, 21)]
        (sandbox.home / "notes.txt").write_text("\n".join(lines) + "\n")
        result = run("grepr", "line 10", ".")
        assert result.returncode == 0
        printed = [re.sub(r"^\./notes\.txt[:-](\d+)[:-]", r"\1 ", row) for row in result.stdout.splitlines()]
        assert printed == [f"{n} line {n}" for n in range(5, 16)]

    def test_should_mark_the_match_with_a_colon_and_context_with_a_dash(self, run, sandbox):
        (sandbox.home / "a.txt").write_text("before\nneedle\nafter\n")
        result = run("grepr", "needle", "a.txt")
        assert result.stdout == "a.txt-1-before\na.txt:2:needle\na.txt-3-after\n"

    def test_should_search_subdirectories(self, run, sandbox):
        (sandbox.home / "deep/er").mkdir(parents=True)
        (sandbox.home / "deep/er/f.txt").write_text("needle\n")
        result = run("grepr", "needle", ".")
        assert result.stdout == "./deep/er/f.txt:1:needle\n"

    def test_should_search_hidden_and_ignored_files(self, run, sandbox):
        (sandbox.home / ".hidden.txt").write_text("needle\n")
        (sandbox.home / ".gitignore").write_text("ignored.txt\n")
        (sandbox.home / "ignored.txt").write_text("needle\n")
        result = run("grepr", "needle", ".")
        assert result.returncode == 0
        assert {line.rsplit(":", 2)[0] for line in result.stdout.splitlines() if line.endswith(":needle")} == {
            "./.hidden.txt",
            "./ignored.txt",
        }

    def test_should_skip_vcs_directories(self, run, sandbox):
        for vcs in (".git", ".svn", "CVS"):
            (sandbox.home / vcs).mkdir()
            (sandbox.home / vcs / "f.txt").write_text("needle\n")
        (sandbox.home / "kept.txt").write_text("needle\n")
        result = run("grepr", "needle", ".")
        assert result.stdout == "./kept.txt:1:needle\n"

    def test_should_skip_binary_files(self, run, sandbox):
        (sandbox.home / "blob.bin").write_bytes(b"needle\x00\x01\x02\n")
        (sandbox.home / "text.txt").write_text("needle\n")
        result = run("grepr", "needle", ".")
        assert result.stdout == "./text.txt:1:needle\n"

    def test_should_accept_a_dashed_pattern_after_e(self, run, sandbox):
        (sandbox.home / "a.txt").write_text("a --flag b\n")
        result = run("grepr", "-e", "--flag", "a.txt")
        assert result.stdout == "a.txt:1:a --flag b\n"

    def test_should_pass_grep_options_through(self, run, sandbox):
        (sandbox.home / "a.txt").write_text("Needle\n")
        result = run("grepr", "-i", "needle", "a.txt")
        assert result.stdout == "a.txt:1:Needle\n"

    class TestOnNoMatch:
        def test_should_exit_1_without_results(self, run, sandbox):
            (sandbox.home / "a.txt").write_text("hay\n")
            result = run("grepr", "needle", "a.txt")
            assert (result.returncode, result.stdout) == (1, "")
