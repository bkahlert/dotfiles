# GitLab private token. chezmoi renders the file from 1Password
# (home/dot_local/share/private_secrets/); after a PAT rotation,
# `chezmoi apply` picks up the new value.
_gitlab_token_file="$HOME/.local/share/secrets/gitlab_token"
[[ -f "$_gitlab_token_file" ]] && export GITLAB_PRIVATE_TOKEN="$(<"$_gitlab_token_file")"
unset _gitlab_token_file
