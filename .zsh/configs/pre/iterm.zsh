# `p10k configure` to create new layout but don't forget to add
# `%{$(iterm2_prompt_mark)%}` again to ~/.p10k.zsh
[ "${INTELLIJ_ENVIRONMENT_READER-}" ] || {
  [ -f "$HOME/.iterm2_shell_integration.zsh" ] || curl -LfsS https://iterm2.com/shell_integration/install_shell_integration_and_utilities.sh | bash
  # shellcheck disable=SC1090
  source "$HOME/.iterm2_shell_integration.zsh"
}
