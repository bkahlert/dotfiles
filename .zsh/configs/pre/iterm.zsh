# `p10k configure` to create new layout but don't forget to add
# `%{$(iterm2_prompt_mark)%}` again to ~/.p10k.zsh
if [ ! "${INTELLIJ_ENVIRONMENT_READER-}" ] \
&& [ "${TERM_PROGRAM#iTerm*}" != "$TERM_PROGRAM" ]; then
  if [ ! -f "$HOME/.iterm2_shell_integration.zsh" ]; then
    curl -LfsS https://iterm2.com/shell_integration/install_shell_integration_and_utilities.sh | bash
  fi

  source "$HOME/.iterm2_shell_integration.zsh"
fi