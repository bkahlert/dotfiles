from itertools import combinations

import pytest

CLIS = {"claude": "claude-code", "gemini": "gemini-cli", "copilot": "github-copilot"}
CLI_COMBINATIONS = [clis for size in range(4) for clis in combinations(CLIS, size)]
SKILLS = ("grill-me", "grilling", "handoff")
# `fnm env` as far as the script needs it: it puts the default Node.js's bin on PATH.
FNM_ENV = 'export PATH="$HOME/node/bin:$PATH"'


@pytest.fixture(autouse=True)
def fnm(sandbox):
    sandbox.fake_bin("fnm", stdout=FNM_ENV)


@pytest.fixture
def script(script, tmp_path):
    def run(key, **kwargs):
        kwargs.setdefault("prefix_root", tmp_path)
        return script(key, **kwargs)
    return run


class TestSetupSkills:
    class TestOnAvailableClis:
        @pytest.mark.parametrize("clis", CLI_COMBINATIONS)
        @pytest.mark.parametrize("company", ["", "bkahlert", "ista", "other"])
        def test_should_install_for_every_detected_agent_independent_of_company(
                self, script, fake_bin, calls, company, clis):
            for cli in clis:
                fake_bin(cli)
            fake_bin("npx")
            result = script("setup-skills", company=company)
            assert result.returncode == 0, result.stderr
            expected = [(skill, [CLIS[cli] for cli in clis]) for skill in SKILLS] if clis else []
            assert installs(calls("npx")) == expected
            for cli in clis:
                assert calls(cli) == []

        def test_should_need_no_node_when_no_cli_is_available(self, script, sandbox, calls):
            (sandbox.fakes / "fnm").unlink()
            result = script("setup-skills")
            assert result.returncode == 0, result.stderr
            assert calls("npx") == []

        @pytest.mark.parametrize("prefix", ["/opt/homebrew", "/usr/local", ".local"])
        def test_should_detect_clis_in_install_locations_off_path(self, script, sandbox, calls, tmp_path, prefix):
            bin_dir = (sandbox.home / prefix if prefix == ".local" else tmp_path / prefix.lstrip("/")) / "bin"
            bin_dir.mkdir(parents=True)
            for cli in CLIS:
                (bin_dir / cli).write_text("#!/bin/sh\nexit 0\n")
                (bin_dir / cli).chmod(0o755)
            sandbox.fake_bin("npx")
            result = script("setup-skills")
            assert result.returncode == 0, result.stderr
            assert installs(calls("npx")) == [(skill, list(CLIS.values())) for skill in SKILLS]

    class TestOnFailedInstall:
        def test_should_fail_and_not_go_on(self, script, fake_bin, calls):
            fake_bin("claude")
            fake_bin("npx", exit_code=1)
            result = script("setup-skills")
            assert result.returncode == 1
            assert len(calls("npx")) == 1

    class TestOnNodeFromFnm:
        def test_should_run_the_npx_of_fnm_s_default_node(self, script, sandbox, calls):
            sandbox.only_tools()
            node_bin = sandbox.home / "node" / "bin"
            node_bin.mkdir(parents=True)
            (node_bin / "npx").write_text('#!/bin/sh\necho "$*" >> "$HOME/npx-calls"\n')
            (node_bin / "npx").chmod(0o755)
            (node_bin / "gemini").write_text("#!/bin/sh\nexit 0\n")
            (node_bin / "gemini").chmod(0o755)
            result = script("setup-skills")
            assert result.returncode == 0, result.stderr
            npx_calls = (sandbox.home / "npx-calls").read_text().splitlines()
            assert len(npx_calls) == len(SKILLS)
            assert all("--agent gemini-cli -y" in call for call in npx_calls)
            assert calls("fnm") == [["env", "--shell", "bash"]]

        def test_should_fail_when_fnm_cannot_initialize(self, script, fake_bin, calls):
            fake_bin("fnm", stderr="fnm failed\n", exit_code=3)
            fake_bin("claude")
            result = script("setup-skills")
            assert result.returncode == 3
            assert result.stderr == "fnm failed\n"
            assert calls("npx") == []

    class TestOnMissingFnm:
        @pytest.mark.parametrize("cli", CLIS)
        def test_should_fail_and_name_the_script_that_installs_it(self, script, fake_bin, calls, sandbox, cli):
            fake_bin(cli)
            fake_bin("npx")
            (sandbox.fakes / "fnm").unlink()
            result = script("setup-skills")
            assert (result.returncode, calls("npx")) == (1, [])
            assert result.stderr == "fnm not found; run_once_before_01-install-packages installs it\n"


def installs(npx_calls):
    return [(call[4].partition("#")[0].rsplit("/", 1)[-1], call[call.index("--agent") + 1:-1]) for call in npx_calls]
