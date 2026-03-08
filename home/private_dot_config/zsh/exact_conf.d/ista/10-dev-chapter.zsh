# Manages dev-chapter repository and adds tools to PATH
# Automatically clones repo if missing and keeps it updated (weekly)

readonly DEV_CHAPTER_REPO="$HOME/Development/istaexpress/dev-chapter"
readonly DEV_CHAPTER_TOOLS="$DEV_CHAPTER_REPO/tools"
readonly _DC_GIT_REMOTE="https://gitlab.com/ista-se/cas/ista-express/shared/dev-chapter-time/dev-chapter.git"
readonly _DC_CACHE_DIR="$HOME/.cache/dev-chapter"
readonly _DC_LAST_PULL_FILE="$_DC_CACHE_DIR/last_pull"
readonly _DC_PULL_INTERVAL=$((7 * 24 * 60 * 60))

# Early exit if tools already in PATH
if [[ ":$PATH:" == *":$DEV_CHAPTER_TOOLS:"* ]]; then
  return 0
fi

# Clone repository if it doesn't exist
if [[ ! -d "$DEV_CHAPTER_REPO" ]]; then
  echo "Cloning dev-chapter repository to $DEV_CHAPTER_REPO..."
  mkdir -p "$(dirname "$DEV_CHAPTER_REPO")"

  if git clone "$_DC_GIT_REMOTE" "$DEV_CHAPTER_REPO" 2>/dev/null; then
    printf_success "Repository cloned successfully"
    mkdir -p "$_DC_CACHE_DIR"
    date +%s > "$_DC_LAST_PULL_FILE"
  else
    printf_error "Failed to clone dev-chapter repository"
    return 1
  fi
fi

# Update repository if it's been more than a week
if [[ -d "$DEV_CHAPTER_REPO/.git" ]]; then
  local should_pull=false

  if [[ ! -f "$_DC_LAST_PULL_FILE" ]]; then
    should_pull=true
  else
    local last_pull=$(cat "$_DC_LAST_PULL_FILE")
    local now=$(date +%s)
    local age=$((now - last_pull))

    if [[ $age -gt $_DC_PULL_INTERVAL ]]; then
      should_pull=true
    fi
  fi

  if [[ "$should_pull" == "true" ]]; then
    if git -C "$DEV_CHAPTER_REPO" pull --quiet --autostash 2>/dev/null; then
      mkdir -p "$_DC_CACHE_DIR"
      date +%s > "$_DC_LAST_PULL_FILE"
    else
      printf_warning "Failed to update dev-chapter repository"
    fi
  fi
fi

# Add tools to PATH if directory exists
if [[ -d "$DEV_CHAPTER_TOOLS" ]]; then
  export PATH="$DEV_CHAPTER_TOOLS:$PATH"
else
  printf_warning "dev-chapter tools directory not found at $DEV_CHAPTER_TOOLS"
fi
