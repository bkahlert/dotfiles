import base64
import io
import shlex
import tarfile


class TestPbcopyDir:
    def test_should_put_a_base64_gzipped_tar_of_the_paths_on_the_clipboard(self, run, fake_bin, sandbox):
        clipboard = clipboard_fake(fake_bin, sandbox)
        (sandbox.home / "src").mkdir()
        (sandbox.home / "src/a.txt").write_text("alpha")
        (sandbox.home / "README.md").write_text("readme")
        result = run("pbcopy-dir", "src", "README.md")
        assert result.returncode == 0
        assert sorted(archived_names(clipboard)) == ["README.md", "src", "src/a.txt"]

    def test_should_store_relative_paths_as_given(self, run, fake_bin, sandbox):
        clipboard = clipboard_fake(fake_bin, sandbox)
        (sandbox.home / "d").mkdir()
        (sandbox.home / "d/f").write_text("x")
        run("pbcopy-dir", "d/f")
        assert archived_names(clipboard) == ["d/f"]

    class TestOnMissingPath:
        def test_should_exit_2_and_leave_the_clipboard_alone(self, run, fake_bin, calls, sandbox):
            clipboard_fake(fake_bin, sandbox)
            (sandbox.home / "here").write_text("x")
            result = run("pbcopy-dir", "here", "gone")
            assert result.returncode == 2
            assert result.stderr == "pbcopy-dir: no such file or directory: gone\nSee 'pbcopy-dir --help'\n"
            assert calls("pbcopy") == []

    class TestOnNoArguments:
        def test_should_print_the_help_to_stderr_and_exit_2(self, run):
            result = run("pbcopy-dir")
            assert (result.returncode, result.stdout) == (2, "")
            assert result.stderr.startswith("Purpose: Copy files or directories to the clipboard")

    class TestOnUnknownOption:
        def test_should_exit_2_and_name_the_option(self, run):
            result = run("pbcopy-dir", "--nope")
            assert result.returncode == 2
            assert result.stderr == "pbcopy-dir: unknown option: --nope\nSee 'pbcopy-dir --help'\n"

    class TestOnHelp:
        def test_should_print_the_header(self, run):
            result = run("pbcopy-dir", "--help")
            assert result.returncode == 0
            assert "Usage:   pbcopy-dir <path>...\n" in result.stdout

    class TestOnDoubleDash:
        def test_should_treat_a_dashed_name_as_a_path(self, run, fake_bin, sandbox):
            clipboard = clipboard_fake(fake_bin, sandbox)
            (sandbox.home / "-odd").write_text("x")
            result = run("pbcopy-dir", "--", "-odd")
            assert result.returncode == 0
            assert archived_names(clipboard) == ["-odd"]


def clipboard_fake(fake_bin, sandbox):
    clipboard = sandbox.home / "clipboard"
    fake_bin("pbcopy", script=f"cat > {shlex.quote(str(clipboard))}\n")
    return clipboard


def archived_names(clipboard):
    # macOS tar adds a "._name" AppleDouble entry per file that has extended attributes.
    with tarfile.open(fileobj=io.BytesIO(base64.b64decode(clipboard.read_bytes())), mode="r:gz") as archive:
        return [name for name in archive.getnames() if not name.rpartition("/")[2].startswith("._")]
