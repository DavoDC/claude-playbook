#!/bin/bash
# launch-claude.sh - Claude Code session launcher
# Arrow-key or number-key picker for session type and model.
# Copy to your workspace root and run instead of typing claude flags manually.

WORKSPACE_DIR="$(pwd)"   # or set to an absolute path
LOG_DIR="$WORKSPACE_DIR/logs"
LOG_FILE="$LOG_DIR/claude-launch.log"
PICK=0

_pick_draw() {
  local i
  for i in "${!_items[@]}"; do
    if [ "$i" -eq "$_sel" ]; then printf "\e[7m> %s\e[0m\e[K\n" "${_items[$i]}"
    else printf "  %s\e[K\n" "${_items[$i]}"; fi
  done
}

_pick() {
  local prompt="$1"; shift
  local _items=("$@") _sel=0 _n=${#_items[@]} key rest
  printf "  %s\n  (arrows + Enter  |  1-%d quick  |  q quit)\n\n" "$prompt" "$_n"
  printf "\e[?25l"
  _pick_draw
  while true; do
    IFS= read -rsn1 key
    if [[ "$key" == $'\e' ]]; then IFS= read -rsn2 -t 0.05 rest || rest=""; key+="$rest"; fi
    case "$key" in
      $'\e[A'|k) ((_sel = (_sel - 1 + _n) % _n)) ;;
      $'\e[B'|j) ((_sel = (_sel + 1) % _n)) ;;
      [1-9]) if (( key >= 1 && key <= _n )); then _sel=$((key - 1)); break; fi ;;
      "") break ;;
      q|Q) printf "\e[?25h\n"; exit 0 ;;
    esac
    printf "\e[%dA" "$_n"
    _pick_draw
  done
  printf "\e[?25h\n"
  PICK=$_sel
}

cd "$WORKSPACE_DIR"

# Screen 1: session type
clear
printf "\n  Claude Code\n\n"
_pick "Session?" \
  "bypass-permissions  (skip permission prompts - use with trusted projects)" \
  "new                 (fresh start)" \
  "continue            (auto-resumes most recent, no prompt)" \
  "resume              (shows conversation picker)"
session=$PICK

# Screen 2: model
clear
printf "\n  Claude Code\n\n"
session_labels=("bypass-permissions" "new" "continue" "resume")
printf "  Session: %s\n\n" "${session_labels[$session]}"
_pick "Model?" \
  "sonnet   (default - interactive + daily work)" \
  "haiku    (fast + cheap - simple tasks + automation)" \
  "opus     (most capable - complex reasoning)"
model=$PICK

# Build command
cmd="claude"
case $session in
  0) cmd="claude --dangerously-skip-permissions" ;;
  2) cmd+=" --continue" ;;
  3) cmd+=" --resume" ;;
esac
case $model in
  0) cmd+=" --model sonnet" ;;
  1) cmd+=" --model haiku" ;;
  2) cmd+=" --model opus" ;;
esac

clear
printf "\n  Launching: %s\n\n" "$cmd"
mkdir -p "$LOG_DIR"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] $cmd" >> "$LOG_FILE"
eval $cmd
EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ]; then
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Exit code: $EXIT_CODE" >> "$LOG_FILE"
fi

exec bash
