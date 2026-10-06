# Company-Specific Dotfiles Split Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the public dotfiles checkout company-neutral and create a complete local downstream checkout at `../dotfiles-ista` for work machines.

**Architecture:** Keep the public split on a local topic branch and preserve the existing public history. Create the internal checkout from public `main` before removing work files publicly, then make its work configuration unconditional; each machine continues to use exactly one chezmoi source.

**Tech Stack:** Git, chezmoi templates and ignore rules, zsh, Bash, pytest, Make, Podman or Docker.

**Spec:** `docs/superpowers/specs/2026-10-06-dotfiles-company-split-design.md`

## Global Constraints

- Each machine uses one chezmoi source: public for general use, internal for work.
- The internal checkout is `../dotfiles-ista`; work configuration there is unconditional and has no `.company` profile gate.
- Preserve public history; do not rewrite existing public commits.
- Keep public `main` unchanged during local implementation; make public changes on a local topic branch.
- Commit this reviewed implementation plan on the public topic branch before starting the implementation tasks.
- Do not create or configure a hosted internal remote, publish either checkout, or apply changes to `$HOME`.
- Do not perform the later internal rebase; it requires the public split to be squash-merged and separate user authorization.
- Retain shared behavior and supporting tests/docs in both checkouts where needed; move all company-specific source state and its supporting tests/docs to the internal checkout.

## Review Focus

- Personal/public template rendering must work without `.company` data; pin the KeePassXC Context7-secret path in `tests/templates/test_context7_api_key.py`.
- Work-only secret templates, files, and required tools must remain available unconditionally internally; pin rendered work secrets/file inclusion in internal template and secret-file tests and assert `glab`/`1password-cli` in `tests/chezmoiscripts/test_install_packages.py`.
- macOS/Linux ignore rules must still distinguish platform-specific files without company profiles; pin both OS cases in `tests/templates/test_chezmoiignore.py`.
- The public checkout must not deploy work-only files, while the internal checkout must not gate them; pin both expected ignored/included path sets in each checkout's `test_chezmoiignore.py`.
- Applying either checkout must start a silent login shell with no profile environment variable; pin this in container and native integration tests.

---

### Task 1: Create the local internal checkout before the public split

**Files:**
- Create repository: `../dotfiles-ista`

**Interfaces:**
- Consumes: the clean public `main` history and the existing public `origin` URL.
- Produces: a local `ista` branch rooted at public `main`, with the public GitHub remote retained and no internal hosted remote.

- [ ] **Step 1: Verify the destination does not exist and the public topic branch is not `main`**

Run from the public repository root:

```bash
test ! -e ../dotfiles-ista
test "$(git branch --show-current)" != main
test -z "$(git status --porcelain)"
```

Expected: destination absent, current branch is the local topic branch, and no unrelated changes are present.

- [ ] **Step 2: Clone public `main` locally and create the internal branch**

```bash
git clone --no-hardlinks --branch main . ../dotfiles-ista
git -C ../dotfiles-ista remote set-url origin "$(git remote get-url origin)"
git -C ../dotfiles-ista switch -c ista
```

Expected: `../dotfiles-ista` contains the public `main` history, branch `ista` is checked out, and `origin` points only to the public repository.

- [ ] **Step 3: Verify ancestry and remote state**

Run:

```bash
git -C ../dotfiles-ista merge-base --is-ancestor "$(git rev-parse main)" ista
git -C ../dotfiles-ista remote -v
git rev-parse main
```

Record the public `main` SHA. Expected: the ancestry check succeeds; no internal-hosted remote is configured.

---

### Task 2: Make work configuration unconditional in the internal checkout

**Files:**
- Modify: `../dotfiles-ista/home/.chezmoi.toml.tmpl`
- Modify: `../dotfiles-ista/home/.chezmoiignore`
- Modify: `../dotfiles-ista/home/private_dot_config/zsh/dot_zshrc`
- Retain: `../dotfiles-ista/home/private_dot_config/zsh/exact_conf.d/exact_ista/`
- Retain: `../dotfiles-ista/home/private_dot_config/starship.toml`
- Retain: `../dotfiles-ista/home/private_dot_npmrc.tmpl`
- Retain: `../dotfiles-ista/home/private_dot_ssh/private_conf.d/20-ista-1password.conf.tmpl`
- Retain: `../dotfiles-ista/home/dot_local/share/private_secrets/private_{context7_api_key,gitlab_token}.tmpl`
- Retain: `../dotfiles-ista/home/dot_local/exact_bin/executable_{gcloud-login,op-agent}`
- Retain: `../dotfiles-ista/home/dot_agents/skills/gcloud-{auth,login-automation}/`
- Retain: `../dotfiles-ista/home/.chezmoiscripts/run_once_before_01-install-packages.sh`
- Modify: `../dotfiles-ista/entrypoint.sh`
- Modify: `../dotfiles-ista/AGENTS.md`
- Modify: `../dotfiles-ista/quick-access/README.md`
- Modify: `../dotfiles-ista/tests/repo.py`
- Modify: `../dotfiles-ista/tests/templates/conftest.py`
- Modify: `../dotfiles-ista/tests/chezmoiscripts/conftest.py`
- Modify: `../dotfiles-ista/tests/templates/test_{chezmoi_toml,chezmoiignore,context7_api_key,gitlab_token,npmrc,ista_1password_conf}.py`
- Modify: `../dotfiles-ista/tests/{test_secret_files,test_copilot_config,test_bash_version}.py`
- Modify: `../dotfiles-ista/tests/bin/test_{gcloud_login,op_agent}.py`
- Modify: `../dotfiles-ista/tests/chezmoiscripts/test_dump_ssh_from_kdbx.py`
- Modify: `../dotfiles-ista/tests/chezmoiscripts/test_install_packages.py`
- Modify: `../dotfiles-ista/tests/integration/test_apply_{container,native}.py`

**Interfaces:**
- Consumes: the public-history checkout created in Task 1.
- Produces: an internal source tree with all approved work files, installed work tools, no `.company` gating, and accurate work-specific guidance.

- [ ] **Step 1: Add failing internal tests for unconditional work deployment**

Update the internal chezmoi fixtures and `tests/templates/test_{chezmoiignore,chezmoi_toml}.py` to assert that the internal source does not require a `company` data value and includes work-only targets on macOS and Linux. Add an assertion to `tests/chezmoiscripts/test_install_packages.py` that `glab` and `1password-cli` are installed. Remove company parameterization from internal shared tests and both native and container integration tests; run them without `DOTFILES_COMPANY`.

- [ ] **Step 2: Run the focused tests to verify the current profile-gated source fails**

Run from `../dotfiles-ista`:

```bash
pytest tests/templates/test_chezmoiignore.py tests/templates/test_chezmoi_toml.py tests/chezmoiscripts/test_install_packages.py
```

Expected: failures identify the `.company` prompt or work-only targets not being included without the profile value.

- [ ] **Step 3: Remove profile selection from the internal source**

Remove the `company` data prompt/value from `.chezmoi.toml.tmpl` and its branches from `.chezmoiignore`. Make the zsh loader source the work modules unconditionally. Retain platform-only ignores and all work files. Keep the Context7 key template on the 1Password backend internally; retain GitLab/npm/SSH/gcloud configuration.

- [ ] **Step 4: Keep work packages and documentation aligned**

Retain `glab` and `1password-cli` in the internal package installer. Update internal `AGENTS.md` and `quick-access/README.md` to describe the unconditional work configuration and the actual moved source/test locations; do not document `.company` as a runtime selector.

- [ ] **Step 5: Run internal focused tests**

Run:

```bash
pytest tests/templates/test_chezmoiignore.py tests/templates/test_chezmoi_toml.py tests/templates/test_context7_api_key.py tests/templates/test_gitlab_token.py tests/templates/test_npmrc.py tests/templates/test_ista_1password_conf.py tests/chezmoiscripts/test_install_packages.py tests/test_secret_files.py
```

Expected: all focused unit tests pass.

- [ ] **Step 6: Commit the internal work configuration**

```bash
git -C ../dotfiles-ista add home tests entrypoint.sh AGENTS.md quick-access/README.md
git -C ../dotfiles-ista commit -m "feat: make work dotfiles unconditional"
```

---

### Task 3: Remove company-specific behavior from the public checkout

**Files:**
- Modify: `home/.chezmoi.toml.tmpl`
- Modify: `home/.chezmoiignore`
- Modify: `home/private_dot_config/zsh/dot_zshrc`
- Remove from current tree: `home/private_dot_config/zsh/exact_conf.d/exact_ista/`
- Modify: `home/private_dot_config/starship.toml`
- Remove: `home/private_dot_npmrc.tmpl`
- Remove: `home/private_dot_ssh/private_conf.d/20-ista-1password.conf.tmpl`
- Modify: `home/dot_local/share/private_secrets/private_context7_api_key.tmpl`
- Remove: `home/dot_local/share/private_secrets/private_gitlab_token.tmpl`
- Remove: `home/dot_local/exact_bin/executable_{gcloud-login,op-agent}`
- Remove: `home/dot_agents/skills/gcloud-{auth,login-automation}/`
- Modify: `home/.chezmoiscripts/run_once_before_01-install-packages.sh`
- Modify: `entrypoint.sh`
- Modify: `AGENTS.md`
- Modify: `quick-access/README.md`
- Modify: `tests/repo.py`, `tests/templates/conftest.py`, and `tests/chezmoiscripts/conftest.py`
- Modify: `tests/templates/test_{chezmoi_toml,chezmoiignore,context7_api_key,gitconfig}.py`
- Remove from public: `tests/templates/test_{gitlab_token,npmrc,ista_1password_conf}.py`
- Modify: `tests/bin/test_{gcloud_login,op_agent,bash_version}.py` (delete work-only tests; retain public Bash coverage)
- Modify: `tests/test_{secret_files,copilot_config}.py`
- Modify: `tests/chezmoiscripts/test_dump_ssh_from_kdbx.py`
- Modify: `tests/chezmoiscripts/test_install_packages.py`
- Modify: `tests/integration/test_apply_{container,native}.py`

**Interfaces:**
- Consumes: the original public files, still present in Git history and in the internal checkout.
- Produces: a public current tree with general-purpose configuration only; shared KeePassXC, Claude/Copilot, and shell behavior remain public.

- [ ] **Step 1: Add failing public assertions for profile-neutral behavior**

Update public template tests to render without a `company` value, verify the personal KeePassXC Context7 secret path, and verify work-only targets are ignored for each supported OS. Add an assertion to `tests/chezmoiscripts/test_install_packages.py` that `glab` and `1password-cli` are absent. Remove profile parameterization from shared tests such as Copilot configuration and the KeePassXC SSH-dump script.

- [ ] **Step 2: Run focused tests to establish the failures**

Run:

```bash
pytest tests/templates/test_chezmoi_toml.py tests/templates/test_chezmoiignore.py tests/templates/test_context7_api_key.py tests/templates/test_gitconfig.py tests/chezmoiscripts/test_install_packages.py tests/test_copilot_config.py tests/chezmoiscripts/test_dump_ssh_from_kdbx.py
```

Expected: failures are limited to the profile prompts/branches, package ownership assertion, and context parameterization being removed.

- [ ] **Step 3: Remove profile selectors and work-only source files**

Remove the company data prompt and profile branches from `.chezmoi.toml.tmpl` and `.chezmoiignore`; remove work module loading and gcloud aliases; retain the shared Context7 secret template using KeePassXC. Remove work-only SSH/npm/GitLab/gcloud files and skills from the public current tree. Keep their historical commits unchanged.

- [ ] **Step 4: Keep public package setup and guidance general**

Remove `glab` and `1password-cli` from the public Homebrew bundle, retaining KeePassXC. Add assertions to `tests/chezmoiscripts/test_install_packages.py` that those work-only tools are absent. Revise public `AGENTS.md` and `quick-access/README.md` to remove active work-only instructions and paths while preserving the general conventions. Retain generic sandbox guards for `glab` and `op`; those are not company-specific behavior.

- [ ] **Step 5: Remove company-profile test infrastructure**

Remove `CONTEXTS` and company arguments from `tests/repo.py`, template and chezmoiscript fixtures, and native/container integration tests. Remove `DOTFILES_COMPANY` handling from `entrypoint.sh`; generate only shared chezmoi data. Delete work-only tests whose subjects moved internally, and adjust shared `test_bash_version.py`/secret-file tests to cover only public subjects.

- [ ] **Step 6: Run public focused tests**

Run:

```bash
pytest tests/templates tests/chezmoiscripts/test_dump_ssh_from_kdbx.py tests/chezmoiscripts/test_install_packages.py tests/test_copilot_config.py tests/test_secret_files.py tests/test_bash_version.py
```

Expected: all focused unit tests pass.

- [ ] **Step 7: Commit the public split**

```bash
git add home tests entrypoint.sh AGENTS.md quick-access/README.md
git commit -m "refactor: remove company-specific dotfiles"
```

---

### Task 4: Verify both local checkouts and the migration boundary

**Files:**
- Verify: public checkout and `../dotfiles-ista`
- Modify only if needed: tests and documentation in the checkout whose behavior they describe

**Interfaces:**
- Consumes: completed public split and internal work configuration from Tasks 2–3.
- Produces: evidence that both trees meet the spec without publishing, rewriting history, or applying to the host.

- [ ] **Step 1: Run lint and unit tests in both checkouts**

Run `make lint && make unit` in the public checkout, then the same commands in `../dotfiles-ista`.

Expected: both commands succeed in both repositories.

- [ ] **Step 2: Run container integration in both checkouts when available**

Run `make integration` in each checkout if Podman or Docker is available. If unavailable, record the skipped validation explicitly.

Expected: each available run applies its own source to a temporary home and starts a silent login shell; do not run `chezmoi apply` against the real home.

- [ ] **Step 3: Verify public and internal source boundaries**

Review the source paths listed in Tasks 2–3 alongside the tests: the public source must have no active `.company` selector, work-only modules/secrets/scripts/skills, or `glab`/`1password-cli` package entries; the internal source must retain every work file and package and deploy it without `.company` gating. Confirm both template test suites pass with their context-specific secret backends.

- [ ] **Step 4: Verify Git and host safety**

Compare public `main` with the SHA recorded in Task 1; confirm the public topic branch and internal `ista` branch descend from the original public history, `../dotfiles-ista` has only the public remote, neither checkout was published, and no `chezmoi apply` was run against `$HOME`.

- [ ] **Step 5: Commit any validation-driven corrections**

If validation requires corrections, rerun the affected focused test command before committing only those corrections in the relevant checkout. Do not rebase the internal branch or simulate the post-merge rebase.
