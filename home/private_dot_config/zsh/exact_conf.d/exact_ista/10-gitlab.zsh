# GitLab private token — cached locally so the password manager is asked once
# rather than per shell. Stays ista-scoped: unlike the context7 key, this token
# only exists in the work vault.
_gitlab_token_file="${XDG_DATA_HOME:-$HOME/.local/share}/secrets/gitlab_token"

# Refresh the cached token (e.g. after PAT rotation).
# Writes only once the read succeeded: a plain redirect leaves an empty file
# behind on failure, which the export below would then hand out as the token.
gitlab-token-refresh() {
  local file="${XDG_DATA_HOME:-$HOME/.local/share}/secrets/gitlab_token" token
  token=$(secret-read "GitLab Token") || return 1
  mkdir -p "${file:h}" && chmod 700 "${file:h}"
  print -r -- "$token" >| "$file"
  chmod 600 "$file"
  export GITLAB_PRIVATE_TOKEN="$token"
}

[[ -f "$_gitlab_token_file" ]] || gitlab-token-refresh
[[ -f "$_gitlab_token_file" ]] && export GITLAB_PRIVATE_TOKEN="$(<"$_gitlab_token_file")"
unset _gitlab_token_file
