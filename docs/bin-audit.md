# `~/.local/bin` audit

Working document for cleaning up the scripts in
[home/dot_local/exact_bin](../home/dot_local/exact_bin) (`quick-access/bin`).
Started 2026-09-25 on the ista machine (macOS 27, podman instead of Docker,
Homebrew bash 5.3 as `/usr/bin/env bash`). Update the **Status** column as
decisions are made and fixes land, so a later session can pick up here.

## How to read the table

- **Effect** — what the script touches when run.
  `read` = no state change; `write:<target>` = changes the named thing;
  `net` = talks to the network; `sudo` = escalates.
- **Idempotent** — running it twice gives the same result as once.
  `n/a` for pure read scripts.
- **Verified** — what was checked on 2026-09-25.
  `run ✔` = executed successfully here, `run ✘` = executed and failed,
  `read` = code reviewed only (running it would have side effects),
  `n/t` = not tested.
- **Uses** — hits in `~/.local/state/zsh/history`. The file only holds ~470
  lines, so `0` means "not recently", not "never".
- **Recommendation** — `keep`, `fix` (keep, needs the listed change),
  `merge` (fold into another script), `drop` (delete), `review` (needs its
  own session).
- **Status** — `open` until you decide; then `keep`, `fixed`, `dropped`,
  `deferred`.

## Table

| Script | Purpose | Effect | Idempotent | Verified | Uses | Findings | Recommendation | Status |
|---|---|---|---|---|---|---|---|---|
| `ansi-test` | Terminal capability reference card | read | n/a | run ✔ | 1 | Fine. | fix: template | fixed |
| `apply-macos-defaults` | 93 `defaults write` calls, timezone, Spotlight, restarts Dock/Finder/Mail/SystemUIServer/Terminal | write:system prefs, sudo, kills apps | mostly (restarts every run) | read | 0 | Written for macOS 11.3, header points at a `scripts/capture-defaults-key` that no longer exists; many keys are likely obsolete on macOS 27; `--no-restart` is the only flag. Biggest blast radius in the directory. | drop | dropped |
| `box` | Throwaway container shell / one-shot command | write:pulls image, runs container | yes | run ✔ | 0 | Works on podman. Supersedes `docker-command` / `docker-shell`. | keep | keep |
| `cert-get` (+ `cert-download` symlink) | Print leaf cert as PEM; symlink writes `<domain>.pem` in cwd | read, net (write:cwd as `cert-download`) | yes | run ✔ | 0 | Fine. | fix: template | fixed |
| `cert-print` | Print decoded certificate | read, net | n/a | run ✔ | 0 | Fine. | fix: template | fixed |
| `cleanup` | Reclaim disk space (caches, logs, Trash, simulators, docker prune, brew/npm/yarn/gem caches) | dry-run by default; `--apply` = write:many, sudo rm -rf | yes | run ✔ (dry run, ~31 GiB estimated) | 1 | Good design: dry run default, prompts for risky items, non-interactive keeps them. `Gradle caches` deletion forces a full re-download. | keep | keep |
| `docker` | Wrapper: real docker, else podman | passthrough | n/a | run ✔ | 3 | Resolves to `/usr/local/bin/docker`, which is podman's own shim; `/etc/containers/nodocker` exists so it stays quiet. Fine. | keep | keep |
| `docker-ansi-test` | Run remote ANSI demo file inside an image | read, net | n/a | run ✘ | 0 | Upstream `raw.githubusercontent.com/bkahlert/-/master/ansi-test.ansi` returns 404. `ansi-test` covers the use case locally. | drop | dropped |
| `docker-command` | `docker run --rm [-it] <image> [cmd]` | write:runs container | yes | run ✔ | 0 | Works, but `box` does the same with cwd mounting and better defaults. | drop | dropped |
| `docker-enter` | `docker run --rm --entrypoint <cmd> <image>` | write:runs container | yes | run ✔ | 0 | One-liner around `--entrypoint`. | drop | dropped |
| `docker-host` | Shell into the container VM via privileged `nsenter` | write:privileged container | yes | run ✘ | 0 | `nsenter: can't open /proc/1/ns/ipc: Permission denied` on podman. `podman machine ssh` is the replacement. Only caller is `docker-logs-raw`. | drop | dropped |
| `docker-ip` | IP of a container (default: latest) | read | n/a | run ✘ | 0 | Breaks twice: depends on `docker-latest`, and reads `.Networks.bridge` while podman's default network is `podman`. | drop | dropped |
| `docker-latest` | ID of the most recently created container | read | n/a | run ✘ | 0 | `--latest` is not available in the remote podman client (macOS). Fix: `docker ps -a -n 1 --format '{{.ID}}'`. Called by `docker-ip`, `docker-logs`. | drop | dropped |
| `docker-list-shells` | Shells present in an image (`/etc/shells`) | write:runs container | yes | run ✔ | 0 | Works; only caller is `docker-shell`. | drop | dropped |
| `docker-logs` | Host path of a container's log file | read | n/a | run ✘ | 0 | Depends on `docker-latest`; the path is inside the podman VM, so it is useless on macOS without `docker-host`. | drop | dropped |
| `docker-logs-raw` | Cat the raw JSON log via `docker-host` | read | n/a | n/t | 0 | Depends on two broken scripts (`docker-host`, `docker-logs`). `docker logs` covers the everyday case. | drop | dropped |
| `docker-shell` | Start the "best" shell (zsh > bash) in an image | write:runs container | yes | run ✘ | 0 | `docker-shell alpine` exits 1 silently: no `sh` fallback and no error message. `box` covers this. | drop | dropped |
| `docker-watch` | `watch docker ps` every 2 s | read | n/a | run ✘ | 0 | `watch` is not installed (`brew install watch`). Alternative: a `while sleep 2` loop, no dependency. | drop | dropped |
| `dscleanup` | Delete `.DS_Store` recursively | write:deletes files | yes | run ✔ | 0 | Fine. | fix: template | fixed |
| `explain` | Open explainshell.com for a command | read, opens browser | n/a | read | 0 | Uses `http://`, which now 301-redirects; switch to `https://`. | fix: https + template | fixed |
| `flushdns` | Flush the DNS cache | write:signals mDNSResponder | yes | run ✘ | 0 | Without sudo: `No matching processes belonging to you were found`. Needs `sudo killall -HUP mDNSResponder`. | fix: sudo + template | fixed |
| `ft` (+ `full-text-search` symlink) | Recursive grep with 5 lines of context | read | n/a | run ✔ | 0 | Works with BSD grep. | keep | keep |
| `gcloud-login`, `gcloud-login-browser`, `gcloud-login-driver`, `op-agent` | Unattended gcloud / ADC login and 1Password agent | write:gcloud credentials, browser profile, op session | yes | run ✔ (`--status`, `op-agent status`) | 3 | Added 2026-09-23 (PR #48) with design docs, a skill and tests. Out of scope for this audit. | fix: --help, unknown option exits 2 | fixed |
| `gh-latest` | Latest release tag of a GitHub repo | read, net | n/a | run ✔ | 0 | Unauthenticated API (60 req/h). Could use `gh release view --json tagName` since `gh` is installed. | fix: template | fixed |
| `idea` | Locate and run the IntelliJ CLI | passthrough | n/a | run ✔ (2026.2.3 via app bundle) | 2 | Toolbox script path absent here, app-bundle fallback works. Callers: suffix aliases, `idea-wait`. | keep | keep |
| `idea-wait` | `idea --wait` for `$VISUAL`, git editor, `KUBE_EDITOR` | passthrough | n/a | read | 0 | Wired into `10-editor.zsh`, `dot_gitconfig.tmpl`, `10-kubernetes.zsh`. | keep | keep |
| `intellij-workspace-fix` | Enable format/optimize-imports on save in every `workspace.xml` below cwd | write:`.idea/workspace.xml` (+ timestamped backup), installs xmlstarlet via brew | yes | read (find expression tested ✔) | 0 | xmlstarlet not installed; `brew install` as a side effect of a script is unexpected; `dry_run` can never be set; computed `diff` is unused (SC2034). Relevance doubtful — one-off per project. | fix: real --dry-run, fails without xmlstarlet instead of brew-installing, count()-based component check, template | fixed |
| `iterm-integration` | iTerm2 ssh-integration hook | read, calls `notify` | n/a | read | 0 | Hard-coded to hosts `unicorn.local` / `netmon.local` and user `bkahlert`; usage text says `notify` (copy-paste); `port` unused (SC2034). Dead code. | drop | dropped |
| `kill-zscaler` | Unload Zscaler launch agents/daemons | write:launchctl, sudo | yes | read | 0 | Zscaler is not installed on this machine and there are no launch items. | drop | dropped |
| `killport` | Kill listeners on a TCP port, SIGTERM then SIGKILL | write:kills processes | yes | read (in daily use) | 4 | The one you love. Has a completion (`_killport`). | fix: tput colours + template | fixed |
| `known-hosts-fix` | Remove a host or line from `~/.ssh/known_hosts` | write:`~/.ssh/known_hosts` (ssh-keygen leaves `.old`, hashed path leaves `.bak`) | yes | read | 0 | Logic is sound. Leaves backup files behind. | keep | keep |
| `mir` | Mirror a directory with `rsync --delete` | write:destination, deletes extraneous files | yes | run ✔ (openrsync) | 0 | Bug: the "source is no directory" message prints the destination instead of the source. | fix: error message + --dry-run + template | fixed |
| `notify` | macOS notification via osascript | write:UI notification | yes | run ✔ | 0 | Fine. (The `notify` in the Ghostty config is Ghostty's built-in, not this script.) | fix: template, --opt=value, no join_by | fixed |
| `omlx` | Locate oMLX CLI, offer to install | passthrough (may `brew install` interactively) | n/a | run ✔ (not installed → exit 127 with instructions) | 0 | Behaves as designed; personal-context tool. | keep | keep |
| `pbcopy-dir` | tar+gzip+base64 a directory into the clipboard | write:clipboard | yes | read | 0 | Pair with `pbpaste-dir`. | fix: template, path check | fixed |
| `pbpaste-dir` | Extract clipboard into cwd | write:cwd (overwrites files), errors hidden by `2>/dev/null` | no (re-extract overwrites) | read | 0 | Silently swallows errors. | fix: template, errors visible, optional <dir> | fixed |
| `pick-port` | First bindable port: 80, 8080, else random | read (transient bind) | n/a | run ✔ | 0 | Dependency of `serve`, `serve-live`. | fix: template | fixed |
| `ports-print` | List listening TCP sockets via netstat | read | n/a | run ✘ (see note) | 0 | Confirmed: under Homebrew bash 5.3 (`/usr/bin/env bash`) `netstat -anvp tcp` prints nothing, sandbox or not; `/bin/bash` and zsh are fine. Replaced by `lsof`. Overlaps with `whats-in-port` and the `_killport` completion, which use `lsof`. | fix: lsof on macOS, ss/netstat on Linux, template | fixed |
| `secret-read` | Read a secret from 1Password (ista) or KeePassXC | read, may prompt | n/a | run ✔ | 0 | Called at shell startup by `10-context7.zsh` and `exact_ista/10-gitlab.zsh`. | fix: template | fixed |
| `serve` | `npx http-server` on `pick-port` | net, write:npx cache | yes | read | 0 | Added 2026-09-19. | keep | keep |
| `serve-live` | `npx live-server` on `pick-port` | net, write:npx cache | yes | read | 0 | Added 2026-09-19. | keep | keep |
| `share-example` (+ `unshare-example` symlink) | Route domains through another host's Zscaler tunnel | write:routes, sudo, net; needs `nmap` | yes | read | 0 | Needs `nmap` (not installed), a `192.168.206.x` LAN and a Zscaler host. Upstream script still exists. Same fate as `kill-zscaler`. | drop | dropped |
| `start-zscaler` | Start Zscaler app and load its daemons | write:launchctl, sudo | yes | read | 0 | Zscaler not installed. | drop | dropped |
| `upgrade-all` | brew, podman machine, mas, npm, gems, gh extensions | write:packages | yes | read (fixed in #50, #51 this week) | 2 | Actively maintained. `softwareupdate -l` always runs and is slow. | fix: template | fixed |
| `whats-in-port` | `lsof` listeners on one port | read | n/a | run ✔ | 0 | Fine. Natural home for `ports-print`'s "list all" case. | fix: bash, template, exit 1 message | fixed |

## Decisions (2026-09-25)

Taken one by one in the first session:

- Dropped: the nine docker helpers that podman broke or `box` duplicates, plus
  `docker-latest` / `docker-ip`; the four Zscaler entries; `iterm-integration`
  (the only other iTerm trace in the repo is a "not working yet" comment over
  generic tmux options in `dot_tmux.conf`).
- Kept and fixed: `intellij-workspace-fix`, `pbcopy-dir` / `pbpaste-dir`,
  `ports-print` (stays separate from `whats-in-port`).
- Every keeper that takes arguments now follows the header/help/argument
  template from `rules/bash.md` (PR #52): `-h`/`--help` prints the file
  header, unknown options exit 2 with a hint, a script that needs arguments
  and gets none prints the help. `Options:` only lists real options, and
  `Examples:` holds tried invocations (rules extended accordingly). Pure
  pass-through wrappers
  (`docker`, `ft`, `idea`, `idea-wait`, `omlx`, `serve`, `serve-live`) are
  left alone on purpose: their `--help` belongs to the wrapped command.
- `apply-macos-defaults` dropped (decision 2026-09-25): written for macOS 11.3, never
  re-verified, and the biggest blast radius in the directory. History keeps it
  if a curated `defaults` set is ever wanted again.
- Open: nothing in this directory. Next candidates for the same treatment are
  `quick-access/functions` and the inline functions in `conf.d`.

## Cross-cutting observations

- **Podman broke the docker helpers.** Everything that relies on `--latest`,
  `nsenter` into the VM, or the `bridge` network name fails on podman.
  `box` and the `docker` wrapper are the two container scripts that work
  and are worth keeping; the rest either duplicate them or are broken.
- **Dead context.** Zscaler (4 entries), iTerm ssh integration and
  IntelliJ `workspace.xml` patching all belong to setups that no longer
  exist on this machine.
- **Three trivial bugs in otherwise fine scripts:** `flushdns` needs sudo,
  `mir` prints the wrong variable in an error, `explain` uses `http://`.
- **Shellcheck at warning level** is clean except the unused variables in
  `intellij-workspace-fix` and `iterm-integration` and false-positive SC2209
  in `box` and `gcloud-login`.
- **Source-file modes:** `executable_killport`, `executable_omlx`,
  `executable_secret-read` are `0644` in the repo. Harmless (the
  `executable_` prefix sets the target mode) but inconsistent with the rest.
- `~/.local/bin` has no drift against source state; the only unmanaged
  entry is `claude`, which `.chezmoiignore` protects on purpose.

## Suggested order of work

1. Decide the `drop` rows (mostly docker-*, Zscaler, iTerm, IntelliJ). Deleting
   the source file is enough; `exact_bin` removes the target on apply.
2. Apply the three trivial fixes (`flushdns`, `mir`, `explain`).
3. Fix `docker-latest` if `docker-ip` is kept; otherwise drop both.
4. Merge `ports-print` into `whats-in-port` (no argument = list every listener).
5. Update [quick-access/README.md](../quick-access/README.md) if any
   location or convention changes.
