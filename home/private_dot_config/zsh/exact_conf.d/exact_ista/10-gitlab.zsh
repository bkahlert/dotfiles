# GitLab private token — cached locally to avoid per-shell op prompts.
# On first use (or after gitlab-token-refresh), fetched once from 1Password.
_gitlab_token_file="${XDG_DATA_HOME:-$HOME/.local/share}/secrets/gitlab_token"

if [[ ! -f "$_gitlab_token_file" ]]; then
  mkdir -p "${_gitlab_token_file:h}" && chmod 700 "${_gitlab_token_file:h}"
  op read "op://Employee/GitLab Token/credential" > "$_gitlab_token_file" && \
    chmod 600 "$_gitlab_token_file"
fi

[[ -f "$_gitlab_token_file" ]] && export GITLAB_PRIVATE_TOKEN="$(<"$_gitlab_token_file")"
unset _gitlab_token_file

# Refresh the cached token (e.g. after PAT rotation)
gitlab-token-refresh() {
  local _dir="${XDG_DATA_HOME:-$HOME/.local/share}/secrets"
  mkdir -p "$_dir" && chmod 700 "$_dir"
  op read "op://Employee/GitLab Token/credential" > "$_dir/gitlab_token" && \
    chmod 600 "$_dir/gitlab_token"
  export GITLAB_PRIVATE_TOKEN="$(<"$_dir/gitlab_token")"
}
