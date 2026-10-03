import os
import shutil
import subprocess

import pytest

from repo import CONTEXTS, ROOT, SHIMS

pytestmark = pytest.mark.integration

ENGINE = os.environ.get("CONTAINER_ENGINE", "podman")
IMAGE = "dotfiles-test:base"


@pytest.fixture(scope="module")
def image():
    if shutil.which(ENGINE) is None:
        pytest.fail(f"{ENGINE} not found; install it or point CONTAINER_ENGINE at docker")
    subprocess.run([ENGINE, "build", "--target", "base", "-t", IMAGE, str(ROOT)], check=True, timeout=1200)
    return IMAGE


class TestApplyInContainer:
    @pytest.mark.parametrize("company", CONTEXTS, ids=lambda c: c or "none")
    def test_should_apply_and_start_a_silent_interactive_login_shell(self, image, company):
        result = subprocess.run(
            [ENGINE, "run", "--rm", "-i",
             "-e", "TERM=xterm-256color", "-e", f"DOTFILES_COMPANY={company}",
             "-v", f"{ROOT}:/dotfiles:ro", "-v", f"{SHIMS}:/opt/shims:ro",
             image, "-c", "true"],
            input="dummy-password\n", capture_output=True, text=True, timeout=900)
        assert result.returncode == 0, report("apply or shell failed", result)
        assert result.stderr == "", report("zsh startup wrote to stderr", result)


def report(headline, result):
    return f"{headline} (exit {result.returncode})\n--- stdout ---\n{result.stdout}\n--- stderr ---\n{result.stderr}"
