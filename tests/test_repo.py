from pathlib import Path

import pytest

import repo
from repo import require_chezmoi


class TestRepositoryPaths:
    def test_should_resolve_the_repository_root_from_harness(self):
        assert repo.ROOT == Path(__file__).resolve().parents[1]
        assert Path(repo.__file__).resolve() == repo.ROOT / "tests" / "harness" / "repo.py"


class TestBrewfileEntries:
    def test_should_ignore_blank_lines_and_standalone_comments(self, monkeypatch):
        monkeypatch.setattr(repo, "brewfile_lines", lambda: [
            "",
            " \t",
            "# Creative apps",
            '  # Includes "Craft" apps',
            'brew "uv" # Python package manager',
            'cask "artcraft" # Creative studio',
        ])

        result = repo.brewfile_entries()

        assert result == [
            'brew "uv" # Python package manager',
            'cask "artcraft" # Creative studio',
        ]

    def test_should_keep_invalid_lines_for_validation(self, monkeypatch):
        monkeypatch.setattr(repo, "brewfile_lines", lambda: ["unexpected entry"])

        result = repo.brewfile_entries()

        assert result == ["unexpected entry"]


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

        @pytest.mark.parametrize("value", ["", "0", "false", "FALSE"])
        def test_should_skip_when_the_ci_variable_says_no(self, monkeypatch, value):
            monkeypatch.setenv("CI", value)
            with pytest.raises(pytest.skip.Exception):
                require_chezmoi()
