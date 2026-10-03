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

        def test_should_not_run_anything_a_password_contains(self, zsh, settings, sandbox):
            settings(password="x$(touch pwned)")
            zsh("true", modules=MODULES)
            assert not (sandbox.home / "pwned").exists()

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
            ({"active": ""}, "no activeProfile"),
            ({"active": "<activeProfile>gone</activeProfile>"}, 'profile "gone" not found'),
        ])
        def test_should_warn_and_export_nothing(self, zsh, settings, settings_args, complaint):
            settings(**settings_args)
            result = zsh(SHOW, modules=MODULES)
            assert (result.returncode, result.stdout) == (0, "||\n")
            assert "artifactory: " in result.stderr and complaint in result.stderr

        def test_should_warn_in_every_shell(self, zsh, settings):
            settings(active="")
            assert all("no activeProfile" in zsh("true", modules=MODULES).stderr for _ in range(2))
