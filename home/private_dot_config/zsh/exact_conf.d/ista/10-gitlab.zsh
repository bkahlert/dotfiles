# GitLab private token — only fetch when IntelliJ is reading the shell environment
if [[ -n "${INTELLIJ_ENVIRONMENT_READER}" ]]; then
  export GITLAB_PRIVATE_TOKEN="$(op read "op://Employee/GitLab Token/credential")"
fi
