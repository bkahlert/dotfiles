# remove ~/.antigen to force re-installation

# update Oh My Zsh without asking for confirmation
# shellcheck disable=SC2034
DISABLE_UPDATE_PROMPT=true

# update Oh My Zsh once a week
# shellcheck disable=SC2034
UPDATE_ZSH_DAYS=7

printf -v ZLE_RPROMPT_INDENT 0                       # no right margin for Powerlevel10k prompt

[ "${INTELLIJ_ENVIRONMENT_READER-}" ] || {
  source $(brew --prefix)/share/antigen/antigen.zsh

  antigen use oh-my-zsh

  antigen bundle zsh-users/zsh-autosuggestions        # proposes in dark grey an auto-completes command
  antigen bundle zsh-users/zsh-syntax-highlighting    # syntax highlighting
  antigen bundle zsh-users/zsh-completions            # tab to choose from completion options
  antigen bundle git                                  # aliases, i.e. g=git ga=add gp=push gl=pull glol=log
  antigen bundle dotenv                               # sources .env files automatically
  antigen bundle viasite-ansible/zsh-ansible-server   # auto-completion for ansible
  antigen bundle greymd/docker-zsh-completion         # auto-completion for Docker / Docker Compose
  antigen bundle gradle/gradle-completion             # auto-completion for Gradle
  antigen bundle Downager/zsh-helmfile                # auto-completion for Helm
  antigen bundle djui/alias-tips                      # show alias if not used
  antigen bundle Cloudstek/zsh-plugin-appup           # up, down, start, restart, stop commands in docker-compose / vagrant dirs

  antigen bundle desyncr/auto-ls                      # automatically call ls on cwd
  auto-ls-custom () {
    echo "Current directory list:"
    ls -ltra
  }
  AUTO_LS_COMMANDS=(custom)
  AUTO_LS_NEWLINE=false

  antigen bundle unixorn/autoupdate-antigen.zshplugin # auto-updates for Antigen and bundles
  antigen bundle TamCore/autoupdate-oh-my-zsh-plugins # auto-updates for Oh-my-ZSH plugins
  antigen bundle skywind3000/z.lua                    # use z instead of cd
  antigen bundle colored-man-pages                    # colors man pages
  antigen bundle macos                                # pfs=return the current Finder selection; cdf=cd to the current Finder directory

  antigen bundle web-search                           # search using google, bing, etc.
  ZSH_WEB_SEARCH_ENGINES=(
    q "https://search.bkahlert.com/?q="
    h "https://hello.bkahlert.com/?q="
  )

  antigen theme romkatv/powerlevel10k
  # antigen theme robbyrussell

  antigen apply
}
