"""Evaluation harness (Phase 2).

Loads eval/test_cases.jsonl, runs each description through embed + search,
and reports recall@10 and MRR versus the latest entry in eval/baselines.json.

Usage:
    python eval/eval.py
    python eval/eval.py --save-baseline --phase 1
"""

import argparse
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from embedding.embedder import embed
from index.engine import load, search

TEST_CASES_PATH = ROOT / "eval" / "test_cases.jsonl"
BASELINES_PATH = ROOT / "eval" / "baselines.json"


def load_test_cases() -> list[dict]:
    cases = []
    with open(TEST_CASES_PATH) as f:
        for line in f:
            line = line.strip()
            if line:
                cases.append(json.loads(line))
    return cases


def load_baselines() -> list[dict]:
    with open(BASELINES_PATH) as f:
        return json.load(f)


def run_eval(cases: list[dict], k: int = 10) -> tuple[float, float, list[dict]]:
    """Return (recall_at_k, mrr, per_case_results)."""
    load()
    descriptions = [c["description"] for c in cases]
    vectors = embed(descriptions)

    results = []
    reciprocal_ranks = []
    hits = 0

    for i, case in enumerate(cases):
        expected = case["expected_word"].lower()
        query_vec = vectors[i]
        top_k = search(query_vec, k=k)

        rank = None
        for j, sr in enumerate(top_k, 1):
            if sr.record.word.lower() == expected:
                rank = j
                break

        hit = rank is not None
        if hit:
            hits += 1
            reciprocal_ranks.append(1.0 / rank)
        else:
            reciprocal_ranks.append(0.0)

        results.append({
            "description": case["description"],
            "expected": expected,
            "difficulty": case.get("difficulty", ""),
            "rank": rank,
            "hit": hit,
            "score": top_k[rank - 1].score if hit else None,
        })

    recall = hits / len(cases)
    mrr = sum(reciprocal_ranks) / len(cases)
    return recall, mrr, results


def print_report(recall: float, mrr: float, results: list[dict], baselines: list[dict]) -> None:
    total = len(results)
    col_w = 52

    print()
    print("=" * 90)
    print("EVAL RESULTS")
    print("=" * 90)

    # Per-difficulty breakdown
    by_diff: dict[str, list[dict]] = {}
    for r in results:
        d = r["difficulty"] or "unknown"
        by_diff.setdefault(d, []).append(r)

    for diff in ["easy", "medium", "hard", "unknown"]:
        group = by_diff.get(diff, [])
        if not group:
            continue
        ghits = sum(1 for r in group if r["hit"])
        grr = sum((1.0 / r["rank"]) if r["hit"] else 0.0 for r in group) / len(group)
        print(f"\n--- {diff.upper()} ({len(group)} cases) ---")
        print(f"{'Description':{col_w}}  {'Expected':18s}  {'Rank':>6}  {'Score':>7}")
        print("-" * 90)
        for r in group:
            desc = r["description"][:col_w]
            rank_str = str(r["rank"]) if r["hit"] else "MISS"
            score_str = f"{r['score']:.4f}" if r["score"] is not None else "  —   "
            print(f"{desc:{col_w}}  {r['expected']:18s}  {rank_str:>6}  {score_str:>7}")
        print(f"  recall@{10}: {ghits}/{len(group)} = {ghits/len(group):.3f}   MRR: {grr:.3f}")

    # Aggregate
    print()
    print("=" * 90)
    print(f"TOTAL  {total} cases")
    print(f"  recall@10 : {recall:.4f}  ({sum(1 for r in results if r['hit'])}/{total})")
    print(f"  MRR       : {mrr:.4f}")

    # Baseline comparison
    if baselines:
        latest = baselines[-1]
        delta_r = recall - latest["recall_at_10"]
        delta_m = mrr - latest["mrr"]
        sign_r = "+" if delta_r >= 0 else ""
        sign_m = "+" if delta_m >= 0 else ""
        print()
        print(f"vs Phase {latest['phase']} baseline ({latest['date']})")
        print(f"  recall@10 : {latest['recall_at_10']:.4f}  →  {recall:.4f}  ({sign_r}{delta_r:.4f})")
        print(f"  MRR       : {latest['mrr']:.4f}  →  {mrr:.4f}  ({sign_m}{delta_m:.4f})")
    else:
        print()
        print("No baseline recorded yet. Run with --save-baseline --phase 1 to record one.")

    print("=" * 90)
    print()


def save_baseline(recall: float, mrr: float, phase: int) -> None:
    baselines = load_baselines()
    entry = {
        "phase": phase,
        "recall_at_10": round(recall, 6),
        "mrr": round(mrr, 6),
        "date": str(date.today()),
    }
    baselines.append(entry)
    with open(BASELINES_PATH, "w") as f:
        json.dump(baselines, f, indent=2)
    print(f"Baseline saved: phase={phase}, recall@10={recall:.4f}, MRR={mrr:.4f}")


def compute_metrics(cases: list[dict], expected_words: list[str], top_k_results: list[list]) -> tuple[float, float]:
    """Standalone metric computation for unit testing — no index or embed calls."""
    hits = 0
    rr_sum = 0.0
    for expected, results in zip(expected_words, top_k_results):
        expected = expected.lower()
        rank = None
        for j, word in enumerate(results, 1):
            if word.lower() == expected:
                rank = j
                break
        if rank is not None:
            hits += 1
            rr_sum += 1.0 / rank
    recall = hits / len(cases) if cases else 0.0
    mrr = rr_sum / len(cases) if cases else 0.0
    return recall, mrr


def main() -> None:
    parser = argparse.ArgumentParser(description="Run reverse-dictionary eval harness")
    parser.add_argument("--save-baseline", action="store_true", help="Append result to baselines.json")
    parser.add_argument("--phase", type=int, help="Phase number for baseline entry (default: max+1)")
    args = parser.parse_args()

    cases = load_test_cases()
    baselines = load_baselines()

    print(f"Running eval on {len(cases)} test cases …")
    recall, mrr, results = run_eval(cases)

    print_report(recall, mrr, results, baselines)

    if args.save_baseline:
        if args.phase is not None:
            phase = args.phase
        else:
            phase = (max(b["phase"] for b in baselines) + 1) if baselines else 1
        save_baseline(recall, mrr, phase)


if __name__ == "__main__":
    main()
