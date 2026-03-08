# Reduce Chezmoi Templates — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace chezmoi compile-time template conditionals with runtime checks, moving business-specific logic to `conf.d/ista/` so the directory acts as the conditional.

**Architecture:** A single `$DOTFILES_CONTEXT` env var (set by one minimal template) replaces `.is_personal` across the board. OS checks move to `$OSTYPE`/`uname`. Business-only zsh files move to `conf.d/ista/` and are sourced by a second pass in `.zshrc`.

**Tech Stack:** chezmoi, zsh, bash, 1Password CLI (`op`)

**Design doc:** [`docs/plans/2026-03-08-reduce-chezmoi-templates-design.md`](2026-03-08-reduce-chezmoi-templates-design.md)

---

## Task 1: Update chezmoi data model

Replace `is_personal` with `company` in `.chezmoi.toml.tmpl`.

**Files:**
- Modify: `home/.chezmoi.toml.tmpl`

**Step 1: Edit the file**

Replace entire content with:

```toml
[data]
    email = {{ promptStringOnce . "email" "Email address" | quote }}
    name = {{ promptStringOnce . "name" "Full name" | quote }}
    company = {{ promptStringOnce . "company" "Company name (empty for personal)" | quote }}
{{ if (promptStringOnce . "company" "Company name (empty for personal)") -}}
    op_account = {{ promptStringOnce . "op_account" "1Password account UUID (from `op account list`)" | quote }}

[env]
    OP_ACCOUNT = {{ promptStringOnce . "op_account" "1Password account UUID" | quote }}
{{ end -}}
```

**Step 2: Verify syntax**

```bash
chezmoi execute-template < home/.chezmoi.toml.tmpl
```
Expected: renders without error (values will be empty since not prompted).

**Step 3: Commit**

```bash
git add home/.chezmoi.toml.tmpl
git commit -m "refactor: replace is_personal with company in chezmoi data model"
```

---

## Task 2: Create `00-context.zsh.tmpl`

The single minimal template that stamps `$DOTFILES_CONTEXT` at apply time.

**Files:**
- Create: `home/private_dot_config/zsh/exact_conf.d/00-context.zsh.tmpl`

**Step 1: Create the file**

```zsh
{{ if .company -}}
export DOTFILES_CONTEXT="{{ .company }}"
{{ end -}}
```

**Step 2: Verify it renders to empty on this machine**

```bash
chezmoi execute-template < home/private_dot_config/zsh/exact_conf.d/00-context.zsh.tmpl
```
Expected: empty output (this is a personal machine, `company` is unset).

**Step 3: Verify chezmoi diff**

```bash
chezmoi diff ~/.config/zsh/conf.d/00-context.zsh
```
Expected: new empty file would be created (or no diff if chezmoi skips empty files).

**Step 4: Apply**

```bash
chezmoi apply ~/.config/zsh/conf.d/00-context.zsh
```

**Step 5: Commit**

```bash
git add home/private_dot_config/zsh/exact_conf.d/00-context.zsh.tmpl
git commit -m "feat: add 00-context.zsh.tmpl to stamp DOTFILES_CONTEXT"
```

---

## Task 3: Update `.zshrc` — two-pass conf.d loader

**Files:**
- Modify: `home/private_dot_config/zsh/dot_zshrc`

**Step 1: View current loader**

```bash
grep -n "conf.d" home/private_dot_config/zsh/dot_zshrc
```

**Step 2: Replace the single-pass loop with two-pass**

Find:
```zsh
# Source modular configs in order
for config in $ZDOTDIR/conf.d/*.zsh(N); do
  source "$config"
done
```

Replace with:
```zsh
# Source modular configs in order
for config in $ZDOTDIR/conf.d/*.zsh(N); do
  source "$config"
done

# Source company-specific configs (only when DOTFILES_CONTEXT is set)
if [[ -n "$DOTFILES_CONTEXT" ]]; then
  for config in $ZDOTDIR/conf.d/$DOTFILES_CONTEXT/*.zsh(N); do
    source "$config"
  done
fi
```

**Step 3: Verify zsh syntax**

```bash
zsh -n home/private_dot_config/zsh/dot_zshrc
```
Expected: no output (no syntax errors).

**Step 4: Apply and open a new shell to verify it loads cleanly**

```bash
chezmoi apply ~/.config/zsh/.zshrc
zsh -i -c "echo shell ok"
```
Expected: `shell ok`

**Step 5: Commit**

```bash
git add home/private_dot_config/zsh/dot_zshrc
git commit -m "feat: add two-pass conf.d loader for company-specific modules"
```

---

## Task 4: Convert `dot_zprofile.tmpl` → runtime

**Files:**
- Delete: `home/private_dot_config/zsh/dot_zprofile.tmpl`
- Create: `home/private_dot_config/zsh/dot_zprofile`

**Step 1: Create plain file**

```zsh
# Homebrew
if [[ $OSTYPE == darwin* ]] && [[ -x /opt/homebrew/bin/brew ]]; then
  eval "$(/opt/homebrew/bin/brew shellenv)"
elif [[ -x /home/linuxbrew/.linuxbrew/bin/brew ]]; then
  eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"
fi
```

**Step 2: Verify zsh syntax**

```bash
zsh -n home/private_dot_config/zsh/dot_zprofile
```
Expected: no output.

**Step 3: Remove the old template**

```bash
rm home/private_dot_config/zsh/dot_zprofile.tmpl
```

**Step 4: Verify chezmoi diff**

```bash
chezmoi diff ~/.config/zsh/.zprofile
```
Expected: no diff (content is functionally identical on macOS).

**Step 5: Apply**

```bash
chezmoi apply ~/.config/zsh/.zprofile
```

**Step 6: Commit**

```bash
git add home/private_dot_config/zsh/dot_zprofile
git rm home/private_dot_config/zsh/dot_zprofile.tmpl
git commit -m "refactor: convert dot_zprofile.tmpl to runtime OS check"
```

---

## Task 5: Convert `10-path.zsh.tmpl` → runtime

**Files:**
- Delete: `home/private_dot_config/zsh/exact_conf.d/10-path.zsh.tmpl`
- Create: `home/private_dot_config/zsh/exact_conf.d/10-path.zsh`

**Step 1: Create plain file**

```zsh
# Local bins
PATH="$HOME/.local/bin:/usr/local/sbin:$PATH"

# JetBrains Toolbox (macOS)
[[ -d "$HOME/Library/Application Support/JetBrains/Toolbox/scripts" ]] \
  && PATH="$PATH:$HOME/Library/Application Support/JetBrains/Toolbox/scripts"

# Python user install (macOS)
[[ -d "$HOME/Library/Python/3.11/bin" ]] \
  && PATH="$HOME/Library/Python/3.11/bin:$PATH"

# Kubernetes tools
PATH="$HOME/.krew/bin:$HOME/.arkade/bin:$PATH"

# Deduplicate PATH
export -U PATH
```

**Step 2: Verify syntax**

```bash
zsh -n home/private_dot_config/zsh/exact_conf.d/10-path.zsh
```

**Step 3: Remove old template**

```bash
rm home/private_dot_config/zsh/exact_conf.d/10-path.zsh.tmpl
```

**Step 4: Apply and verify PATH includes local bin**

```bash
chezmoi apply ~/.config/zsh/conf.d/10-path.zsh
zsh -i -c "echo $PATH" | tr ':' '\n' | grep local
```
Expected: `~/.local/bin` appears.

**Step 5: Commit**

```bash
git add home/private_dot_config/zsh/exact_conf.d/10-path.zsh
git rm home/private_dot_config/zsh/exact_conf.d/10-path.zsh.tmpl
git commit -m "refactor: convert 10-path.zsh.tmpl to directory existence checks"
```

---

## Task 6: Convert `10-java.zsh.tmpl` → runtime

**Files:**
- Delete: `home/private_dot_config/zsh/exact_conf.d/10-java.zsh.tmpl`
- Create: `home/private_dot_config/zsh/exact_conf.d/10-java.zsh`

**Step 1: Create plain file**

```zsh
[[ $OSTYPE == darwin* ]] || return 0

if command -v brew &>/dev/null; then
  local brew_jdk="$(brew --prefix)/opt/openjdk/libexec/openjdk.jdk"
  local system_jdk='/Library/Java/JavaVirtualMachines/openjdk.jdk'

  if [ -r "$brew_jdk" ] && [ ! -e "$system_jdk" ]; then
    sudo ln -sfn "$brew_jdk" "$system_jdk" 2>/dev/null
  fi

  [ -e "$system_jdk" ] && JAVA_HOME="$system_jdk/Contents/Home"
  [ -x "$JAVA_HOME/bin/java" ] || JAVA_HOME=$(/usr/libexec/java_home 2>/dev/null)
  export JAVA_HOME
fi
```

**Step 2: Verify syntax**

```bash
zsh -n home/private_dot_config/zsh/exact_conf.d/10-java.zsh
```

**Step 3: Remove old template**

```bash
rm home/private_dot_config/zsh/exact_conf.d/10-java.zsh.tmpl
```

**Step 4: Apply**

```bash
chezmoi apply ~/.config/zsh/conf.d/10-java.zsh
```

**Step 5: Commit**

```bash
git add home/private_dot_config/zsh/exact_conf.d/10-java.zsh
git rm home/private_dot_config/zsh/exact_conf.d/10-java.zsh.tmpl
git commit -m "refactor: convert 10-java.zsh.tmpl to runtime OS check"
```

---

## Task 7: Split `10-gitlab.zsh.tmpl` → generic + ista

**Files:**
- Delete: `home/private_dot_config/zsh/exact_conf.d/10-gitlab.zsh.tmpl`
- Create: `home/private_dot_config/zsh/exact_conf.d/10-gitlab.zsh`
- Create: `home/private_dot_config/zsh/exact_conf.d/ista/10-gitlab.zsh`

**Step 1: Create the ista subdirectory**

```bash
mkdir -p home/private_dot_config/zsh/exact_conf.d/ista
```

**Step 2: Create generic `10-gitlab.zsh`**

```zsh
# Auto-install glab CLI wrapper
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

**Step 3: Create `ista/10-gitlab.zsh`**

```zsh
# GitLab private token — only fetch when IntelliJ is reading the shell environment
if [[ -n "${INTELLIJ_ENVIRONMENT_READER}" ]]; then
  export GITLAB_PRIVATE_TOKEN="$(op read "op://Employee/GitLab Token/credential")"
fi
```

**Step 4: Verify syntax on both files**

```bash
zsh -n home/private_dot_config/zsh/exact_conf.d/10-gitlab.zsh
zsh -n home/private_dot_config/zsh/exact_conf.d/ista/10-gitlab.zsh
```

**Step 5: Remove old template**

```bash
rm home/private_dot_config/zsh/exact_conf.d/10-gitlab.zsh.tmpl
```

**Step 6: Apply generic file**

```bash
chezmoi apply ~/.config/zsh/conf.d/10-gitlab.zsh
```

**Step 7: Commit**

```bash
git add home/private_dot_config/zsh/exact_conf.d/10-gitlab.zsh
git add home/private_dot_config/zsh/exact_conf.d/ista/10-gitlab.zsh
git rm home/private_dot_config/zsh/exact_conf.d/10-gitlab.zsh.tmpl
git commit -m "refactor: split 10-gitlab.zsh.tmpl into generic + ista/ token"
```

---

## Task 8: Move `10-dev-chapter.zsh.tmpl` → `ista/`

**Files:**
- Delete: `home/private_dot_config/zsh/exact_conf.d/10-dev-chapter.zsh.tmpl`
- Create: `home/private_dot_config/zsh/exact_conf.d/ista/10-dev-chapter.zsh`

**Step 1: Copy content, strip template wrapper**

Copy the file body (everything between `{{ if not .is_personal -}}` and `{{ end -}}`) to `ista/10-dev-chapter.zsh`.

**Step 2: Verify syntax**

```bash
zsh -n home/private_dot_config/zsh/exact_conf.d/ista/10-dev-chapter.zsh
```

**Step 3: Remove old template**

```bash
rm home/private_dot_config/zsh/exact_conf.d/10-dev-chapter.zsh.tmpl
```

**Step 4: Commit**

```bash
git add home/private_dot_config/zsh/exact_conf.d/ista/10-dev-chapter.zsh
git rm home/private_dot_config/zsh/exact_conf.d/10-dev-chapter.zsh.tmpl
git commit -m "refactor: move 10-dev-chapter.zsh.tmpl to ista/ — directory is the conditional"
```

---

## Task 9: Move `10-gcloud.zsh.tmpl` → `ista/`

**Files:**
- Delete: `home/private_dot_config/zsh/exact_conf.d/10-gcloud.zsh.tmpl`
- Create: `home/private_dot_config/zsh/exact_conf.d/ista/10-gcloud.zsh`

**Step 1: Copy content, strip template wrapper**

Copy the file body (everything between `{{ if not .is_personal -}}` and `{{ end -}}`) to `ista/10-gcloud.zsh`.

**Step 2: Verify syntax**

```bash
zsh -n home/private_dot_config/zsh/exact_conf.d/ista/10-gcloud.zsh
```

**Step 3: Remove old template**

```bash
rm home/private_dot_config/zsh/exact_conf.d/10-gcloud.zsh.tmpl
```

**Step 4: Commit**

```bash
git add home/private_dot_config/zsh/exact_conf.d/ista/10-gcloud.zsh
git rm home/private_dot_config/zsh/exact_conf.d/10-gcloud.zsh.tmpl
git commit -m "refactor: move 10-gcloud.zsh.tmpl to ista/ — directory is the conditional"
```

---

## Task 10: Convert `run_once_before_00-install-homebrew.sh.tmpl`

Move the OS check from template to runtime. Note: chezmoi will treat this as a
new script (content changed) and re-run it — this is safe since `brew` install
is idempotent.

**Files:**
- Delete: `home/.chezmoiscripts/run_once_before_00-install-homebrew.sh.tmpl`
- Create: `home/.chezmoiscripts/run_once_before_00-install-homebrew.sh`

**Step 1: Create plain script**

```bash
#!/usr/bin/env bash
# Purpose: Install Homebrew if not already installed.
# Usage:   Run automatically by chezmoi on first apply.

set -euo pipefail

[[ $(uname) == Darwin ]] || exit 0

if ! command -v brew &>/dev/null; then
  echo "Installing Homebrew..."
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
fi
```

**Step 2: Make executable**

```bash
chmod +x home/.chezmoiscripts/run_once_before_00-install-homebrew.sh
```

**Step 3: Verify syntax**

```bash
bash -n home/.chezmoiscripts/run_once_before_00-install-homebrew.sh
```

**Step 4: Remove old template**

```bash
rm home/.chezmoiscripts/run_once_before_00-install-homebrew.sh.tmpl
```

**Step 5: Commit**

```bash
git add home/.chezmoiscripts/run_once_before_00-install-homebrew.sh
git rm home/.chezmoiscripts/run_once_before_00-install-homebrew.sh.tmpl
git commit -m "refactor: convert install-homebrew script to runtime OS check"
```

---

## Task 11: Convert `run_once_before_01-install-packages.sh.tmpl`

**Files:**
- Delete: `home/.chezmoiscripts/run_once_before_01-install-packages.sh.tmpl`
- Create: `home/.chezmoiscripts/run_once_before_01-install-packages.sh`

**Step 1: Create plain script**

```bash
#!/usr/bin/env bash
# Purpose: Install core packages via Homebrew (macOS) or curl (Linux).
# Usage:   Run automatically by chezmoi on first apply.

set -euo pipefail

if [[ $(uname) == Darwin ]]; then
  brew bundle --file=/dev/stdin <<EOF
brew "sheldon"
brew "starship"
brew "zoxide"
brew "bat"
brew "jq"
brew "btop"
cask "1password-cli"
cask "font-jetbrains-mono-nerd-font"
EOF

else
  # Sheldon
  if ! command -v sheldon &>/dev/null; then
    curl --proto '=https' -fLsS https://rossmacarthur.github.io/install/crate.sh \
      | bash -s -- --repo rossmacarthur/sheldon --to ~/.local/bin
  fi

  # Starship
  if ! command -v starship &>/dev/null; then
    curl -sS https://starship.rs/install.sh | sh -s -- --yes
  fi

  # zoxide
  if ! command -v zoxide &>/dev/null; then
    curl -sSfL https://raw.githubusercontent.com/ajeetdsouza/zoxide/main/install.sh | sh
  fi
fi
```

**Step 2: Make executable and verify syntax**

```bash
chmod +x home/.chezmoiscripts/run_once_before_01-install-packages.sh
bash -n home/.chezmoiscripts/run_once_before_01-install-packages.sh
```

**Step 3: Remove old template**

```bash
rm home/.chezmoiscripts/run_once_before_01-install-packages.sh.tmpl
```

**Step 4: Commit**

```bash
git add home/.chezmoiscripts/run_once_before_01-install-packages.sh
git rm home/.chezmoiscripts/run_once_before_01-install-packages.sh.tmpl
git commit -m "refactor: convert install-packages script to runtime OS check"
```

---

## Task 12: Convert `run_once_after_setup-startup-launchagent.sh.tmpl`

**Files:**
- Delete: `home/.chezmoiscripts/run_once_after_setup-startup-launchagent.sh.tmpl`
- Create: `home/.chezmoiscripts/run_once_after_setup-startup-launchagent.sh`

**Step 1: Read the full current file**

```bash
cat home/.chezmoiscripts/run_once_after_setup-startup-launchagent.sh.tmpl
```

**Step 2: Create plain script**

Strip `{{ if eq .chezmoi.os "darwin" -}}` / `{{ end -}}` wrapper. Add at top:

```bash
#!/usr/bin/env bash
# Purpose: Sets up a LaunchAgent that runs ~/.startup at login.
# Usage:   Run automatically by chezmoi on first apply. Re-run with: chezmoi apply --force

set -euo pipefail

[[ $(uname) == Darwin ]] || exit 0
```

Then paste the rest of the body unchanged.

**Step 3: Make executable and verify syntax**

```bash
chmod +x home/.chezmoiscripts/run_once_after_setup-startup-launchagent.sh
bash -n home/.chezmoiscripts/run_once_after_setup-startup-launchagent.sh
```

**Step 4: Remove old template**

```bash
rm home/.chezmoiscripts/run_once_after_setup-startup-launchagent.sh.tmpl
```

**Step 5: Commit**

```bash
git add home/.chezmoiscripts/run_once_after_setup-startup-launchagent.sh
git rm home/.chezmoiscripts/run_once_after_setup-startup-launchagent.sh.tmpl
git commit -m "refactor: convert setup-startup-launchagent script to runtime OS check"
```

---

## Task 13: SSH config — introduce Include structure

**Files:**
- Modify: `home/private_dot_ssh/private_config.tmpl` → `home/private_dot_ssh/private_config`
- Create: `home/private_dot_ssh/private_conf.d/ista/10-1password-agent.conf.tmpl`

**Step 1: Create directory structure**

```bash
mkdir -p home/private_dot_ssh/private_conf.d/ista
```

**Step 2: Create plain `private_config`**

```
Include conf.d/*.conf
Include conf.d/ista/*.conf
```

**Step 3: Create `ista/10-1password-agent.conf.tmpl`**

```
{{ if eq .chezmoi.os "darwin" -}}
Host *
	IdentityAgent "~/Library/Group Containers/2BUA8C4S2C.com.1password/t/agent.sock"
{{ end -}}
```

**Step 4: Remove old template**

```bash
rm home/private_dot_ssh/private_config.tmpl
```

**Step 5: Apply and verify SSH config**

```bash
chezmoi apply ~/.ssh/config
cat ~/.ssh/config
```
Expected: shows Include directives.

**Step 6: Commit**

```bash
git add home/private_dot_ssh/private_config
git add home/private_dot_ssh/private_conf.d/ista/10-1password-agent.conf.tmpl
git rm home/private_dot_ssh/private_config.tmpl
git commit -m "refactor: split SSH config — Include structure with ista/ for 1Password agent"
```

---

## Task 14: Update remaining templates to use `company` instead of `is_personal`

Update `dot_npmrc.tmpl` and `accounts.json.tmpl` to use `{{ if .company }}` instead of `{{ if not .is_personal }}`.

**Files:**
- Modify: `home/dot_npmrc.tmpl`
- Modify: `home/private_dot_config/copy-password/accounts.json.tmpl`

**Step 1: Update `dot_npmrc.tmpl`**

Replace `{{ if not .is_personal -}}` with `{{ if .company -}}`.

**Step 2: Update `accounts.json.tmpl`**

Replace `{{ if not .is_personal -}}` / `{{ else if not .is_personal -}}` etc. with `{{ if .company -}}`.

**Step 3: Verify diff is clean**

```bash
chezmoi diff
```
Expected: no changes to `~/.npmrc` or `~/.config/copy-password/accounts.json` on this machine (personal, `company` is empty either way).

**Step 4: Commit**

```bash
git add home/dot_npmrc.tmpl home/private_dot_config/copy-password/accounts.json.tmpl
git commit -m "refactor: replace is_personal with company in remaining templates"
```

---

## Final verification

```bash
chezmoi diff
```
Expected: only the `run_once` scripts show (they re-run due to content change — safe, idempotent).

```bash
# Count remaining templates (should be 5: .chezmoi.toml, gitconfig, npmrc, accounts.json, sheldon-lock + 2 new minimal ones)
find home -name "*.tmpl" | sort
```
