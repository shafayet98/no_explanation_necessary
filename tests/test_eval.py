"""Unit tests for the eval harness (Phase 2)."""

import json
from pathlib import Path

ROOT = Path(__file__).parent.parent
TEST_CASES_PATH = ROOT / "eval" / "test_cases.jsonl"
BASELINES_PATH = ROOT / "eval" / "baselines.json"


def test_test_cases_parse_and_have_required_keys():
    cases = []
    with open(TEST_CASES_PATH) as f:
        for line in f:
            line = line.strip()
            if line:
                cases.append(json.loads(line))
    assert len(cases) >= 150, f"Expected >= 150 test cases, got {len(cases)}"
    for i, case in enumerate(cases):
        assert "description" in case, f"Case {i} missing 'description'"
        assert "expected_word" in case, f"Case {i} missing 'expected_word'"
        assert isinstance(case["description"], str) and case["description"]
        assert isinstance(case["expected_word"], str) and case["expected_word"]


def test_baselines_valid_and_nonempty():
    with open(BASELINES_PATH) as f:
        baselines = json.load(f)
    assert isinstance(baselines, list), "baselines.json must be a JSON array"
    assert len(baselines) >= 1, "At least one baseline must be recorded"
    for entry in baselines:
        assert "phase" in entry
        assert "recall_at_10" in entry
        assert "mrr" in entry
        assert "date" in entry
        assert 0.0 <= entry["recall_at_10"] <= 1.0
        assert 0.0 <= entry["mrr"] <= 1.0


def test_compute_metrics_smoke():
    from eval.eval import compute_metrics

    cases = [
        {"description": "desc1", "expected_word": "alpha"},
        {"description": "desc2", "expected_word": "beta"},
        {"description": "desc3", "expected_word": "gamma"},
    ]
    # alpha is rank 1, beta is rank 5, gamma is missing
    top_k_results = [
        ["alpha", "delta", "epsilon"],
        ["zeta", "eta", "theta", "iota", "beta"],
        ["kappa", "lambda"],
    ]
    expected_words = [c["expected_word"] for c in cases]

    recall, mrr = compute_metrics(cases, expected_words, top_k_results)

    assert abs(recall - 2 / 3) < 1e-9, f"recall should be 2/3, got {recall}"
    expected_mrr = (1 / 1 + 1 / 5 + 0) / 3
    assert abs(mrr - expected_mrr) < 1e-9, f"mrr should be {expected_mrr}, got {mrr}"
