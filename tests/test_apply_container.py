import pytest

from integration import test_apply_container as apply_container
from repo import ROOT


class TestApplyContainer:
    class TestOnImageBuild:
        @pytest.mark.parametrize("engine", ["docker", "podman"])
        def test_should_select_the_repository_containerfile(self, engine, monkeypatch, sandbox, fake_bin, calls):
            fake_bin(engine)
            monkeypatch.setattr(apply_container, "ENGINE", engine)
            monkeypatch.setenv("PATH", sandbox.env["PATH"])

            result = apply_container.image.__wrapped__()

            assert result == "dotfiles-test:base"
            assert calls(engine) == [
                ["build", "--target", "base", "-f", str(ROOT / "tests" / "harness" / "container" / "Containerfile"),
                 "-t", "dotfiles-test:base", str(ROOT)]
            ]
