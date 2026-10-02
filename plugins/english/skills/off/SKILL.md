---
name: off
description: Turn the English layer off (no ✎ feedback, no prompt logging, normal Claude Code replies).
disable-model-invocation: true
allowed-tools: Bash
---

!`mkdir -p ~/.claude/enpr && printf off > ~/.claude/enpr/mode && echo "mode=$(cat ~/.claude/enpr/mode)"`

Reply with exactly one short Persian line confirming the English layer is off from the next
message, and that `/english:on` turns it back on. Nothing else.
