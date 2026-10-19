#!/usr/bin/env python3
"""Validate TCK YAML files against live Presidio recognizers."""

import importlib
import sys
from pathlib import Path

import yaml

DATA_DIR = Path(__file__).resolve().parent / "data"
sys.path.insert(
    0,
    str(Path(__file__).resolve().parent.parent / "presidio-analyzer"),
)

EPSILON = 0.00001


def run_test_case(recognizer, entity_type, tc):
    """Run one test case. Return error string or None."""
    text = tc["input"]
    results = sorted(
        recognizer.analyze(text, [entity_type]),
        key=lambda r: r.start,
    )

    if "expected_count" in tc:
        n = tc["expected_count"]
        if len(results) != n:
            return f"count: got {len(results)}, expected {n} | {text!r}"
        return None

    expected = tc["expected"]
    if len(results) != len(expected):
        return f"count: got {len(results)}, expected {len(expected)} | {text!r}"

    for i, (res, exp) in enumerate(zip(results, expected)):
        if res.start != exp["start"] or res.end != exp["end"]:
            return (
                f"span[{i}]: got ({res.start},{res.end}),"
                f" expected ({exp['start']},{exp['end']})"
                f" | {text!r}"
            )
        if "score" in exp:
            if abs(res.score - exp["score"]) > EPSILON:
                return (
                    f"span[{i}] score: got {res.score},"
                    f" expected {exp['score']} | {text!r}"
                )
        if "score_min" in exp:
            if res.score < exp["score_min"] - EPSILON:
                return (
                    f"span[{i}] score {res.score} < min {exp['score_min']} | {text!r}"
                )
        if "score_max" in exp:
            if res.score > exp["score_max"] + EPSILON:
                return (
                    f"span[{i}] score {res.score} > max {exp['score_max']} | {text!r}"
                )
    return None


def validate_file(yaml_path):
    """Validate a single TCK YAML file. Return (passed, failed)."""
    data = yaml.safe_load(yaml_path.read_text())
    mod = importlib.import_module("presidio_analyzer.predefined_recognizers")
    recognizer = getattr(mod, data["recognizer"])()
    entity_type = data["entity_type"]

    passed = failed = 0
    for i, tc in enumerate(data["test_cases"]):
        err = run_test_case(recognizer, entity_type, tc)
        if err:
            failed += 1
            print(f"    FAIL [{i}]: {err}")
        else:
            passed += 1
    return passed, failed


def main():
    """Validate all TCK YAML files against Presidio."""
    yaml_files = sorted(DATA_DIR.glob("*.yaml"))
    if not yaml_files:
        print(f"No YAML files in {DATA_DIR}")
        sys.exit(1)

    total_passed = total_failed = 0
    failures = []

    for yf in yaml_files:
        print(f"Validating {yf.name}...")
        p, f = validate_file(yf)
        total_passed += p
        total_failed += f
        if f:
            failures.append(yf.name)
        else:
            print(f"  OK ({p} passed)")

    n = len(yaml_files)
    print(f"\nTotal: {total_passed} passed, {total_failed} failed ({n} files)")
    if failures:
        print("Failures: " + ", ".join(failures))
        sys.exit(1)
    print("All tests passed!")


if __name__ == "__main__":
    main()
