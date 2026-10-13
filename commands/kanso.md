---
description: Turn Kanso on or off, or show its status
argument-hint: on | off | status
allowed-tools: Bash(sh:*)
---

!`sh "${CLAUDE_PLUGIN_ROOT}/scripts/kanso-switch.sh" "$ARGUMENTS"`

If Kanso is now off, stop following the Kanso rules for the rest of this
session. If it's now on and the rules aren't in your context, follow the rules
printed above for the rest of this session. Reply in one line with the state.
