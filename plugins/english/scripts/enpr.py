#!/usr/bin/env python3
"""Hook and helper entry point for the English layer.

Hooks (read the event JSON on stdin):
  enpr.py session-start   SessionStart: inject rules.md once per session (and after /compact)
  enpr.py prompt          UserPromptSubmit: log the prompt, inject a one-line reminder

Helpers (called from skills via !`...`):
  enpr.py due             Mastered patterns whose spaced re-check is due, with the tags to write
  enpr.py record          append one review's counts (JSON on stdin) to history.jsonl
  enpr.py trend           errors per 100 prompts per pattern over the last reviews
  enpr.py context         what the user is working on (git + recent prompts) for practice

State lives in ~/.claude/enpr/ (user-level, never inside a project):
  mode           "on" (default) or "off"
  profile.md     the learner profile; only its "## Active" bullets are injected
  prompts.jsonl  prompts not yet processed by /english:review
  archive.jsonl  processed prompts (bounded)
  history.jsonl  one line of counts per review
  nudged         date of the last "time for a review" nudge

Any failure exits 0 silently: the English layer must never block real work.
"""
import datetime as dt
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

DATA = Path(os.environ.get("ENPR_HOME", Path.home() / ".claude" / "enpr"))
PLUGIN_ROOT = Path(__file__).resolve().parent.parent
MAX_ACTIVE = 5
MAX_LOG_CHARS = 600
MAX_LOG_LINES = 2000
REVIEW_AFTER = 40  # unreviewed prompts before a once-a-day nudge
INTERVALS = [7, 21, 60, 150]  # days between re-checks of a Mastered pattern
TAG_RE = re.compile(r"\[next:\s*(\d{4}-\d{2}-\d{2})\s*·\s*step\s*(\d+)\]")

PROFILE_TEMPLATE = """# English profile

Edited by /english:review. You can edit it by hand too.
Only the bullets under "Active" are sent to Claude (max 5), so keep them short.

## Active
<!-- one line per pattern: rule — wrong → right -->

## Watching

## Mastered
<!-- rule — wrong → right [next: YYYY-MM-DD · step N] -->
"""

SECRET_RE = re.compile(
    r"(?i)(sk-[a-z0-9_-]{16,}|gh[pousr]_[a-z0-9]{20,}|AKIA[0-9A-Z]{16}|"
    r"(?:api[_-]?key|token|secret|password)\s*[:=]\s*\S+|[A-Za-z0-9+/_-]{40,})"
)


def today():
    override = os.environ.get("ENPR_TODAY")
    return dt.date.fromisoformat(override) if override else dt.date.today()


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


def section(name):
    """Bullet texts under '## <name>' in profile.md."""
    try:
        text = (DATA / "profile.md").read_text(encoding="utf-8")
    except OSError:
        return []
    m = re.search(rf"^## {name}\s*$(.*?)(?=^## |\Z)", text, re.M | re.S)
    if not m:
        return []
    return [l[2:].strip() for l in m.group(1).splitlines() if l.startswith("- ") and l[2:].strip()]


def active_patterns():
    return [i[:120] for i in section("Active")][:MAX_ACTIVE]


def due_items():
    """(line, step) for Mastered patterns whose next re-check date has come; untagged ones are due."""
    out = []
    for line in section("Mastered"):
        m = TAG_RE.search(line)
        if not m:
            out.append((line, 0))
        elif dt.date.fromisoformat(m.group(1)) <= today():
            out.append((line, int(m.group(2))))
    return out


def tag(step):
    days = INTERVALS[min(max(step, 1), len(INTERVALS)) - 1]
    return f"[next: {(today() + dt.timedelta(days=days)).isoformat()} · step {step}]"


def count_lines(path):
    try:
        with path.open(encoding="utf-8") as f:
            return sum(1 for _ in f)
    except OSError:
        return 0


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


def review_nudge():
    """At most once a day, ask Claude to suggest /english:review in one line."""
    stamp = DATA / "nudged"
    try:
        if stamp.read_text().strip() == today().isoformat():
            return ""
    except OSError:
        pass
    pending, due = count_lines(DATA / "prompts.jsonl"), len(due_items())
    if pending < REVIEW_AFTER and not due:
        return ""
    stamp.write_text(today().isoformat())
    what = []
    if pending >= REVIEW_AFTER:
        what.append(f"{pending} prompts collected")
    if due:
        what.append(f"{due} mastered pattern(s) due for a re-check")
    return (" Once, after the task (skip if the user is under pressure): add one short Persian line"
            f" suggesting /english:review ({', '.join(what)}).")


# ---- hooks ------------------------------------------------------------------

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
    print(line + review_nudge())


# ---- helpers for skills -----------------------------------------------------

def cmd_due():
    items = due_items()
    print(f"today: {today().isoformat()}")
    print(f"tag for a newly mastered pattern: {tag(1)}")
    if not items:
        print("due re-checks: none")
        return
    print("due re-checks (pass → replace the tag; fail → move the line back to Active without a tag):")
    for line, step in items:
        print(f"- {TAG_RE.sub('', line).strip()}\n    pass → {tag(step + 1)}")


def cmd_record():
    data = json.load(sys.stdin)
    prompts = int(data["prompts"])
    patterns = {str(k): {"errors": int(v.get("errors", 0)), "correct": int(v.get("correct", 0))}
                for k, v in data.get("patterns", {}).items()}
    ensure_data()
    entry = {"date": today().isoformat(), "prompts": prompts, "patterns": patterns}
    with (DATA / "history.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    print("recorded")


def cmd_trend(limit=6):
    try:
        rows = [json.loads(l) for l in (DATA / "history.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    except OSError:
        rows = []
    rows = [r for r in rows if r.get("prompts")][-limit:]
    if not rows:
        print("no review history yet")
        return
    print("errors per 100 prompts, oldest → newest (dates: " + ", ".join(r["date"] for r in rows) + ")")
    keys = {k for r in rows for k in r["patterns"]}
    latest = rows[-1]

    def rate(r, k):
        p = r["patterns"].get(k)
        return None if p is None else round(100 * p["errors"] / r["prompts"])

    order = sorted(keys, key=lambda k: -(rate(latest, k) or 0))
    for k in order[:8]:
        series = " → ".join("·" if rate(r, k) is None else str(rate(r, k)) for r in rows)
        print(f"- {k}: {series}")


def git(*args):
    try:
        r = subprocess.run(["git", *args], capture_output=True, text=True, timeout=5)
        return r.stdout.strip() if r.returncode == 0 else ""
    except Exception:
        return ""


def cmd_context():
    cwd = Path.cwd()
    branch = git("rev-parse", "--abbrev-ref", "HEAD")
    print(f"project: {cwd.name}")
    if branch:
        print(f"branch: {branch}")
        for title, args in [("uncommitted changes", ("diff", "--stat", "HEAD")),
                            ("recent commits", ("log", "--oneline", "-5"))]:
            out = "\n".join(git(*args).splitlines()[-12:])
            if out:
                print(f"{title}:\n{out}")
    else:
        print("not a git repository")
    try:
        lines = (DATA / "prompts.jsonl").read_text(encoding="utf-8").splitlines()
    except OSError:
        lines = []
    recent = [json.loads(l)["text"][:200] for l in lines if l.strip()
              and json.loads(l).get("project") == cwd.name][-5:]
    if recent:
        print("user's recent requests in this project:")
        for t in recent:
            print(f"- {t}")


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    hooks = {"session-start": session_start, "prompt": prompt_submit}
    if cmd in hooks:
        try:
            event = json.load(sys.stdin)
        except Exception:
            event = {}
        hooks[cmd](event)
    elif cmd in ("due", "record", "trend", "context"):
        {"due": cmd_due, "record": cmd_record, "trend": cmd_trend, "context": cmd_context}[cmd]()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # never break the session; helpers report why they did nothing
        if len(sys.argv) > 1 and sys.argv[1] in ("due", "record", "trend", "context"):
            print(f"enpr {sys.argv[1]} failed: {e}")
    sys.exit(0)
