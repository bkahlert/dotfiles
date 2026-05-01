# granted: AWS IAM Identity Center profile switcher (https://docs.commonfate.io/granted)
# Install: brew install common-fate/granted/granted
# Usage:   assume prod          # switch to profile "prod" (prompts SSO login if token expired)
#          assume                # fuzzy-pick from all configured profiles
#
# `assume` must be sourced (not executed) so it can export AWS_* vars into the current shell.
# The env var suppresses granted's "alias not configured" warning on every shell start.
assume() {
  if ! command -v assume &>/dev/null; then
    if command -v brew &>/dev/null; then
      echo "granted not found — installing via Homebrew..."
      brew install common-fate/granted/granted || return 1
    else
      echo "granted not found and Homebrew is not available. Please install it manually."
      return 1
    fi
  fi
  source assume "$@"
}
export GRANTED_ALIAS_CONFIGURED="true"
