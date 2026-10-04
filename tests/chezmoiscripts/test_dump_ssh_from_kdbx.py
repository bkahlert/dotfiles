import re
import shutil
import stat
import subprocess
import sys

import pytest
from pykeepass import PyKeePass, create_database

from repo import CHEZMOISCRIPTS_SOURCE, CONTEXTS, HOME_SOURCE, require_chezmoi

PASSWORD = "master"
KDBX = "Library/Mobile Documents/com~apple~CloudDocs/Vault/choam.kdbx"
PUB = b"ssh-ed25519 AAAA key\n"


class TestDumpSshFromKdbx:
    class TestOnRender:
        """The template is rendered by the real chezmoi: a render error aborts the whole `chezmoi apply`."""

        @pytest.mark.parametrize("company", CONTEXTS, ids=lambda c: c or "none")
        def test_should_render_nothing_instead_of_failing_without_a_vault(self, rendered, company):
            result = rendered(company)
            assert (result.returncode, result.stdout) == (0, "")

        @pytest.mark.skipif(sys.platform != "darwin", reason="the script is only rendered on macOS")
        def test_should_embed_the_hash_of_the_vault_so_a_change_reruns_the_script(self, rendered, vault):
            first = rendered("bkahlert").stdout
            vault.entry("pi", file="~/.ssh/conf.d/pi.conf", content="Host pi")
            second = rendered("bkahlert").stdout
            assert first.startswith("#!/usr/bin/env -S uv run --script\n")
            assert re.search(r"^# kdbx-hash: [0-9a-f]{64}  ", first, re.MULTILINE)
            assert re.search(r"^# kdbx-hash: [0-9a-f]{64}  ", second, re.MULTILINE)
            assert first != second

    class TestOnEntries:
        def test_should_join_blocks_sharing_a_file_sorted_by_entry_title(self, vault, dump, sandbox):
            vault.entry("b-pi", file="~/.ssh/conf.d/berries.conf", content="Host b")
            vault.entry("a-pi", file="~/.ssh/conf.d/berries.conf", content="Host a")
            result = dump()
            assert result.returncode == 0
            assert (sandbox.home / ".ssh/conf.d/berries.conf").read_text() == "Host a\n\nHost b\n"

        def test_should_keep_the_conf_file_and_its_directory_private(self, vault, dump, sandbox):
            vault.entry("pi", file="~/.ssh/conf.d/berries.conf", content="Host a")
            dump()
            conf = sandbox.home / ".ssh/conf.d/berries.conf"
            assert stat.S_IMODE(conf.stat().st_mode) == 0o600
            assert stat.S_IMODE(conf.parent.stat().st_mode) == 0o700

        def test_should_report_what_it_wrote(self, vault, dump, sandbox):
            vault.entry("pi", file="~/.ssh/conf.d/berries.conf", content="Host a")
            result = dump()
            assert result.stdout == ("dump-ssh-from-kdbx: 1 conf file(s), 0 pub key(s)\n"
                                     f"  conf  {sandbox.home}/.ssh/conf.d/berries.conf\n")

        @pytest.mark.parametrize("fields", [
            {"file": "~/.ssh/conf.d/x.conf", "content": ""},
            {"file": "", "content": "Host a"},
            {"file": None, "content": None},
        ], ids=["empty content", "empty file", "no fields"])
        def test_should_skip_an_entry_missing_either_field(self, vault, dump, sandbox, fields):
            vault.entry("key-only", **fields)
            result = dump()
            assert result.returncode == 0
            assert not (sandbox.home / ".ssh").exists()

        def test_should_skip_an_entry_in_the_recycle_bin(self, vault, dump, sandbox):
            vault.entry("kept", file="~/.ssh/conf.d/kept.conf", content="Host kept")
            vault.entry("deleted", file="~/.ssh/conf.d/deleted.conf", content="Host deleted", recycle=True)
            dump()
            assert sorted(p.name for p in (sandbox.home / ".ssh/conf.d").iterdir()) == ["kept.conf"]

    class TestOnIdentityFile:
        def test_should_write_the_matching_attachment_to_that_path(self, vault, dump, sandbox):
            vault.entry("pi", file="~/.ssh/conf.d/pi.conf", content="Host pi\n  IdentityFile ~/.ssh/pi.pub",
                        attachments={"pi.pub": PUB})
            result = dump()
            pub = sandbox.home / ".ssh/pi.pub"
            assert result.returncode == 0
            assert pub.read_bytes() == PUB
            assert stat.S_IMODE(pub.stat().st_mode) == 0o600

        def test_should_end_the_public_key_with_exactly_one_newline(self, vault, dump, sandbox):
            vault.entry("pi", file="~/.ssh/conf.d/pi.conf", content="Host pi\n  IdentityFile ~/.ssh/pi.pub",
                        attachments={"pi.pub": PUB.rstrip(b"\n")})
            dump()
            assert (sandbox.home / ".ssh/pi.pub").read_bytes() == PUB

        def test_should_pick_the_attachment_by_file_name(self, vault, dump, sandbox):
            vault.entry("pi", file="~/.ssh/conf.d/pi.conf", content="Host pi\n  IdentityFile ~/.ssh/pi.pub",
                        attachments={"other.pub": b"ssh-ed25519 OTHER\n", "pi.pub": PUB})
            dump()
            assert (sandbox.home / ".ssh/pi.pub").read_bytes() == PUB

        def test_should_abort_before_any_write_on_a_missing_attachment(self, vault, dump, sandbox):
            vault.entry("ok", file="~/.ssh/conf.d/ok.conf", content="Host ok")
            vault.entry("pi", file="~/.ssh/conf.d/pi.conf", content="Host pi\n  IdentityFile ~/.ssh/pi.pub")
            result = dump()
            assert result.returncode == 1
            assert result.stderr.strip() == (
                "entry 'pi': ssh-config-content references IdentityFile "
                f"{sandbox.home}/.ssh/pi.pub but no attachment named 'pi.pub' on the entry. "
                "Aborting before any write.")
            assert not (sandbox.home / ".ssh").exists()

    class TestOnMissingVault:
        def test_should_say_that_iCloud_may_not_be_synced(self, dump, sandbox):
            result = dump()
            assert result.returncode == 1
            assert result.stderr.startswith(f"kdbx not found at {sandbox.home}/{KDBX} (iCloud not synced?")

    class TestOnCancelledPrompt:
        def test_should_exit_without_writing(self, vault, dump, fake_bin, sandbox):
            vault.entry("pi", file="~/.ssh/conf.d/pi.conf", content="Host pi")
            fake_bin("osascript", exit_code=1)
            result = dump()
            assert result.returncode == 1
            assert result.stderr == "cancelled by user\n"
            assert not (sandbox.home / ".ssh").exists()


@pytest.fixture
def rendered(sandbox, tmp_path):
    chezmoi = require_chezmoi()
    template = CHEZMOISCRIPTS_SOURCE / "run_onchange_after_dump-ssh-from-kdbx.tmpl"

    def run(company):
        config = tmp_path / f"{company or 'none'}.toml"
        config.write_text(f'[data]\n  email = "a@b.c"\n  name = "n"\n  company = "{company}"\n')
        return subprocess.run([chezmoi, "execute-template", "--config", str(config), "--source", str(HOME_SOURCE)],
                              input=template.read_text(), env=sandbox.env, cwd=sandbox.home, capture_output=True, text=True, timeout=30)
    return run


@pytest.fixture
def dump(sandbox, fake_bin, tmp_path):
    fake_bin("osascript", stdout=f"{PASSWORD}\n")
    script = tmp_path / "dump-ssh-from-kdbx.py"
    script.write_text(render(CHEZMOISCRIPTS_SOURCE / "run_onchange_after_dump-ssh-from-kdbx.tmpl"))

    def run():
        return subprocess.run([sys.executable, str(script)], env=sandbox.env, cwd=sandbox.home,
                              stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=30)
    return run


@pytest.fixture(scope="session")
def empty_vault(tmp_path_factory):
    path = tmp_path_factory.mktemp("kdbx") / "empty.kdbx"
    kp = create_database(str(path), password=PASSWORD)
    kdf = kp.kdbx.header.value.dynamic_header.kdf_parameters.data.dict
    kdf["I"].value, kdf["M"].value, kdf["P"].value = 1, 64 * 1024, 1
    kp.save()
    return path


@pytest.fixture
def vault(sandbox, empty_vault):
    path = sandbox.home / KDBX
    path.parent.mkdir(parents=True)
    shutil.copy(empty_vault, path)
    return Vault(path)


class Vault:
    def __init__(self, path):
        self.kp = PyKeePass(str(path), password=PASSWORD)

    def entry(self, title, *, file, content, attachments=None, recycle=False):
        entry = self.kp.add_entry(self.kp.root_group, title, "user", "pw")
        for key, value in (("ssh-config-file", file), ("ssh-config-content", content)):
            if value is not None:
                entry.set_custom_property(key, value)
        for name, data in (attachments or {}).items():
            entry.add_attachment(self.kp.add_binary(data), name)
        if recycle:
            self.kp.trash_entry(entry)
        self.kp.save()


def render(template):
    lines = template.read_text().splitlines(keepends=True)
    return "".join(line for line in lines if not re.match(r"\{\{.*\}\}$|# kdbx-hash:", line.rstrip("\n")))
