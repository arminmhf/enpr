import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "plugins" / "english" / "scripts" / "enpr.py"


class EnprTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.env = {**os.environ, "ENPR_HOME": str(self.home), "ENPR_TODAY": "2026-10-02"}

    def tearDown(self):
        self.tmp.cleanup()

    def run_cmd(self, cmd, stdin="", cwd=None, today=None):
        env = dict(self.env)
        if today:
            env["ENPR_TODAY"] = today
        r = subprocess.run([sys.executable, str(SCRIPT), cmd], input=stdin, capture_output=True,
                           text=True, env=env, cwd=cwd)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout

    def prompt(self, text, cwd="/x/proj", **kw):
        return self.run_cmd("prompt", json.dumps({"prompt": text, "cwd": cwd}), **kw)

    def logged(self):
        p = self.home / "prompts.jsonl"
        return [json.loads(l) for l in p.read_text().splitlines()] if p.exists() else []

    def write_profile(self, active=(), mastered=()):
        self.run_cmd("session-start", "{}")
        text = "# English profile\n\n## Active\n" + "".join(f"- {a}\n" for a in active)
        text += "\n## Watching\n\n## Mastered\n" + "".join(f"- {m}\n" for m in mastered)
        (self.home / "profile.md").write_text(text)

    def test_session_start_injects_rules_and_respects_off(self):
        out = json.loads(self.run_cmd("session-start", "{}"))
        self.assertIn("✎", out["hookSpecificOutput"]["additionalContext"])
        (self.home / "mode").write_text("off")
        self.assertEqual(self.run_cmd("session-start", "{}"), "")

    def test_logging_filters_code_secrets_persian_and_commands(self):
        self.prompt("I want you check why it fail\n```\nx = 1\n```\n    at a.b (c.js:1)\ntoken=abcdef123")
        self.prompt("این رو درست کن لطفا")
        self.prompt("/english:review")
        self.prompt("fix it")
        rows = self.logged()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["project"], "proj")
        self.assertNotIn("x = 1", rows[0]["text"])
        self.assertNotIn("abcdef123", rows[0]["text"])
        self.assertIn("want you check", rows[0]["text"])

    def test_off_mode_logs_nothing(self):
        (self.home / "mode").write_text("off")
        self.assertIn("OFF", self.prompt("I want you check this please"))
        self.assertEqual(self.logged(), [])

    def test_active_patterns_are_injected(self):
        self.write_profile(active=["want + you + to — want you check → want you to check"])
        self.assertIn("Active patterns: want + you + to", self.prompt("please check the build now"))

    def test_due_and_tags(self):
        self.write_profile(mastered=["there is/are — there is bugs → there are bugs [next: 2026-10-01 · step 1]",
                                     "dropped subject — is broken → it is broken [next: 2026-12-01 · step 2]"])
        out = self.run_cmd("due")
        self.assertIn("tag for a newly mastered pattern: [next: 2026-10-09 · step 1]", out)
        self.assertIn("there is/are", out)
        self.assertNotIn("dropped subject", out)
        self.assertIn("pass → [next: 2026-10-23 · step 2]", out)

    def test_nudge_once_a_day(self):
        self.write_profile(mastered=["x — a → b [next: 2026-09-01 · step 1]"])
        self.assertIn("/english:review", self.prompt("check the tests please now"))
        self.assertNotIn("/english:review", self.prompt("check the tests again please"))
        self.assertIn("/english:review", self.prompt("check the tests again please", today="2026-10-03"))

    def test_nudge_after_enough_prompts(self):
        self.write_profile()
        for i in range(39):
            self.assertNotIn("/english:review", self.prompt(f"please check item number {i}"))
        self.assertIn("40 prompts collected", self.prompt("please check the last item"))

    def test_record_and_trend(self):
        self.assertIn("no review history", self.run_cmd("trend"))
        self.run_cmd("record", json.dumps({"prompts": 50, "patterns": {"want-to": {"errors": 10, "correct": 5}}}))
        self.run_cmd("record", json.dumps({"prompts": 40, "patterns": {"want-to": {"errors": 2, "correct": 12},
                                                                       "articles": {"errors": 8}}}), today="2026-10-09")
        out = self.run_cmd("trend")
        self.assertIn("- want-to: 20 → 5", out)
        self.assertIn("- articles: · → 20", out)

    def test_context_outside_git(self):
        self.prompt("explain why the cache is stale", cwd=self.tmp.name)
        out = self.run_cmd("context", cwd=self.tmp.name)
        self.assertIn("not a git repository", out)
        self.assertIn("explain why the cache is stale", out)

    def test_garbage_stdin_never_fails(self):
        self.run_cmd("prompt", "not json")
        self.run_cmd("unknown-command")


if __name__ == "__main__":
    unittest.main()
