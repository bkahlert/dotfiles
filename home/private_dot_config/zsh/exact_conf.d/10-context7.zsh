# Context7 API key — cached locally so the password manager is asked once
# rather than per shell. Required by the context7 MCP plugin enabled in
# home/.chezmoitemplates/claude-settings.json (enabledPlugins.context7@claude-plugins-official).
#
# Generic, not company-scoped: `secret-read` picks the backend per machine
# (1Password on ista, KeePassXC elsewhere), so both get the key from their own
# vault under the same item title.
_context7_token_file="${XDG_DATA_HOME:-$HOME/.local/share}/secrets/context7_api_key"

# Refresh the cached key (e.g. after key rotation).
# Writes only once the read succeeded: a plain redirect leaves an empty file
# behind on failure, which the export below would then hand out as the key.
context7-token-refresh() {
  local file="${XDG_DATA_HOME:-$HOME/.local/share}/secrets/context7_api_key" key
  key=$(secret-read CONTEXT7_API_KEY) || return 1
  mkdir -p "${file:h}" && chmod 700 "${file:h}"
  print -r -- "$key" >| "$file"
  chmod 600 "$file"
  export CONTEXT7_API_KEY="$key"
}

[[ -f "$_context7_token_file" ]] || context7-token-refresh
[[ -f "$_context7_token_file" ]] && export CONTEXT7_API_KEY="$(<"$_context7_token_file")"
unset _context7_token_file
