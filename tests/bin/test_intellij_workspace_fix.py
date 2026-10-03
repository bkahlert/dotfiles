import importlib.machinery
import importlib.util
import re
import sys

import pytest

from repo import BIN_SOURCE


class TestIntellijWorkspaceFix:
    class TestOnWorkspaceWithoutTheSaveOptions:
        def test_should_add_both_components_for_all_file_types_in_sorted_position(self, run, sandbox):
            workspace = write(sandbox, "app/.idea/workspace.xml", WITHOUT_SAVE_OPTIONS)
            result = run("intellij-workspace-fix")
            assert result.returncode == 0
            assert workspace.read_text() == FIXED
            assert result.stdout.startswith("✔ fixed: ./app/.idea/workspace.xml (backup: workspace.")

        def test_should_keep_the_original_in_a_timestamped_backup_next_to_it(self, run, sandbox):
            workspace = write(sandbox, "app/.idea/workspace.xml", WITHOUT_SAVE_OPTIONS)
            run("intellij-workspace-fix")
            backups = [p for p in workspace.parent.iterdir() if re.fullmatch(r"workspace\.\d+\.xml", p.name)]
            assert [p.read_text() for p in backups] == [WITHOUT_SAVE_OPTIONS]

        def test_should_append_after_the_last_component_when_none_sorts_later(self, run, sandbox):
            workspace = write(sandbox, "app/.idea/workspace.xml", project(component("Alpha", RUN_ON_SAVE_ONLY)))
            run("intellij-workspace-fix")
            assert workspace.read_text() == project(
                component("Alpha", RUN_ON_SAVE_ONLY),
                component("FormatOnSaveOptions", ALL_FILE_TYPES),
                component("OptimizeOnSaveOptions", ALL_FILE_TYPES))

    class TestOnRunOnSaveOnly:
        def test_should_select_all_file_types_which_the_go_plugin_defaults_away(self, run, sandbox):
            workspace = write(sandbox, "app/.idea/workspace.xml", with_save_options(RUN_ON_SAVE_ONLY))
            run("intellij-workspace-fix")
            assert workspace.read_text() == FIXED

    class TestOnGoFilesSelected:
        def test_should_replace_the_selection_with_all_file_types(self, run, sandbox):
            workspace = write(sandbox, "app/.idea/workspace.xml", with_save_options(GO_FILES))
            run("intellij-workspace-fix")
            assert workspace.read_text() == FIXED

    class TestOnDisabledSaveOptions:
        def test_should_switch_them_on_for_all_file_types(self, run, sandbox):
            workspace = write(sandbox, "app/.idea/workspace.xml", with_save_options(DISABLED))
            run("intellij-workspace-fix")
            assert workspace.read_text() == FIXED

    class TestOnIdeWrittenAllFileTypes:
        def test_should_only_add_the_explicit_myrunonsave(self, run, sandbox):
            workspace = write(sandbox, "app/.idea/workspace.xml", with_save_options(IDE_ALL_FILE_TYPES))
            run("intellij-workspace-fix")
            assert workspace.read_text() == FIXED

    class TestOnSiblingOptions:
        def test_should_keep_them_where_they_are(self, run, sandbox):
            workspace = write(sandbox, "app/.idea/workspace.xml", with_save_options(GO_FILES, ONLY_CHANGED_LINES))
            run("intellij-workspace-fix")
            assert workspace.read_text() == with_save_options(ALL_FILE_TYPES, ONLY_CHANGED_LINES)

    class TestOnSelfClosingComponent:
        def test_should_expand_it(self, run, sandbox):
            before = project('  <component name="FormatOnSaveOptions" />\n', GIT, component("OptimizeOnSaveOptions", ALL_FILE_TYPES))
            workspace = write(sandbox, "app/.idea/workspace.xml", before)
            run("intellij-workspace-fix")
            assert workspace.read_text() == project(
                component("FormatOnSaveOptions", ALL_FILE_TYPES), GIT, component("OptimizeOnSaveOptions", ALL_FILE_TYPES))

    class TestOnAlreadyFixedWorkspace:
        def test_should_report_it_and_write_no_backup(self, run, sandbox):
            workspace = write(sandbox, "app/.idea/workspace.xml", FIXED)
            result = run("intellij-workspace-fix")
            assert (result.returncode, result.stdout) == (0, "▪ already fixed: ./app/.idea/workspace.xml\n")
            assert sorted(p.name for p in workspace.parent.iterdir()) == ["workspace.xml"]
            assert workspace.read_text() == FIXED

        def test_should_find_its_own_output_fixed(self, run, sandbox):
            write(sandbox, "app/.idea/workspace.xml", with_save_options(GO_FILES))
            run("intellij-workspace-fix")
            second = run("intellij-workspace-fix")
            assert second.stdout == "▪ already fixed: ./app/.idea/workspace.xml\n"

    class TestOnDryRun:
        @pytest.mark.parametrize("flag", ["--dry-run", "-n"])
        def test_should_report_what_would_change_and_write_nothing(self, run, sandbox, flag):
            workspace = write(sandbox, "app/.idea/workspace.xml", WITHOUT_SAVE_OPTIONS)
            result = run("intellij-workspace-fix", flag)
            assert (result.returncode, result.stdout) == (0, "ℹ would fix: ./app/.idea/workspace.xml\n")
            assert workspace.read_text() == WITHOUT_SAVE_OPTIONS
            assert sorted(p.name for p in workspace.parent.iterdir()) == ["workspace.xml"]

    class TestOnSkippedDirectories:
        @pytest.mark.parametrize("skipped", [".git", "build", "cache", "node_modules"])
        def test_should_leave_workspaces_below_them_alone(self, run, sandbox, skipped):
            hidden = write(sandbox, f"app/{skipped}/.idea/workspace.xml", WITHOUT_SAVE_OPTIONS)
            visible = write(sandbox, "app/.idea/workspace.xml", WITHOUT_SAVE_OPTIONS)
            result = run("intellij-workspace-fix")
            assert hidden.read_text() == WITHOUT_SAVE_OPTIONS
            assert visible.read_text() == FIXED
            assert skipped not in result.stdout

    class TestOnUnparsableWorkspace:
        def test_should_report_it_leave_it_alone_and_still_fix_the_others(self, run, sandbox):
            broken = write(sandbox, "a/.idea/workspace.xml", "<project><component></project>\n")
            fine = write(sandbox, "b/.idea/workspace.xml", WITHOUT_SAVE_OPTIONS)
            result = run("intellij-workspace-fix")
            assert result.returncode == 1
            assert result.stderr.startswith("✖ failed: ./a/.idea/workspace.xml")
            assert broken.read_text() == "<project><component></project>\n"
            assert fine.read_text() == FIXED

    class TestOnSiblingOrderAsTheIdeWritesIt:
        def test_should_find_it_fixed_without_moving_the_sibling(self, run, sandbox):
            ide_order = project(component("FormatOnSaveOptions", """\
    <option name="myAllFileTypesSelected" value="true" />
    <option name="myFormatOnlyChangedLines" value="true" />
    <option name="myRunOnSave" value="true" />
    <option name="mySelectedFileTypes">
      <set />
    </option>
"""), GIT, component("OptimizeOnSaveOptions", ALL_FILE_TYPES), PROBLEMS)
            write(sandbox, "app/.idea/workspace.xml", ide_order)
            result = run("intellij-workspace-fix")
            assert result.stdout == "▪ already fixed: ./app/.idea/workspace.xml\n"

    class TestOnOptionsItCannotTell:
        def test_should_leave_an_unusually_indented_option_and_its_siblings_alone(self, run, sandbox):
            odd = project(component("FormatOnSaveOptions", """\
    <option name="mySelectedFileTypes">
      <set />
      </option>
    <option name="myRunOnSave" value="true" />
    <option name="myKeep">
      <list>
        <option value="a" />
      </list>
    </option>
    <option name="myOther" value="1" />
"""), GIT, PROBLEMS)
            workspace = write(sandbox, "app/.idea/workspace.xml", odd)
            result = run("intellij-workspace-fix")
            assert (result.returncode, workspace.read_text()) == (1, odd)
            assert result.stderr.startswith("✖ failed: ./app/.idea/workspace.xml")

        def test_should_not_add_a_second_copy_of_an_option_it_failed_to_match(self, run, sandbox):
            odd = project(component("FormatOnSaveOptions", """\
    <option value="true" name="myRunOnSave" />
"""), GIT, PROBLEMS)
            workspace = write(sandbox, "app/.idea/workspace.xml", odd)
            result = run("intellij-workspace-fix")
            assert (result.returncode, workspace.read_text()) == (1, odd)

    class TestOnFilesItDoesNotUnderstand:
        def test_should_leave_crlf_files_alone(self, run, sandbox):
            crlf = WITHOUT_SAVE_OPTIONS.replace("\n", "\r\n").encode()
            workspace = sandbox.home / "app/.idea/workspace.xml"
            workspace.parent.mkdir(parents=True)
            workspace.write_bytes(crlf)
            result = run("intellij-workspace-fix")
            assert (result.returncode, workspace.read_bytes()) == (1, crlf)

        def test_should_leave_non_utf8_files_alone_and_fix_the_others(self, run, sandbox):
            workspace = sandbox.home / "a/.idea/workspace.xml"
            workspace.parent.mkdir(parents=True)
            workspace.write_bytes(b"<project>caf\xe9</project>\n")
            fine = write(sandbox, "b/.idea/workspace.xml", WITHOUT_SAVE_OPTIONS)
            result = run("intellij-workspace-fix")
            assert result.returncode == 1
            assert result.stderr.startswith("✖ failed: ./a/.idea/workspace.xml")
            assert workspace.read_bytes() == b"<project>caf\xe9</project>\n"
            assert fine.read_text() == FIXED

        def test_should_leave_read_only_files_alone_and_write_no_backup(self, run, sandbox):
            workspace = write(sandbox, "app/.idea/workspace.xml", WITHOUT_SAVE_OPTIONS)
            workspace.chmod(0o444)
            result = run("intellij-workspace-fix")
            assert result.returncode == 1
            assert result.stderr.startswith("✖ failed: ./app/.idea/workspace.xml")
            assert sorted(p.name for p in workspace.parent.iterdir()) == ["workspace.xml"]

        def test_should_leave_a_file_without_a_project_root_alone(self, run, sandbox):
            workspace = write(sandbox, "app/.idea/workspace.xml", "<settings />\n")
            result = run("intellij-workspace-fix")
            assert (result.returncode, workspace.read_text()) == (1, "<settings />\n")

    class TestOnExistingBackup:
        def test_should_not_overwrite_it(self, tmp_path, monkeypatch):
            # A .pyc next to the source would be applied into ~/.local/bin, chezmoi ignores .gitignore.
            monkeypatch.setattr(sys, "dont_write_bytecode", True)
            source = str(BIN_SOURCE / "executable_intellij-workspace-fix")
            loader = importlib.machinery.SourceFileLoader("workspace_fix", source)
            module = importlib.util.module_from_spec(importlib.util.spec_from_loader("workspace_fix", loader))
            loader.exec_module(module)
            workspace = tmp_path / "workspace.xml"
            workspace.write_text(WITHOUT_SAVE_OPTIONS)
            backup = tmp_path / "workspace.1.xml"
            backup.write_text("PRECIOUS")
            assert module.fix_workspace(str(workspace), False, 1) is False
            assert (backup.read_text(), workspace.read_text()) == ("PRECIOUS", WITHOUT_SAVE_OPTIONS)

    class TestOnBadArguments:
        def test_should_exit_2_on_an_unknown_argument(self, run):
            result = run("intellij-workspace-fix", "--nope")
            assert (result.returncode, result.stderr) == (
                2, "intellij-workspace-fix: unknown argument: --nope\nSee 'intellij-workspace-fix --help'\n")

    class TestOnHelp:
        def test_should_print_the_header_without_the_shebang(self, run):
            result = run("intellij-workspace-fix", "--help")
            assert result.returncode == 0
            assert result.stdout.startswith('Purpose: Select "All file types" for "Reformat code" and "Optimize imports" on\n')
            assert "Usage:   intellij-workspace-fix [--dry-run]\n" in result.stdout
            assert "close the project" in result.stdout


def write(sandbox, relative, body):
    path = sandbox.home / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body)
    return path


# The state "Tools > Actions on Save > All file types" must end up in, as the IDE writes it, plus the explicit
# `myRunOnSave` that keeps the entry independent of the plugins (the Go plugin's default is `true`, the platform's `false`).
ALL_FILE_TYPES = """\
    <option name="myAllFileTypesSelected" value="true" />
    <option name="myRunOnSave" value="true" />
    <option name="mySelectedFileTypes">
      <set />
    </option>
"""

# What the IDE wrote in a project after the dropdown was switched to "All file types" while the Go plugin was
# installed: `myRunOnSave` equals the Go plugin's default and is therefore left out.
IDE_ALL_FILE_TYPES = """\
    <option name="myAllFileTypesSelected" value="true" />
    <option name="mySelectedFileTypes">
      <set />
    </option>
"""

# What the previous version of the script wrote. Under the Go plugin's defaults it still means "Go files".
RUN_ON_SAVE_ONLY = """\
    <option name="myRunOnSave" value="true" />
"""

GO_FILES = """\
    <option name="myAllFileTypesSelected" value="false" />
    <option name="myRunOnSave" value="true" />
    <option name="mySelectedFileTypes">
      <set>
        <option value="Go" />
      </set>
    </option>
"""

DISABLED = """\
    <option name="myRunOnSave" value="false" />
"""

ONLY_CHANGED_LINES = """\
    <option name="myFormatOnlyChangedLines" value="true" />
"""

GIT = """\
  <component name="Git.Settings">
    <option name="RECENT_GIT_ROOT_PATH" value="$PROJECT_DIR$" />
  </component>
"""

PROBLEMS = """\
  <component name="ProblemsViewState">
    <option name="selectedTabId" value="ProjectErrors" />
  </component>
"""


def component(name, options):
    return f'  <component name="{name}">\n{options}  </component>\n'


def project(*components):
    return '<?xml version="1.0" encoding="UTF-8"?>\n<project version="4">\n' + "".join(components) + "</project>\n"


# The IDE writes the components sorted by name.
WITHOUT_SAVE_OPTIONS = project(GIT, PROBLEMS)
FIXED = project(
    component("FormatOnSaveOptions", ALL_FILE_TYPES), GIT, component("OptimizeOnSaveOptions", ALL_FILE_TYPES), PROBLEMS)


def with_save_options(options, format_extra=""):
    return project(
        component("FormatOnSaveOptions", format_extra + options), GIT, component("OptimizeOnSaveOptions", options), PROBLEMS)
