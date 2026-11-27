"""Unit and smoke tests for Copy Title URL (Alfred 6 workflow)."""

import json
import os
import plistlib
import subprocess
import sys
import tempfile
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORKFLOW_DIR = os.path.join(REPO_ROOT, ".workflow")
SCRIPTS_DIR = os.path.join(WORKFLOW_DIR, "picker.alfredui", "scripts")

sys.path.insert(0, SCRIPTS_DIR)

import patterns  # noqa: E402
import webloc  # noqa: E402


class TestPatterns(unittest.TestCase):
    def test_parse_patterns_skips_blank_and_comments(self):
        raw = "\n# header\n  title  \n\n[title](url)\n# trailing\n"
        self.assertEqual(patterns.parse_patterns(raw), ["title", "[title](url)"])

    def test_parse_patterns_default_when_empty(self):
        parsed = patterns.parse_patterns("   \n")
        self.assertIn("[title](url)", parsed)
        self.assertIn("[title](surl)", parsed)

    def test_format_pattern_single_pass_no_double_replace(self):
        out = patterns.format_pattern(
            "[title](url)",
            title='Alfred 6 "UI" & url Guide',
            url="https://example.com/a",
        )
        self.assertEqual(out, '[Alfred 6 "UI" & url Guide](https://example.com/a)')

    def test_format_pattern_with_surl(self):
        out = patterns.format_pattern(
            "title - surl",
            title="Docs",
            url="https://example.com/long",
            surl="https://is.gd/abc",
        )
        self.assertEqual(out, "Docs - https://is.gd/abc")

    def test_build_rows_states(self):
        plist = ["[title](url)", "[title](surl)"]
        pending = patterns.build_rows(plist, "Hello", "https://ex.com", "is.gd", surl=None)
        self.assertEqual(pending[0]["preview"], "[Hello](https://ex.com)")
        self.assertIn("shortening via is.gd", pending[1]["preview"])

        done = patterns.build_rows(plist, "Hello", "https://ex.com", "is.gd", surl="https://is.gd/x")
        self.assertEqual(done[1]["preview"], "[Hello](https://is.gd/x)")
        self.assertIn("Shortened (is.gd)", done[1]["badge"])

        failed = patterns.build_rows(plist, "Hello", "https://ex.com", "is.gd", shorten_error="timeout")
        self.assertIn("timeout", failed[1]["preview"])
        self.assertEqual(failed[1]["badge"], "is.gd failed")


class TestWebloc(unittest.TestCase):
    def test_sanitize_filename_removes_invalid_chars(self):
        name = webloc.sanitize_filename("cage1016/alfred: Copy\\URL", "https://example.com")
        self.assertNotIn("/", name)
        self.assertNotIn(":", name)
        self.assertNotIn("\\", name)

    def test_sanitize_filename_fallback_to_url(self):
        name = webloc.sanitize_filename("", "https://github.com/cage1016/fmctl")
        self.assertTrue(name.startswith("github.com"))

    def test_save_webloc_creates_valid_plist_and_deduplicates(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            p1 = webloc.save_webloc("My/Page: Title", "https://example.com/test", tmpdir)
            p2 = webloc.save_webloc("My/Page: Title", "https://example.com/test", tmpdir)
            self.assertTrue(p1.endswith(".webloc"))
            self.assertTrue(p2.endswith(" (2).webloc"))
            with open(p1, "rb") as f:
                data = plistlib.load(f)
            self.assertEqual(data, {"URL": "https://example.com/test"})


class TestWorkflowBundle(unittest.TestCase):
    def test_info_plist_valid_xml(self):
        plist_path = os.path.join(WORKFLOW_DIR, "info.plist")
        with open(plist_path, "rb") as f:
            raw = f.read()
        self.assertTrue(raw.lstrip().startswith(b"<?xml"))
        info = plistlib.loads(raw)
        self.assertEqual(info["bundleid"], "com.kaichu.copytitleurl")

    def test_ui_json_valid_and_scripts_executable(self):
        ui_path = os.path.join(WORKFLOW_DIR, "picker.alfredui", "ui.json")
        with open(ui_path, "r", encoding="utf-8") as f:
            ui = json.load(f)
        self.assertIn("window", ui)
        for name in ("load", "shorten", "copy_selection", "save_webloc", "save_webloc_cli"):
            script_path = os.path.join(SCRIPTS_DIR, name)
            self.assertTrue(os.path.isfile(script_path), f"missing {name}")
            self.assertTrue(os.access(script_path, os.X_OK), f"not executable: {name}")

    def test_copy_selection_cli_output(self):
        env = dict(
            os.environ,
            title='Page "Title" & url',
            url="https://example.com",
            surl="https://is.gd/abc",
        )
        proc = subprocess.run(
            [os.path.join(SCRIPTS_DIR, "copy_selection"), "[title](url)"],
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        action = json.loads(proc.stdout)
        self.assertEqual(action["copy"]["src"], '[Page "Title" & url](https://example.com)')
        self.assertIn("finish", action)


if __name__ == "__main__":
    unittest.main()
