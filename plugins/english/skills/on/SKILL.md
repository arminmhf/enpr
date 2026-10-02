---
name: on
description: Turn the English layer back on (Persian replies, occasional one-line ✎ English feedback).
disable-model-invocation: true
allowed-tools: Bash
---

!`mkdir -p ~/.claude/enpr && printf on > ~/.claude/enpr/mode && echo "mode=$(cat ~/.claude/enpr/mode)"; wc -l < ~/.claude/enpr/prompts.jsonl 2>/dev/null | xargs echo "unreviewed_prompts="`

Reply with exactly one short Persian line confirming the English layer is on. If
`unreviewed_prompts` is 40 or more, add one more short line suggesting `/english:review`.
Nothing else.
