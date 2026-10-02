#!/usr/bin/env python3
"""Hook entry point for the English layer.

  enpr.py session-start   -> SessionStart: inject rules.md once per session (and after /compact)
  enpr.py prompt          -> UserPromptSubmit: log the prompt, inject a one-line reminder

State lives in ~/.claude/enpr/ (user-level, never inside a project):
  mode          "on" (default) or "off"
  profile.md    the learner profile; only its "## Active" bullets are injected
  prompts.jsonl prompts not yet processed by /english:review

Any failure exits 0 silently: the English layer must never block real work.
"""
import json
import os
import re
import sys
import time
from pathlib import Path

DATA = Path(os.environ.get("ENPR_HOME", Path.home() / ".claude" / "enpr"))
PLUGIN_ROOT = Path(__file__).resolve().parent.parent
MAX_ACTIVE = 5
MAX_LOG_CHARS = 600
MAX_LOG_LINES = 2000

PROFILE_TEMPLATE = """# English profile

Edited by /english:review. You can edit it by hand too.
Only the bullets under "Active" are sent to Claude (max 5), so keep them short.

## Active
<!-- one line per pattern: rule — wrong → right -->

## Watching

## Mastered
"""

SECRET_RE = re.compile(
    r"(?i)(sk-[a-z0-9_-]{16,}|gh[pousr]_[a-z0-9]{20,}|AKIA[0-9A-Z]{16}|"
    r"(?:api[_-]?key|token|secret|password)\s*[:=]\s*\S+|[A-Za-z0-9+/_-]{40,})"
)


def mode():
    try:
        return (DATA / "mode").read_text().strip() or "on"
    except OSError:
        return "on"


def ensure_data():
    DATA.mkdir(parents=True, exist_ok=True)
    profile = DATA / "profile.md"
    if not profile.exists():
        profile.write_text(PROFILE_TEMPLATE)


def active_patterns():
    try:
        text = (DATA / "profile.md").read_text()
    except OSError:
        return []
    m = re.search(r"^## Active\s*$(.*?)(?=^## |\Z)", text, re.M | re.S)
    if not m:
        return []
    items = [l[2:].strip() for l in m.group(1).splitlines() if l.startswith("- ")]
    return [i[:120] for i in items if i][:MAX_ACTIVE]


def prose_only(prompt):
    """Drop fenced code and log-like lines; English feedback is about the user's own sentences."""
    prompt = re.sub(r"```.*?```", " ", prompt, flags=re.S)
    keep = []
    for line in prompt.splitlines():
        s = line.strip()
        if not s or line.startswith(("    ", "\t")) or s.startswith(("at ", "File \"", "Traceback", "$ ", ">")):
            continue
        keep.append(s)
    return SECRET_RE.sub("[redacted]", " ".join(keep))[:MAX_LOG_CHARS]


def is_mostly_persian(text):
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return True
    arabic = sum(1 for c in letters if "؀" <= c <= "ۿ")
    return arabic / len(letters) > 0.3


def log_prompt(prompt, cwd):
    if prompt.lstrip().startswith("/"):
        return
    text = prose_only(prompt)
    if len(text.split()) < 3 or is_mostly_persian(text):
        return
    path = DATA / "prompts.jsonl"
    entry = {"ts": int(time.time()), "project": Path(cwd or ".").name, "text": text}
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    # Keep the unreviewed log bounded even if the user never runs a review.
    lines = path.read_text(encoding="utf-8").splitlines()
    if len(lines) > MAX_LOG_LINES:
        path.write_text("\n".join(lines[-MAX_LOG_LINES:]) + "\n", encoding="utf-8")


def session_start(_event):
    ensure_data()
    if mode() == "off":
        return
    rules = (PLUGIN_ROOT / "rules.md").read_text(encoding="utf-8")
    print(json.dumps({
        "hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": rules}
    }))


def prompt_submit(event):
    if mode() == "off":
        print("[enpr] English layer is OFF: give no ✎ feedback and reply in the language the user wrote in.")
        return
    ensure_data()
    log_prompt(event.get("prompt", ""), event.get("cwd"))
    line = "[enpr] English layer ON: reply in Persian; at most one ✎ line at the very end, only if the rules' threshold is met."
    patterns = active_patterns()
    if patterns:
        line += " Active patterns: " + " | ".join(patterns)
    print(line)


def main():
    try:
        event = json.load(sys.stdin)
    except Exception:
        event = {}
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    {"session-start": session_start, "prompt": prompt_submit}.get(cmd, lambda e: None)(event)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
