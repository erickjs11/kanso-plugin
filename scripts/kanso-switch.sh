#!/bin/sh
# Kanso is off while ~/.kanso-off exists. The SessionStart hook checks the same file.
case "$1" in
  off) touch "$HOME/.kanso-off" ;;
  on) rm -f "$HOME/.kanso-off" ;;
esac

if [ -f "$HOME/.kanso-off" ]; then
  echo "Kanso is off. It stays off in new sessions until /kanso on."
else
  echo "Kanso is on. It loads in every new session."
  [ "$1" = on ] && cat "$(dirname "$0")/../kanso.md"
fi
exit 0
