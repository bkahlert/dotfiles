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

# %{$(iterm2_prompt_mark)%} needed in ~/.p10k.zsh
[[ -f ~/.iterm2_shell_integration.zsh ]] || curl -L https://iterm2.com/shell_integration/install_shell_integration_and_utilities.sh | bash
[[ -f ~/.iterm2_shell_integration.zsh ]] && source ~/.iterm2_shell_integration.zsh

# Enable Powerlevel10k instant prompt. Should stay close to the top of ~/.zshrc.
# Initialization code that may require console input (password prompts, [y/n]
# confirmations, etc.) must go above this block; everything else may go below.
if [[ -r "${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh" ]]; then
  source "${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh"
fi

unsetopt nomatch # Don't require escaping globbing characters in zsh
unset LSCOLORS
export CLICOLOR=1
export CLICOLOR_FORCE=1
export HOMEBREW_AUTO_UPDATE_SECS=604800 # Homebrew updates once a week

ZLE_RPROMPT_INDENT=0
ZSH_AUTOSUGGEST_HIGHLIGHT_STYLE=fg=#666666
source $(brew --prefix)/share/antigen/antigen.zsh
antigen use oh-my-zsh
antigen bundles <<BUNDLES
zsh-users/zsh-autosuggestions                           # Proposes in dark grey an auto-completes command
zsh-users/zsh-syntax-highlighting                       # Syntax highlighting
zsh-users/zsh-completions                               # Tab to choose from completion options
git                                                     # Auto-completion?
brew                                                    # Auto-completion?
viasite-ansible/zsh-ansible-server                      # Auto-completion for ansible
greymd/docker-zsh-completion                            # Auto-completion for Docker / Docker Compose
gradle/gradle-completion                                # Auto-completion for Gradle
Downager/zsh-helmfile                                   # Auto-completion for Helm
djui/alias-tips                                         # Show alias if not used
Cloudstek/zsh-plugin-appup                              # up, down, start, restart, stop commands in docker-compose / vagrant dirs
desyncr/auto-ls                                         # Automatically call �ls� on cwd
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

PATH="/usr/local/sbin:$PATH"
PATH="$HOME/.local/bin:$PATH"
PATH="$HOME/bin:$PATH"
PATH="$HOME/.arkade/bin:$PATH"

export JAVA_HOME="/Library/Java/JavaVirtualMachines/jdk-11.0.2.jdk/Contents/Home"

# Aliases

# Prints the latest release version of a GitHub project.
# Example: gh-latest bkahlert/kommons
function gh-latest() {
    curl -s https://api.github.com/repos/"${1?Repository missing}"/releases/latest | jq -r .tag_name
}

## macOS aliases
if [[ $OSTYPE == darwin* ]]; then


    # Bluetooth restart
    function btrestart() {
      sudo kextunload -b com.apple.iokit.BroadcomBluetoothHostControllerUSBTransport
      sudo kextload -b com.apple.iokit.BroadcomBluetoothHostControllerUSBTransport
    }

    function ql() {
      (( $# > 0 )) && qlmanage -p $* &>/dev/null &
    }

    # Remove .DS_Store files recursively in a directory, default .
    function rmdsstore() {
      find "${@:-.}" -type f -name .DS_Store -delete
    }


    # kill ZScaler (and don't load it at startup; manually start by opening ZScaler app)
    alias start-zscaler="open -a /Applications/ZScaler/ZScaler.app --hide; sudo find /Library/LaunchDaemons -name '*zscaler*' -exec launchctl load {} \;"
    alias kill-zscaler="find /Library/LaunchAgents -name '*zscaler*' -exec launchctl unload {} \;;sudo find /Library/LaunchDaemons -name '*zscaler*' -exec launchctl unload {} \;"

    # open following file extensions with IDEA IntelliJ
    alias -s {kt,bat,txt,.md,.json,.yaml,.yml}=idea

    alias ip="dig +short myip.opendns.com @resolver1.opendns.com"
    alias localip="ipconfig getifaddr en0"
    alias flushdns="dscacheutil -flushcache"
    alias browse="open -a /Applications/Google\ Chrome.app"

    # open ~/.zshrc in using the default editor specified in $EDITOR
    alias ec="$EDITOR $HOME/.zshrc"

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

    # A cat(1) clone with syntax highlighting and Git integration.
    alias cat="bat --theme=\$(defaults read -globalDomain AppleInterfaceStyle &> /dev/null && echo default || echo GitHub)"

    alias ft="grep -rn -H -C 5 --exclude-dir={.git,.svn,CVS} -e"
    killport() {
     local port="$1"
     lsof -P -i:"${port}" | grep -i "listen" | sed -n 2p | awk '{print $2}' | xargs kill -9
    }

    # https://gitlab.dev.codefactory.sh/banking-platform/tooling-api-doc-builder#run-the-generator-locally
    alias dkb-docs=~/Development/DKB/tooling-api-doc-builder/bin/tooling-api-doc-builder-generate-docs-locally

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
fi

# To customize prompt, run `p10k configure` or edit ~/.p10k.zsh.
[[ ! -f ~/.p10k.zsh ]] || source ~/.p10k.zsh
