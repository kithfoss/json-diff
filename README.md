# json-diff

Compare two JSON files and show what actually changed.

```
json-diff old.json new.json
```

## Usage

```
json-diff FILE_A FILE_B [--json]
```

## Examples

```bash
$ json-diff config-v1.json config-v2.json
3 differences between config-v1.json and config-v2.json:

  - retries: 3
  + timeout: 30
  ~ version: "1.2" → "1.3"

1 removed, 1 added, 1 changed

$ json-diff a.json b.json
No differences found.

$ json-diff old.json new.json --json
{
  "file_a": "old.json",
  "file_b": "new.json",
  "differences": true,
  "added": [{"path": "timeout", "value": 30}],
  "removed": [{"path": "retries", "value": 3}],
  "changed": [{"path": "version", "old": "1.2", "new": "1.3"}]
}
```

## Flags

| Flag | Description |
|------|-------------|
| `--json` | Output machine-readable JSON |

## Exit codes

| Code | Meaning |
|------|---------|
| `0` | No differences |
| `1` | Differences found |
| `2` | File not found or invalid JSON |

## What it handles

- Nested objects — paths shown as `parent.child.key`
- Arrays — compared by position, paths shown as `list[0]`
- Mixed — `list[2].key`
- All JSON types: strings, numbers, booleans, null
- Key ordering is ignored (two dicts with the same keys and values are equal)

## Limitations

- Arrays are compared positionally — it does not detect that an element was moved to a different index
- Keys containing `.` in their names will look ambiguous in dot-path output
- No recursive diff display for added/removed sub-objects (shows the object compactly at the key that was added/removed)

## Stack

Python 3, stdlib only (`json`, `argparse`). No external dependencies.

## Earn model

Free.
