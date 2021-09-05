#
# .zshrc
#
# @author Björn Kahlert
#
if [ ! -z "${recording}" ]; then
    [ ! -f ~/.hushlogin ] && touch ~/.hushlogin
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
    [ -f ~/.hushlogin ] && rm ~/.hushlogin

    export ITERM2_SQUELCH_MARK=1
    source ~/.iterm2_shell_integration.zsh

    export ZSH="/Users/bkahlert/.oh-my-zsh"
    ZSH_THEME="powerlevel9k/powerlevel9k"
    POWERLEVEL9K_LEFT_PROMPT_ELEMENTS=(root_indicator os_icon dir dir_writable rbenv vcs)
    POWERLEVEL9K_RIGHT_PROMPT_ELEMENTS=(status root_indicator background_jobs time)
    POWERLEVEL9K_PROMPT_ON_NEWLINE=true
    POWERLEVEL9K_PROMPT_ADD_NEWLINE=true
    #POWERLEVEL9K_VCS_MODIFIED_BACKGROUND=’red’

    # Visual customisation of the second prompt line
    local user_symbol="$"
    if [[ $(print -P "%#") =~ "#" ]]; then
        user_symbol = "#"
    fi
    POWERLEVEL9K_MULTILINE_LAST_PROMPT_PREFIX="%{$(iterm2_prompt_mark)%}%{%B%F{black}%K{yellow}%} $user_symbol%{%b%f%k%F{yellow}%} %{%f%}"

    ENABLE_CORRECTION=false
    COMPLETION_WAITING_DOTS=true
    HIST_STAMPS="yyyy-mm-dd"
    plugins=(git zsh-autosuggestions zsh-syntax-highlighting)

    source $ZSH/oh-my-zsh.sh
    source /usr/local/share/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh
fi

export SSH_KEY_PATH="${HOME}/.ssh/id_rsa20"
ssh-add -K "${SSH_KEY_PATH}" &>/dev/null

export EDITOR=idea

export JAVA_HOME=/Library/Java/JavaVirtualMachines/jdk-11.0.2.jdk/Contents/Home
#export ANDROID_SDK_PATH=/Users/bkahlert/Library/Android/sdk/platform-tools
#export JAVA_HOME=/Library/Java/JavaVirtualMachines/graalvm-ce-java11-20.2.0/Contents/Home
export GRAALVM_HOME=/Library/Java/JavaVirtualMachines/graalvm-ce-java11-20.2.0/Contents/Home
export GRAALVM_VERSION=20.2.0-java11

# Python
export PATH="$HOME/Library/Python/3.9/bin:$PATH"
# Guile (Ansible dependency)
export GUILE_LOAD_PATH="/usr/local/share/guile/site/3.0"
export GUILE_LOAD_COMPILED_PATH="/usr/local/lib/guile/3.0/site-ccache"
export GUILE_SYSTEM_EXTENSIONS_PATH="/usr/local/lib/guile/3.0/extensions"

# ALIASES

# kill ZScaler (and don't load it at startup; manually start by opening ZScaler app)
alias start-zscaler="open -a /Applications/ZScaler/ZScaler.app --hide; sudo find /Library/LaunchDaemons -name '*zscaler*' -exec launchctl load {} \;"
alias kill-zscaler="find /Library/LaunchAgents -name '*zscaler*' -exec launchctl unload {} \;;sudo find /Library/LaunchDaemons -name '*zscaler*' -exec launchctl unload {} \;"

# open following file extensions with IDEA IntelliJ
alias -s {kt,bat,txt}=idea

# macOS aliasses
if [[ $OSTYPE == darwin* ]]; then
    alias flush="dscacheutil -flushcache"
    alias browse="open -a /Applications/Google\ Chrome.app"
fi

# open ~/.zshrc in using the default editor specified in $EDITOR
alias ec="$EDITOR $HOME/.zshrc"

# source ~/.zshrc
alias sc="source $HOME/.zshrc"

# serve . (or public dir if exists) by http
alias serve="npx http-server -c -p 80"
alias live="npx live-server --port=80 --no-browser"

# session record <name>
# https://github.com/faressoft/terminalizer
# Usage:
# 1) record session: `record name`
# 2) play recorded session: `play name`
# 3) edit recorded session: `open name.yml`
# 4) render preview: `preview name`
# 5) render: `render name`
alias session="npx terminalizer"
alias record="[ ! -f \"${HOME}/.hushlogin\" ] && touch \"${HOME}/.hushlogin\"; osascript -e \"tell application \\\"iTerm\\\"\" -e \"set bounds of front window to {300, 30, 1290, 740}\" -e \"end tell\"; npx terminalizer record --skip-sharing"
alias play="npx terminalizer play"
alias preview="npx terminalizer render -s 10 -q 30"
alias render="npx terminalizer render -s 1 -q 30"

# https://github.com/nvbn/thefuck
# type fuck to auto-correct failed commands
eval $(thefuck --alias fuck)

# type "samples x" instead of "man x" for examples for a command
alias samples="tldr"
alias examples="tldr"

# An interactive cheatsheet tool for the command-line and application launchers.
eval "$(navi widget zsh)"

# A cat(1) clone with syntax highlighting and Git integration.
alias cat="bat --theme=\$(defaults read -globalDomain AppleInterfaceStyle &> /dev/null && echo default || echo GitHub)"

# IP address aliases
alias publicip="dig +short myip.opendns.com @resolver1.opendns.com"
alias localip="ipconfig getifaddr en0" #wireless
alias ipv4="ifconfig -a | grep -o 'inet \(\([0-9]\+\.[0-9]\+\.[0-9]\+\.[0-9]\+\)\|[a-fA-F0-9:]\+\)' | sed -e 's/inet //'"
alias ipv6="ifconfig -a | grep -o 'inet6 \(\([0-9]\+\.[0-9]\+\.[0-9]\+\.[0-9]\+\)\|[a-fA-F0-9:]\+\)' | sed -e 's/inet6 //'"
alias afconfig="ifconfig | pcregrep -M -o '^[^\t:]+:([^\n]|\n\t)*status: active'"

# Flush Directory Service cache
alias flushdns="dscacheutil -flushcache && sudo killall -HUP mDNSResponder"


alias findtext="grep -rnw . -e"
killport() {
 local port="$1"
 lsof -P -i:"${port}" | grep -i "listen" | sed -n 2p | awk '{print $2}' | xargs kill -9
}

# https://gitlab.dev.codefactory.sh/banking-platform/tooling-api-doc-builder#run-the-generator-locally
alias dkb-docs=~/Development/DKB/tooling-api-doc-builder/bin/tooling-api-doc-builder-generate-docs-locally

# docker auto-completion, https://docs.docker.com/docker-for-mac/#zsh
etc=/Applications/Docker.app/Contents/Resources/etc
[ ! -f /usr/local/share/zsh/site-functions/_docker ] && ln -s $etc/docker.zsh-completion /usr/local/share/zsh/site-functions/_docker
[ ! -f /usr/local/share/zsh/site-functions/_docker-compose ] && ln -s $etc/docker-compose.zsh-completion /usr/local/share/zsh/site-functions/_docker-compose

# generates code for OpenAPI spec $1 (default: first json/yaml/yml file found in specs dir) in generator $2 (default: kotlin)
openapi() {
 local specFile="${1:-$(find specs -type f \( -iname \*.json -o -iname \*.yaml -o -iname \*.yml \) | head -n 1)}"
 local generator="${2:-kotlin}"
 local outDir="out/${generator}"
 local absOutDir="${PWD}/${outDir}"
 echo "Generating ${generator} code for ${specFile} at ${absOutDir}"
 mkdir -p "${absOutDir}"
 docker run --rm -v "${PWD}:/local" openapitools/openapi-generator-cli generate \
   -i "/local/${specFile}" \
   -g "${generator}" \
   -o "/local/${outDir}"
}
swagger() {
 local specFile="${1:-$(find specs -type f \( -iname \*.json -o -iname \*.yaml -o -iname \*.yml \) | head -n 1)}"
 local lang="${2:-kotlin}"
 local outDir="out/${lang}"
 local absOutDir="${PWD}/${outDir}"
 echo "Generating ${lang} code for ${specFile} at ${absOutDir}"
 mkdir -p "${absOutDir}"
 docker run --rm -v "${PWD}:/local" swaggerapi/swagger-codegen-cli generate \
   -i "/local/${specFile}" \
   -l "${lang}" \
   -o "/local/${outDir}"
}

alias fix-spotlight='find . -type d \( -name "node_modules" -o -name ".git" \) -exec touch "{}/.metadata_never_index" \;'


#export PATH=$GRAALVM_HOME/bin:$PATH


POWERLEVEL9K_MODE='awesome-patched'
POWERLEVEL9K_SHORTEN_DIR_LENGTH=20




POWERLEVEL9K_OS_ICON_BACKGROUND="white"
POWERLEVEL9K_OS_ICON_FOREGROUND="blue"
POWERLEVEL9K_DIR_HOME_FOREGROUND="white"
POWERLEVEL9K_DIR_HOME_SUBFOLDER_FOREGROUND="white"
POWERLEVEL9K_DIR_DEFAULT_FOREGROUND="white"

export PATH="$HOME/bin:/usr/local/sbin:$PATH"

#THIS MUST BE AT THE END OF THE FILE FOR SDKMAN TO WORK!!!
export SDKMAN_DIR="/Users/bkahlert/.sdkman"
[[ -s "/Users/bkahlert/.sdkman/bin/sdkman-init.sh" ]] && source "/Users/bkahlert/.sdkman/bin/sdkman-init.sh"


#
# .zshrc
#
# @author Jeff Geerling
#

# Colors.
unset LSCOLORS
export CLICOLOR=1
export CLICOLOR_FORCE=1

# Don't require escaping globbing characters in zsh.
unsetopt nomatch

# Tell homebrew to not autoupdate every single time I run it (just once a week).
export HOMEBREW_AUTO_UPDATE_SECS=604800
