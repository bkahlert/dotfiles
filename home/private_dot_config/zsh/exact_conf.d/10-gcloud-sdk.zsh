# Google Cloud SDK — source PATH + completion from tarball or brew install.
_gcloud_sdk_dirs=(
  "$HOME/google-cloud-sdk"
)
# $HOMEBREW_PREFIX is exported by `brew shellenv` (.zprofile); a shell that did not inherit it takes
# the prefix brew sits in (<prefix>/bin/brew), which needs no fork either.
_brew_prefix=${HOMEBREW_PREFIX:-${commands[brew]:+${commands[brew]:h:h}}}
[[ -n $_brew_prefix ]] && _gcloud_sdk_dirs+=("$_brew_prefix/share/google-cloud-sdk")

for _gcloud_sdk_dir in "${_gcloud_sdk_dirs[@]}"; do
  [[ -d $_gcloud_sdk_dir ]] || continue
  [[ -f $_gcloud_sdk_dir/path.zsh.inc ]]       && source "$_gcloud_sdk_dir/path.zsh.inc"
  [[ -f $_gcloud_sdk_dir/completion.zsh.inc ]] && source "$_gcloud_sdk_dir/completion.zsh.inc"
  break
done

unset _gcloud_sdk_dirs _gcloud_sdk_dir _brew_prefix
