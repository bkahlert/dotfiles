import pytest

# fnm as far as the script needs it: `default` prints the default version or fails without one, and like the real
# one, the first `install` makes its version the default.
FNM = """\
case $1 in
  default) if [[ -f $HOME/fnm-default ]]; then cat "$HOME/fnm-default"; else exit 1; fi ;;
  install) [[ -f $HOME/fnm-default ]] || echo v24.21.0 > "$HOME/fnm-default" ;;
esac
"""


@pytest.fixture(autouse=True)
def fnm(sandbox):
    sandbox.only_tools("cat")
    sandbox.fake_bin("fnm", script=FNM)


class TestInstallNode:
    class TestOnFreshMachine:
        def test_should_install_the_latest_lts_as_the_default(self, script, calls):
            result = script("install-node")
            assert (result.returncode, result.stdout) == (0, ""), result.stderr
            assert calls("fnm") == [["default"], ["install", "--lts"]]

    class TestOnExistingDefault:
        def test_should_install_nothing(self, script, sandbox, calls):
            (sandbox.home / "fnm-default").write_text("v22.23.3\n")
            result = script("install-node")
            assert (result.returncode, calls("fnm")) == (0, [["default"]])

    class TestOnMissingFnm:
        def test_should_fail_and_name_the_script_that_installs_it(self, script, sandbox, tmp_path):
            (sandbox.fakes / "fnm").unlink()
            result = script("install-node", prefix_root=tmp_path)
            assert result.returncode == 1
            assert result.stderr == "fnm not found; run_once_before_01-install-packages installs it\n"

    class TestOnNvmUsedBefore:
        @pytest.mark.parametrize(("nvm_default", "installed"), [("22", "22"), ("v22.22.0", "22.22.0"),
                                                                ("lts/*", "--lts"), ("node", "--lts")])
        def test_should_install_a_numbered_default_of_nvm_and_the_latest_lts_otherwise(
                self, script, nvm, calls, nvm_default, installed):
            nvm(default=nvm_default)
            result = script("install-node")
            assert result.returncode == 0, result.stderr
            assert calls("fnm")[1] == ["install", installed]

        def test_should_say_what_is_left_to_do_by_hand(self, script, nvm, sandbox):
            nvm_dir = nvm(default="22", packages={"v16.20.0": ["aws-cdk", "@scope/tool", "@empty"],
                                                  "v22.22.0": ["openclaw"]})
            result = script("install-node")
            assert result.stdout == (
                f"\nNode.js now comes from fnm (default v24.21.0); nvm in {nvm_dir} is no longer used. To finish:\n"
                "  npm install -g @scope/tool aws-cdk   # global packages of nvm's v16.20.0, if still needed\n"
                "  npm install -g openclaw   # global packages of nvm's v22.22.0, if still needed\n"
                f"  rm -rf {nvm_dir}\n\n")

        def test_should_name_brew_for_a_homebrew_nvm(self, script, nvm, tmp_path):
            nvm_dir = nvm(default="22")
            (nvm_dir / "nvm.sh").symlink_to(tmp_path / "homebrew-nvm.sh")
            result = script("install-node")
            assert "\n  brew uninstall nvm\n" in result.stdout

        def test_should_leave_nvm_in_place(self, script, nvm):
            nvm_dir = nvm(default="22")
            script("install-node")
            assert (nvm_dir / "alias" / "default").read_text() == "22\n"


@pytest.fixture
def nvm(sandbox):
    """Builds ~/.nvm with a default alias and, per version, global packages beside npm and corepack."""
    def build(*, default, packages=None):
        nvm_dir = sandbox.home / ".nvm"
        (nvm_dir / "alias").mkdir(parents=True)
        (nvm_dir / "alias" / "default").write_text(f"{default}\n")
        for version, names in (packages or {}).items():
            for name in ["npm", "corepack", *names]:
                (nvm_dir / "versions" / "node" / version / "lib" / "node_modules" / name).mkdir(parents=True)
        return nvm_dir
    return build
