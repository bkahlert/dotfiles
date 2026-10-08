import subprocess

from repo import BIN_SOURCE, SHIMS, SYSTEM_PATH, isolated_env, require_chezmoi


def test_should_preserve_unmanaged_bin_files(tmp_path):
    home = tmp_path / "home"
    source = tmp_path / "source"
    source_bin = source / "dot_local" / BIN_SOURCE.name
    source_bin.mkdir(parents=True)
    (source_bin / "executable_managed").write_text("#!/bin/sh\n")

    unmanaged = home / ".local" / "bin" / "installer-tool"
    unmanaged.parent.mkdir(parents=True)
    unmanaged.write_text("#!/bin/sh\n")

    result = subprocess.run(
        [require_chezmoi(), "apply", "--source", str(source), "--no-tty"],
        env=isolated_env(home, [str(SHIMS), *SYSTEM_PATH]),
        input="", capture_output=True, text=True, timeout=60)

    assert result.returncode == 0, result.stderr
    assert (home / ".local" / "bin" / "managed").is_file()
    assert unmanaged.exists()
