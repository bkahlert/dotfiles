# Scratch workflow: draft a zsh idea in 90-scratch.zsh before it is mature enough for its own home.
#   ec  edit the scratch module in $EDITOR, then apply it
#   sc  reload the shell, so the draft is live
ec() {
  local target="$HOME/.config/zsh/conf.d/90-scratch.zsh"
  local src
  src=$(chezmoi source-path "$target") || return 1
  "${EDITOR:-vim}" "$src"
  chezmoi apply "$target"
}

# An alias, not a function: sourced inside a function, the typeset in .zshrc would turn function-local.
alias sc='source "$ZDOTDIR/.zshrc"'
