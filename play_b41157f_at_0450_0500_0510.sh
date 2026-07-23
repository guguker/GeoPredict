#!/bin/zsh
set -euo pipefail

MP3_FILE="$HOME/Documents/b41157f24341e2.mp3"
VOLUME_PERCENT=85
TARGET_DATE="$(/bin/date "+%Y-%m-%d")"
TARGET_TIMES=("04:50:00" "05:00:00" "05:10:00")
PLAYER_PID=""

if [[ ! -f "$MP3_FILE" ]]; then
  print -u2 "MP3 file not found: $MP3_FILE"
  exit 1
fi

cleanup() {
  if [[ -n "$PLAYER_PID" ]] && /bin/kill -0 "$PLAYER_PID" 2>/dev/null; then
    /bin/kill "$PLAYER_PID" 2>/dev/null || true
  fi
}

trap cleanup INT TERM

epoch_for_target() {
  local target_time="$1"
  /bin/date -j -f "%Y-%m-%d %H:%M:%S" "$TARGET_DATE $target_time" "+%s"
}

wait_until_epoch() {
  local target_epoch="$1"
  local remaining

  while (( (remaining = target_epoch - $(/bin/date "+%s")) > 0 )); do
    if (( remaining > 60 )); then
      /bin/sleep 60
    else
      /bin/sleep "$remaining"
    fi
  done
}

start_or_keep_playing() {
  local target_label="$1"

  /usr/bin/osascript -e "set volume output volume $VOLUME_PERCENT"

  if [[ -n "$PLAYER_PID" ]] && /bin/kill -0 "$PLAYER_PID" 2>/dev/null; then
    print "Playback is already running at $target_label; volume reset to $VOLUME_PERCENT%."
    return
  fi

  print "Starting infinite MP3 loop at $target_label with volume $VOLUME_PERCENT%."
  while true; do
    /usr/bin/afplay "$MP3_FILE"
  done &
  PLAYER_PID="$!"
}

for target_time in "${TARGET_TIMES[@]}"; do
  target_epoch="$(epoch_for_target "$target_time")"
  target_label="$TARGET_DATE $target_time"

  if (( $(/bin/date "+%s") > target_epoch )); then
    print "Skipping passed time: $target_label"
    continue
  fi

  print "Armed for $target_label. Keep this terminal open."
  wait_until_epoch "$target_epoch"
  start_or_keep_playing "$target_label"
done

if [[ -z "$PLAYER_PID" ]]; then
  print -u2 "All target times have already passed for $TARGET_DATE."
  exit 1
fi

wait "$PLAYER_PID"
