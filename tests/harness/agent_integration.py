import json
import os
import shutil
import signal
import subprocess
from pathlib import Path

from repo import ROOT

CAPABILITIES = ("context7", "chrome-devtools", "idea", "superpowers")
CHECK_MARKER = "DOTFILES_AGENT_CHECK_OK"
IDE_FIXTURE = "tests/harness/fixtures/agent-capability.txt"


class Transcript:
    def __init__(self, agent, events):
        self.calls = []
        self.final = ""
        pending = {}
        for index, event in enumerate(events):
            kind = event.get("type")
            if agent == "claude":
                for block in event.get("message", {}).get("content", []):
                    if not isinstance(block, dict):
                        continue
                    if block.get("type") == "tool_use":
                        pending[block["id"]] = (index, block["name"], block.get("input", {}))
                    elif block.get("type") == "tool_result" and block["tool_use_id"] in pending:
                        self.calls.append((*pending[block["tool_use_id"]], block.get("content"),
                                           not has_error(block), index))
                if kind == "result":
                    assert not event.get("is_error") and event.get("subtype") == "success", (
                        f"Claude run failed: {event.get('subtype')}")
                    self.final = event.get("result", "")
            else:
                data = event.get("data", {})
                if kind == "tool.execution_start":
                    pending[data["toolCallId"]] = (index, data["toolName"], data.get("arguments", {}))
                elif kind == "tool.execution_complete" and data["toolCallId"] in pending:
                    self.calls.append((*pending[data["toolCallId"]], data.get("result"),
                                       data.get("success") is True and not has_error(data), index,
                                       data.get("toolTelemetry", {}).get("restrictedProperties", {})))
                elif kind == "assistant.message":
                    self.final = data.get("content", "")
                elif kind == "session.error":
                    raise AssertionError(f"Copilot run failed: {data.get('errorType', 'session.error')}")

    @classmethod
    def from_output(cls, agent, output):
        events = []
        for line in output.splitlines():
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError("agent output is not JSON; inspect the saved transcript") from error
            if not isinstance(event, dict):
                raise ValueError("agent event must be a JSON object")
            events.append(event)
        return cls(agent, events)

    def matching_calls(self, server, tool, marker=""):
        return [call for call in self.calls
                if call[4] and tool_name_matches(call[1], server, tool)
                and call[3] and marker.lower() in json.dumps(call[3]).lower()]

    def require_call(self, server, tool, marker=""):
        matches = self.matching_calls(server, tool, marker)
        assert matches, f"missing successful {server}/{tool} result containing {marker!r}"
        return matches[0][2]

    def verify(self, capability):
        if capability == "context7":
            resolutions = self.matching_calls("context7", "resolve-library-id", "Context7-compatible library ID:")
            queries = self.matching_calls("context7", "query-docs", "len(")
            assert resolutions, "missing successful Context7 library resolution"
            assert any(query[2].get("libraryId") and "Source:" in json.dumps(query[3])
                       and query[2]["libraryId"] in json.dumps(resolution[3])
                       and resolution[5] < query[0]
                       for resolution in resolutions for query in queries), (
                "missing successful Context7 documentation query for the resolved library")
        elif capability == "chrome-devtools":
            self.require_call("chrome-devtools", "list_pages", "Pages")
        elif capability == "idea":
            arguments = self.require_call("idea", "read_file", "DOTFILES_IDEA_CAPABILITY_OK")
            assert arguments.get("file_path") == IDE_FIXTURE, "IDE must read the public fixture"
        elif capability == "superpowers":
            skills = [call for call in self.matching_calls("", "skill")
                      if call[2].get("skill") == "superpowers:verification-before-completion"
                      or (call[2].get("skill") == "verification-before-completion"
                          and len(call) > 6 and call[6].get("pluginName") == "superpowers")]
            assert skills, "missing successful Superpowers verification-before-completion invocation"
            checks = [call for call in self.matching_calls("", "bash", CHECK_MARKER)
                      if call[2].get("command") == f"printf '{CHECK_MARKER}\\n'"]
            assert checks, "missing successful printf verification"
            assert any(skill[5] < check[0] for skill in skills for check in checks), (
                "verification must execute after the skill has loaded")
            assert CHECK_MARKER in self.final, "final answer must cite the fresh verification evidence"
        else:
            raise ValueError(f"unknown capability: {capability}")


def agent_command(agent, prompt):
    if agent == "claude":
        return [
            "claude", "-p", prompt, "--output-format", "stream-json", "--verbose",
            "--model", "haiku", "--max-budget-usd", "0.50", "--max-turns", "8",
            "--no-session-persistence", "--tools", "Skill,Bash",
            "--allowedTools", "Skill", "Bash(printf *)", "mcp__context7__resolve-library-id",
            "mcp__context7__query-docs", "mcp__chrome-devtools__list_pages", "mcp__idea__read_file",
            "mcp__plugin_context7_context7__resolve-library-id", "mcp__plugin_context7_context7__query-docs",
            "mcp__plugin_chrome-devtools-mcp_chrome-devtools__list_pages",
        ]
    if agent == "copilot":
        return [
            "copilot", "-p", prompt, "--output-format", "json",
            "--model", "auto", "--auto-tier", "efficiency", "--max-ai-credits", "30",
            "--no-ask-user", "--no-color", "--no-remote", "--no-remote-export",
            "--add-dir", str(Path.home() / ".config" / "agents"),
            "--deny-tool=write", "--allow-tool=shell(printf)",
            "--allow-tool=context7(resolve-library-id)", "--allow-tool=context7(query-docs)",
            "--allow-tool=chrome-devtools(list_pages)", "--allow-tool=idea(read_file)",
        ]
    raise ValueError(f"unknown agent: {agent}")


def probe_prompt(capabilities):
    tasks = {
        "context7": "Use Context7 resolve-library-id for Python, then query-docs for one example of len. "
                    "Use only public documentation and keep the query narrow.",
        "chrome-devtools": "Call the Chrome DevTools list_pages tool once. Do not open, navigate, "
                           "close, inspect, or modify any pages or the user's browser.",
        "idea": f"Call idea read_file with file_path='{IDE_FIXTURE}', projectPath='{ROOT}'. "
                "Read no other project files; shared agent guidance may be read.",
        "superpowers": "Invoke the installed Superpowers verification-before-completion skill through "
                      f"the Skill/skill tool. After it loads, execute exactly printf '{CHECK_MARKER}\\n' "
                      f"with Bash/bash, then cite {CHECK_MARKER} as fresh evidence in your final answer.",
    }
    return (
        "This is a bounded capability smoke test, not an implementation task. Perform only these probes. "
        "Do not install anything, edit files, delegate, use workflows, or retry failed calls. "
        "Missing capabilities are failures; never substitute shell/HTTP tools for MCP tools. "
        "Parallelize independent probes. Give a final answer under 40 words.\n"
        + "\n".join(tasks[capability] for capability in capabilities)
    )


def run_agent(agent, capabilities, artifact_dir=None):
    assert shutil.which(agent), f"{agent} is not installed"
    command = agent_command(agent, probe_prompt(capabilities))
    if agent == "copilot" and artifact_dir is not None:
        usage_path = Path(artifact_dir) / "usage.json"
        usage_path.touch(mode=0o600)
        command += ["--usage-output-file", str(usage_path)]
    try:
        result = execute(command)
    except subprocess.TimeoutExpired as error:
        result = subprocess.CompletedProcess(command, 124, decode_output(error.output),
                                             decode_output(error.stderr))
    if artifact_dir is not None:
        for name, content in (("transcript.jsonl", result.stdout), ("stderr.txt", result.stderr)):
            path = Path(artifact_dir) / name
            path.touch(mode=0o600)
            path.write_text(content)
        if agent == "copilot":
            usage_path.chmod(0o600)
    failure = "timed out after 180 seconds" if result.returncode == 124 else f"exited with exit {result.returncode}"
    assert result.returncode == 0, (
        f"{agent} {failure}; check login, permissions and limits"
        + (f"; diagnostic files: {artifact_dir}" if artifact_dir else ""))
    transcript = Transcript.from_output(agent, result.stdout)
    assert transcript.final, "agent did not produce a final response; inspect the saved transcript"
    return transcript


def execute(command):
    process = subprocess.Popen(command, cwd=ROOT, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, text=True, start_new_session=True)
    try:
        stdout, stderr = process.communicate(timeout=180)
        return subprocess.CompletedProcess(command, process.returncode, stdout, stderr)
    finally:
        # Stop this run's MCP/browser children too, including after a timeout.
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        if process.poll() is None:
            try:
                process.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.communicate()


def has_error(value):
    if isinstance(value, dict):
        return value.get("is_error") is True or value.get("isError") is True or any(
            has_error(item) for item in value.values())
    if isinstance(value, list):
        return any(has_error(item) for item in value)
    return False


def tool_name_matches(name, server, tool):
    normalized = name.lower().replace("_", "-")
    suffix = tool.lower().replace("_", "-")
    if not server:
        return normalized == suffix
    return normalized in {
        f"{server}-{suffix}", f"mcp--{server}--{suffix}",
        f"mcp--plugin-{server}-{server}--{suffix}", f"mcp--plugin-{server}-mcp-{server}--{suffix}",
    }


def decode_output(output):
    if output is None:
        return ""
    return output.decode() if isinstance(output, bytes) else output
