import os
import shutil
import stat

import pytest

MODULES = ["ista/10-maven-settings-ci-env.zsh"]
SHOW = 'print -r -- "$CAS_ARTIFACTORY_BASE_URL|$CAS_ARTIFACTORY_CI_USER|$CAS_ARTIFACTORY_CI_TOKEN"'
SETTINGS = """\
<settings xmlns="http://maven.apache.org/SETTINGS/1.0.0">
  <servers>
    <server><id>other</id><username>nobody</username><password>nothing</password></server>
    <server><id>cas</id><username>{user}</username><password>{password}</password></server>
  </servers>
  <profiles>
    <profile><id>inactive</id>
      <repositories><repository><id>other</id><url>https://other.example/artifactory/libs</url></repository></repositories>
    </profile>
    <profile><id>ci</id>
      <repositories><repository><id>cas</id><url>https://repo.example/artifactory/libs-release</url></repository></repositories>
    </profile>
  </profiles>
  <activeProfiles>{active}</activeProfiles>
</settings>
"""


@pytest.fixture(autouse=True)
def bare(sandbox):
    sandbox.only_tools("zsh", "python3", "touch")


@pytest.fixture
def settings(sandbox):
    def write(user="deploy", password="s3cret", active="<activeProfile>ci</activeProfile>", raw=None):
        (sandbox.home / ".m2").mkdir(exist_ok=True)
        (sandbox.home / ".m2" / "settings.xml").write_text(
            raw if raw is not None else SETTINGS.format(user=user, password=password, active=active))
    return write


@pytest.fixture
def python_calls(fake_bin, calls):
    fake_bin("python3", script=f'exec {shutil.which("python3")} "$@"\n')
    return lambda: calls("python3")


class TestMavenSettingsCiEnv:
    class TestOnNoSettingsFile:
        def test_should_stay_silent_and_export_nothing(self, zsh):
            result = zsh(SHOW, modules=MODULES)
            assert (result.returncode, result.stdout, result.stderr) == (0, "||\n", "")

    class TestOnActiveProfile:
        def test_should_export_the_repository_base_url_and_the_credentials_of_its_server(self, zsh, settings):
            settings()
            result = zsh(SHOW, modules=MODULES)
            assert (result.stdout, result.stderr) == ("https://repo.example/artifactory|deploy|s3cret\n", "")

        @pytest.mark.parametrize("password", ['a"b', "a$HOME", "a`id`b", "a\\b", "a b'c", "a;echo pwned"])
        def test_should_export_a_password_exactly_as_written(self, zsh, settings, password):
            settings(password=password)
            result = zsh(SHOW, modules=MODULES)
            assert (result.stdout, result.stderr) == (f"https://repo.example/artifactory|deploy|{password}\n", "")

        @pytest.mark.parametrize("password", ['a"b', "a$HOME", "a b'c"])
        def test_should_export_a_password_exactly_as_written_from_the_cache(self, zsh, settings, password):
            settings(password=password)
            zsh("true", modules=MODULES)
            result = zsh(SHOW, modules=MODULES)
            assert (result.stdout, result.stderr) == (f"https://repo.example/artifactory|deploy|{password}\n", "")

        def test_should_not_run_anything_a_password_contains(self, zsh, settings, sandbox):
            settings(password="x$(touch pwned)")
            zsh("true", modules=MODULES)
            zsh("true", modules=MODULES)
            assert not (sandbox.home / "pwned").exists()

    class TestOnNoActiveProfile:
        def test_should_stay_silent_and_export_nothing(self, zsh, settings):
            settings(active="")
            result = zsh(SHOW, modules=MODULES)
            assert (result.returncode, result.stdout, result.stderr) == (0, "||\n", "")

    class TestOnVariablesAlreadySet:
        def test_should_leave_them_alone(self, zsh, settings, sandbox):
            settings()
            sandbox.env.update(CAS_ARTIFACTORY_BASE_URL="https://ci.example", CAS_ARTIFACTORY_CI_USER="ci",
                               CAS_ARTIFACTORY_CI_TOKEN="from-ci")
            result = zsh(SHOW, modules=MODULES)
            assert (result.stdout, result.stderr) == ("https://ci.example|ci|from-ci\n", "")

    class TestOnUnusableSettings:
        @pytest.mark.parametrize("settings_args, complaint", [
            ({"raw": "<settings>"}, "failed to parse"),
            ({"active": "<activeProfile>gone</activeProfile>"}, 'profile "gone" not found'),
        ])
        def test_should_warn_and_export_nothing(self, zsh, settings, settings_args, complaint):
            settings(**settings_args)
            result = zsh(SHOW, modules=MODULES)
            assert (result.returncode, result.stdout) == (0, "||\n")
            assert "artifactory: " in result.stderr and complaint in result.stderr

        def test_should_warn_in_every_shell(self, zsh, settings):
            settings(active="<activeProfile>gone</activeProfile>")
            assert all("not found" in zsh("true", modules=MODULES).stderr for _ in range(2))

    class TestOnSecondShell:
        def test_should_export_the_same_values_without_running_python_again(self, zsh, settings, python_calls):
            settings()
            results = [zsh(SHOW, modules=MODULES) for _ in range(2)]
            assert [(r.stdout, r.stderr) for r in results] == [("https://repo.example/artifactory|deploy|s3cret\n", "")] * 2
            assert len(python_calls()) == 1

        def test_should_not_run_python_again_on_no_active_profile(self, zsh, settings, python_calls):
            settings(active="")
            for _ in range(2):
                zsh("true", modules=MODULES)
            assert len(python_calls()) == 1

        def test_should_read_a_changed_settings_file_anew(self, zsh, settings, sandbox, python_calls):
            settings()
            zsh("true", modules=MODULES)
            settings(password="rotated")
            file = sandbox.home / ".m2" / "settings.xml"
            os.utime(file, (1, file.stat().st_mtime + 10))
            result = zsh(SHOW, modules=MODULES)
            assert (result.stdout, result.stderr) == ("https://repo.example/artifactory|deploy|rotated\n", "")
            assert len(python_calls()) == 2

        def test_should_keep_the_cached_credentials_readable_by_the_owner_only(self, zsh, settings, sandbox):
            settings()
            zsh("true", modules=MODULES)
            cached = [f for f in (sandbox.home / ".cache").rglob("*") if f.is_file()]
            assert [stat.S_IMODE(f.stat().st_mode) for f in cached] == [0o600]
