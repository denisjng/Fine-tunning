#!/usr/bin/env python3
"""Check a competition submission CSV against the organizer's sample submission.

Usage:
  python check_submission.py SAMPLE SUBMISSION   -> "OK" (exit 0) or "INVALID:" + reasons (exit 1)
  python check_submission.py --self-test
"""
# shortcut: CSV only and the ID is the first column; extend if a competition uses JSON/JSONL/parquet or a different ID column.
import csv
import math
import os
import sys
import tempfile


def _read(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        rows = [r for r in csv.reader(f) if r]
    return (rows[0], rows[1:]) if rows else ([], [])


def _is_number(value):
    try:
        return math.isfinite(float(value))
    except ValueError:
        return False


def check(sample_path, sub_path):
    s_head, s_rows = _read(sample_path)
    head, rows = _read(sub_path)
    if not head:
        return ["submission is empty"]
    if head != s_head:
        return [f"columns {head} differ from sample columns {s_head} (names and order must match)"]
    problems = []
    if len(rows) != len(s_rows):
        problems.append(f"{len(rows)} rows, sample has {len(s_rows)}")
    ids = [r[0] for r in rows if r]
    if len(set(ids)) != len(ids):
        problems.append(f"{len(ids) - len(set(ids))} duplicate ids")
    s_ids = {r[0] for r in s_rows if r}
    missing, extra = s_ids - set(ids), set(ids) - s_ids
    if missing or extra:
        problems.append(f"id set differs from sample: {len(missing)} missing, {len(extra)} unknown (e.g. {sorted(missing or extra)[0]!r})")
    bad_len = [i for i, r in enumerate(rows, 2) if len(r) != len(head)]
    if bad_len:
        problems.append(f"{len(bad_len)} rows with wrong field count, first at line {bad_len[0]}")
    s_empty = {j for r in s_rows for j, v in enumerate(r) if not v.strip()}
    empty = [i for i, r in enumerate(rows, 2) if any(not v.strip() for j, v in enumerate(r) if j not in s_empty)]
    if empty:
        problems.append(f"{len(empty)} rows with empty values, first at line {empty[0]}")
    for j in range(1, len(head)):
        if s_rows and all(len(r) > j and _is_number(r[j]) for r in s_rows):
            bad = [r[j] for r in rows if len(r) > j and r[j].strip() and not _is_number(r[j])]
            if bad:
                problems.append(f"column {head[j]!r} must be a finite number, got e.g. {bad[0]!r}")
    return problems


def _write(folder, name, text):
    path = os.path.join(folder, name)
    with open(path, "w", newline="", encoding="utf-8") as f:
        f.write(text)
    return path


def self_test():
    num = "id,target\n1,0.5\n2,0.5\n3,0.5\n"
    lab = "id,label\n1,cat\n2,cat\n3,cat\n"
    cases = [
        ("good, rows reordered", num, "id,target\n3,0.1\n1,0.9\n2,0.4\n", True),
        ("good, BOM + CRLF", num, "﻿id,target\r\n1,0.1\r\n2,0.9\r\n3,0.4\r\n", True),
        ("good, text labels", lab, "id,label\n1,dog\n2,cat\n3,dog\n", True),
        ("wrong column name", num, "id,label\n1,0.1\n2,0.9\n3,0.4\n", False),
        ("columns swapped", num, "target,id\n0.1,1\n0.9,2\n0.4,3\n", False),
        ("missing row", num, "id,target\n1,0.1\n2,0.9\n", False),
        ("extra row", num, "id,target\n1,0.1\n2,0.9\n3,0.4\n4,0.2\n", False),
        ("unknown id", num, "id,target\n1,0.1\n2,0.9\n4,0.4\n", False),
        ("duplicate id", num, "id,target\n1,0.1\n1,0.9\n2,0.4\n", False),
        ("empty value", num, "id,target\n1,0.1\n2,\n3,0.4\n", False),
        ("nan value", num, "id,target\n1,0.1\n2,nan\n3,0.4\n", False),
        ("text in numeric column", num, "id,target\n1,0.1\n2,high\n3,0.4\n", False),
        ("short row", num, "id,target\n1,0.1\n2\n3,0.4\n", False),
        ("empty file", num, "", False),
        ("good, blank line ignored", num, "id,target\n1,0.1\n\n2,0.9\n3,0.4\n", True),
        ("good, empty where sample has empties", "id,mask\n1,\n2,1 3\n", "id,mask\n1,1 2\n2,\n", True),
    ]
    with tempfile.TemporaryDirectory() as d:
        for i, (name, sample, sub, ok) in enumerate(cases):
            problems = check(_write(d, f"s{i}.csv", sample), _write(d, f"p{i}.csv", sub))
            assert (problems == []) == ok, f"{name}: expected {'valid' if ok else 'invalid'}, got {problems}"
    print(f"self-test passed ({len(cases)} cases)")


if __name__ == "__main__":
    if sys.argv[1:] == ["--self-test"]:
        self_test()
        sys.exit(0)
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    problems = check(sys.argv[1], sys.argv[2])
    if problems:
        print("INVALID:\n" + "\n".join(f"- {p}" for p in problems))
        sys.exit(1)
    print("OK")
