import re
import shutil

import pytest

from repo import BIN_SOURCE

needs_xmlstarlet = pytest.mark.skipif(shutil.which("xmlstarlet") is None, reason="xmlstarlet is not installed")

OTHER_ONLY = """<?xml version="1.0" encoding="UTF-8"?>
<project version="4">
  <component name="Other">
    <option name="x" value="1" />
  </component>
</project>
"""

FIXED = """<?xml version="1.0" encoding="UTF-8"?>
<project version="4">
  <component name="Other">
    <option name="x" value="1" />
  </component>
  <component name="OptimizeOnSaveOptions">
    <option name="myRunOnSave" value="true" />
  </component>
  <component name="FormatOnSaveOptions">
    <option name="myRunOnSave" value="true" />
  </component>
</project>
"""

DISABLED = """<?xml version="1.0" encoding="UTF-8"?>
<project version="4">
  <component name="FormatOnSaveOptions">
    <option name="myRunOnSave" value="false" />
  </component>
  <component name="OptimizeOnSaveOptions">
    <option name="myRunOnSave" value="false" />
  </component>
</project>
"""


class TestIntellijWorkspaceFix:
    @needs_xmlstarlet
    class TestOnWorkspaceWithoutTheSaveOptions:
        def test_should_add_both_components_with_myrunonsave_true(self, run, sandbox):
            workspace = write(sandbox, "app/.idea/workspace.xml", OTHER_ONLY)
            result = run("intellij-workspace-fix")
            assert result.returncode == 0
            assert workspace.read_text() == FIXED
            assert result.stdout.startswith("✔ fixed: ./app/.idea/workspace.xml (backup: workspace.")

        def test_should_keep_the_original_in_a_timestamped_backup_next_to_it(self, run, sandbox):
            workspace = write(sandbox, "app/.idea/workspace.xml", OTHER_ONLY)
            run("intellij-workspace-fix")
            backups = [p for p in workspace.parent.iterdir() if re.fullmatch(r"workspace\.\d+\.xml", p.name)]
            assert [p.read_text() for p in backups] == [OTHER_ONLY]

    @needs_xmlstarlet
    class TestOnDisabledSaveOptions:
        def test_should_switch_them_on(self, run, sandbox):
            workspace = write(sandbox, "app/.idea/workspace.xml", DISABLED)
            run("intellij-workspace-fix")
            assert workspace.read_text().count('<option name="myRunOnSave" value="true" />') == 2
            assert "false" not in workspace.read_text()

    @needs_xmlstarlet
    class TestOnAlreadyFixedWorkspace:
        def test_should_report_it_and_write_no_backup(self, run, sandbox):
            workspace = write(sandbox, "app/.idea/workspace.xml", FIXED)
            result = run("intellij-workspace-fix")
            assert (result.returncode, result.stdout) == (0, "▪ already fixed: ./app/.idea/workspace.xml\n")
            assert sorted(p.name for p in workspace.parent.iterdir()) == ["workspace.xml"]
            assert workspace.read_text() == FIXED

    @needs_xmlstarlet
    class TestOnDryRun:
        @pytest.mark.parametrize("flag", ["--dry-run", "-n"])
        def test_should_report_what_would_change_and_write_nothing(self, run, sandbox, flag):
            workspace = write(sandbox, "app/.idea/workspace.xml", OTHER_ONLY)
            result = run("intellij-workspace-fix", flag)
            assert (result.returncode, result.stdout) == (0, "ℹ would fix: ./app/.idea/workspace.xml\n")
            assert workspace.read_text() == OTHER_ONLY
            assert sorted(p.name for p in workspace.parent.iterdir()) == ["workspace.xml"]

    @needs_xmlstarlet
    class TestOnSkippedDirectories:
        @pytest.mark.parametrize("skipped", [".git", "build", "cache", "node_modules"])
        def test_should_leave_workspaces_below_them_alone(self, run, sandbox, skipped):
            hidden = write(sandbox, f"app/{skipped}/.idea/workspace.xml", OTHER_ONLY)
            visible = write(sandbox, "app/.idea/workspace.xml", OTHER_ONLY)
            result = run("intellij-workspace-fix")
            assert hidden.read_text() == OTHER_ONLY
            assert visible.read_text() == FIXED
            assert skipped not in result.stdout

    class TestOnMissingXmlstarlet:
        def test_should_exit_1_and_name_the_package(self, run, tmp_path):
            bare = tmp_path / "bare"
            bare.mkdir()
            (bare / "bash").symlink_to(shutil.which("bash"))
            (bare / "intellij-workspace-fix").symlink_to(BIN_SOURCE / "executable_intellij-workspace-fix")
            result = run("env", f"PATH={bare}", "intellij-workspace-fix")
            assert (result.returncode, result.stderr) == (
                1, "intellij-workspace-fix: xmlstarlet not found (brew install xmlstarlet)\n")

    class TestOnBadArguments:
        def test_should_exit_2_on_an_unknown_argument(self, run):
            result = run("intellij-workspace-fix", "--nope")
            assert (result.returncode, result.stderr) == (
                2, "intellij-workspace-fix: unknown argument: --nope\nSee 'intellij-workspace-fix --help'\n")

    class TestOnHelp:
        def test_should_print_the_header_without_the_shebang(self, run):
            result = run("intellij-workspace-fix", "--help")
            assert result.returncode == 0
            assert result.stdout.startswith("Purpose: Enable \"Reformat code\" and \"Optimize imports\" on save in every\n")
            assert "Usage:   intellij-workspace-fix [--dry-run]\n" in result.stdout


def write(sandbox, relative, body):
    path = sandbox.home / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body)
    return path
