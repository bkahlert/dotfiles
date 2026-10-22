import tomllib

import pytest

from repo import HOME_SOURCE, require_chezmoi

SCRIPT = HOME_SOURCE / "private_dot_codex" / "modify_private_config.toml"


class TestModifyConfigToml:
    class TestOnStableSettings:
        def test_should_replace_drift_and_drop_settings_absent_from_source(self, modify):
            result = modify(SCRIPT, 'hide_agent_reasoning = true\n[tui]\nstatus_line = []\nstatus_line_use_colors = false\n'
                                    '[desktop]\npreventSleepWhileRunning = false\n')
            settings = tomllib.loads(result.stdout)
            assert result.returncode == 0, result.stderr
            assert "hide_agent_reasoning" not in settings
            assert "context-used" in settings["tui"]["status_line"]
            assert settings["tui"]["status_line_use_colors"] is True
            assert settings["desktop"]["preventSleepWhileRunning"] is True

        def test_should_restore_managed_mcp_definitions_and_plugin_enablement(self, modify):
            result = modify(SCRIPT, '[mcp_servers.idea]\ncommand = "obsolete-command"\n'
                                    '[mcp_servers.chrome-devtools]\nargs = ["--not-isolated"]\n'
                                    '[plugins."superpowers@superpowers-dev"]\nenabled = false\n')
            settings = tomllib.loads(result.stdout)
            assert result.returncode == 0, result.stderr
            assert settings["mcp_servers"]["idea"] == {"url": "http://127.0.0.1:64342/stream"}
            assert settings["mcp_servers"]["context7"] == {
                "command": "npx", "args": ["--yes", "@upstash/context7-mcp@latest"],
            }
            assert settings["mcp_servers"]["chrome-devtools"] == {
                "command": "npx", "args": ["--yes", "chrome-devtools-mcp@latest", "--headless", "--isolated", "--no-usage-statistics"],
            }
            assert settings["plugins"]["superpowers@superpowers-dev"]["enabled"] is True

    class TestOnMachineValues:
        @pytest.mark.parametrize("key,value", [
            ("model", '"local-model"'),
            ("model_provider", '"local-provider"'),
            ("model_reasoning_effort", '"high"'),
            ("model_reasoning_summary", '"detailed"'),
            ("service_tier", '"fast"'),
            ("notify", '["/local/integration", "notify"]'),
        ])
        def test_should_preserve_the_live_value(self, modify, key, value):
            current = f"{key} = {value}\n"
            result = modify(SCRIPT, current)
            assert result.returncode == 0, result.stderr
            assert tomllib.loads(result.stdout)[key] == tomllib.loads(current)[key]

        def test_should_preserve_project_trust_and_onboarding_state(self, modify):
            result = modify(SCRIPT, '[projects."/local/work"]\ntrust_level = "trusted"\n'
                                    '[notice]\nhide_full_access_warning = true\n'
                                    '[tui]\nscreen_reader_detection_done = true\n'
                                    '[tui.model_availability_nux]\nlocal-model = 1\n')
            settings = tomllib.loads(result.stdout)
            assert result.returncode == 0, result.stderr
            assert settings["projects"] == {"/local/work": {"trust_level": "trusted"}}
            assert settings["notice"]["hide_full_access_warning"] is True
            assert settings["tui"]["screen_reader_detection_done"] is True
            assert settings["tui"]["model_availability_nux"] == {"local-model": 1}

        def test_should_keep_a_selected_private_provider_and_its_definition_together(self, modify):
            result = modify(SCRIPT, 'model_provider = "private"\n[model_providers.private]\n'
                                    'name = "Private provider"\nbase_url = "http://127.0.0.1:8080/v1"\n'
                                    'env_key = "PRIVATE_API_KEY"\nwire_api = "responses"\n')
            settings = tomllib.loads(result.stdout)
            assert result.returncode == 0, result.stderr
            assert settings["model_provider"] == "private"
            assert settings["model_providers"]["private"] == {
                "name": "Private provider", "base_url": "http://127.0.0.1:8080/v1",
                "env_key": "PRIVATE_API_KEY", "wire_api": "responses",
            }

        @pytest.mark.parametrize("field,value", [
            ("env", '{ CONTEXT7_API_KEY = "test-placeholder" }'),
            ("env_vars", '["CONTEXT7_API_KEY"]'),
            ("http_headers", '{ Authorization = "test-placeholder" }'),
            ("env_http_headers", '{ Authorization = "IDE_TOKEN" }'),
            ("bearer_token_env_var", '"IDE_TOKEN"'),
            ("http_headers_helper", '"/local/auth-helper"'),
        ])
        def test_should_keep_mcp_credentials_while_restoring_managed_transport(self, modify, field, value):
            current = f'[mcp_servers.idea]\nurl = "http://obsolete.invalid"\n{field} = {value}\n'
            result = modify(SCRIPT, current)
            settings = tomllib.loads(result.stdout)
            assert result.returncode == 0, result.stderr
            assert settings["mcp_servers"]["idea"]["url"] == "http://127.0.0.1:64342/stream"
            assert settings["mcp_servers"]["idea"][field] == tomllib.loads(current)["mcp_servers"]["idea"][field]

        def test_should_preserve_private_mcp_marketplace_and_plugin_entries(self, modify):
            result = modify(SCRIPT, '[mcp_servers.private]\ncommand = "internal-server"\n'
                                    '[marketplaces.private]\nsource = "local-source"\n'
                                    '[plugins."private@private"]\nenabled = true\n')
            settings = tomllib.loads(result.stdout)
            assert result.returncode == 0, result.stderr
            assert settings["mcp_servers"]["private"] == {"command": "internal-server"}
            assert settings["marketplaces"]["private"] == {"source": "local-source"}
            assert settings["plugins"]["private@private"] == {"enabled": True}

    class TestOnNoCurrentFile:
        @pytest.mark.parametrize("current", ["", "\n"])
        def test_should_render_defaults_without_inventing_machine_values(self, modify, current):
            result = modify(SCRIPT, current)
            settings = tomllib.loads(result.stdout)
            assert result.returncode == 0, result.stderr
            assert not {"model", "model_provider", "model_reasoning_effort", "model_reasoning_summary",
                        "service_tier", "projects", "notice", "notify", "marketplaces", "model_providers"} & settings.keys()
            assert "screen_reader_detection_done" not in settings["tui"]
            assert "model_availability_nux" not in settings["tui"]

    class TestOnRepeatedApply:
        def test_should_leave_the_config_byte_identical(self, modify):
            first = modify(SCRIPT, 'model = "local-model"\n')
            second = modify(SCRIPT, first.stdout)
            assert first.returncode == second.returncode == 0
            assert second.stdout == first.stdout

    class TestOnInvalidToml:
        def test_should_fail_without_emitting_content(self, modify):
            result = modify(SCRIPT, "[broken")
            assert result.returncode != 0
            assert result.stdout == ""


@pytest.fixture(autouse=True)
def real_chezmoi(sandbox):
    executable = require_chezmoi()
    guard = sandbox.fakes / "chezmoi"
    guard.unlink()
    guard.symlink_to(executable)
