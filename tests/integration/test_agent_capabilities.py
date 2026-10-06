import pytest

from agent_integration import CAPABILITIES, run_agent

pytestmark = [pytest.mark.integration, pytest.mark.authenticated]


class TestAgentCapabilities:
    def test_should_execute_the_installed_capability(self, agent_transcript, smoke_capability):
        agent_transcript.verify(smoke_capability)


def pytest_generate_tests(metafunc):
    if "smoke_capability" in metafunc.fixturenames:
        capabilities = metafunc.config.getoption("--agent-capability") or CAPABILITIES
        metafunc.parametrize("smoke_capability", capabilities)


@pytest.fixture(scope="module")
def agent_transcript(request, tmp_path_factory):
    agent = request.config.getoption("--live-agent")
    if agent is None:
        pytest.skip("authenticated model calls require --live-agent; use an integration-claude/copilot target")
    capabilities = request.config.getoption("--agent-capability") or CAPABILITIES
    artifacts = tmp_path_factory.mktemp(f"{agent}-capabilities")
    print(f"\n{agent}: one paid session, no retries; private diagnostic files: {artifacts}")
    return run_agent(agent, capabilities, artifacts)
