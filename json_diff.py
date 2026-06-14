#!/usr/bin/env python3
"""json-diff: compare two JSON files and show what actually changed."""

import argparse
import json
import sys


def make_path(parent, key):
    if not parent:
        return f"[{key}]" if isinstance(key, int) else str(key)
    if isinstance(key, int):
        return f"{parent}[{key}]"
    return f"{parent}.{key}"


def display_path(path):
    return path if path else "(root)"


def diff(old, new, path=""):
    """Return (added, removed, changed) lists for the given pair of values."""
    added = []
    removed = []
    changed = []

    if isinstance(old, dict) and isinstance(new, dict):
        old_keys = set(old.keys())
        new_keys = set(new.keys())

        for key in sorted(old_keys - new_keys):
            removed.append({"path": make_path(path, key), "value": old[key]})

        for key in sorted(new_keys - old_keys):
            added.append({"path": make_path(path, key), "value": new[key]})

        for key in sorted(old_keys & new_keys):
            a, r, c = diff(old[key], new[key], make_path(path, key))
            added.extend(a)
            removed.extend(r)
            changed.extend(c)

    elif isinstance(old, list) and isinstance(new, list):
        length = max(len(old), len(new))
        for i in range(length):
            if i >= len(old):
                added.append({"path": make_path(path, i), "value": new[i]})
            elif i >= len(new):
                removed.append({"path": make_path(path, i), "value": old[i]})
            else:
                a, r, c = diff(old[i], new[i], make_path(path, i))
                added.extend(a)
                removed.extend(r)
                changed.extend(c)

    else:
        if old != new:
            changed.append({"path": path, "old": old, "new": new})

    return added, removed, changed


def format_value(v):
    """Compact, human-readable representation of a JSON value."""
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, str):
        return json.dumps(v)
    if isinstance(v, (int, float)):
        return str(v)
    return json.dumps(v, separators=(",", ":"))


def print_human(added, removed, changed, file_a, file_b):
    total = len(added) + len(removed) + len(changed)
    if total == 0:
        print("No differences found.")
        return

    noun = "difference" if total == 1 else "differences"
    print(f"{total} {noun} between {file_a} and {file_b}:")
    print()

    for item in removed:
        print(f"  - {display_path(item['path'])}: {format_value(item['value'])}")
    for item in added:
        print(f"  + {display_path(item['path'])}: {format_value(item['value'])}")
    for item in changed:
        print(
            f"  ~ {display_path(item['path'])}: "
            f"{format_value(item['old'])} → {format_value(item['new'])}"
        )

    print()
    parts = []
    if removed:
        parts.append(f"{len(removed)} removed")
    if added:
        parts.append(f"{len(added)} added")
    if changed:
        parts.append(f"{len(changed)} changed")
    print(", ".join(parts))


def load_json(path, label):
    try:
        with open(path) as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"json-diff: {label}: file not found", file=sys.stderr)
        sys.exit(2)
    except json.JSONDecodeError as e:
        print(f"json-diff: {label}: invalid JSON: {e}", file=sys.stderr)
        sys.exit(2)
    except OSError as e:
        print(f"json-diff: {label}: {e}", file=sys.stderr)
        sys.exit(2)


def main():
    parser = argparse.ArgumentParser(
        prog="json-diff",
        description="Compare two JSON files and show what changed.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Exit codes:\n"
            "  0  files are identical\n"
            "  1  differences found\n"
            "  2  usage or file error"
        ),
    )
    parser.add_argument("file_a", help="original JSON file")
    parser.add_argument("file_b", help="new JSON file")
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="output machine-readable JSON",
    )
    args = parser.parse_args()

    old = load_json(args.file_a, args.file_a)
    new = load_json(args.file_b, args.file_b)

    added, removed, changed = diff(old, new)
    has_diff = bool(added or removed or changed)

    if args.json_output:
        result = {
            "file_a": args.file_a,
            "file_b": args.file_b,
            "differences": has_diff,
            "added": added,
            "removed": removed,
            "changed": changed,
        }
        print(json.dumps(result, indent=2))
    else:
        print_human(added, removed, changed, args.file_a, args.file_b)

    sys.exit(1 if has_diff else 0)


if __name__ == "__main__":
    main()
