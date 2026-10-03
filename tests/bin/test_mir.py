MIRROR = ["-av", "--progress", "--delete", "--no-perms", "--no-owner", "--no-group"]


class TestMir:
    def test_should_mirror_with_delete_between_directories_with_trailing_slashes(self, run, fake_bin, calls, sandbox):
        fake_bin("rsync")
        src, dst = pair(sandbox)
        result = run("mir", str(src), str(dst))
        assert result.returncode == 0
        assert calls("rsync") == [[*MIRROR, f"{src}/", f"{dst}/"]]

    def test_should_strip_trailing_slashes_from_both_paths(self, run, fake_bin, calls, sandbox):
        fake_bin("rsync")
        src, dst = pair(sandbox)
        run("mir", f"{src}/", f"{dst}/")
        assert calls("rsync") == [[*MIRROR, f"{src}/", f"{dst}/"]]

    def test_should_accept_a_destination_that_does_not_exist_yet(self, run, fake_bin, calls, sandbox):
        fake_bin("rsync")
        src, _ = pair(sandbox)
        dst = sandbox.home / "new/Pictures"
        result = run("mir", str(src), str(dst))
        assert result.returncode == 0
        assert calls("rsync") == [[*MIRROR, f"{src}/", f"{dst}/"]]

    def test_should_pass_the_exit_code_of_rsync_on(self, run, fake_bin, sandbox):
        fake_bin("rsync", exit_code=23)
        src, dst = pair(sandbox)
        assert run("mir", str(src), str(dst)).returncode == 23

    class TestOnDryRun:
        def test_should_add_dry_run_to_rsync(self, run, fake_bin, calls, sandbox):
            fake_bin("rsync")
            src, dst = pair(sandbox)
            run("mir", "--dry-run", str(src), str(dst))
            assert calls("rsync") == [[*MIRROR, "--dry-run", f"{src}/", f"{dst}/"]]

        def test_should_accept_the_short_option_after_the_paths(self, run, fake_bin, calls, sandbox):
            fake_bin("rsync")
            src, dst = pair(sandbox)
            run("mir", str(src), str(dst), "-n")
            assert calls("rsync")[0][-3:] == ["--dry-run", f"{src}/", f"{dst}/"]

    class TestOnBadArguments:
        def test_should_print_the_help_to_stderr_and_exit_2_without_arguments(self, run, fake_bin, calls):
            fake_bin("rsync")
            result = run("mir")
            assert (result.returncode, result.stdout) == (2, "")
            assert result.stderr.startswith("Purpose: Mirror a directory into another with rsync")
            assert calls("rsync") == []

        def test_should_exit_2_and_name_an_unknown_option(self, run):
            result = run("mir", "--nope")
            assert result.returncode == 2
            assert result.stderr == "mir: unknown option: --nope\nSee 'mir --help'\n"

        def test_should_exit_2_on_a_single_path(self, run, sandbox):
            result = run("mir", str(sandbox.home))
            assert result.returncode == 2
            assert result.stderr == "mir: expected <source-dir> and <destination-dir>\nSee 'mir --help'\n"

        def test_should_exit_2_on_three_paths(self, run, sandbox):
            result = run("mir", "a", "b", "c")
            assert result.returncode == 2
            assert result.stderr == "mir: expected <source-dir> and <destination-dir>\nSee 'mir --help'\n"

        def test_should_exit_2_when_the_source_is_not_a_directory(self, run, fake_bin, calls, sandbox):
            fake_bin("rsync")
            result = run("mir", str(sandbox.home / "gone/Pictures"), str(sandbox.home / "x/Pictures"))
            assert result.returncode == 2
            assert result.stderr == (f"mir: source is not a directory: {sandbox.home}/gone/Pictures\n"
                                     "See 'mir --help'\n")
            assert calls("rsync") == []

        def test_should_exit_2_when_the_destination_is_a_file(self, run, fake_bin, calls, sandbox):
            fake_bin("rsync")
            src, dst = pair(sandbox)
            dst.rmdir()
            dst.write_text("x")
            result = run("mir", str(src), str(dst))
            assert result.returncode == 2
            assert result.stderr == f"mir: destination is an existing file: {dst}\nSee 'mir --help'\n"
            assert calls("rsync") == []

        def test_should_exit_2_when_the_base_names_differ(self, run, fake_bin, calls, sandbox):
            fake_bin("rsync")
            src = sandbox.home / "Pictures"
            src.mkdir()
            result = run("mir", str(src), str(sandbox.home / "Backup/Photos"))
            assert result.returncode == 2
            assert result.stderr == "mir: base names differ: Pictures vs Photos\nSee 'mir --help'\n"
            assert calls("rsync") == []

    class TestOnHelp:
        def test_should_print_the_header(self, run):
            result = run("mir", "--help")
            assert result.returncode == 0
            assert result.stdout.startswith("Purpose: Mirror a directory into another with rsync")
            assert "Usage:   mir [--dry-run] <source-dir> <destination-dir>\n" in result.stdout


def pair(sandbox):
    src, dst = sandbox.home / "src/Pictures", sandbox.home / "dst/Pictures"
    src.mkdir(parents=True)
    dst.mkdir(parents=True)
    return src, dst
