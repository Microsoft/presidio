#!/usr/bin/env python3
"""Extract TCK YAML from Presidio @pytest.mark.parametrize test data.

Source of truth stays in the Python tests. Run this script to
regenerate the YAML TCK whenever the tests change.
"""

import ast
import importlib
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TESTS_DIR = REPO_ROOT / "presidio-analyzer" / "tests"
OUTPUT_DIR = Path(__file__).resolve().parent / "data"

sys.path.insert(0, str(TESTS_DIR.parent))
sys.path.insert(0, str(TESTS_DIR))

SKIP_FILES = {
    "test_spacy_recognizer.py",
    "test_stanza_recognizer.py",
    "test_transformers_recognizer.py",
    "test_gliner_recognizer.py",
    "test_huggingface_ner_recognizer.py",
    "test_medical_ner_recognizer.py",
    "test_azure_ai_language_recognizer.py",
    "test_azure_openai_langextract_recognizer.py",
    "test_basic_langextract_recognizer.py",
    "test_lm_recognizer.py",
    "test_ahds_recognizer.py",
    "test_entity_recognizer.py",
    "test_pattern_recognizer.py",
    "test_phone_recognizer.py",
    "test_ph_mobile_number_recognizer.py",
    "test_tr_phone_number_recognizer.py",
}

SKIP_ARGNAMES = {
    "nlp_artifacts",
    "deny_list",
    "leniency",
    "expected_textual_explanations",
}
STANDARD_RECOGNIZER_PARAMS = {"recognizer", "cc_recognizer"}
COMMENT_RE = re.compile(r"^\s*#\s?(.*)$")


def get_recognizer_metadata(class_name):
    """Return (language, country_code) for a recognizer class."""
    mod = importlib.import_module("presidio_analyzer.predefined_recognizers")
    cls = getattr(mod, class_name, None)
    if cls is None:
        return "en", None
    country = getattr(cls, "COUNTRY_CODE", None)
    if not isinstance(country, str):
        country = None
    return getattr(cls(), "supported_language", "en"), country


def _is_eligible_test(node, tree):
    """Check if a FunctionDef is an eligible test function."""
    if not node.name.startswith("test_"):
        return False
    params = {arg.arg for arg in node.args.args}
    rec_params = {p for p in params if "recognizer" in p.lower()}
    if rec_params and not (rec_params & STANDARD_RECOGNIZER_PARAMS):
        return False
    return True


def _is_eligible_block(argnames):
    """Check if a parametrize block should be extracted."""
    if set(argnames) & SKIP_ARGNAMES:
        return False
    has_text = "text" in argnames or "iban" in argnames
    if "expected" in argnames and not has_text:
        return False
    if len(argnames) == 2 and argnames[1] == "expected":
        return False
    return True


def find_parametrize_blocks(test_file, tree):
    """Import test module, return parametrize blocks.

    Returns
    -------
    list of (argnames, argvalues, func_name) tuples.
    """
    eligible = {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and _is_eligible_test(node, tree)
    }

    try:
        mod = importlib.import_module(test_file.stem)
    except Exception as e:
        print(f"  SKIP (import error: {e})")
        return []

    blocks = []
    for name in eligible:
        func = getattr(mod, name, None)
        if func is None or not hasattr(func, "pytestmark"):
            continue
        for mark in func.pytestmark:
            if mark.name != "parametrize":
                continue
            argnames = [s.strip() for s in mark.args[0].split(",")]
            if not _is_eligible_block(argnames):
                continue
            blocks.append((argnames, list(mark.args[1]), name))
    return blocks


def extract_comments_for_block(tree, func_name, source_lines, num_cases):
    """Extract comments preceding each test case tuple."""
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        if node.name != func_name:
            continue
        for dec in node.decorator_list:
            if not isinstance(dec, ast.Call):
                continue
            if len(dec.args) < 2:
                continue
            func = dec.func
            if not isinstance(func, ast.Attribute):
                continue
            if func.attr != "parametrize":
                continue
            arg_node = dec.args[1]
            if not isinstance(arg_node, ast.List):
                return [None] * num_cases
            ranges = [(e.lineno, e.end_lineno) for e in arg_node.elts]
            if len(ranges) != num_cases:
                return [None] * num_cases
            return _collect_comments(arg_node.lineno, ranges, source_lines)
    return [None] * num_cases


def _collect_comments(list_start, ranges, source_lines):
    """Scan source lines between tuples for comments."""
    result = []
    for i, (start, _end) in enumerate(ranges):
        prev = list_start if i == 0 else ranges[i - 1][1]
        comments = []
        for ln in range(prev, start + 1):
            m = COMMENT_RE.match(source_lines[ln - 1])
            if m:
                text = m.group(1).strip()
                if text and text not in ("fmt: off", "fmt: on"):
                    comments.append(text)
        result.append("\n".join(comments) if comments else None)
    return result


def _as_seq(val):
    """Normalize tuple-or-list to list of tuples."""
    if not isinstance(val, (tuple, list)) or not val:
        return []
    if isinstance(val[0], (tuple, list)):
        return [tuple(v) for v in val]
    return [tuple(val)]


def normalize_case(argnames, values):
    """Convert one parametrize row to TCK format."""
    if not isinstance(values, tuple):
        values = (values,)
    row = dict(zip(argnames, values))
    text = str(row.get("text") or row.get("iban", ""))

    positions = _extract_positions(row)
    expected_len = row.get("expected_len")
    if expected_len is None:
        expected_len = len(positions) if positions else 0

    if expected_len == 0:
        return {"input": text, "expected": []}
    if not positions or expected_len > len(positions):
        return {"input": text, "expected_count": expected_len}

    scores = _extract_scores(row, expected_len)
    expected = []
    for i in range(expected_len):
        entry = {
            "start": positions[i][0],
            "end": positions[i][1],
        }
        if i < len(scores) and scores[i]:
            entry.update(scores[i])
        expected.append(entry)
    return {"input": text, "expected": expected}


def _extract_positions(row):
    """Extract (start, end) positions from a test row."""
    for key in ("expected_positions", "expected_res"):
        if key in row:
            return _as_seq(row[key])
    if "expected_position" in row:
        pos = row["expected_position"]
        if isinstance(pos, (tuple, list)) and len(pos) == 2:
            return [tuple(pos)]
    if "expected_start" in row:
        return [(row["expected_start"], row["expected_end"])]
    return []


def _extract_scores(row, n):
    """Extract score constraints from a test row."""
    if "expected_score_ranges" in row:
        ranges = row["expected_score_ranges"]
        if not isinstance(ranges, (tuple, list)) or not ranges:
            return [None] * n
        result = []
        for r in ranges:
            if not isinstance(r, (tuple, list)) or len(r) != 2:
                result.append(None)
                continue
            lo = 1.0 if r[0] == "max" else float(r[0])
            hi = 1.0 if r[1] == "max" else float(r[1])
            if lo == hi:
                result.append({"score": lo})
            else:
                result.append({"score_min": lo, "score_max": hi})
        return result
    if "expected_scores" in row:
        s = row["expected_scores"]
        if isinstance(s, (tuple, list)) and s:
            return [{"score": float(v)} for v in s]
        return [None] * n
    if "expected_score" in row:
        s = row["expected_score"]
        if isinstance(s, (int, float)) and s > 0:
            return [{"score": float(s)}] * n
    return [None] * n


def _quote(value):
    """Format a value as a YAML scalar."""
    if isinstance(value, str):
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        escaped = escaped.replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t")
        return f'"{escaped}"'
    if isinstance(value, float) and value == int(value):
        return f"{value:.1f}"
    return str(value)


def write_yaml(
    recognizer_name,
    entity_type,
    language,
    country_code,
    test_cases,
    comments,
    output_path,
):
    """Write a TCK YAML file with preserved comments."""
    lines = [
        f"# TCK for {recognizer_name}",
        f"recognizer: {recognizer_name}",
        f"entity_type: {entity_type}",
        f"language: {language}",
    ]
    if country_code:
        lines.append(f"country_code: {country_code}")
    lines += ["", "test_cases:"]

    for i, case in enumerate(test_cases):
        c = comments[i] if i < len(comments) else None
        if c:
            lines.extend(f"  # {cl}" for cl in c.split("\n"))

        lines.append(f"  - input: {_quote(case['input'])}")
        if "expected_count" in case:
            lines.append(f"    expected_count: {case['expected_count']}")
        elif not case.get("expected"):
            lines.append("    expected: []")
        else:
            lines.append("    expected:")
            for exp in case["expected"]:
                lines.append(f"      - start: {exp['start']}")
                lines.append(f"        end: {exp['end']}")
                for key in ("score", "score_min", "score_max"):
                    if key in exp:
                        lines.append(f"        {key}: {_quote(exp[key])}")
        lines.append("")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n")


def _find_metadata(tree):
    """Extract recognizer class name and entity type from AST."""
    recognizer_name = None
    entity_type = None
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.ImportFrom)
            and node.module
            and "predefined_recognizers" in node.module
        ):
            for alias in node.names:
                name = alias.asname or alias.name
                if name.endswith("Recognizer"):
                    recognizer_name = name
        if isinstance(node, ast.FunctionDef) and node.name == "entities":
            for stmt in node.body:
                if not isinstance(stmt, ast.Return):
                    continue
                val = stmt.value
                if not isinstance(val, ast.List):
                    continue
                if val.elts and isinstance(val.elts[0], ast.Constant):
                    entity_type = val.elts[0].value
    return recognizer_name, entity_type


def process_file(test_file):
    """Process a single test file and generate TCK YAML."""
    source = test_file.read_text()
    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        print(f"  SKIP (syntax error): {e}")
        return False

    recognizer_name, entity_type = _find_metadata(tree)
    if not recognizer_name or not entity_type:
        print("  SKIP (no recognizer/entity found)")
        return False

    blocks = find_parametrize_blocks(test_file, tree)
    if not blocks:
        print("  SKIP (no parametrize blocks)")
        return False

    language, country_code = get_recognizer_metadata(recognizer_name)
    source_lines = source.splitlines()
    all_cases, all_comments = [], []

    for argnames, argvalues, func_name in blocks:
        all_cases.extend(normalize_case(argnames, v) for v in argvalues)
        all_comments.extend(
            extract_comments_for_block(tree, func_name, source_lines, len(argvalues))
        )

    if not all_cases:
        print("  SKIP (no extractable test cases)")
        return False

    stem = test_file.stem.removeprefix("test_")
    output_path = OUTPUT_DIR / f"{stem}.yaml"
    write_yaml(
        recognizer_name,
        entity_type,
        language,
        country_code,
        all_cases,
        all_comments,
        output_path,
    )
    print(f"  -> {output_path.name} ({len(all_cases)} test cases)")
    return True


def main():
    """Extract TCK YAML files from all recognizer tests."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    success = skipped = 0
    for f in sorted(TESTS_DIR.glob("test_*_recognizer.py")):
        if f.name in SKIP_FILES:
            skipped += 1
            continue
        print(f"Processing {f.name}...")
        if process_file(f):
            success += 1
        else:
            skipped += 1
    print(f"\nDone: {success} YAML files generated, {skipped} skipped")


if __name__ == "__main__":
    main()
