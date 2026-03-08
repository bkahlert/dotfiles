# Starts a Claude session pre-loaded with ista Express GCloud debugging context
# Usage: gcloud-debug [claude options]
gcloud-debug() {
  claude --append-system-prompt "$(cat ~/Development/istaexpress/dev-chapter/ai/claude/agents/gcloud-debugger.md)" "$@"
}

# Logs into gcloud with the specified account
# Usage: gcloud-login [--admin]
gcloud-login() {
  local email="bjoern.kahlert@ista-express.de"

  while [ $# -gt 0 ]; do
    case $1 in
      --admin) email="bjoern.kahlert.admin@ista-express.de" && shift ;;
      *)
        printf_error "Unknown option: $1"
        printf_error "Usage: gcloud-login [--admin]"
        return 1
        ;;
    esac
  done

  if ! command -v gcloud &>/dev/null; then
    printf_error "gcloud CLI not found. Please install it first."
    return 1
  fi

  local current_account
  current_account=$(gcloud config get-value account 2>/dev/null)
  if [[ -n "$current_account" ]]; then
    printf_info "Current account: $current_account"
  fi

  printf_info "Logging in as: $email"
  printf_info "Chrome will open - select the appropriate profile from the dialog"

  if gcloud auth login "$email"; then
    printf_success "Successfully logged in as: $email"
  else
    printf_error "Login failed"
    return 1
  fi
}
