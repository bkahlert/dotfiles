from repo import BIN_SOURCE, HOME_SOURCE

INIT_SCRIPT = "gradle-updates/gradle-versions-plugin.init.gradle.kts"


class TestGradleUpdates:
    def test_should_run_the_dependency_updates_task_with_the_init_script(self, run, sandbox, fake_bin, calls):
        fake_bin("gradle")
        result = run("gradle-updates")
        assert result.returncode == 0
        assert calls("gradle") == [["dependencyUpdates", "--init-script",
                                    str(sandbox.home / ".local/share" / INIT_SCRIPT)]]

    def test_should_ship_the_init_script_it_points_at(self):
        assert (HOME_SOURCE / "dot_local/share" / INIT_SCRIPT).is_file()

    def test_should_pass_every_argument_on_to_gradle(self, run, sandbox, fake_bin, calls):
        fake_bin("gradle")
        run("gradle-updates", "--refresh-dependencies", "-q")
        assert calls("gradle")[0][-2:] == ["--refresh-dependencies", "-q"]

    def test_should_exit_with_the_status_of_gradle(self, run, fake_bin):
        fake_bin("gradle", exit_code=3)
        assert run("gradle-updates").returncode == 3

    class TestOnGradlewInTheCurrentDirectory:
        def test_should_prefer_it_over_the_system_gradle(self, run, sandbox, fake_bin, calls):
            fake_bin("gradle")
            gradlew = sandbox.home / "gradlew"
            gradlew.write_text("#!/usr/bin/env bash\nprintf '%s\\n' \"$@\"\n")
            gradlew.chmod(0o755)
            result = run("gradle-updates", "-q")
            assert result.stdout.splitlines() == ["dependencyUpdates", "--init-script",
                                                  str(sandbox.home / ".local/share" / INIT_SCRIPT), "-q"]
            assert calls("gradle") == []

        def test_should_ignore_one_that_is_not_executable(self, run, sandbox, fake_bin, calls):
            fake_bin("gradle")
            (sandbox.home / "gradlew").write_text("#!/usr/bin/env bash\nexit 9\n")
            assert run("gradle-updates").returncode == 0
            assert len(calls("gradle")) == 1

    class TestOnNeitherGradlewNorGradle:
        def test_should_exit_1_and_say_so(self, run, sandbox):
            result = run("env", "PATH=/usr/bin:/bin", str(BIN_SOURCE / "executable_gradle-updates"))
            assert (result.returncode, result.stderr) == (1, "gradle-updates: neither ./gradlew nor gradle found\n")

    class TestOnHelp:
        def test_should_print_the_header_without_running_gradle(self, run, fake_bin, calls):
            fake_bin("gradle")
            result = run("gradle-updates", "--help")
            assert result.returncode == 0
            assert result.stdout.startswith("Purpose: List the dependency updates")
            assert calls("gradle") == []
