class TestDscleanup:
    def test_should_delete_nested_ds_store_files_and_keep_everything_else(self, run, sandbox):
        tree = sandbox.home / "tree"
        (tree / "a/b").mkdir(parents=True)
        for path in (tree / ".DS_Store", tree / "a/b/.DS_Store"):
            path.write_text("x")
        keep = [tree / "a/file.txt", tree / "a/b/.DS_Store.bak", tree / "a/.hidden"]
        for path in keep:
            path.write_text("x")
        result = run("dscleanup", str(tree))
        assert result.returncode == 0
        assert sorted(p.name for p in tree.rglob("*") if p.is_file()) == sorted(p.name for p in keep)

    def test_should_clean_the_current_directory_without_arguments(self, run, sandbox):
        (sandbox.home / ".DS_Store").write_text("x")
        run("dscleanup")
        assert not (sandbox.home / ".DS_Store").exists()

    def test_should_clean_every_path_given(self, run, sandbox):
        first, second = sandbox.home / "one", sandbox.home / "two"
        for directory in (first, second):
            directory.mkdir()
            (directory / ".DS_Store").write_text("x")
        run("dscleanup", str(first), str(second))
        assert [(first / ".DS_Store").exists(), (second / ".DS_Store").exists()] == [False, False]

    def test_should_leave_a_directory_named_ds_store_alone(self, run, sandbox):
        directory = sandbox.home / ".DS_Store"
        directory.mkdir()
        run("dscleanup")
        assert directory.is_dir()

    class TestOnMissingPath:
        def test_should_fail_and_name_the_path(self, run, sandbox):
            result = run("dscleanup", "nowhere")
            assert result.returncode == 1
            assert "nowhere" in result.stderr

    class TestOnHelp:
        def test_should_print_the_header(self, run):
            result = run("dscleanup", "--help")
            assert result.returncode == 0
            assert result.stdout.startswith("Purpose: Recursively delete .DS_Store files.\nUsage:   dscleanup [<path>...]\n")

    class TestOnUnknownOption:
        def test_should_exit_2_and_name_the_option(self, run):
            result = run("dscleanup", "--nope")
            assert result.returncode == 2
            assert result.stderr == "dscleanup: unknown option: --nope\nSee 'dscleanup --help'\n"

    class TestOnDoubleDash:
        def test_should_treat_a_dashed_name_as_a_path(self, run, sandbox):
            directory = sandbox.home / "-odd"
            directory.mkdir()
            (directory / ".DS_Store").write_text("x")
            result = run("dscleanup", "--", "./-odd")
            assert result.returncode == 0
            assert not (directory / ".DS_Store").exists()
