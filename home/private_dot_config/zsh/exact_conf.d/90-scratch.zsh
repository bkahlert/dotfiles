# Scratch space for quick, not-yet-organized zsh customizations.
# Edit via `ec` (zsh-scratch), reload the current shell via `sc`.
# Once something here proves useful, promote it into its own conf.d module
# or functions/ file.
#
# `ec` runs `chezmoi apply` after the editor closes, so `sc` alone picks up
# its changes. If this file is edited directly (source-path, not via `ec`),
# run `chezmoi apply` before `sc` — otherwise `sc` re-sources the stale
# already-applied target file.

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

  curl -fsSL https://raw.githubusercontent.com/grafana/docker-otel-lgtm/refs/heads/main/run-lgtm.sh | bash
}
