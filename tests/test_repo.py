import pytest

from repo import require_chezmoi


class TestRequireChezmoi:
    def test_should_return_the_path_of_chezmoi_on_the_path(self, tmp_path, monkeypatch):
        chezmoi = tmp_path / "chezmoi"
        chezmoi.write_text("#!/bin/sh\n")
        chezmoi.chmod(0o755)
        monkeypatch.setenv("PATH", str(tmp_path))
        monkeypatch.setenv("CI", "true")
        assert require_chezmoi() == str(chezmoi)

    class TestOnMissingChezmoi:
        @pytest.fixture(autouse=True)
        def without_chezmoi(self, tmp_path, monkeypatch):
            monkeypatch.setenv("PATH", str(tmp_path))

        def test_should_skip_outside_ci(self, monkeypatch):
            monkeypatch.delenv("CI", raising=False)
            with pytest.raises(pytest.skip.Exception, match="chezmoi is not installed"):
                require_chezmoi()

        def test_should_fail_on_ci(self, monkeypatch):
            monkeypatch.setenv("CI", "true")
            with pytest.raises(pytest.fail.Exception, match="chezmoi is not installed"):
                require_chezmoi()

        def test_should_skip_on_an_empty_ci_variable(self, monkeypatch):
            monkeypatch.setenv("CI", "")
            with pytest.raises(pytest.skip.Exception):
                require_chezmoi()
