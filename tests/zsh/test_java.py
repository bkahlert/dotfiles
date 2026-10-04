import shlex

import pytest

from repo import module_path

# Both lines of output: the variable in the shell, and as a child process sees it.
SHOW = 'print -r -- "${JAVA_HOME-unset}"\nzsh -fc \'print -r -- "${JAVA_HOME-unset}"\''
BREW_JDK = "opt/openjdk/libexec/openjdk.jdk/Contents/Home"


@pytest.fixture(autouse=True)
def bare(sandbox):
    sandbox.only_tools("zsh")


@pytest.fixture
def jdk(sandbox):
    def make(*parts):
        home = sandbox.home.joinpath(*parts)
        (home / "bin").mkdir(parents=True)
        (home / "bin" / "java").write_text("")
        (home / "bin" / "java").chmod(0o755)
        return str(home)
    return make


@pytest.fixture
def start(zsh):
    def run(*, ostype="darwin24.0", java_home=None):
        """Source the module on a shell of the given OSTYPE; java_home is what /usr/libexec/java_home prints, or None if it fails."""
        answer = f"echo {shlex.quote(java_home)}" if java_home else "return 1"
        return zsh("\n".join([
            f"OSTYPE={ostype}",
            f"function /usr/libexec/java_home() {{ {answer} }}",
            f"source {shlex.quote(str(module_path('10-java.zsh')))}",
            SHOW]))
    return run


def installed_brew_jdk(sandbox, jdk):
    sandbox.env["HOMEBREW_PREFIX"] = str(sandbox.home / "prefix")
    return jdk("prefix", *BREW_JDK.split("/"))


class TestJava:
    class TestOnLinux:
        def test_should_leave_an_existing_java_home_alone(self, start, sandbox, jdk):
            sandbox.env["JAVA_HOME"] = str(sandbox.home / "deleted-jdk")
            result = start(ostype="linux-gnu", java_home=jdk("system"))
            assert result.stdout == f"{sandbox.home}/deleted-jdk\n" * 2

        def test_should_not_set_java_home(self, start, sandbox, jdk):
            installed_brew_jdk(sandbox, jdk)
            result = start(ostype="linux-gnu", java_home=jdk("system"))
            assert result.stdout == "unset\nunset\n"

    class TestOnMacOS:
        class TestOnWorkingJavaHome:
            def test_should_keep_it_over_the_homebrew_jdk_without_asking_brew(self, start, sandbox, jdk, calls):
                installed_brew_jdk(sandbox, jdk)
                sandbox.env["JAVA_HOME"] = jdk("mine")
                result = start(java_home=jdk("system"))
                assert (result.stdout, result.stderr, calls("brew")) == (f"{sandbox.home}/mine\n" * 2, "", [])

        class TestOnHomebrewJdk:
            def test_should_export_it(self, start, sandbox, jdk):
                brew_jdk = installed_brew_jdk(sandbox, jdk)
                result = start()
                assert (result.stdout, result.stderr) == (f"{brew_jdk}\n" * 2, "")

            def test_should_not_fork_brew_for_the_prefix(self, start, sandbox, jdk, calls):
                installed_brew_jdk(sandbox, jdk)
                start()
                assert calls("brew") == []

            def test_should_prefer_it_to_java_home(self, start, sandbox, jdk):
                brew_jdk = installed_brew_jdk(sandbox, jdk)
                result = start(java_home=jdk("system"))
                assert result.stdout == f"{brew_jdk}\n" * 2

        class TestOnNoHomebrewJdk:
            def test_should_export_what_java_home_finds_when_homebrew_has_no_openjdk(self, start, sandbox, jdk):
                sandbox.env["HOMEBREW_PREFIX"] = str(sandbox.home / "prefix")
                result = start(java_home=jdk("system"))
                assert (result.stdout, result.stderr) == (f"{sandbox.home}/system\n" * 2, "")

            def test_should_export_what_java_home_finds_on_unset_homebrew_prefix_without_forking_brew(self, start, sandbox, jdk, calls):
                result = start(java_home=jdk("system"))
                assert (result.stdout, result.stderr, calls("brew")) == (f"{sandbox.home}/system\n" * 2, "", [])

        class TestOnNoJdk:
            def test_should_export_nothing_and_stay_silent(self, start, sandbox):
                (sandbox.fakes / "brew").unlink()
                result = start()
                assert (result.stdout.splitlines()[-1], result.stderr) == ("unset", "")

        class TestOnStaleJavaHome:
            def test_should_replace_it_with_the_jdk_java_home_finds(self, start, sandbox, jdk):
                (sandbox.fakes / "brew").unlink()
                sandbox.env["JAVA_HOME"] = str(sandbox.home / "deleted-jdk")
                result = start(java_home=jdk("system"))
                assert result.stdout == f"{sandbox.home}/system\n" * 2

            def test_should_not_hand_the_stale_value_on_when_no_jdk_exists(self, start, sandbox):
                (sandbox.fakes / "brew").unlink()
                sandbox.env["JAVA_HOME"] = str(sandbox.home / "deleted-jdk")
                result = start()
                assert result.stdout.splitlines()[-1] == "unset"
