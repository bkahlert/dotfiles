# Context7 API key, required by the context7 MCP plugin enabled in
# home/.chezmoitemplates/claude-settings.json. chezmoi renders the file from the
# password manager (home/dot_local/share/private_secrets/); after a key
# rotation, `chezmoi apply` picks up the new value.
_context7_key_file="$HOME/.local/share/secrets/context7_api_key"
[[ -f "$_context7_key_file" ]] && export CONTEXT7_API_KEY="$(<"$_context7_key_file")"
unset _context7_key_file
