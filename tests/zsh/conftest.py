import pytest


@pytest.fixture
def uninherited_brew(sandbox):
    """A shell that did not inherit `brew shellenv`: no HOMEBREW_PREFIX, but brew at <prefix>/bin first on PATH. Returns
    the prefix. That brew fails when run, so a module that forks it shows on stderr."""
    prefix = sandbox.home / "brew-prefix"
    (prefix / "bin").mkdir(parents=True)
    (prefix / "bin" / "brew").write_text("#!/bin/sh\necho 'brew: must not run' >&2\nexit 1\n")
    (prefix / "bin" / "brew").chmod(0o755)
    sandbox.env.pop("HOMEBREW_PREFIX", None)
    sandbox.env["PATH"] = f"{prefix / 'bin'}:{sandbox.env['PATH']}"
    return prefix
