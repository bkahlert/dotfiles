# Logs into gcloud with the specified account.
# Copies the account's Google password from 1Password to the clipboard so it can
# be pasted into the browser login that gcloud opens; the previous clipboard
# content is restored once gcloud returns.
# Usage: gcloud-login [--admin]
gcloud-login() {
  local email="bjoern.kahlert@ista-express.de"
  # Items are referenced by ID: the admin item's title, "Google (Admin)",
  # contains parentheses, which op:// secret references reject.
  local op_ref="op://Employee/gzcxoxeug2wr2bq6moqkozamlq/password" # "Google"

  while [ $# -gt 0 ]; do
    case $1 in
      --admin)
        email="bjoern.kahlert.admin@ista-express.de"
        op_ref="op://Employee/p44thhnd5ylh6zrm6etwozs63a/password" # "Google (Admin)"
        shift
        ;;
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
  local password previous_clipboard
  if password=$(op read --no-newline "$op_ref" 2>/dev/null) && [[ -n "$password" ]]; then
    previous_clipboard=$(pbpaste)
    printf '%s' "$password" | pbcopy
    printf_info "Password for $email copied to clipboard"
  else
    printf_warning "Could not read password from 1Password ($op_ref)"
  fi
  printf_info "Chrome will open - select the appropriate profile from the dialog"

  local login_status=0
  gcloud auth login "$email" || login_status=$?

  if [[ -n "$password" ]]; then
    printf '%s' "$previous_clipboard" | pbcopy
    printf_info "Clipboard restored"
  fi

  if (( login_status == 0 )); then
    printf_success "Successfully logged in as: $email"
  else
    printf_error "Login failed"
    return 1
  fi
}
