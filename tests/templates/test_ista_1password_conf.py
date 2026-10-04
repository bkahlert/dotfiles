import pytest

TEMPLATE = "private_dot_ssh/private_conf.d/20-ista-1password.conf.tmpl"


class TestIsta1passwordConf:
    class TestOnIstaMacOS:
        def test_should_route_gitlab_com_alone_through_the_1password_agent(self, chezmoi):
            lines = [line for line in chezmoi.render(TEMPLATE, company="ista").splitlines() if not line.startswith("#")]
            assert lines == ["Host gitlab.com",
                             '\tIdentityAgent "~/Library/Group Containers/2BUA8C4S2C.com.1password/t/agent.sock"']

    @pytest.mark.parametrize("company,os", [("ista", "linux"), ("bkahlert", "darwin"), ("", "darwin")],
                             ids=("ista-linux", "bkahlert-macos", "none-macos"))
    class TestElsewhere:
        def test_should_leave_the_personal_agent_alone(self, chezmoi, company, os):
            assert chezmoi.render(TEMPLATE, company=company, os=os).strip() == ""
