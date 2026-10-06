import json
import shutil
import subprocess
import sys

import pytest

from repo import HOME_SOURCE, SHIMS, SYSTEM_PATH, isolated_env

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(sys.platform != "darwin", reason="native apply targets macOS"),
]

CORE_TOOLS = ("chezmoi", "sheldon", "starship", "zoxide")
CHEZMOI_CONFIG = '[data]\n    email = "test@example.com"\n    name = "Test User"\n'


@pytest.fixture(scope="module")
def core_tools():
    missing = [tool for tool in CORE_TOOLS if shutil.which(tool) is None]
    if missing:
        pytest.fail(f"missing on PATH: {' '.join(missing)}; brew install {' '.join(missing)}")


class TestApplyNatively:
    def test_should_apply_and_start_a_silent_interactive_login_shell(self, core_tools, tmp_path):
        home = tmp_path / "home"
        # The container leg starts the shell under the same terminal; isolated_env's dumb one is for unit tests.
        env = {**isolated_env(home, [str(SHIMS), *SYSTEM_PATH]), "TERM": "xterm-256color"}
        seen = chezmoi("data", "--format", "json", env=env)
        assert json.loads(seen.stdout)["chezmoi"]["homeDir"] == str(home), "chezmoi does not see the temp home; refusing to apply"

        (home / ".config" / "chezmoi").mkdir(parents=True)
        (home / ".config" / "chezmoi" / "chezmoi.toml").write_text(CHEZMOI_CONFIG)
        applied = chezmoi("init", "--apply", "--exclude=scripts", "--no-tty", env=env, stdin="dummy-password\n")
        assert applied.returncode == 0, report("apply failed", applied)
        locked = subprocess.run(["sheldon", "lock"], env=env, capture_output=True, text=True, timeout=600)
        assert locked.returncode == 0, report("sheldon lock failed", locked)

        shell = subprocess.run(["zsh", "-li", "-c", "true"], env=env, stdin=subprocess.DEVNULL,
                               capture_output=True, text=True, timeout=120)
        assert shell.returncode == 0, report("shell failed", shell)
        assert shell.stderr == "", report("zsh startup wrote to stderr", shell)


def chezmoi(*args, env, stdin=None):
    return subprocess.run(["chezmoi", *args, "--source", str(HOME_SOURCE)], env=env, input=stdin,
                          capture_output=True, text=True, timeout=600)


def report(headline, result):
    return f"{headline} (exit {result.returncode})\n--- stdout ---\n{result.stdout}\n--- stderr ---\n{result.stderr}"
