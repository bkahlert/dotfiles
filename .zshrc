[[ -f ~/.hushlogin ]] || touch .hushlogin &>/dev/null
if [ ! -z "${recording}" ]; then
######################################### RECORDING
    PS1='%F{gray}%n%f$ '
    NPS1='[%l] %n@%m # '
    RPS1='%B%F{gray}%~%f%b'

    # Hook function which gets executed right before shell prints prompt.
    function precmd() {
        local expandedPrompt="$(print -P "$NPS1")"
        local promptLength="${#expandedPrompt}"
        PS2="> "
        PS2="$(printf "%${promptLength}s" "$PS2")"
    }
else
######################################### NO RECORDING

# `p10k configure` to create new layout but don't forget to add
# `%{$(iterm2_prompt_mark)%}` again to ~/.p10k.zsh
[[ -f ~/.iterm2_shell_integration.zsh ]] || curl -L https://iterm2.com/shell_integration/install_shell_integration_and_utilities.sh | bash
[[ -f ~/.iterm2_shell_integration.zsh ]] && source ~/.iterm2_shell_integration.zsh

# Enable Powerlevel10k instant prompt. Should stay close to the top of ~/.zshrc.
# Initialization code that may require console input (password prompts, [y/n]
# confirmations, etc.) must go above this block; everything else may go below.
if [[ -r "${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh" ]]; then
  source "${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh"
fi

export LANG=en_US.UTF-8 LC_CTYPE=en_US.UTF-8

unsetopt nomatch | true     # Don't require escaping globbing characters in zsh
setopt sh_word_split | true # word splitting as in sh / bash
unset LSCOLORS
export CLICOLOR=1
export CLICOLOR_FORCE=1
export HOMEBREW_AUTO_UPDATE_SECS=604800 # Homebrew updates once a week

# Local terminfo patch that adds italics to xterm-256color
if [ ! -n "$(find ~/.terminfo -type f -name xterm-256color 2>/dev/null)" ]; then
 tmp_terminfo="$(mktemp)" && cat <<TERMINFO > "$tmp_terminfo" && tic -o ~/.terminfo "$tmp_terminfo"
xterm-256color|xterm with 256 colors and italic,
  sitm=\E[3m, ritm=\E[23m,
  use=xterm-256color,
TERMINFO
  if [ $? ]; then
    echo "terminfo fixed: $(tput sitm)italics$(tput ritm) & $(tput smso)standout$(tput rmso)"
  else
   "Failed to patch terminfo" >&2
  fi
fi

ZLE_RPROMPT_INDENT=0
ZSH_AUTOSUGGEST_HIGHLIGHT_STYLE=fg=#666666
source $(brew --prefix)/share/antigen/antigen.zsh
antigen use oh-my-zsh
antigen bundles <<BUNDLES
zsh-users/zsh-autosuggestions                           # Proposes in dark grey an auto-completes command
zsh-users/zsh-syntax-highlighting                       # Syntax highlighting
zsh-users/zsh-completions                               # Tab to choose from completion options
git                                                     # Aliases, i.e. g=git ga=add gp=push gl=pull glol=log
dotenv                                                  # Sources .env files automatically
viasite-ansible/zsh-ansible-server                      # Auto-completion for ansible
greymd/docker-zsh-completion                            # Auto-completion for Docker / Docker Compose
gradle/gradle-completion                                # Auto-completion for Gradle
Downager/zsh-helmfile                                   # Auto-completion for Helm
djui/alias-tips                                         # Show alias if not used
Cloudstek/zsh-plugin-appup                              # up, down, start, restart, stop commands in docker-compose / vagrant dirs
desyncr/auto-ls                                         # Automatically call ls on cwd
unixorn/autoupdate-antigen.zshplugin                    # Auto-updates for Antigen and bundles
TamCore/autoupdate-oh-my-zsh-plugins                    # Auto-updates for Oh-my-ZSH plugins
colored-man                                             # Colored man pages
anatolykopyl/sshukh                                     # Offers to remove known_host entry if connection failed
skywind3000/z.lua                                       # Use z instead of cd
BUNDLES
antigen theme romkatv/powerlevel10k
antigen apply
fi

export SSH_KEY_PATH="${HOME}/.ssh/id_rsa20"
export EDITOR=idea

PATH="/usr/local/sbin:${PATH}"
[ -d "$HOME/bin" ]         && PATH="$HOME/bin:$PATH"                            # set PATH so it includes user's private bin if it exists
[ -d "$HOME/.local/bin" ]  && PATH="$HOME/.local/bin:$PATH"                     # set PATH so it includes user's private bin if it exists
[ -d "$HOME/.arkade/bin" ] && PATH="$HOME/.arkade/bin:$PATH"                    # set PATH so it includes user's arkade bin if it exists
[ -d "$HOME/.krew/bin" ]   && PATH="$HOME/.krew/bin:$PATH"                      # set PATH so it includes user's krew bin if it exists

export JAVA_HOME="/Library/Java/JavaVirtualMachines/jdk-11.0.2.jdk/Contents/Home"

source "$HOME/.aliases"
alias sc='source "$HOME/.aliases"'

# To customize prompt, run `p10k configure` or edit ~/.p10k.zsh.
[[ ! -f ~/.p10k.zsh ]] || source ~/.p10k.zsh
