# Google Cloud SDK — source PATH + completion from tarball or brew install.
_gcloud_sdk_dirs=(
  "$HOME/google-cloud-sdk"
)
# $HOMEBREW_PREFIX is exported by `brew shellenv` (.zprofile); unset means no Homebrew lookup.
[[ -n ${HOMEBREW_PREFIX-} ]] && _gcloud_sdk_dirs+=("$HOMEBREW_PREFIX/share/google-cloud-sdk")

for _gcloud_sdk_dir in "${_gcloud_sdk_dirs[@]}"; do
  [[ -d $_gcloud_sdk_dir ]] || continue
  [[ -f $_gcloud_sdk_dir/path.zsh.inc ]]       && source "$_gcloud_sdk_dir/path.zsh.inc"
  [[ -f $_gcloud_sdk_dir/completion.zsh.inc ]] && source "$_gcloud_sdk_dir/completion.zsh.inc"
  break
done

unset _gcloud_sdk_dirs _gcloud_sdk_dir
