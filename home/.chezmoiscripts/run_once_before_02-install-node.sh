#!/usr/bin/env bash
# Purpose: Install a default Node.js with fnm; conf.d/10-fnm.zsh puts it on PATH.
# Usage:   Run automatically by chezmoi on first apply.

set -euo pipefail

# fnm comes from run_once_before_01-install-packages: Homebrew's on macOS, whose bin a fresh Mac has on no PATH yet,
# ~/.local/bin on Linux.
PATH="$PATH:/opt/homebrew/bin:/usr/local/bin:$HOME/.local/bin"
command -v fnm >/dev/null || { printf 'fnm not found; run_once_before_01-install-packages installs it\n' >&2; exit 1; }

nvm_dir="$HOME/.nvm"

# fnm makes the first version it installs the default. The latest LTS, unless nvm had a numbered default, which
# fnm takes over.
if ! fnm default >/dev/null 2>&1; then
  version=--lts
  if [[ -s $nvm_dir/alias/default ]]; then
    nvm_default=$(<"$nvm_dir/alias/default")
    [[ $nvm_default =~ ^v?[0-9] ]] && version=${nvm_default#v}
  fi
  fnm install "$version"
fi

# A machine that used nvm before: what is left to do by hand.
[[ -d $nvm_dir ]] || exit 0
printf '\nNode.js now comes from fnm (default %s); nvm in %s is no longer used. To finish:\n' "$(fnm default)" "$nvm_dir"
for modules in "$nvm_dir"/versions/node/*/lib/node_modules; do
  [[ -d $modules ]] || continue
  packages=()
  for package in "$modules"/*; do
    name=${package##*/}
    case $name in
      npm | corepack | '*') ;;
      @*) for scoped in "$package"/*; do [[ -e $scoped ]] && packages+=("$name/${scoped##*/}"); done ;;
      *) packages+=("$name") ;;
    esac
  done
  (( ${#packages[@]} )) || continue
  version=${modules%/lib/node_modules}
  printf '  npm install -g %s   # global packages of nvm'\''s %s, if still needed\n' "${packages[*]}" "${version##*/}"
done
if [[ -L $nvm_dir/nvm.sh ]]; then
  printf '  brew uninstall nvm\n'
fi
printf '  rm -rf %s\n\n' "$nvm_dir"
