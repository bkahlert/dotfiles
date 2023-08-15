# used by `web-search` plugin
# shellcheck disable=SC2034
ZSH_WEB_SEARCH_ENGINES=(
  q "https://search.bkahlert.com/?q="
  h "https://hello.bkahlert.com/?q="
)

# update Oh My Zsh without asking for confirmation
# shellcheck disable=SC2034
DISABLE_UPDATE_PROMPT=true

# update Oh My Zsh once a week
# shellcheck disable=SC2034
UPDATE_ZSH_DAYS=7

printf -v ZSH_AUTOSUGGEST_HIGHLIGHT_STYLE fg=#666666 # color of auto-suggestions
printf -v ZLE_RPROMPT_INDENT 0                       # no right margin for Powerlevel10k prompt
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
skywind3000/z.lua                                       # use z instead of cd
colored-man-pages                                       # colors man pages
web-search                                              # search using google, bing, etc.
macos                                                   # pfs=return the current Finder selection; cdf=cd to the current Finder directory
BUNDLES
  antigen theme romkatv/powerlevel10k
  antigen apply
}
