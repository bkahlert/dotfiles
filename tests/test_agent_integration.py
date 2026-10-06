import json
import signal
import subprocess
import xml.etree.ElementTree as ET

import pytest

from agent_integration import CAPABILITIES, IDE_FIXTURE, Transcript, agent_command, execute, probe_prompt, run_agent
from repo import ROOT


class TestAgentIntegration:
    class TestOnCommands:
        @pytest.mark.parametrize("agent", ["claude", "copilot"])
        def test_should_load_the_real_configuration_without_replacements(self, agent):
            command = agent_command(agent, "probe")
            assert command[0] == agent
            assert "-p" in command
            assert not {"--bare", "--plugin-dir", "--mcp-config", "--additional-mcp-config",
                        "--no-custom-instructions", "--allow-all", "--dangerously-skip-permissions"} & set(command)

        def test_should_bound_claude_spending_and_turns(self):
            command = agent_command("claude", "probe")
            assert command[command.index("--model") + 1] == "haiku"
            assert command[command.index("--max-budget-usd") + 1] == "0.50"
            assert command[command.index("--max-turns") + 1] == "8"

        def test_should_use_copilot_efficiency_and_its_minimum_credit_cap(self):
            command = agent_command("copilot", "probe")
            assert command[command.index("--auto-tier") + 1] == "efficiency"
            assert command[command.index("--max-ai-credits") + 1] == "30"
            assert "--deny-tool=write" in command

    class TestOnPrompts:
        def test_should_request_only_selected_capabilities(self):
            prompt = probe_prompt(("idea",))
            assert IDE_FIXTURE in prompt
            assert "Context7" not in prompt
            assert "list_pages" not in prompt
            assert "verification-before-completion" not in prompt

        def test_should_use_public_inputs_and_no_browser_navigation(self):
            prompt = probe_prompt(CAPABILITIES)
            assert "list_pages" in prompt
            assert "Do not open" in prompt
            assert "len" in prompt
            assert "printf" in prompt

    class TestOnTranscripts:
        @pytest.mark.parametrize("agent", ["claude", "copilot"])
        def test_should_verify_each_capability_from_real_results(self, agent):
            data = events(agent, "mcp__plugin_context7_context7__resolve-library-id" if agent == "claude"
                          else "context7-resolve-library-id", {"libraryName": "Python"},
                          "Context7-compatible library ID: /python/cpython", call_id="resolve")
            data += events(agent, "mcp__plugin_context7_context7__query-docs" if agent == "claude"
                           else "context7-query-docs", {"libraryId": "/python/cpython"},
                           "Source: https://docs.python.org; len('abc')", call_id="docs")
            data += events(agent, "mcp__plugin_chrome-devtools-mcp_chrome-devtools__list_pages" if agent == "claude"
                           else "chrome-devtools-list_pages", {}, "## Pages\n1: about:blank [selected]", call_id="browser")
            data += events(agent, "mcp__idea__read_file" if agent == "claude" else "idea-read_file",
                           {"file_path": IDE_FIXTURE}, "L1: DOTFILES_IDEA_CAPABILITY_OK", call_id="ide")
            transcript = Transcript(agent, data)
            for capability in CAPABILITIES[:-1]:
                transcript.verify(capability)

        @pytest.mark.parametrize("agent", ["claude", "copilot"])
        def test_should_reject_documentation_for_an_unresolved_library(self, agent):
            data = events(agent, "context7-resolve-library-id", {}, "Context7-compatible library ID: /python/cpython")
            data += events(agent, "context7-query-docs", {"libraryId": "/other"},
                           "Source: https://example.com; len('abc')", call_id="docs")
            with pytest.raises(AssertionError, match="resolved library"):
                Transcript(agent, data).verify("context7")

        @pytest.mark.parametrize("agent", ["claude", "copilot"])
        def test_should_require_a_successful_result_from_the_called_tool(self, agent):
            transcript = Transcript(agent, events(agent, "idea-read_file", {"file_path": "README.md"},
                                                "L1: # dotfiles", success=True))
            result = transcript.require_call("idea", "read_file", "# dotfiles")
            assert result["file_path"] == "README.md"

        @pytest.mark.parametrize("agent", ["claude", "copilot"])
        def test_should_reject_a_claim_without_a_call(self, agent):
            transcript = Transcript(agent, [final_event(agent, "idea works, # dotfiles")])
            with pytest.raises(AssertionError, match="missing successful"):
                transcript.require_call("idea", "read_file", "# dotfiles")

        @pytest.mark.parametrize("agent", ["claude", "copilot"])
        def test_should_reject_failed_tool_results(self, agent):
            transcript = Transcript(agent, events(agent, "idea-read_file", {}, "# dotfiles", success=False))
            with pytest.raises(AssertionError, match="missing successful"):
                transcript.require_call("idea", "read_file", "# dotfiles")

        @pytest.mark.parametrize("agent", ["claude", "copilot"])
        def test_should_reject_incomplete_calls(self, agent):
            transcript = Transcript(agent, events(agent, "idea-read_file", {}, "# dotfiles")[:1])
            with pytest.raises(AssertionError, match="missing successful"):
                transcript.require_call("idea", "read_file", "# dotfiles")

        @pytest.mark.parametrize("agent", ["claude", "copilot"])
        def test_should_reject_nested_mcp_errors(self, agent):
            transcript = Transcript(agent, events(agent, "idea-read_file", {},
                                                {"isError": True, "content": "# dotfiles"}))
            with pytest.raises(AssertionError, match="missing successful"):
                transcript.require_call("idea", "read_file", "# dotfiles")

        @pytest.mark.parametrize("agent", ["claude", "copilot"])
        def test_should_reject_the_wrong_server_or_tool(self, agent):
            transcript = Transcript(agent, events(agent, "other-read_file", {}, "# dotfiles"))
            with pytest.raises(AssertionError, match="missing successful"):
                transcript.require_call("idea", "read_file", "# dotfiles")

        def test_should_reject_a_similarly_named_server(self):
            transcript = Transcript("copilot", events("copilot", "other-idea-read_file", {}, "# dotfiles"))
            with pytest.raises(AssertionError, match="missing successful"):
                transcript.require_call("idea", "read_file", "# dotfiles")

        @pytest.mark.parametrize("agent", ["claude", "copilot"])
        def test_should_reject_empty_or_irrelevant_results(self, agent):
            transcript = Transcript(agent, events(agent, "idea-read_file", {}, "unrelated"))
            with pytest.raises(AssertionError, match="missing successful"):
                transcript.require_call("idea", "read_file", "# dotfiles")

        @pytest.mark.parametrize("agent", ["claude", "copilot"])
        def test_should_require_skill_loading_before_verification(self, agent):
            data = events(agent, "Skill" if agent == "claude" else "skill",
                          {"skill": "superpowers:verification-before-completion"}, "skill loaded", call_id="s")
            data += events(agent, "Bash" if agent == "claude" else "bash",
                           {"command": "printf 'DOTFILES_AGENT_CHECK_OK\\n'"},
                           "DOTFILES_AGENT_CHECK_OK", call_id="b")
            data += [final_event(agent, "DOTFILES_AGENT_CHECK_OK")]
            transcript = Transcript(agent, data)
            transcript.verify("superpowers")

        def test_should_accept_copilot_s_unqualified_skill_only_from_superpowers(self):
            data = events("copilot", "skill", {"skill": "verification-before-completion"},
                          "loaded", call_id="s")
            data[1]["data"]["toolTelemetry"] = {"restrictedProperties": {"pluginName": "superpowers"}}
            data += events("copilot", "bash", {"command": "printf 'DOTFILES_AGENT_CHECK_OK\\n'"},
                           "DOTFILES_AGENT_CHECK_OK", call_id="b")
            data += [final_event("copilot", "DOTFILES_AGENT_CHECK_OK")]
            transcript = Transcript("copilot", data)
            transcript.verify("superpowers")

        def test_should_reject_a_same_named_skill_from_another_source(self):
            data = events("copilot", "skill", {"skill": "verification-before-completion"}, "loaded")
            with pytest.raises(AssertionError, match="Superpowers"):
                Transcript("copilot", data).verify("superpowers")

        @pytest.mark.parametrize("agent", ["claude", "copilot"])
        def test_should_reject_session_errors(self, agent):
            data = ({"type": "result", "subtype": "error_max_budget_usd", "is_error": True}
                    if agent == "claude" else {"type": "session.error", "data": {"errorType": "authentication"}})
            with pytest.raises(AssertionError, match="run failed"):
                Transcript(agent, [data])

        @pytest.mark.parametrize("agent", ["claude", "copilot"])
        def test_should_reject_verification_before_loading_the_skill(self, agent):
            data = events(agent, "Bash" if agent == "claude" else "bash",
                          {"command": "printf 'DOTFILES_AGENT_CHECK_OK\\n'"},
                          "DOTFILES_AGENT_CHECK_OK", call_id="b")
            data += events(agent, "Skill" if agent == "claude" else "skill",
                           {"skill": "superpowers:verification-before-completion"}, "skill loaded", call_id="s")
            data += [final_event(agent, "DOTFILES_AGENT_CHECK_OK")]
            with pytest.raises(AssertionError, match="after"):
                Transcript(agent, data).verify("superpowers")

    class TestOnExecution:
        @pytest.mark.parametrize("agent", ["claude", "copilot"])
        def test_should_save_private_diagnostics_and_parse_the_run(self, monkeypatch, tmp_path, agent):
            monkeypatch.setattr("agent_integration.shutil.which", lambda _: f"/bin/{agent}")
            executed = []

            def fake_execute(command):
                executed.append(command)
                data = events(agent, "idea-read_file", {"file_path": IDE_FIXTURE}, "DOTFILES_IDEA_CAPABILITY_OK")
                data += [final_event(agent, "done")]
                return subprocess.CompletedProcess(command, 0, "\n".join(map(json.dumps, data)), "")

            monkeypatch.setattr("agent_integration.execute", fake_execute)
            result = run_agent(agent, ("idea",), tmp_path)
            result.verify("idea")
            assert len(executed) == 1
            assert (tmp_path / "transcript.jsonl").stat().st_mode & 0o777 == 0o600
            if agent == "copilot":
                assert "--usage-output-file" in executed[0]

        def test_should_preserve_partial_diagnostics_on_timeout(self, monkeypatch, tmp_path):
            monkeypatch.setattr("agent_integration.shutil.which", lambda _: "/bin/copilot")

            def timeout(command):
                raise subprocess.TimeoutExpired(command, 180, output=b"partial", stderr=b"diagnostic")

            monkeypatch.setattr("agent_integration.execute", timeout)
            with pytest.raises(AssertionError, match="timed out after 180"):
                run_agent("copilot", ("idea",), tmp_path)
            assert (tmp_path / "transcript.jsonl").read_text() == "partial"
            assert (tmp_path / "stderr.txt").read_text() == "diagnostic"

        def test_should_start_a_private_process_group_and_stop_only_that_group(self, monkeypatch):
            process = FakeProcess()
            started = []
            stopped = []
            monkeypatch.setattr("agent_integration.subprocess.Popen",
                                lambda command, **kwargs: (started.append(kwargs), process)[1])
            monkeypatch.setattr("agent_integration.os.killpg", lambda pid, sig: stopped.append((pid, sig)))
            result = execute(["copilot"])
            assert result.returncode == 0
            assert started[0]["start_new_session"] is True
            assert stopped == [(process.pid, signal.SIGTERM)]

        def test_should_force_stop_a_process_that_ignores_termination(self, monkeypatch):
            process = FakeProcess(timeouts=2)
            stopped = []
            monkeypatch.setattr("agent_integration.subprocess.Popen", lambda *args, **kwargs: process)
            monkeypatch.setattr("agent_integration.os.killpg", lambda pid, sig: stopped.append((pid, sig)))
            with pytest.raises(subprocess.TimeoutExpired):
                execute(["copilot"])
            assert stopped == [(process.pid, signal.SIGTERM), (process.pid, signal.SIGKILL)]

        def test_should_fail_before_spending_when_the_cli_is_missing(self, monkeypatch):
            monkeypatch.setattr("agent_integration.shutil.which", lambda _: None)
            with pytest.raises(AssertionError, match="not installed"):
                run_agent("copilot", ("idea",))

        def test_should_reject_invalid_json(self):
            with pytest.raises(ValueError, match="JSON"):
                Transcript.from_output("copilot", "not JSON")

        def test_should_reject_non_object_events(self):
            with pytest.raises(ValueError, match="object"):
                Transcript.from_output("copilot", "[]")

        def test_should_report_nonzero_exit_without_dumping_sensitive_output(self, monkeypatch):
            monkeypatch.setattr("agent_integration.shutil.which", lambda _: "/bin/copilot")
            monkeypatch.setattr("agent_integration.execute", lambda _: subprocess.CompletedProcess(
                ["copilot"], 1, "private result", "private error"))
            with pytest.raises(AssertionError, match="exit 1") as error:
                run_agent("copilot", ("idea",))
            assert "private" not in str(error.value)


class TestAgentRunConfigurations:
    def test_should_run_ci_through_the_native_makefile_configuration(self):
        config = ET.parse(ROOT / ".run" / "ci.run.xml").getroot().find("configuration")
        makefile = config.find("makefile")
        assert config.attrib["type"] == "MAKEFILE_TARGET_RUN_CONFIGURATION"
        assert makefile.attrib["filename"] == "$PROJECT_DIR$/Makefile"
        assert makefile.attrib["target"] == "ci"
        assert makefile.attrib["arguments"] == ""

    @pytest.mark.parametrize("filename,target", [
        ("integration-claude", "integration-claude"), ("integration-copilot", "integration-copilot"),
    ])
    def test_should_run_the_matching_target_from_the_project_with_a_login_shell(self, filename, target):
        config = ET.parse(ROOT / ".run" / f"{filename}.run.xml").getroot().find("configuration")
        options = {option.attrib["name"]: option.attrib["value"] for option in config.findall("option")}
        assert config.attrib["type"] == "ShConfigurationType"
        assert options["SCRIPT_TEXT"] == f"make {target}"
        assert options["SCRIPT_WORKING_DIRECTORY"] == "$PROJECT_DIR$"
        assert options["INTERPRETER_PATH"] == "/bin/zsh"
        assert options["INTERPRETER_OPTIONS"] == "-li"
        assert options["EXECUTE_SCRIPT_FILE"] == "false"


class FakeProcess:
    def __init__(self, timeouts=0):
        self.pid = 12345
        self.returncode = 0
        self.timeouts = timeouts

    def communicate(self, timeout=None):
        if self.timeouts:
            self.timeouts -= 1
            raise subprocess.TimeoutExpired(["copilot"], timeout)
        return "", ""

    def poll(self):
        return None if self.timeouts else self.returncode


def events(agent, tool, arguments, output, success=True, call_id="t"):
    if agent == "claude":
        return [
            {"type": "assistant", "message": {"content": [
                {"type": "tool_use", "id": call_id, "name": tool, "input": arguments}]}},
            {"type": "user", "message": {"content": [
                {"type": "tool_result", "tool_use_id": call_id, "content": output, "is_error": not success}]}},
        ]
    return [
        {"type": "tool.execution_start", "data": {
            "toolCallId": call_id, "toolName": tool, "arguments": arguments}},
        {"type": "tool.execution_complete", "data": {
            "toolCallId": call_id, "success": success, "result": {"content": output}}},
    ]


def final_event(agent, content):
    if agent == "claude":
        return {"type": "result", "subtype": "success", "is_error": False, "result": content}
    return {"type": "assistant.message", "data": {"content": content}}
