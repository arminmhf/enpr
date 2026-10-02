# enpr — invisible English layer for Claude Code

Work in English, get Persian replies, and once in a while a single line like:

```
✎ `want you check` → `want you to check`
```

Recurring mistakes are tracked automatically and reviewed only when you ask (`/english:review`).
Design rationale (Persian): [docs/DESIGN.md](docs/DESIGN.md).

## Install

```
/plugin marketplace add arminmhf/enpr
/plugin install english@enpr
```

Restart Claude Code. Requires `python3` on your PATH.

## Commands

| Command | What it does |
|---|---|
| `/english:off` | No feedback, no logging, normal replies |
| `/english:on` | Back on (default) |
| `/english:review [quick]` | Find recurring patterns, update your profile, 3-item retry drill (`quick` skips the drill) |

## How it works

- `SessionStart` hook injects `plugins/english/rules.md` once per session (and after `/compact`).
- `UserPromptSubmit` hook logs the prose part of each English prompt (code, logs and obvious secrets
  stripped) and injects a one-line reminder plus your Active patterns.
- State lives in `~/.claude/enpr/` (never in a project): `mode`, `profile.md`, `prompts.jsonl`,
  `archive.jsonl`. Edit `profile.md` by hand any time; only its `## Active` bullets (max 5) are sent.

Tip: dictate your prompts instead of typing them. That turns every prompt into speaking practice.
