# Reduce Chezmoi Templates — Design

## Goal

Replace compile-time chezmoi template conditionals with runtime checks wherever
possible. Where business-specific logic exists, move it to a company-namespaced
subdirectory so the directory itself acts as the conditional.

---

## Runtime Context Signal

### Problem

Many templates branch on `.is_personal`. This is a compile-time flag with no
runtime equivalent, making every consumer a template.

### Solution: `$DOTFILES_CONTEXT`

Add a `company` prompt to `.chezmoi.toml.tmpl`:

```toml
company = {{ promptStringOnce . "company" "Company name (empty for personal)" | quote }}
```

Remove the `is_personal` prompt entirely. Presence/absence of `company` is the
new source of truth.

Deploy a single minimal template as the first conf.d file:

**`home/private_dot_config/zsh/exact_conf.d/00-context.zsh.tmpl`**
```zsh
{{ if .company -}}
export DOTFILES_CONTEXT="{{ .company }}"
{{ end -}}
```

On personal machines this renders to an empty file. On business machines it
exports `DOTFILES_CONTEXT=ista`. All subsequent conf.d files can branch on
`$DOTFILES_CONTEXT` at runtime.

---

## conf.d Structure

### Loader (`.zshrc`)

Two-pass sourcing — generic first, company-specific after:

```zsh
# Pass 1 — generic modules
for f in "${ZDOTDIR}/conf.d/"*.zsh(N); do source "$f"; done

# Pass 2 — company-specific modules
if [[ -n "$DOTFILES_CONTEXT" ]]; then
  for f in "${ZDOTDIR}/conf.d/${DOTFILES_CONTEXT}/"*.zsh(N); do
    source "$f"
  done
fi
```

### Files Moved to `conf.d/ista/` (plain `.zsh`, no template)

The `ista/` directory is the conditional — no `{{ if .company }}` guard needed.

| Old | New |
|---|---|
| `conf.d/10-dev-chapter.zsh.tmpl` | `conf.d/ista/10-dev-chapter.zsh` |
| `conf.d/10-gcloud.zsh.tmpl` | `conf.d/ista/10-gcloud.zsh` |

### Files Split — Generic + Business

**`10-gitlab.zsh.tmpl`** splits into two plain files:

`conf.d/10-gitlab.zsh` — generic `glab` auto-install wrapper, always sourced:
```zsh
glab() {
  if ! command -v glab &>/dev/null; then
    if command -v brew &>/dev/null; then
      echo "glab not found — installing via Homebrew..."
      brew install glab || return 1
    else
      echo "glab not found and Homebrew is not available. Please install glab manually."
      return 1
    fi
  fi
  command glab "$@"
}
```

`conf.d/ista/10-gitlab.zsh` — token, lazy via `$INTELLIJ_ENVIRONMENT_READER`:
```zsh
# Only fetch when IntelliJ is reading the shell environment
if [[ -n "${INTELLIJ_ENVIRONMENT_READER}" ]]; then
  export GITLAB_PRIVATE_TOKEN="$(op read "op://Employee/GitLab Token/credential")"
fi
```

### Files Converted to Runtime OS Check (stay in `conf.d/`)

| Old | New | Check |
|---|---|---|
| `10-java.zsh.tmpl` | `10-java.zsh` | `[[ $OSTYPE == darwin* ]]` |
| `10-path.zsh.tmpl` | `10-path.zsh` | `[[ -d <path> ]]` existence |

---

## `.zprofile`

`dot_zprofile.tmpl` uses only a `chezmoi.os` check for Homebrew. Convert to
plain `dot_zprofile` with runtime check:

```zsh
# Homebrew
if [[ $OSTYPE == darwin* ]] && [[ -x /opt/homebrew/bin/brew ]]; then
  eval "$(/opt/homebrew/bin/brew shellenv)"
elif [[ -x /home/linuxbrew/.linuxbrew/bin/brew ]]; then
  eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"
fi
```

---

## Install Scripts

`run_once` scripts currently gated by `{{ if eq .chezmoi.os "darwin" }}`.
Replace with `uname` checks inside the script body and drop `.tmpl`:

```bash
[[ $(uname) == Darwin ]] || { echo "Skipping: macOS only"; exit 0; }
```

Applies to:
- `run_once_before_00-install-homebrew.sh.tmpl`
- `run_once_before_01-install-packages.sh.tmpl`
- `run_once_after_setup-startup-launchagent.sh.tmpl`

Note: `run_onchange_after_sheldon-lock.sh.tmpl` **must stay a template** — it
uses `{{ include … | sha256sum }}` for chezmoi change detection, which has no
runtime equivalent.

---

## SSH Config

SSH config is static — no runtime conditionals. Apply the same
`ista/` subdirectory pattern using SSH's native `Include` directive.

**`home/private_dot_ssh/private_config`** (non-template):
```
Include conf.d/*.conf
Include conf.d/ista/*.conf
```

**`home/private_dot_ssh/private_conf.d/ista/10-1password-agent.conf.tmpl`**
(template retained for OS check only — SSH config has no runtime equivalent):
```
{{ if eq .chezmoi.os "darwin" -}}
Host *
    IdentityAgent "~/Library/Group Containers/2BUA8C4S2C.com.1password/t/agent.sock"
{{ end -}}
```

This removes the `is_personal`/`company` condition from the template. The `ista/`
directory acts as the business conditional; only the macOS check remains.

---

## Templates: Before / After

### Eliminated entirely

| File | Mechanism |
|---|---|
| `conf.d/10-dev-chapter.zsh.tmpl` | Moved to `conf.d/ista/` |
| `conf.d/10-gcloud.zsh.tmpl` | Moved to `conf.d/ista/` |
| `conf.d/10-gitlab.zsh.tmpl` | Split; runtime `op read` in `ista/` |
| `conf.d/10-java.zsh.tmpl` | Runtime `$OSTYPE` check |
| `conf.d/10-path.zsh.tmpl` | Runtime directory existence checks |
| `dot_zprofile.tmpl` | Runtime `$OSTYPE` check |
| `run_once_before_00-install-homebrew.sh.tmpl` | Runtime `uname` check |
| `run_once_before_01-install-packages.sh.tmpl` | Runtime `uname` check |
| `run_once_after_setup-startup-launchagent.sh.tmpl` | Runtime `uname` check |

### New (minimal)

| File | Purpose |
|---|---|
| `conf.d/00-context.zsh.tmpl` | Stamps `$DOTFILES_CONTEXT` at apply time |
| `private_dot_ssh/private_conf.d/ista/10-1password-agent.conf.tmpl` | SSH: OS check only |

### Unchanged (genuinely need templates)

| File | Reason |
|---|---|
| `.chezmoi.toml.tmpl` | Chezmoi config itself |
| `dot_gitconfig.tmpl` | `.name` / `.email` interpolation |
| `dot_npmrc.tmpl` | 1Password secret in static config |
| `accounts.json.tmpl` | 1Password secret in static config |
| `run_onchange_after_sheldon-lock.sh.tmpl` | Chezmoi `sha256sum` change detection |
