import json
from pathlib import Path

import pytest

from bharatbench.validate import main, validate_dir

REPO_DATA = Path(__file__).resolve().parents[1] / "data"


def good(**over):
    t = {
        "id": "gst-001",
        "category": "gst_tax",
        "prompt": "What is 18% of 100?",
        "language": "en",
        "answer_type": "numeric",
        "reference_answer": 18,
        "worked_solution": "100 * 18% = 18",
        "difficulty": "easy",
        "verified": False,
    }
    t.update(over)
    return t


def write(tmp_path, rows, name="t.jsonl"):
    (tmp_path / name).write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")


def test_valid_task_passes(tmp_path):
    write(tmp_path, [good()])
    assert validate_dir(tmp_path) == []


@pytest.mark.parametrize("field", ["id", "category", "prompt", "language", "answer_type",
                                    "reference_answer", "difficulty", "verified"])
def test_missing_required_field_fails(tmp_path, field):
    t = good()
    del t[field]
    write(tmp_path, [t])
    assert validate_dir(tmp_path)


def test_needs_worked_solution_or_source(tmp_path):
    t = good(category="documents", id="doc-001")
    del t["worked_solution"]
    write(tmp_path, [t])
    assert validate_dir(tmp_path)


def test_duplicate_ids_fail(tmp_path):
    write(tmp_path, [good(), good()])
    errs = validate_dir(tmp_path)
    assert any("duplicate id" in e for e in errs)


def test_duplicate_ids_across_files_fail(tmp_path):
    write(tmp_path, [good()], "a.jsonl")
    write(tmp_path, [good()], "b.jsonl")
    assert any("duplicate id" in e for e in validate_dir(tmp_path))


def test_id_prefix_must_match_category(tmp_path):
    write(tmp_path, [good(id="law-001")])
    assert any("does not match category" in e for e in validate_dir(tmp_path))


def test_gst_requires_worked_solution(tmp_path):
    t = good(source_url="https://example.gov.in")
    del t["worked_solution"]
    write(tmp_path, [t])
    assert any("worked_solution" in e for e in validate_dir(tmp_path))


def test_law_requires_source_url(tmp_path):
    write(tmp_path, [good(id="law-001", category="law_policy")])
    assert any("source_url" in e for e in validate_dir(tmp_path))


def test_answer_type_must_fit_reference(tmp_path):
    write(tmp_path, [good(reference_answer="eighteen")])
    assert any("does not fit answer_type" in e for e in validate_dir(tmp_path))


def test_bad_enum_fails(tmp_path):
    write(tmp_path, [good(language="fr")])
    assert validate_dir(tmp_path)


def test_invalid_json_line_fails(tmp_path):
    (tmp_path / "t.jsonl").write_text("{not json}\n", encoding="utf-8")
    assert any("invalid JSON" in e for e in validate_dir(tmp_path))


def test_unknown_field_fails(tmp_path):
    write(tmp_path, [good(extra=1)])
    assert validate_dir(tmp_path)


def test_empty_dir_fails(tmp_path):
    assert validate_dir(tmp_path)


def test_expected_count(tmp_path):
    write(tmp_path, [good()])
    assert any("expected 20" in e for e in validate_dir(tmp_path, expect_per_category=20))


def test_main_exit_codes(tmp_path):
    write(tmp_path, [good()])
    assert main(["--data-dir", str(tmp_path)]) == 0
    write(tmp_path, [good(), good()])
    assert main(["--data-dir", str(tmp_path)]) == 1


def test_real_dataset_is_valid_and_complete():
    assert validate_dir(REPO_DATA, expect_per_category=20) == []
