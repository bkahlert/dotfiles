import pytest


class TestUpgradeAll:
    def test_should_run_every_upgrader_and_report_success(self, run, fake_bin, calls):
        tooling(fake_bin)
        result = run("upgrade-all")
        assert result.returncode == 0
        assert result.stdout.endswith("⚙ Summary\n  ✔ all steps succeeded\n")
        assert calls("brew") == [["tap"], ["tap"], ["update"], ["upgrade"],
                                 ["outdated", "--formula", "--quiet"], ["cleanup"]]
        assert calls("mas") == [["upgrade"]]
        assert calls("npm") == [["update", "-g"]]
        assert calls("gh") == [["extension", "upgrade", "--all"]]
        assert calls("softwareupdate") == [["-l"]]

    class TestOnAFailingStep:
        def test_should_continue_and_exit_1_with_the_failures_listed(self, run, fake_bin, calls):
            tooling(fake_bin, brew='[[ $1 == upgrade ]] && exit 1\nexit 0\n', mas=1)
            result = run("upgrade-all")
            assert result.returncode == 1
            assert calls("npm") == [["update", "-g"]]
            assert result.stdout.endswith("⚙ Summary\n  ✘ brew upgrade\n  ✘ mas upgrade\n  ! 2 step(s) failed\n")

    class TestOnHomebrew:
        @pytest.mark.parametrize("failing,listed", [
            ("update", "brew update"),
            ("cleanup", "brew cleanup"),
            ("upgrade --build-from-source", "brew upgrade --build-from-source"),
        ], ids=["update", "cleanup", "build-from-source"])
        def test_should_list_a_failing_brew_step_exit_1_and_carry_on(self, run, fake_bin, calls, failing, listed):
            brew = f'case "$*" in "outdated --formula --quiet") echo foo ;; "{failing}"*) exit 1 ;; esac\nexit 0\n'
            tooling(fake_bin, brew=brew)
            result = run("upgrade-all")
            assert result.returncode == 1
            assert result.stdout.endswith(f"⚙ Summary\n  ✘ {listed}\n  ! 1 step(s) failed\n")
            assert calls("npm") == [["update", "-g"]]
            assert "all steps succeeded" not in result.stdout

        def test_should_untap_a_retired_tap(self, run, fake_bin, calls):
            tooling(fake_bin, brew='case $1 in tap) printf "homebrew/core\\nhomebrew/cask-fonts\\n" ;; esac\nexit 0\n')
            result = run("upgrade-all")
            assert "  ℹ untapping deprecated homebrew/cask-fonts\n" in result.stdout
            assert ["untap", "homebrew/cask-fonts"] in calls("brew")

        def test_should_rebuild_unbottled_formulae_from_source(self, run, fake_bin, calls):
            tooling(fake_bin, brew='case $1 in outdated) printf "foo\\nbar\\n" ;; esac\nexit 0\n')
            result = run("upgrade-all")
            assert "  ℹ rebuilding unbottled formulae from source: foo bar \n" in result.stdout
            assert ["upgrade", "--build-from-source", "foo", "bar"] in calls("brew")

    class TestOnPodmanMachine:
        def test_should_leave_a_machine_on_the_clients_version_alone(self, run, fake_bin, calls):
            tooling(fake_bin, podman=podman(client="5.6.1", server="5.6.0"))
            result = run("upgrade-all")
            assert "  ✔ machine already on podman 5.6.0 (client 5.6.1)\n" in result.stdout
            assert not any(call[:3] == ["machine", "os", "apply"] for call in calls("podman"))

        def test_should_rebase_a_machine_behind_the_client(self, run, fake_bin, calls):
            tooling(fake_bin, podman=podman(client="5.6.1", server="5.5.2"))
            result = run("upgrade-all")
            assert "  ℹ machine on podman 5.5.2, client on 5.6.1 — rebasing\n" in result.stdout
            assert "  ✔ machine rebased to podman 5.6\n" in result.stdout
            assert ["machine", "os", "apply", "quay.io/podman/machine-os:5.6", "--restart"] in calls("podman")

        def test_should_warn_when_the_machine_is_ahead(self, run, fake_bin, calls):
            tooling(fake_bin, podman=podman(client="5.5.1", server="5.6.2"))
            result = run("upgrade-all")
            assert "  ! machine (5.6.2) is ahead of the client (5.5.1) — upgrade the client first\n" in result.stdout
            assert not any(call[:3] == ["machine", "os", "apply"] for call in calls("podman"))

        def test_should_skip_without_a_machine(self, run, fake_bin):
            tooling(fake_bin, podman="exit 1\n")
            result = run("upgrade-all")
            assert "  ▪ no podman machine (create one with: podman machine init)\n" in result.stdout

    class TestOnRubyGems:
        def test_should_update_only_the_gems_outside_rubys_prefix(self, run, fake_bin, calls):
            tooling(fake_bin, gems="foo\nbar\n")
            run("upgrade-all")
            assert calls("gem") == [["update", "foo", "bar"]]

        def test_should_skip_when_only_shipped_gems_exist(self, run, fake_bin, calls):
            tooling(fake_bin, gems="")
            result = run("upgrade-all")
            assert "  ▪ no gems installed besides those shipped with Ruby\n" in result.stdout
            assert calls("gem") == []

    class TestOnAnyArgument:
        def test_should_exit_2(self, run):
            result = run("upgrade-all", "x")
            assert result.returncode == 2
            assert result.stderr == "upgrade-all: unknown argument: x\nSee 'upgrade-all --help'\n"


def tooling(fake_bin, *, brew="exit 0\n", podman="exit 1\n", mas=0, gems=""):
    fake_bin("brew", script=brew)
    fake_bin("podman", script=podman)
    fake_bin("mas", exit_code=mas)
    fake_bin("npm")
    fake_bin("gh")
    fake_bin("softwareupdate", stdout="No new software available.\n")
    fake_bin("gem")
    fake_bin("ruby", stdout=gems)


def podman(*, client, server):
    return "\n".join([
        'case "$*" in',
        '  "machine inspect --format {{.State}}") echo running ;;',
        '  "version --format {{.Client.Version}}") echo ' + client + ' ;;',
        '  "version --format {{.Server.Version}}") echo ' + server + ' ;;',
        "esac", "exit 0", ""])
