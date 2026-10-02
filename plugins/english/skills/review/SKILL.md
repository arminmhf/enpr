---
name: review
description: Review the user's recent English prompts, find recurring grammar patterns, update ~/.claude/enpr/profile.md, re-check mastered patterns on a spaced schedule, show the trend, and run a short retry drill built from the user's own sentences.
disable-model-invocation: true
argument-hint: "[quick]"
allowed-tools: Read, Edit, Write, Bash
---

# English review

The user is a Persian-speaking developer (reading C1, speaking A2, weak grammar) who wants
to turn passive English into active production. This is the main place where teaching happens.
Talk to the user in Persian; examples stay English. Keep the whole review under ~5 minutes.

## Data

Current profile:
!`cat ~/.claude/enpr/profile.md 2>/dev/null || echo "(no profile yet)"`

Spaced re-checks:
!`python3 "${CLAUDE_PLUGIN_ROOT}/scripts/enpr.py" due`

Trend from earlier reviews (pattern keys to reuse):
!`python3 "${CLAUDE_PLUGIN_ROOT}/scripts/enpr.py" trend`

Unreviewed prompts (newest last, max 300):
!`tail -n 300 ~/.claude/enpr/prompts.jsonl 2>/dev/null || echo "(no prompts logged)"`

## Steps

1. **Find patterns, not mistakes.** Group real errors (same rules as the ✎ line: structure, verb
   form/tense, agreement, missing `to`, dropped subject, question order, calques, and articles only
   when they recur) by underlying rule. Ignore typos, punctuation, terse imperative style, voice.
   A pattern needs ≥ 3 occurrences, or ≥ 2 if it is a structure error. For each pattern, also count
   how often the user produced the same structure correctly. Give each pattern a short kebab-case
   key; reuse the keys from the trend above for the same rule.

2. **Warm-up re-check** (only if re-checks are due; skip with `quick`): for each due Mastered
   pattern (max 2), first check the new prompts — if the user used that structure correctly ≥ 2
   times and never wrongly, it passes without asking. Otherwise give one quick production item
   (Persian meaning + dev context → they say/write the English). Pass → replace its tag with the
   `pass →` tag shown above. Fail → move the line back to Active without a tag.

3. **Update the profile** (`~/.claude/enpr/profile.md`) with Edit, keeping its sections:
   - `## Active` (max 5): `rule — wrong → right`, ≤ 100 chars. Injected into every prompt, so be
     terse. Most frequent / most damaging first.
   - `## Watching`: candidates with 1–2 hits, or patterns demoted from Active.
   - `## Mastered`: an Active pattern moves here when the new prompts show it used correctly ≥ 3
     times with no new errors. Append the "newly mastered" tag shown above.
   - Do not store: full prompts, project names, code, vocabulary lists, typos, CEFR self-ratings.

4. **Record the counts** for this review (all patterns you counted, including ones that were
   only correct) so the trend works next time:
   `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/enpr.py" record <<'EOF'`
   `{"prompts": <number of prompts reviewed>, "patterns": {"<key>": {"errors": N, "correct": N}}}`
   `EOF`

5. **Report** in ≤ 12 Persian lines:
   - top patterns (max 3), each with ONE of the user's own sentences → fixed, and a one-line rule;
   - promotions to Mastered and re-check results — the only progress signal, so state them plainly;
   - one trend line if there is history (e.g. `want-to: 20 → 5 خطا در هر ۱۰۰ prompt`). No charts.

6. **Retry drill** (skip if `$ARGUMENTS` is `quick`): pick 3 of the user's real wrong sentences.
   Show each one at a time as the *meaning* (short Persian paraphrase) plus a dev-context cue, and
   ask the user to produce the English sentence themselves (say it out loud first, or dictate).
   Do not show the original or the answer first. After each answer, give at most one ✎-style
   correction; if wrong, ask them to say it once more. Stop after 3 items or if the user says stop.

7. **Archive** the processed log so the next review only sees new prompts:
   `cd ~/.claude/enpr && cat prompts.jsonl >> archive.jsonl && : > prompts.jsonl && tail -n 3000 archive.jsonl > a.tmp && mv a.tmp archive.jsonl`

If there are fewer than 15 logged prompts, say so in one line, show the current Active patterns,
do the warm-up if something is due, and do the retry drill only if there is something to drill.
Do not record history for a review with fewer than 15 prompts.
