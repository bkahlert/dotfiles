# Scratch space for quick, not-yet-organized zsh customizations.
# Edit via `ec`, reload the current shell via `sc` (both in 89-scratch-workflow.zsh).
# Once something here proves useful, promote it into its own conf.d module
# or functions/ file.
#
# `ec` runs `chezmoi apply` after the editor closes, so `sc` alone picks up
# its changes. If this file is edited directly (source-path, not via `ec`),
# run `chezmoi apply` before `sc` — otherwise `sc` re-sources the stale
# already-applied target file.

# Pinned: these functions pipe third-party scripts into bash. Bump deliberately.
_pihero_release=v2.8.1
_lgtm_commit=65b3a0510089a7171e4fba3f986cfb2a324d6e4d  # grafana/docker-otel-lgtm

hero() {
  curl -fsSL https://github.com/bkahlert/pihero/releases/download/${_pihero_release}/hero | bash -s -- "$@"
}
wizard() {
  curl -fsSL https://github.com/bkahlert/pihero/releases/download/${_pihero_release}/wizard | bash -s -- "$@"
}
visitor() {
  curl -fsSL https://github.com/bkahlert/pihero/releases/download/${_pihero_release}/visitor | bash -s -- "$@"
}

grafana-start() {
  local url="http://localhost:3000"

  (
    for _ in $(seq 60); do
      curl -sf "$url" >/dev/null 2>&1 && break
      sleep 1
    done
    open "$url"
  ) &
  local watcher=$!
  trap 'kill "$watcher" 2>/dev/null' EXIT

  curl -fsSL https://raw.githubusercontent.com/grafana/docker-otel-lgtm/${_lgtm_commit}/run-lgtm.sh | bash
}
