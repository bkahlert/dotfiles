import pytest

PREFIX = ["run", "--rm", "-e", "LANG=C.UTF-8"]


class TestBox:
    class TestOnNoCommand:
        def test_should_start_an_interactive_sh_in_alpine(self, run, fake_bin, calls):
            fake_bin("docker")
            result = run("box")
            assert result.returncode == 0
            assert calls("docker") == [[*PREFIX, "-e", "TERM=dumb", "-it", "alpine", "sh"]]

        @pytest.mark.parametrize("image", ["ubuntu", "debian:12", "fedora", "rockylinux", "almalinux"])
        def test_should_start_bash_in_a_distro_image(self, run, fake_bin, calls, image):
            fake_bin("docker")
            run("box", "--image", image)
            assert calls("docker")[0][-2:] == [image, "bash"]

    class TestOnCommand:
        def test_should_run_it_without_a_terminal(self, run, fake_bin, calls):
            fake_bin("docker", stdout="Linux\n", exit_code=3)
            result = run("box", "sh", "-c", "uname -a")
            assert (result.stdout, result.returncode) == ("Linux\n", 3)
            assert calls("docker") == [[*PREFIX, "-e", "TERM=dumb", "alpine", "sh", "-c", "uname -a"]]

        def test_should_pass_dashed_words_after_double_dash_to_the_command(self, run, fake_bin, calls):
            fake_bin("docker")
            run("box", "--", "--here")
            assert calls("docker")[0][-2:] == ["alpine", "--here"]

    class TestOnHere:
        def test_should_mount_the_working_directory_at_the_same_path(self, run, fake_bin, calls, sandbox):
            fake_bin("docker")
            run("box", "--here", "true")
            assert calls("docker") == [
                [*PREFIX, "-e", "TERM=dumb", "-v", f"{sandbox.home}:{sandbox.home}", "-w", str(sandbox.home),
                 "alpine", "true"]]

    class TestOnImage:
        def test_should_accept_the_equals_form(self, run, fake_bin, calls):
            fake_bin("docker")
            run("box", "--image=ubuntu:22.04", "true")
            assert calls("docker")[0][-2:] == ["ubuntu:22.04", "true"]

        def test_should_default_to_box_image(self, run, fake_bin, calls, sandbox):
            fake_bin("docker")
            sandbox.env["BOX_IMAGE"] = "fedora"
            run("box")
            assert calls("docker")[0][-2:] == ["fedora", "bash"]

        def test_should_prefer_the_option_over_box_image(self, run, fake_bin, calls, sandbox):
            fake_bin("docker")
            sandbox.env["BOX_IMAGE"] = "fedora"
            run("box", "--image", "alpine:3", "true")
            assert calls("docker")[0][-2:] == ["alpine:3", "true"]

        def test_should_exit_2_with_a_one_line_hint_on_missing_value(self, run, fake_bin, calls):
            fake_bin("docker")
            result = run("box", "--image")
            assert (result.returncode, result.stdout) == (2, "")
            assert result.stderr == "box: --image: missing value\nSee 'box --help'\n"
            assert calls("docker") == []

    class TestOnUnsetTerm:
        def test_should_run_with_the_dumb_terminal_bash_defaults_to(self, run, fake_bin, calls, sandbox):
            fake_bin("docker")
            del sandbox.env["TERM"]
            result = run("box", "true")
            assert (result.returncode, result.stderr) == (0, "")
            assert calls("docker") == [[*PREFIX, "-e", "TERM=dumb", "alpine", "true"]]

    class TestOnUnknownOption:
        def test_should_exit_2_and_name_the_option(self, run, fake_bin, calls):
            fake_bin("docker")
            result = run("box", "--nope")
            assert result.returncode == 2
            assert result.stderr == "box: unknown option: --nope\nSee 'box --help'\n"
            assert calls("docker") == []

    class TestOnHelp:
        def test_should_print_the_header(self, run):
            result = run("box", "--help")
            assert result.returncode == 0
            assert result.stdout.startswith("Purpose: Run a command (or interactive shell) in a throwaway container.\n")
            assert "--here" in result.stdout
