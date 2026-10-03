import re


class TestGrepr:
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
        def test_should_exit_1_silently(self, run, sandbox):
            (sandbox.home / "a.txt").write_text("hay\n")
            result = run("grepr", "needle", "a.txt")
            assert (result.returncode, result.stdout, result.stderr) == (1, "", "")
