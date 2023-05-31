# `p10k configure` to create new layout but don't forget to add
# `%{$(iterm2_prompt_mark)%}` again to ~/.p10k.zsh
[ "${INTELLIJ_ENVIRONMENT_READER-}" ] || {
  [ -f "$HOME/.iterm2_shell_integration.zsh" ] || curl -LfsS https://iterm2.com/shell_integration/install_shell_integration_and_utilities.sh | bash
  # shellcheck disable=SC1090
  source "$HOME/.iterm2_shell_integration.zsh"
}

# used by `web-search` plugin
# shellcheck disable=SC2034
ZSH_WEB_SEARCH_ENGINES=(
  q "https://search.bkahlert.com/?q="
  h "https://hello.bkahlert.com/?q="
)

# Enable Powerlevel10k instant prompt. Should stay close to the top of ~/.zshrc.
# Initialization code that may require console input (password prompts, [y/n]
# confirmations, etc.) must go above this block; everything else may go below.
if [ ! "${INTELLIJ_ENVIRONMENT_READER-}" ] && [[ -r "${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh" ]]; then
  source ${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh
fi

# update Oh My Zsh without asking for confirmation
# shellcheck disable=SC2034
DISABLE_UPDATE_PROMPT=true

# update Oh My Zsh once a week
# shellcheck disable=SC2034
UPDATE_ZSH_DAYS=7

# homebrew: updates once a week
# shellcheck disable=SC2034
HOMEBREW_AUTO_UPDATE_SECS=604800

printf -v ZSH_AUTO''SUGGEST_HIGHLIGHT_STYLE fg=#666666                          # color of auto-suggestions
printf -v ZLE_R''PROMPT_INDENT 0                                                   # no right margin for Powerlevel10k prompt
eval "$(/opt/homebrew/bin/brew shellenv)"
[ "${INTELLIJ_ENVIRONMENT_READER-}" ] || {
  source $(brew --prefix)/share/antigen/antigen.zsh
  antigen use oh-my-zsh
  antigen bundles <<BUNDLES
zsh-users/zsh-autosuggestions                           # proposes in dark grey an auto-completes command
zsh-users/zsh-syntax-highlighting                       # syntax highlighting
zsh-users/zsh-completions                               # tab to choose from completion options
git                                                     # aliases, i.e. g=git ga=add gp=push gl=pull glol=log
dotenv                                                  # sources .env files automatically
viasite-ansible/zsh-ansible-server                      # auto-completion for ansible
greymd/docker-zsh-completion                            # auto-completion for Docker / Docker Compose
gradle/gradle-completion                                # auto-completion for Gradle
Downager/zsh-helmfile                                   # auto-completion for Helm
djui/alias-tips                                         # show alias if not used
Cloudstek/zsh-plugin-appup                              # up, down, start, restart, stop commands in docker-compose / vagrant dirs
desyncr/auto-ls                                         # automatically call ls on cwd
unixorn/autoupdate-antigen.zshplugin                    # auto-updates for Antigen and bundles
TamCore/autoupdate-oh-my-zsh-plugins                    # auto-updates for Oh-my-ZSH plugins
anatolykopyl/sshukh                                     # offers to remove known_host entry if connection failed
skywind3000/z.lua                                       # use z instead of cd
colored-man-pages                                       # colors man pages
web-search                                              # search using google, bing, etc.
macos                                                   # pfs=return the current Finder selection; cdf=cd to the current Finder directory
BUNDLES
  antigen theme romkatv/powerlevel10k
  antigen apply
}

# Fixes the local terminfo
# - support of italics for xterm-256color
fix_terminfo() {
  [ ! "$(find ~/.terminfo -type f -name xterm-256color 2>/dev/null)" ] || return
  local tmp_terminfo && tmp_terminfo=$(mktemp) && cat <<TERMINFO > "$tmp_terminfo" && tic -o ~/.terminfo "$tmp_terminfo" && rm "$tmp_terminfo"
xterm-256color|xterm with 256 colors and italic,
  dim=\E[2m, sitm=\E[3m, ritm=\E[23m,
  use=xterm-256color,
TERMINFO
  if [ $? ]; then
    echo "terminfo fixed: $(tput dim)half-bright$(tput sgr0) $(tput sitm)italics$(tput ritm) $(tput smso)standout$(tput rmso)"
  else
    echo "$(tput setaf 1)Failed to terminfo$(tput sgr0)" >&2
  fi
}

setopt shwordsplit                                                              # zsh: word splitting as in `sh`
unsetopt nomatch                                                                # zsh: no need to escape globbing characters

# no 'export LANG=C.UTF-8' as that would require C locales
export LC_CTYPE=UTF-8                                                           # UTF-8 for string functions
export EDITOR=idea


## Java

# Link brew-installed JDK
if [ -r "$(brew --prefix)/opt/openjdk/libexec/openjdk.jdk" ] && [ ! -e '/Library/Java/JavaVirtualMachines/openjdk.jdk' ]; then
 ln -sfn "$(brew --prefix)/opt/openjdk/libexec/openjdk.jdk" '/Library/Java/JavaVirtualMachines/openjdk.jdk'
fi

# Use brew-installed JDK as JAVA_HOME by default
[ -e '/Library/Java/JavaVirtualMachines/openjdk.jdk' ] && export JAVA_HOME='/Library/Java/JavaVirtualMachines/openjdk.jdk'

# Use OS default if no brew-installed JDK is available
[ -x "$JAVA_HOME/bin/java" ] || JAVA_HOME=$(/usr/libexec/java_home)


[ "${INTELLIJ_ENVIRONMENT_READER-}" ] || fix_terminfo
export PATH="/usr/local/sbin:$PATH"
export PATH="$HOME/Library/Python/3.11/bin:$PATH"
export PATH="$HOME/bin:$PATH"
export PATH="$HOME/.local/bin:$PATH"
export PATH="$HOME/.arkade/bin:$PATH"
export PATH="$HOME/.krew/bin:$PATH"
export PATH="$HOME/.rd/bin:$PATH"
export ANSIBLE_VAULT_PASS_CLIENT=lastpass
export ANSIBLE_VAULT_PASS_CLIENT_USERNAME=mail@bkahlert.com
export ANSIBLE_VAULT_PASSWORD_FILE=$(command -v ansible-vault-pass-client)

alias sc='source ~/.aliases'
source ~/.aliases

# To customize prompt, run `p10k configure` or edit ~/.p10k.zsh.
[ "${INTELLIJ_ENVIRONMENT_READER-}" ] || [ ! -f ~/.p10k.zsh ] || source ~/.p10k.zsh

# applied https://superuser.com/questions/433746/is-there-a-fix-for-the-too-many-open-files-in-system-error-on-os-x-10-7-1/1171028#1171028
#ulimit -n 16384
#sysctl kern.maxfiles
#sysctl kern.maxfilesperproc
#sysctl -w kern.maxfiles=65536
#sudo sysctl -w kern.maxfilesperproc=65536

export NVM_DIR="$HOME/.nvm"
[ -e "$NVM_DIR" ] || mkdir "$NVM_DIR"
[ -s "$(brew --prefix)/opt/nvm/nvm.sh" ] && \. "$(brew --prefix)/opt/nvm/nvm.sh"  # This loads nvm
[ "${INTELLIJ_ENVIRONMENT_READER-}" ] || {
  [ -s "$(brew --prefix)/opt/nvm/etc/bash_completion.d/nvm" ] && \. "$(brew --prefix)/opt/nvm/etc/bash_completion.d/nvm"  # This loads nvm bash_completion
}

# Auto-prompt for AWS CLI
AWS_CLI_AUTO_PROMPT=on

# tmux -CC for iTerm integration
# read https://gitlab.com/gnachman/iterm2/-/wikis/tmux-Integration-Best-Practices for more details


# Added by Toolbox App
export PATH="$PATH:$HOME/Library/Application Support/JetBrains/Toolbox/scripts"
