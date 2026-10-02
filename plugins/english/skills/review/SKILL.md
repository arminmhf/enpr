---
name: review
description: Review the user's recent English prompts, find recurring grammar patterns, update ~/.claude/enpr/profile.md, and run a short retry drill built from the user's own sentences.
disable-model-invocation: true
argument-hint: "[quick]"
allowed-tools: Read, Edit, Write, Bash
---

# English review

The user is a Persian-speaking developer (reading C1, speaking A2, weak grammar) who wants
to turn passive English into active production. This is the ONLY place where teaching happens.
Talk to the user in Persian; examples stay English.

## Data

Current profile:
!`cat ~/.claude/enpr/profile.md 2>/dev/null || echo "(no profile yet)"`

Unreviewed prompts (newest last, max 300):
!`tail -n 300 ~/.claude/enpr/prompts.jsonl 2>/dev/null || echo "(no prompts logged)"`

## Steps

1. **Find patterns, not mistakes.** Group real errors (same rules as the ✎ line: structure, verb
   form/tense, agreement, missing `to`, dropped subject, question order, calques, and articles only
   when they recur) by underlying rule. Ignore typos, punctuation, terse imperative style, voice.
   A pattern needs ≥ 3 occurrences, or ≥ 2 if it is a structure error. For each, also count how
   often the user produced the same structure correctly.
2. **Update the profile** (`~/.claude/enpr/profile.md`) with Edit, keeping its sections:
   - `## Active` (max 5): one line each, `rule — wrong → right`, ≤ 100 chars. These get injected
     into every prompt, so be terse. Most frequent / most damaging first.
   - `## Watching`: candidates with 1–2 hits, or patterns demoted from Active.
   - `## Mastered`: a pattern moves here when it was Active and the recent prompts show it used
     correctly at least 3 times with no new errors. Mention the promotion to the user — this is
     the only "progress" signal, so make it count.
   - Do not store: full prompts, project names, code, vocabulary lists, typos, CEFR self-ratings.
3. **Report** in ≤ 12 lines of Persian: top patterns (max 3), each with ONE of the user's own
   sentences → fixed, plus a one-line rule. Then any promotions to Mastered.
4. **Retry drill** (skip if `$ARGUMENTS` is `quick`): pick 3 of the user's real wrong sentences.
   Show each one at a time as the *meaning* (short Persian paraphrase) plus a dev-context cue, and
   ask the user to produce the English sentence themselves (suggest saying it out loud first or
   using voice dictation). Do not show the original or the answer first. After each answer, give
   at most one ✎-style correction; if wrong, ask them to say it once more. Stop after 3 items or
   if the user says stop.
5. **Archive** the processed log so the next review only sees new prompts:
   `cd ~/.claude/enpr && cat prompts.jsonl >> archive.jsonl && : > prompts.jsonl`
   Then trim the archive: `tail -n 3000 archive.jsonl > a.tmp && mv a.tmp archive.jsonl`.

If there are fewer than 15 logged prompts, say so in one line, show the current Active patterns,
and do only the retry drill if there is something to drill.
