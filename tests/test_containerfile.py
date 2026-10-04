import re

from repo import ROOT

CONTAINERFILE = (ROOT / "Containerfile").read_text()
DEPENDABOT = (ROOT / ".github" / "dependabot.yml").read_text()
INSTRUCTIONS = re.sub(r"\\\n\s*", " ", CONTAINERFILE).splitlines()
CURL_CALLS = [line for line in INSTRUCTIONS if re.search(r"^RUN\s+curl\s|[;&|(]\s*curl\s|\$\(\s*curl\s", line)]


class TestBaseImage:
    def test_should_be_pinned_to_a_fedora_release_by_digest(self):
        bases = [line for line in INSTRUCTIONS if re.match(r"FROM (?!base )", line)]
        assert bases and all(re.match(r"FROM docker\.io/library/fedora:\d+@sha256:[0-9a-f]{64} ", line) for line in bases), bases


class TestShell:
    def test_should_fail_a_pipeline_when_any_stage_fails(self):
        shell = next((i for i, line in enumerate(INSTRUCTIONS) if line.startswith("SHELL ")), None)
        run = next(i for i, line in enumerate(INSTRUCTIONS) if line.startswith("RUN "))
        assert shell is not None and shell < run, "SHELL must come before the first RUN"
        assert "pipefail" in INSTRUCTIONS[shell]


class TestDownloads:
    def test_should_fail_the_build_on_an_http_error(self):
        assert CURL_CALLS and all(re.search(r"\bcurl\b[^|;&]*\s-[A-Za-z]*f", call) for call in CURL_CALLS), CURL_CALLS

    def test_should_refuse_a_non_https_redirect(self):
        assert all("--proto '=https'" in call for call in CURL_CALLS), CURL_CALLS

    def test_should_not_run_the_output_of_a_failed_download(self):
        assert not [call for call in CURL_CALLS if re.search(r"\$\(\s*curl|\|\s*(?:ba)?sh\b", call)], CURL_CALLS


class TestDependabot:
    def test_should_bump_the_base_image_weekly_with_a_cooldown(self):
        block = next((b for b in re.split(r"(?m)^  - ", DEPENDABOT) if b.startswith("package-ecosystem: docker")), None)
        assert block is not None, "no docker ecosystem entry"
        assert re.search(r"interval: weekly", block) and re.search(r"default-days: 3", block)
