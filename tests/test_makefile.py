import subprocess

from repo import ROOT


class TestContainerTargets:
    def test_should_build_from_the_harness_containerfile_with_root_context(self):
        result = subprocess.run(["make", "--dry-run", "image"], cwd=ROOT, capture_output=True, text=True, check=True)
        build = next(line for line in result.stdout.splitlines() if " build " in f" {line} ")

        assert "-f tests/harness/container/Containerfile" in build
        assert build.endswith(" .")

    def test_should_run_from_the_harness_containerfile_with_root_context(self):
        result = subprocess.run(["make", "--dry-run", "run"], cwd=ROOT, capture_output=True, text=True, check=True)
        build = next(line for line in result.stdout.splitlines() if " build " in f" {line} ")

        assert "-f tests/harness/container/Containerfile" in build
        assert build.endswith(" .")
