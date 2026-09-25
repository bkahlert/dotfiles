# `~/.local/bin` audit

Record of the 2026-09-25 cleanup of the scripts in
[home/dot_local/exact_bin](../home/dot_local/exact_bin) (`quick-access/bin`),
done on the ista machine (macOS 27, podman instead of Docker, Homebrew bash 5.3
as `/usr/bin/env bash`). Every row is decided; the tables are the reference for
what each script touches and why the removed ones went. Landed on branch
`bin-audit`.

## How to read the tables

- **Effect** — what the script touches when run.
  `read` = no state change; `write:<target>` = changes the named thing;
  `net` = talks to the network; `sudo` = escalates;
  `passthrough` = hands over to another command.
- **Idempotent** — running it twice gives the same result as once.
  `n/a` for pure read scripts.
- **Verified** — what was checked on 2026-09-25.
  `run ✔` = executed successfully here, `run ✘` = executed and failed,
  `read` = code reviewed only (running it would have side effects),
  `n/t` = not tested.
- **Uses** — hits in `~/.local/state/zsh/history`. The file only holds ~470
  lines, so `0` means "not recently", not "never".
- **Findings** — what the review turned up before any change.
- **Outcome** — `kept` (unchanged), `fixed: <what>` (kept, changed as
  listed). All fixed scripts also received the header/help template, see
  [Decisions](#decisions).

## Kept

| Script | Purpose | Effect | Idempotent | Verified | Uses | Findings | Outcome |
|---|---|---|---|---|---|---|---|
| `ansi-test` | Terminal capability reference card | read | n/a | run ✔ | 1 | Fine. | fixed: template |
| `box` | Throwaway container shell / one-shot command | write:pulls image, runs container | yes | run ✔ | 0 | Works on podman. Supersedes `docker-command` / `docker-shell`. | kept |
| `cert-get` | Print leaf cert as PEM; `--download` writes `<domain>.pem` in cwd | read, net (write:cwd with `--download`) | yes | run ✔ | 0 | Fine. The `cert-download` symlink was a second name for one flag's worth of behaviour. | fixed: template, `-d`/`--download` replaces the symlink |
| `cert-print` | Print decoded certificate | read, net | n/a | run ✔ | 0 | Fine. | fixed: template |
| `cleanup` | Reclaim disk space (caches, logs, Trash, simulators, docker prune, brew/npm/yarn/gem caches) | dry-run by default; `--apply` = write:many, sudo rm -rf | yes | run ✔ (dry run, ~31 GiB estimated) | 1 | Good design: dry run default, prompts for risky items, non-interactive keeps them. `Gradle caches` deletion forces a full re-download. | fixed: examples |
| `docker` | Wrapper: real docker, else podman | passthrough | n/a | run ✔ | 3 | Resolves to `/usr/local/bin/docker`, which is podman's own shim; `/etc/containers/nodocker` exists so it stays quiet. | kept |
| `dscleanup` | Delete `.DS_Store` recursively | write:deletes files | yes | run ✔ | 0 | Fine. | fixed: template |
| `explain` | Open explainshell.com for a command | read, opens browser | n/a | read | 0 | Used `http://`, which 301-redirects. | fixed: https, template |
| `flushdns` | Flush the DNS cache | write:signals mDNSResponder | yes | run ✘ | 0 | Without sudo: `No matching processes belonging to you were found`. | fixed: sudo, template |
| `gcloud-login`, `gcloud-login-browser`, `gcloud-login-driver`, `op-agent` | Unattended gcloud / ADC login and 1Password agent | write:gcloud credentials, browser profile, op session | yes | run ✔ (`--status`, `op-agent status`) | 3 | Added 2026-09-23 (PR #48) with design docs, a skill and tests; only the option handling was touched. | fixed: `--help`, unknown option exits 2 |
| `gh-latest` | Latest release tag of a GitHub repo | read, net | n/a | run ✔ | 0 | Unauthenticated API (60 req/h). Could use `gh release view --json tagName` since `gh` is installed. | fixed: template, validates `<owner>/<repo>` |
| `grepr` | Recursive grep with 5 lines of context | passthrough | n/a | run ✔ | 0 | Works with BSD grep. Was `ft` with a `full-text-search` symlink; neither name said what it does. | fixed: renamed from `ft`, symlink dropped |
| `idea` | Locate and run the IntelliJ CLI | passthrough | n/a | run ✔ (2026.2.3 via app bundle) | 2 | Toolbox script path absent here, app-bundle fallback works. Callers: suffix aliases, `idea-wait`. | kept |
| `idea-wait` | `idea --wait` for `$VISUAL`, git editor, `KUBE_EDITOR` | passthrough | n/a | read | 0 | Wired into `10-editor.zsh`, `dot_gitconfig.tmpl`, `10-kubernetes.zsh`. | kept |
| `intellij-workspace-fix` | Enable format/optimize-imports on save in every `workspace.xml` below cwd | write:`.idea/workspace.xml` (+ timestamped backup) | yes | run ✔ (`--dry-run` on a sample) | 0 | Ran `brew install xmlstarlet` as a side effect; `dry_run` could never be set; computed `diff` unused (SC2034). One-off per project, but wanted. | fixed: real `--dry-run`, fails with a brew hint instead of installing, `count()`-based component check, template |
| `killport` | Kill listeners on a TCP port, SIGTERM then SIGKILL | write:kills processes | yes | read (in daily use) | 4 | The one you love. Has a completion (`_killport`). | fixed: tput colours, template |
| `known-hosts-fix` | Remove a host or line from `~/.ssh/known_hosts` | write:`~/.ssh/known_hosts` (ssh-keygen leaves `.old`, hashed path leaves `.bak`) | yes | read | 0 | Logic is sound. Leaves backup files behind. | fixed: examples |
| `mir` | Mirror a directory with `rsync --delete` | write:destination, deletes extraneous files | yes | run ✔ (openrsync) | 0 | The "source is no directory" message printed the destination instead of the source. | fixed: error message, `--dry-run`, template |
| `notify` | macOS notification via osascript | write:UI notification | yes | run ✔ | 0 | Fine. (The `notify` in the Ghostty config is Ghostty's built-in, not this script.) | fixed: template, `--opt=value` forms, no `join_by` |
| `omlx` | Locate oMLX CLI, offer to install | passthrough (may `brew install` interactively) | n/a | run ✔ (not installed → exit 127 with instructions) | 0 | Behaves as designed; personal-context tool. | kept |
| `pbcopy-dir` | tar+gzip+base64 a directory into the clipboard | write:clipboard | yes | read | 0 | Pair with `pbpaste-dir`. | fixed: template, path check |
| `pbpaste-dir` | Extract clipboard into cwd or `<dir>` | write:target dir (overwrites files) | no (re-extract overwrites) | read | 0 | Swallowed errors with `2>/dev/null`. | fixed: template, errors visible, optional `<dir>` |
| `pick-port` | First bindable port: 80, 8080, else random | read (transient bind) | n/a | run ✔ | 0 | Dependency of `serve`, `serve-live`. | fixed: template |
| `print-port` | No argument: every TCP listener; with ports: everything bound to them | read | n/a | run ✔ | 0 | Merge of `ports-print` (whose `netstat` printed nothing under Homebrew bash) and `whats-in-port`. Judges by output because `lsof` exits 1 when any one of several ports is unused. | fixed: merged, `lsof` on macOS, `ss`/`netstat` on Linux, template |
| `serve` | `npx http-server` on `pick-port` | net, write:npx cache | yes | read | 0 | Added 2026-09-19. | kept |
| `serve-live` | `npx live-server` on `pick-port` | net, write:npx cache | yes | read | 0 | Added 2026-09-19. | kept |
| `upgrade-all` | brew, podman machine, mas, npm, gems, gh extensions | write:packages | yes | read (fixed in #50, #51 this week) | 2 | Actively maintained. `softwareupdate -l` always runs and is slow. | fixed: template, rejects arguments |

## Removed

Deleting the source file is enough: `exact_bin` removes the target on apply.
History keeps every one of these.

| Script | Purpose | Effect | Verified | Uses | Why |
|---|---|---|---|---|---|
| `apply-macos-defaults` | 93 `defaults write` calls, timezone, Spotlight, restarts Dock/Finder/Mail/SystemUIServer/Terminal | write:system prefs, sudo, kills apps | read | 0 | Written for macOS 11.3, never re-verified; header points at a `scripts/capture-defaults-key` that no longer exists; biggest blast radius in the directory. |
| `cert-download` (symlink) | `cert-get` writing to `<domain>.pem` | write:cwd | run ✔ | 0 | Became `cert-get --download`. |
| `docker-ansi-test` | Run remote ANSI demo file inside an image | read, net | run ✘ | 0 | Upstream `raw.githubusercontent.com/bkahlert/-/master/ansi-test.ansi` returns 404. `ansi-test` covers the use case locally. |
| `docker-command` | `docker run --rm [-it] <image> [cmd]` | write:runs container | run ✔ | 0 | Works, but `box` does the same with cwd mounting and better defaults. |
| `docker-enter` | `docker run --rm --entrypoint <cmd> <image>` | write:runs container | run ✔ | 0 | One-liner around `--entrypoint`. |
| `docker-host` | Shell into the container VM via privileged `nsenter` | write:privileged container | run ✘ | 0 | `nsenter: can't open /proc/1/ns/ipc: Permission denied` on podman. `podman machine ssh` is the replacement. |
| `docker-ip` | IP of a container (default: latest) | read | run ✘ | 0 | Depends on `docker-latest`, and reads `.Networks.bridge` while podman's default network is `podman`. |
| `docker-latest` | ID of the most recently created container | read | run ✘ | 0 | `--latest` is not available in the remote podman client (macOS). `docker ps -a -n 1 --format '{{.ID}}'` would have fixed it; nothing left needs it. |
| `docker-list-shells` | Shells present in an image (`/etc/shells`) | write:runs container | run ✔ | 0 | Only caller was `docker-shell`. |
| `docker-logs` | Host path of a container's log file | read | run ✘ | 0 | Depends on `docker-latest`; the path is inside the podman VM, so it is useless on macOS without `docker-host`. |
| `docker-logs-raw` | Cat the raw JSON log via `docker-host` | read | n/t | 0 | Depends on two broken scripts. `docker logs` covers the everyday case. |
| `docker-shell` | Start the "best" shell (zsh > bash) in an image | write:runs container | run ✘ | 0 | `docker-shell alpine` exited 1 silently: no `sh` fallback, no message. `box` covers this. |
| `docker-watch` | `watch docker ps` every 2 s | read | run ✘ | 0 | `watch` is not installed. A `while sleep 2` loop needs no dependency. |
| `ft` (+ `full-text-search` symlink) | Recursive grep with context | passthrough | run ✔ | 0 | Renamed to `grepr`. |
| `iterm-integration` | iTerm2 ssh-integration hook | read, calls `notify` | read | 0 | Hard-coded to hosts `unicorn.local` / `netmon.local` and user `bkahlert`; usage text said `notify`; `port` unused (SC2034). The only other iTerm trace in the repo is a "not working yet" comment over generic tmux options in `dot_tmux.conf`. |
| `kill-zscaler` | Unload Zscaler launch agents/daemons | write:launchctl, sudo | read | 0 | Zscaler is not installed on this machine and there are no launch items. |
| `ports-print` | List every TCP listener | read | run ✘ | 0 | Under Homebrew bash 5.3 `netstat -anvp tcp` prints nothing, sandbox or not; `/bin/bash` and zsh are fine. Merged into `print-port`. |
| `secret-read` | Read a secret from 1Password (ista) or KeePassXC | read, may prompt | run ✔ | 0 | Encoded vault, field and KeePassXC path in a script because two secrets were fetched at shell startup. Replaced by chezmoi-rendered files under `~/.local/share/secrets/` (follow-up PR); the templates now hold that information. |
| `share-example` (+ `unshare-example` symlink) | Route domains through another host's Zscaler tunnel | write:routes, sudo, net; needs `nmap` | read | 0 | Needs `nmap` (not installed), a `192.168.206.x` LAN and a Zscaler host. |
| `start-zscaler` | Start Zscaler app and load its daemons | write:launchctl, sudo | read | 0 | Zscaler not installed. |
| `whats-in-port` | `lsof` on one TCP port | read | run ✔ | 0 | Merged into `print-port <port>...`. |

## Decisions

Taken one by one on 2026-09-25:

- **Dropped** the eleven docker helpers that podman broke or `box` duplicates,
  the four Zscaler entries, `iterm-integration` and `apply-macos-defaults`.
- **Merged** `ports-print` and `whats-in-port` into `print-port [<port>...]`
  (reversing an earlier "keep separate").
- **Renamed** `ft` to `grepr`; folded the `cert-download` symlink into
  `cert-get --download`. No symlinked aliases remain in the directory.
- **Replaced** `secret-read` by chezmoi templates (follow-up branch): the
  secret files it used to fill are now rendered at apply time.
- **Kept and fixed** `intellij-workspace-fix`, `pbcopy-dir` / `pbpaste-dir`,
  `ports-print` (as part of the merge) after weighing a drop.
- **Template.** Every keeper that takes arguments follows
  [rules/bash.md](../home/private_dot_config/exact_agents/exact_rules/bash.md)
  (PR #52, extended here): `-h`/`--help` prints the file header, unknown
  options exit 2 with a one-line hint, a script that needs arguments and gets
  none prints the help to stderr and exits 2. `Options:` only lists real
  options; `Examples:` holds tried invocations. Pure pass-through wrappers
  (`docker`, `grepr`, `idea`, `idea-wait`, `omlx`, `serve`, `serve-live`) are
  left alone on purpose: their `--help` belongs to the wrapped command.

## Cross-cutting observations

- **Podman broke the docker helpers.** Everything that relied on `--latest`,
  `nsenter` into the VM, or the `bridge` network name fails on podman.
  `box` and the `docker` wrapper are the two container scripts that work.
- **Dead context.** Zscaler (4 entries) and the iTerm ssh integration
  belonged to setups that no longer exist on this machine.
- **Homebrew bash changes behaviour.** `netstat` printing nothing under
  bash 5.3 is why `print-port` uses `lsof`; worth remembering when a script
  works in zsh but not from its shebang.
- **Shellcheck at warning level** is clean apart from false-positive SC2209
  in `box` and `gcloud-login` (`gcloud-login-driver` is node, not shell).
- **Source-file modes** are all `0755` now; three were `0644` before, which
  was harmless (the `executable_` prefix sets the target mode) but
  inconsistent.
- `~/.local/bin` has no drift against source state; the only unmanaged
  entry is `claude`, which `.chezmoiignore` protects on purpose.

## Follow-ups

- [quick-access/README.md](../quick-access/README.md) needed no change: it
  names only `killport`, which kept its name.
- Candidates for the same treatment: `quick-access/functions` and the inline
  functions in `conf.d`.
