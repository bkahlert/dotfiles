# Print utility functions
# Source this file or copy these functions into standalone scripts.

# Prints error message in red to stderr
printf_error() {
  {
    tput setaf 1
    printf '%s' "$*"
    tput sgr0
    printf '\n'
  } >&2
}

# Prints info message in blue
printf_info() {
  tput setaf 4
  printf '%s\n' "$*"
  tput sgr0
}

# Prints success message in green
printf_success() {
  tput setaf 2
  printf '%s\n' "$*"
  tput sgr0
}

# Prints warning message in yellow
printf_warning() {
  tput setaf 3
  printf '%s\n' "$*"
  tput sgr0
}

# Prints error and exits with 1
die() {
  printf_error "${@}"
  exit 1
}
