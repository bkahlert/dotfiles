import pytest

MODULES = ["10-gcloud-sdk.zsh"]
START_PATH = "/usr/bin:/bin"
SHOW = 'print -r -- "${path[1]}"\nprint -r -- "${GCLOUD_COMPLETION_FROM-none}"'


@pytest.fixture(autouse=True)
def bare(sandbox):
    sandbox.only_tools("zsh")
    sandbox.env["PATH"] += f":{START_PATH}"


@pytest.fixture
def sdk(sandbox):
    """An SDK directory as Google's installer leaves it: two files to source, which put its bin on PATH and register completion."""
    def install(directory, *, completion=True):
        directory.mkdir(parents=True)
        (directory / "path.zsh.inc").write_text(f'export PATH="{directory}/bin:$PATH"\n')
        if completion:
            (directory / "completion.zsh.inc").write_text(f'export GCLOUD_COMPLETION_FROM="{directory}"\n')
        return directory
    return install


def brew_sdk(sandbox, fake_bin, sdk, **kwargs):
    prefix = sandbox.home / "prefix"
    fake_bin("brew", stdout=str(prefix))
    return sdk(prefix / "share" / "google-cloud-sdk", **kwargs)


class TestGcloudSdk:
    class TestOnTarballInstall:
        def test_should_put_its_bin_directory_on_the_path_and_register_completion(self, zsh, sandbox, sdk):
            (sandbox.fakes / "brew").unlink()
            home_sdk = sdk(sandbox.home / "google-cloud-sdk")
            result = zsh(SHOW, modules=MODULES)
            assert (result.stdout, result.stderr) == (f"{home_sdk}/bin\n{home_sdk}\n", "")

        def test_should_work_without_a_completion_file(self, zsh, sandbox, sdk):
            (sandbox.fakes / "brew").unlink()
            home_sdk = sdk(sandbox.home / "google-cloud-sdk", completion=False)
            result = zsh(SHOW, modules=MODULES)
            assert (result.stdout, result.stderr) == (f"{home_sdk}/bin\nnone\n", "")

    class TestOnHomebrewInstall:
        def test_should_put_its_bin_directory_on_the_path_and_register_completion(self, zsh, sandbox, fake_bin, sdk):
            brewed = brew_sdk(sandbox, fake_bin, sdk)
            result = zsh(SHOW, modules=MODULES)
            assert (result.stdout, result.stderr) == (f"{brewed}/bin\n{brewed}\n", "")

    class TestOnBothInstalls:
        def test_should_use_the_tarball_only(self, zsh, sandbox, fake_bin, sdk):
            brew_sdk(sandbox, fake_bin, sdk)
            home_sdk = sdk(sandbox.home / "google-cloud-sdk")
            result = zsh('print -rl -- ${(M)path:#*google-cloud-sdk/bin}\nprint -r -- "$GCLOUD_COMPLETION_FROM"', modules=MODULES)
            assert (result.stdout, result.stderr) == (f"{home_sdk}/bin\n{home_sdk}\n", "")

    class TestOnNoInstall:
        def test_should_leave_the_path_alone_and_stay_silent(self, zsh, sandbox, fake_bin):
            fake_bin("brew", stdout=str(sandbox.home / "prefix"))
            result = zsh('print -r -- "${path[1]}"', modules=MODULES)
            assert (result.stdout, result.stderr) == (f"{sandbox.fakes}\n", "")

        def test_should_not_ask_brew_when_there_is_none(self, zsh, sandbox):
            (sandbox.fakes / "brew").unlink()
            result = zsh('print -r -- "${path[1]}"', modules=MODULES)
            assert (result.stdout, result.stderr) == (f"{sandbox.fakes}\n", "")

    def test_should_not_leave_its_helper_variables_behind(self, zsh, sandbox, sdk):
        (sandbox.fakes / "brew").unlink()
        sdk(sandbox.home / "google-cloud-sdk")
        result = zsh('print -r -- ${(M)${(k)parameters}:#_gcloud*}', modules=MODULES)
        assert (result.stdout, result.stderr) == ("\n", "")
