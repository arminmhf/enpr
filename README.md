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
| `/english:review [quick]` | Find recurring patterns, update your profile, re-check mastered patterns on a spaced schedule (7 → 21 → 60 → 150 days), show the trend, 3-item retry drill (`quick` skips the drills) |
| `/english:practice [topic \| commit \| questions]` | 3 short speaking/writing tasks built from your current diff, commits and recent requests, aimed at your Active patterns |

## How it works

- `SessionStart` hook injects `plugins/english/rules.md` once per session (and after `/compact`).
- `UserPromptSubmit` hook logs the prose part of each English prompt (code, logs and obvious secrets
  stripped) and injects a one-line reminder plus your Active patterns.
- Once a day at most, when 40+ prompts are waiting or a mastered pattern is due, Claude adds one
  line suggesting `/english:review`.
- State lives in `~/.claude/enpr/` (never in a project): `mode`, `profile.md`, `prompts.jsonl`,
  `archive.jsonl`, `history.jsonl`, `nudged`. Edit `profile.md` by hand any time; only its `## Active` bullets (max 5) are sent.

## Tests

```
python3 -m unittest tests/test_enpr.py
```

Tip: dictate your prompts instead of typing them. That turns every prompt into speaking practice.
