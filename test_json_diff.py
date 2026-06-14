#!/usr/bin/env python3
"""Tests for json-diff."""

import json
import os
import subprocess
import sys
import tempfile
import unittest

# Allow importing the module directly
sys.path.insert(0, os.path.dirname(__file__))
from json_diff import diff, format_value, make_path, display_path


# ---------------------------------------------------------------------------
# Unit tests: diff() logic
# ---------------------------------------------------------------------------

class TestDiffIdentical(unittest.TestCase):
    def test_empty_dicts(self):
        a, r, c = diff({}, {})
        self.assertEqual((a, r, c), ([], [], []))

    def test_identical_flat(self):
        obj = {"x": 1, "y": "hello"}
        a, r, c = diff(obj, obj)
        self.assertEqual((a, r, c), ([], [], []))

    def test_identical_nested(self):
        obj = {"a": {"b": {"c": 42}}}
        a, r, c = diff(obj, obj)
        self.assertEqual((a, r, c), ([], [], []))

    def test_identical_null(self):
        a, r, c = diff(None, None)
        self.assertEqual((a, r, c), ([], [], []))

    def test_identical_booleans(self):
        a, r, c = diff({"x": True, "y": False}, {"x": True, "y": False})
        self.assertEqual((a, r, c), ([], [], []))

    def test_identical_empty_list(self):
        a, r, c = diff([], [])
        self.assertEqual((a, r, c), ([], [], []))

    def test_identical_list(self):
        a, r, c = diff([1, 2, 3], [1, 2, 3])
        self.assertEqual((a, r, c), ([], [], []))


class TestDiffAdded(unittest.TestCase):
    def test_key_added(self):
        a, r, c = diff({"x": 1}, {"x": 1, "y": 2})
        self.assertEqual(len(a), 1)
        self.assertEqual(a[0]["path"], "y")
        self.assertEqual(a[0]["value"], 2)
        self.assertEqual((r, c), ([], []))

    def test_nested_key_added(self):
        a, r, c = diff({"cfg": {"timeout": 30}}, {"cfg": {"timeout": 30, "retries": 3}})
        self.assertEqual(len(a), 1)
        self.assertEqual(a[0]["path"], "cfg.retries")
        self.assertEqual(a[0]["value"], 3)

    def test_array_element_added(self):
        a, r, c = diff([1, 2], [1, 2, 3])
        self.assertEqual(len(a), 1)
        self.assertEqual(a[0]["path"], "[2]")
        self.assertEqual(a[0]["value"], 3)

    def test_multiple_keys_added(self):
        a, r, c = diff({}, {"a": 1, "b": 2, "c": 3})
        self.assertEqual(len(a), 3)
        paths = {item["path"] for item in a}
        self.assertEqual(paths, {"a", "b", "c"})


class TestDiffRemoved(unittest.TestCase):
    def test_key_removed(self):
        a, r, c = diff({"x": 1, "y": 2}, {"x": 1})
        self.assertEqual(len(r), 1)
        self.assertEqual(r[0]["path"], "y")
        self.assertEqual(r[0]["value"], 2)
        self.assertEqual((a, c), ([], []))

    def test_nested_key_removed(self):
        a, r, c = diff({"cfg": {"timeout": 30, "retries": 3}}, {"cfg": {"timeout": 30}})
        self.assertEqual(len(r), 1)
        self.assertEqual(r[0]["path"], "cfg.retries")

    def test_array_element_removed(self):
        a, r, c = diff([1, 2, 3], [1, 2])
        self.assertEqual(len(r), 1)
        self.assertEqual(r[0]["path"], "[2]")
        self.assertEqual(r[0]["value"], 3)

    def test_entire_key_removed(self):
        a, r, c = diff({"keep": 1, "gone": {"a": 1, "b": 2}}, {"keep": 1})
        self.assertEqual(len(r), 1)
        self.assertEqual(r[0]["path"], "gone")
        self.assertIsInstance(r[0]["value"], dict)


class TestDiffChanged(unittest.TestCase):
    def test_scalar_changed(self):
        a, r, c = diff({"v": "1.2"}, {"v": "1.3"})
        self.assertEqual(len(c), 1)
        self.assertEqual(c[0]["path"], "v")
        self.assertEqual(c[0]["old"], "1.2")
        self.assertEqual(c[0]["new"], "1.3")

    def test_number_changed(self):
        a, r, c = diff({"n": 10}, {"n": 20})
        self.assertEqual(c[0]["old"], 10)
        self.assertEqual(c[0]["new"], 20)

    def test_bool_changed(self):
        a, r, c = diff({"flag": True}, {"flag": False})
        self.assertEqual(c[0]["old"], True)
        self.assertEqual(c[0]["new"], False)

    def test_null_to_string(self):
        a, r, c = diff({"x": None}, {"x": "hello"})
        self.assertEqual(c[0]["old"], None)
        self.assertEqual(c[0]["new"], "hello")

    def test_nested_scalar_changed(self):
        a, r, c = diff({"db": {"host": "localhost"}}, {"db": {"host": "prod.db"}})
        self.assertEqual(c[0]["path"], "db.host")

    def test_type_change_dict_to_list(self):
        a, r, c = diff({"x": {}}, {"x": []})
        self.assertEqual(len(c), 1)
        self.assertEqual(c[0]["path"], "x")

    def test_array_element_changed(self):
        a, r, c = diff([1, 2, 3], [1, 99, 3])
        self.assertEqual(len(c), 1)
        self.assertEqual(c[0]["path"], "[1]")
        self.assertEqual(c[0]["old"], 2)
        self.assertEqual(c[0]["new"], 99)


class TestDiffNested(unittest.TestCase):
    def test_deeply_nested(self):
        old = {"a": {"b": {"c": {"d": 1}}}}
        new = {"a": {"b": {"c": {"d": 2}}}}
        a, r, c = diff(old, new)
        self.assertEqual(c[0]["path"], "a.b.c.d")

    def test_mixed_add_remove_change(self):
        old = {"keep": 1, "remove": 2, "change": "old"}
        new = {"keep": 1, "add": 3, "change": "new"}
        a, r, c = diff(old, new)
        self.assertEqual(len(a), 1)
        self.assertEqual(len(r), 1)
        self.assertEqual(len(c), 1)

    def test_key_ordering_irrelevant(self):
        # Same content, different key order in source
        old = json.loads('{"b": 2, "a": 1}')
        new = json.loads('{"a": 1, "b": 2}')
        a, r, c = diff(old, new)
        self.assertEqual((a, r, c), ([], [], []))

    def test_nested_array_in_dict(self):
        old = {"items": [1, 2, 3]}
        new = {"items": [1, 2, 3, 4]}
        a, r, c = diff(old, new)
        self.assertEqual(len(a), 1)
        self.assertEqual(a[0]["path"], "items[3]")

    def test_dict_in_array(self):
        old = [{"id": 1, "name": "Alice"}]
        new = [{"id": 1, "name": "Bob"}]
        a, r, c = diff(old, new)
        self.assertEqual(c[0]["path"], "[0].name")


# ---------------------------------------------------------------------------
# Unit tests: format_value()
# ---------------------------------------------------------------------------

class TestFormatValue(unittest.TestCase):
    def test_string(self):
        self.assertEqual(format_value("hello"), '"hello"')

    def test_number(self):
        self.assertEqual(format_value(42), "42")

    def test_float(self):
        self.assertEqual(format_value(3.14), "3.14")

    def test_null(self):
        self.assertEqual(format_value(None), "null")

    def test_true(self):
        self.assertEqual(format_value(True), "true")

    def test_false(self):
        self.assertEqual(format_value(False), "false")

    def test_dict(self):
        result = format_value({"a": 1})
        self.assertIn('"a"', result)
        self.assertIn("1", result)

    def test_list(self):
        result = format_value([1, 2])
        self.assertEqual(result, "[1,2]")


# ---------------------------------------------------------------------------
# Unit tests: make_path() and display_path()
# ---------------------------------------------------------------------------

class TestPaths(unittest.TestCase):
    def test_top_level_key(self):
        self.assertEqual(make_path("", "foo"), "foo")

    def test_nested_key(self):
        self.assertEqual(make_path("parent", "child"), "parent.child")

    def test_array_index(self):
        self.assertEqual(make_path("items", 0), "items[0]")

    def test_root_array_index(self):
        self.assertEqual(make_path("", 0), "[0]")

    def test_display_path_empty(self):
        self.assertEqual(display_path(""), "(root)")

    def test_display_path_nonempty(self):
        self.assertEqual(display_path("foo.bar"), "foo.bar")


# ---------------------------------------------------------------------------
# Integration tests: CLI via subprocess
# ---------------------------------------------------------------------------

class TestCLI(unittest.TestCase):
    SCRIPT = os.path.join(os.path.dirname(__file__), "json_diff.py")

    def run_cli(self, a_data, b_data, extra_args=None):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as fa:
            json.dump(a_data, fa)
            fa_path = fa.name
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as fb:
            json.dump(b_data, fb)
            fb_path = fb.name
        try:
            cmd = [sys.executable, self.SCRIPT, fa_path, fb_path] + (extra_args or [])
            result = subprocess.run(cmd, capture_output=True, text=True)
            return result
        finally:
            os.unlink(fa_path)
            os.unlink(fb_path)

    def test_identical_exits_zero(self):
        r = self.run_cli({"a": 1}, {"a": 1})
        self.assertEqual(r.returncode, 0)
        self.assertIn("No differences", r.stdout)

    def test_diff_exits_one(self):
        r = self.run_cli({"a": 1}, {"a": 2})
        self.assertEqual(r.returncode, 1)

    def test_human_output_changed(self):
        r = self.run_cli({"version": "1.2"}, {"version": "1.3"})
        self.assertIn("~", r.stdout)
        self.assertIn("version", r.stdout)
        self.assertIn("1.2", r.stdout)
        self.assertIn("1.3", r.stdout)

    def test_human_output_added(self):
        r = self.run_cli({}, {"new_key": 42})
        self.assertIn("+", r.stdout)
        self.assertIn("new_key", r.stdout)

    def test_human_output_removed(self):
        r = self.run_cli({"old_key": "gone"}, {})
        self.assertIn("-", r.stdout)
        self.assertIn("old_key", r.stdout)

    def test_json_output_structure(self):
        r = self.run_cli({"a": 1}, {"a": 2}, ["--json"])
        data = json.loads(r.stdout)
        self.assertIn("differences", data)
        self.assertIn("added", data)
        self.assertIn("removed", data)
        self.assertIn("changed", data)
        self.assertTrue(data["differences"])

    def test_json_output_no_diff(self):
        r = self.run_cli({"a": 1}, {"a": 1}, ["--json"])
        data = json.loads(r.stdout)
        self.assertFalse(data["differences"])
        self.assertEqual(data["added"], [])
        self.assertEqual(data["removed"], [])
        self.assertEqual(data["changed"], [])

    def test_file_not_found(self):
        cmd = [sys.executable, self.SCRIPT, "no_such_file.json", "no_such_file2.json"]
        r = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(r.returncode, 2)
        self.assertIn("file not found", r.stderr)

    def test_invalid_json(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            f.write("this is not json {{{")
            bad_path = f.name
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump({}, f)
            good_path = f.name
        try:
            cmd = [sys.executable, self.SCRIPT, bad_path, good_path]
            r = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(r.returncode, 2)
            self.assertIn("invalid JSON", r.stderr)
        finally:
            os.unlink(bad_path)
            os.unlink(good_path)

    def test_summary_line(self):
        r = self.run_cli({"a": 1, "b": 2}, {"a": 99, "c": 3})
        # should mention removed, added, changed counts
        self.assertIn("removed", r.stdout)
        self.assertIn("added", r.stdout)
        self.assertIn("changed", r.stdout)

    def test_key_order_irrelevant(self):
        # json.dump will produce keys in insertion order; we test that result is clean
        a = json.loads('{"z": 1, "a": 2}')
        b = json.loads('{"a": 2, "z": 1}')
        r = self.run_cli(a, b)
        self.assertEqual(r.returncode, 0)
        self.assertIn("No differences", r.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
