# granted: AWS IAM Identity Center profile switcher (https://docs.commonfate.io/granted)
# Install: the Brewfile in run_once_before_01-install-packages
# Usage:   assume org           # switch to profile "org" (prompts SSO login if token expired)
#          assume                # fuzzy-pick from all configured profiles
#
# `assume` must be sourced (not executed) so it can export AWS_* vars into the current shell.
# The env var suppresses granted's "alias not configured" warning on every shell start.
assume() {
  source assume "$@"
}
export GRANTED_ALIAS_CONFIGURED="true"
