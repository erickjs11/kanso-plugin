#!/bin/sh
# Kanso is off while ~/.kanso-off exists. The SessionStart hook checks the same file.
OFF="$HOME/.kanso-off"
case "$1" in
  on)
    if [ -f "$OFF" ]; then
      rm -f "$OFF"
      echo "Kanso is turned on"
      cat "$(dirname "$0")/../kanso.md"
    else
      echo "Kanso is already on"
    fi ;;
  off)
    if [ -f "$OFF" ]; then
      echo "Kanso is already off"
    else
      touch "$OFF"
      echo "Kanso is turned off"
    fi ;;
  *)
    if [ -f "$OFF" ]; then echo "Status: Off"; else echo "Status: On"; fi ;;
esac
exit 0
