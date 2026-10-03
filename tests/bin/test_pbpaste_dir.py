import shlex


class TestPbpasteDir:
    class TestOnArchiveFromPbcopyDir:
        def test_should_unpack_files_and_directories_into_the_target(self, run, fake_bin, sandbox):
            clipboard_fakes(fake_bin, sandbox)
            (sandbox.home / "src/sub").mkdir(parents=True)
            (sandbox.home / "src/sub/a.txt").write_text("alpha")
            (sandbox.home / "README.md").write_text("readme")
            assert run("pbcopy-dir", "src", "README.md").returncode == 0
            target = sandbox.home / "out"
            result = run("pbpaste-dir", str(target))
            assert result.returncode == 0
            assert (target / "src/sub/a.txt").read_text() == "alpha"
            assert (target / "README.md").read_text() == "readme"

        def test_should_list_the_unpacked_entries(self, run, fake_bin, sandbox):
            clipboard_fakes(fake_bin, sandbox)
            (sandbox.home / "f.txt").write_text("x")
            run("pbcopy-dir", "f.txt")
            result = run("pbpaste-dir", str(sandbox.home / "out"))
            assert "f.txt" in result.stderr + result.stdout

        def test_should_create_the_target_directory_with_its_parents(self, run, fake_bin, sandbox):
            clipboard_fakes(fake_bin, sandbox)
            (sandbox.home / "f.txt").write_text("x")
            run("pbcopy-dir", "f.txt")
            run("pbpaste-dir", str(sandbox.home / "a/b/c"))
            assert (sandbox.home / "a/b/c/f.txt").read_text() == "x"

        def test_should_unpack_into_the_current_directory_without_arguments(self, run, fake_bin, sandbox):
            clipboard_fakes(fake_bin, sandbox)
            (sandbox.home / "f.txt").write_text("new")
            run("pbcopy-dir", "f.txt")
            (sandbox.home / "f.txt").write_text("old")
            run("pbpaste-dir")
            assert (sandbox.home / "f.txt").read_text() == "new"

    class TestOnBadClipboard:
        def test_should_fail_when_the_clipboard_holds_no_archive(self, run, fake_bin, sandbox):
            clipboard_fakes(fake_bin, sandbox)
            (sandbox.home / "clipboard").write_text("not an archive")
            result = run("pbpaste-dir", str(sandbox.home / "out"))
            assert result.returncode != 0
            assert list((sandbox.home / "out").iterdir()) == []

    class TestOnTooManyArguments:
        def test_should_exit_2(self, run):
            result = run("pbpaste-dir", "a", "b")
            assert result.returncode == 2
            assert result.stderr == "pbpaste-dir: too many arguments\nSee 'pbpaste-dir --help'\n"

    class TestOnUnknownOption:
        def test_should_exit_2_and_name_the_option(self, run):
            result = run("pbpaste-dir", "--nope")
            assert result.returncode == 2
            assert result.stderr == "pbpaste-dir: unknown option: --nope\nSee 'pbpaste-dir --help'\n"

    class TestOnHelp:
        def test_should_print_the_header(self, run):
            result = run("pbpaste-dir", "--help")
            assert result.returncode == 0
            assert "Usage:   pbpaste-dir [<dir>]\n" in result.stdout


def clipboard_fakes(fake_bin, sandbox):
    clipboard = shlex.quote(str(sandbox.home / "clipboard"))
    fake_bin("pbcopy", script=f"cat > {clipboard}\n")
    fake_bin("pbpaste", script=f"cat {clipboard}\n")
