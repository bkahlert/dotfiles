# Enable interactive auto-prompt mode in the AWS CLI when available.
if command -v aws &>/dev/null; then
  export AWS_CLI_AUTO_PROMPT=on
fi
