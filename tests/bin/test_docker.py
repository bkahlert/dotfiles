import shutil

import pytest

from repo import BIN_SOURCE


@pytest.fixture
def wrapper(tmp_path):
    own = tmp_path / "own"
    own.mkdir()
    (own / "docker").symlink_to(BIN_SOURCE / "executable_docker")
    return own / "docker"


@pytest.fixture
def bare_path(tmp_path, sandbox, wrapper):
    tools = tmp_path / "tools"
    tools.mkdir()
    for name in ("env", "bash", "dirname"):
        (tools / name).symlink_to(shutil.which(name))
    sandbox.env["PATH"] = f"{wrapper.parent}:{tools}"
    return sandbox.env["PATH"]


class TestDocker:
    class TestOnDockerInstalled:
        def test_should_run_it_with_all_arguments_and_its_exit_code(self, run, fake_bin, calls, wrapper, sandbox):
            fake_bin("docker", stdout="ok\n", exit_code=3)
            fake_bin("podman")
            sandbox.env["PATH"] = f"{wrapper.parent}:{sandbox.env['PATH']}"
            result = run(str(wrapper), "run", "--rm", "alpine", "echo", "hi there")
            assert (result.stdout, result.returncode) == ("ok\n", 3)
            assert calls("docker") == [["run", "--rm", "alpine", "echo", "hi there"]]
            assert calls("podman") == []

    class TestOnlyPodmanInstalled:
        def test_should_fall_back_to_podman(self, run, fake_bin, calls, wrapper, sandbox, bare_path):
            fake_bin("podman", stdout="from podman\n")
            sandbox.env["PATH"] = f"{bare_path}:{sandbox.fakes}"
            result = run(str(wrapper), "ps", "-a")
            assert (result.stdout, result.returncode) == ("from podman\n", 0)
            assert calls("podman") == [["ps", "-a"]]

    class TestOnNeitherInstalled:
        def test_should_exit_127_instead_of_calling_itself_again(self, run, wrapper, bare_path):
            result = run(str(wrapper), "ps")
            assert (result.returncode, result.stdout) == (127, "")
            assert result.stderr == "docker: neither docker nor podman found on PATH\n"
