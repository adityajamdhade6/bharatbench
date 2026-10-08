import pytest

from bharatbench.scoring import normalize, parse_final_number, score_response
from bharatbench.scoring.base import extract_json_object
from bharatbench.scoring.exact import score_exact
from bharatbench.scoring.extraction import score_extraction
from bharatbench.scoring.numeric import score_numeric, within_tolerance


# ---------- exact ----------
@pytest.mark.parametrize("resp,ref", [
    ("Yes.", "yes"), (" T + 1 ", "T+1"), ("**District**", "District"), ("(b)", "b"),
    ("हाँ।", "हाँ"), ("NATIONAL\n", "national"), ("ｙｅｓ", "yes"),
])
def test_exact_matches_after_normalisation(resp, ref):
    assert score_exact(resp, ref).score == 1.0


@pytest.mark.parametrize("resp,ref", [("not", "no"), ("District Commission", "District"), ("T+2", "T+1"), ("", "no")])
def test_exact_rejects_different_answers(resp, ref):
    assert score_exact(resp, ref).score == 0.0


def test_normalize_keeps_devanagari_marks():
    assert normalize("नमस्ते!") == "नमस्ते"


# ---------- numeric parsing ----------
@pytest.mark.parametrize("text,want", [
    ("10030", 10030), ("₹10,030", 10030), ("Rs. 1,23,456.50", 123456.5), ("rs.10030/-", 10030),
    ("1.2 crore", 12_000_000), ("₹30 lakh", 3_000_000), ("2 lakhs", 200_000), ("5 Cr", 50_000_000),
    ("१२३४", 1234), ("-250", -250), ("It is 45.", 45), ("1,499,", 1499),
    ("GST is 8,100 so CGST = ₹4,050.", 4050), ("Answer: 4050 (half of 8,100)", 4050),
    ("**Final answer: 61,360**", 61360), ("उत्तर: ₹2,70,000", 270000),
])
def test_parse_final_number(text, want):
    assert parse_final_number(text) == pytest.approx(want)


@pytest.mark.parametrize("text", ["", "no idea", "crazy talk"])
def test_parse_final_number_none(text):
    assert parse_final_number(text) is None


def test_crazy_is_not_crore():
    assert parse_final_number("5 crazy") == 5


# ---------- numeric scoring ----------
def test_numeric_tolerance_is_half_a_percent():
    assert within_tolerance(10_040, 10_030)       # 0.1% off
    assert within_tolerance(10_080, 10_030)       # 0.5% off
    assert not within_tolerance(10_100, 10_030)   # 0.7% off


def test_numeric_zero_reference_uses_absolute_tolerance():
    assert score_numeric("0", 0).score == 1.0
    assert score_numeric("5", 0).score == 0.0
    assert score_numeric("0.01", 0, abs_tol=0.01).score == 1.0


def test_numeric_scores_real_formats():
    assert score_numeric("Total: ₹10,030", 10030).score == 1.0
    assert score_numeric("It is 1.2 crore rupees", 12_000_000).score == 1.0
    assert score_numeric("₹10,500", 10030).score == 0.0
    assert score_numeric("I don't know", 10030).score == 0.0


# ---------- extraction ----------
REF = {"order_id": "OD2025-7731", "amount": 1499, "return_date": "12 March"}


def test_extraction_full_marks_with_fenced_json_and_prose():
    reply = 'Sure!\n```json\n{"order_id": "OD2025-7731", "amount": "₹1,499", "return_date": "12 march"}\n```'
    assert score_extraction(reply, REF).score == 1.0


def test_extraction_share_of_fields():
    s = score_extraction('{"order_id": "OD2025-7731", "amount": 1498, "return_date": "12 March"}', REF)
    assert s.score == pytest.approx(2 / 3) and "amount" in s.detail


def test_extraction_missing_extra_and_case_insensitive_keys():
    s = score_extraction('{"ORDER_ID": "OD2025-7731", "unrelated": 1}', REF)
    assert s.score == pytest.approx(1 / 3)


def test_extraction_without_json_scores_zero():
    assert score_extraction("The order id is OD2025-7731", REF).score == 0.0


def test_extraction_number_as_text_for_string_reference():
    assert score_extraction('{"pincode": 201301}', {"pincode": "201301"}).score == 1.0


def test_extract_json_object_variants():
    assert extract_json_object('prefix {"a": 1} suffix') == {"a": 1}
    assert extract_json_object('{"a": {"b": 2}}') == {"a": {"b": 2}}
    assert extract_json_object("[1, 2]") is None
    assert extract_json_object("no json") is None


# ---------- dispatch ----------
def test_score_response_dispatch_and_rubric_needs_judge():
    num = {"id": "gst-001", "answer_type": "numeric", "reference_answer": 100, "tolerance": 0.01}
    assert score_response(num, "100").score == 1.0
    rub = {"id": "hin-016", "answer_type": "rubric", "reference_answer": ["x"]}
    with pytest.raises(ValueError, match="judge"):
        score_response(rub, "reply")


# ---------- the real dataset ----------
def test_every_reference_answer_scores_full_marks_as_a_reply():
    """Feeding each task's own reference answer back as the reply must score 1.0."""
    import json
    from pathlib import Path

    data = Path(__file__).resolve().parents[1] / "data"
    checked = 0
    for path in data.glob("*.jsonl"):
        for line in path.read_text(encoding="utf-8").splitlines():
            t = json.loads(line)
            if t["answer_type"] == "rubric":
                continue
            ref = t["reference_answer"]
            reply = json.dumps(ref, ensure_ascii=False) if isinstance(ref, dict) else str(ref)
            assert score_response(t, reply).score == 1.0, t["id"]
            checked += 1
    assert checked == 94  # 100 tasks minus the 6 rubric tasks
