# granted: AWS IAM Identity Center profile switcher (https://docs.commonfate.io/granted)
# `assume` must be sourced (not executed) so it can export AWS_* vars into the current shell.
# The env var suppresses granted's "alias not configured" warning on every shell start.
[[ -n "$GRANTED_ALIAS_CONFIGURED" ]] || export GRANTED_ALIAS_CONFIGURED="true"
alias assume="source assume"
