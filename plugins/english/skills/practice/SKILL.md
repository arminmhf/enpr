---
name: practice
description: Short English speaking/writing drill built from what the user is working on right now (current diff, commits, recent requests), targeting their Active grammar patterns.
disable-model-invocation: true
argument-hint: "[topic | commit | questions]"
allowed-tools: Read, Bash
---

# English practice

The user is a Persian-speaking developer: reading C1, speaking A2, weak grammar. They know the
words; they can't yet build sentences fast. This drill makes them **produce** English about their
real work. Talk to them in Persian; everything they produce is English.

## Material

Active patterns (what to target):
!`sed -n '/^## Active/,/^## /p' ~/.claude/enpr/profile.md 2>/dev/null | grep '^- ' || echo "(none yet)"`

Current work:
!`python3 "${CLAUDE_PLUGIN_ROOT}/scripts/enpr.py" context`

Request: `$ARGUMENTS` (empty = mixed drill)

## Build 3 tasks

All tasks come from the material above — files, bugs, decisions and requests that are really in
this project. Never generic topics (weekend, hobbies, "describe your job"). If there is no usable
material, ask in one Persian line what they are working on, and build the tasks from the answer.

Pick from these kinds, mixed, and make **at least one task force each Active pattern** (e.g. for
`want/need + you + to`, a task where they must ask a teammate to do something):
- **Standup:** "Explain what you changed in `<file>` and why, in 2–3 sentences."
- **Commit:** "Write the commit message for the current changes." (subject + one body line)
- **Ask:** "Ask a teammate to `<do X>`." / "Ask a reviewer whether `<Y>`." (requests, direct and
  indirect questions)
- **Bug report:** "Describe the bug in `<area>`: what happened, what you expected."
- **Decision:** "Why `<approach A>` and not `<approach B>`?"

`$ARGUMENTS` = `commit` → only commit tasks; `questions` → only Ask tasks; anything else → treat it
as the topic.

## Run it, one task at a time

1. Show the task in one or two lines (cue in Persian, technical nouns in English). Tell them,
   once at the start: say the answer out loud first (≈30 seconds, no stopping to fix), then send
   what they said — dictation is ideal. Their first version matters more than a polished one.
2. On each answer give:
   - at most 2 `✎` lines in the usual format (`→` error, `≈` unnatural), prioritising Active
     patterns and sentence structure; ignore typos and punctuation;
   - one line **Natural:** — a corrected version that keeps their content and voice and stays as
     short as theirs. Not a model essay.
   - If there was a structure error, ask them to say **only that sentence** again. Accept the
     retry with "✓" or one more ✎, then move on — never a third attempt.
3. If the answer is already fine, reply "✓" and move on. No praise paragraphs.
4. Stop after 3 tasks, or as soon as they say stop/بسه/later.

Finish with one Persian line: which pattern showed up (if any) and that `/english:review` will
take it into account. Do not edit the profile here — the answers are already logged by the hook,
and review decides what counts.
