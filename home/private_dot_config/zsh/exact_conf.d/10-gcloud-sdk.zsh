# Google Cloud SDK — source PATH + completion from tarball or brew install.
_gcloud_sdk_dirs=(
  "$HOME/google-cloud-sdk"
)
if command -v brew &>/dev/null; then
  _gcloud_sdk_dirs+=("$(brew --prefix)/share/google-cloud-sdk")
fi

for _gcloud_sdk_dir in "${_gcloud_sdk_dirs[@]}"; do
  [[ -d $_gcloud_sdk_dir ]] || continue
  [[ -f $_gcloud_sdk_dir/path.zsh.inc ]]       && source "$_gcloud_sdk_dir/path.zsh.inc"
  [[ -f $_gcloud_sdk_dir/completion.zsh.inc ]] && source "$_gcloud_sdk_dir/completion.zsh.inc"
  break
done

unset _gcloud_sdk_dirs _gcloud_sdk_dir
