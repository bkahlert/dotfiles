# Context7 API key — cached locally to avoid per-shell op prompts.
# Required by the context7 MCP plugin enabled in
# home/.chezmoitemplates/claude-settings.json (enabledPlugins.context7@claude-plugins-official).
# On first use (or after context7-token-refresh), fetched once from 1Password.
_context7_token_file="${XDG_DATA_HOME:-$HOME/.local/share}/secrets/context7_api_key"

if [[ ! -f "$_context7_token_file" ]]; then
  mkdir -p "${_context7_token_file:h}" && chmod 700 "${_context7_token_file:h}"
  op read "op://Employee/CONTEXT7_API_KEY/credential" > "$_context7_token_file" && \
    chmod 600 "$_context7_token_file"
fi

[[ -f "$_context7_token_file" ]] && export CONTEXT7_API_KEY="$(<"$_context7_token_file")"
unset _context7_token_file

# Refresh the cached key (e.g. after key rotation)
context7-token-refresh() {
  local _dir="${XDG_DATA_HOME:-$HOME/.local/share}/secrets"
  mkdir -p "$_dir" && chmod 700 "$_dir"
  op read "op://Employee/CONTEXT7_API_KEY/credential" > "$_dir/context7_api_key" && \
    chmod 600 "$_dir/context7_api_key"
  export CONTEXT7_API_KEY="$(<"$_dir/context7_api_key")"
}
