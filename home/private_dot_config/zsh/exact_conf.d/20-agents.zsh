# Permission-bypassing shortcuts for installed AI CLIs; no CLI is invoked during shell startup.
if (( $+commands[claude] )); then
  alias clauded="claude --dangerously-skip-permissions"
fi
if (( $+commands[copilot] )); then
  alias copilotd="copilot --yolo"
fi
if (( $+commands[gemini] )); then
  alias geminid="gemini --yolo"
fi
