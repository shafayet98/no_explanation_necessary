"""Unit tests for Phase 6: filters, lucky mode, and phrase normalization.

All external calls (index/engine, embedder, reranker) are mocked so these
tests pass without a loaded index or API key.
"""

from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers — build fake WordRecord / SearchResult objects
# ---------------------------------------------------------------------------

def _make_record(word, pos, definition="a definition"):
    from data.models import WordRecord
    return WordRecord(id=0, word=word, sense=0, pos=pos, definition=definition,
                      embed_text=f"{word}: {definition}")


def _make_sr(word, pos, score=0.5, definition="a definition"):
    from index.engine import SearchResult
    return SearchResult(record=_make_record(word, pos, definition), score=score)


# ---------------------------------------------------------------------------
# _normalize_input
# ---------------------------------------------------------------------------

class TestNormalizeInput:
    def _fn(self, text):
        from understanding.query import _normalize_input
        return _normalize_input(text)

    def test_strips_outer_whitespace(self):
        assert self._fn("  hello world  ") == "hello world"

    def test_collapses_internal_whitespace(self):
        assert self._fn("the  smell   of  rain") == "the smell of rain"

    def test_strips_trailing_period(self):
        assert self._fn("silver lining.") == "silver lining"

    def test_strips_trailing_comma(self):
        assert self._fn("silver lining,") == "silver lining"

    def test_strips_trailing_exclamation(self):
        assert self._fn("eureka!") == "eureka"

    def test_strips_trailing_question_mark(self):
        assert self._fn("why?") == "why"

    def test_combined_whitespace_and_punctuation(self):
        assert self._fn("  the smell  of rain. ") == "the smell of rain"

    def test_empty_string(self):
        assert self._fn("") == ""

    def test_only_whitespace(self):
        assert self._fn("   ") == ""

    def test_no_change_needed(self):
        assert self._fn("petrichor") == "petrichor"


# ---------------------------------------------------------------------------
# _passes_filter
# ---------------------------------------------------------------------------

class TestPassesFilter:
    def _fn(self, record, filters):
        from understanding.query import _passes_filter
        return _passes_filter(record, filters)

    def _filters(self, pos=None, starts_with=None, max_length=None):
        from understanding.query import QueryFilters
        return QueryFilters(pos=pos, starts_with=starts_with, max_length=max_length)

    def test_all_none_passes_everything(self):
        r = _make_record("bank", "n")
        assert self._fn(r, self._filters()) is True

    def test_pos_match_passes(self):
        r = _make_record("bank", "n")
        assert self._fn(r, self._filters(pos="n")) is True

    def test_pos_mismatch_fails(self):
        r = _make_record("bank", "v")
        assert self._fn(r, self._filters(pos="n")) is False

    def test_starts_with_match_passes(self):
        r = _make_record("petrichor", "n")
        assert self._fn(r, self._filters(starts_with="p")) is True

    def test_starts_with_mismatch_fails(self):
        r = _make_record("saudade", "n")
        assert self._fn(r, self._filters(starts_with="p")) is False

    def test_starts_with_case_insensitive(self):
        r = _make_record("Petrichor", "n")
        assert self._fn(r, self._filters(starts_with="P")) is True
        assert self._fn(r, self._filters(starts_with="p")) is True

    def test_max_length_exact_passes(self):
        r = _make_record("hello", "n")   # 5 chars
        assert self._fn(r, self._filters(max_length=5)) is True

    def test_max_length_under_passes(self):
        r = _make_record("hi", "n")   # 2 chars
        assert self._fn(r, self._filters(max_length=5)) is True

    def test_max_length_over_fails(self):
        r = _make_record("petrichor", "n")   # 9 chars
        assert self._fn(r, self._filters(max_length=5)) is False

    def test_combined_all_pass(self):
        r = _make_record("pride", "n")
        assert self._fn(r, self._filters(pos="n", starts_with="p", max_length=6)) is True

    def test_combined_one_fails(self):
        r = _make_record("pride", "v")   # pos wrong
        assert self._fn(r, self._filters(pos="n", starts_with="p", max_length=6)) is False


# ---------------------------------------------------------------------------
# _run_single_concept with filters
# ---------------------------------------------------------------------------

MIXED_RESULTS = [
    _make_sr("petrichor", "n", 0.9),   # noun, 9 chars, starts with p
    _make_sr("run",       "v", 0.8),   # verb, 3 chars, starts with r
    _make_sr("pride",     "n", 0.7),   # noun, 5 chars, starts with p
    _make_sr("saudade",   "n", 0.6),   # noun, 7 chars, starts with s
    _make_sr("equanimity","n", 0.5),   # noun, 9 chars, starts with e
]


def _patch_pipeline(results):
    """Return context managers that mock the full pipeline with given results."""
    return (
        patch("index.engine.load"),
        patch("embedding.embedder.embed", return_value=[[0.0] * 384]),
        patch("index.engine.search", return_value=results),
        patch("understanding.reranker.rerank", return_value=results),
    )


class TestRunSingleConceptWithFilters:
    def _call(self, query_text, filters=None):
        from understanding.query import _run_single_concept
        load_p, embed_p, search_p, rerank_p = _patch_pipeline(MIXED_RESULTS)
        with load_p, embed_p, search_p, rerank_p:
            return _run_single_concept(query_text, is_interpretation=False, filters=filters)

    def test_no_filter_returns_all(self):
        group = self._call("some query")
        assert len(group.results) == len(MIXED_RESULTS)

    def test_pos_filter_nouns_only(self):
        from understanding.query import QueryFilters
        filters = QueryFilters(pos="n", starts_with=None, max_length=None)
        group = self._call("some query", filters=filters)
        assert all(r.pos == "n" for r in group.results)
        assert len(group.results) == 4   # petrichor, pride, saudade, equanimity

    def test_starts_with_filter(self):
        from understanding.query import QueryFilters
        filters = QueryFilters(pos=None, starts_with="p", max_length=None)
        group = self._call("some query", filters=filters)
        assert all(r.word.lower().startswith("p") for r in group.results)
        assert len(group.results) == 2   # petrichor, pride

    def test_max_length_filter(self):
        from understanding.query import QueryFilters
        filters = QueryFilters(pos=None, starts_with=None, max_length=5)
        group = self._call("some query", filters=filters)
        assert all(len(r.word) <= 5 for r in group.results)
        assert len(group.results) == 2   # run(3), pride(5)

    def test_combined_filter(self):
        from understanding.query import QueryFilters
        # noun + starts with p + max_length 6 → only "pride"
        filters = QueryFilters(pos="n", starts_with="p", max_length=6)
        group = self._call("some query", filters=filters)
        assert len(group.results) == 1
        assert group.results[0].word == "pride"

    def test_zero_results_when_nothing_matches(self):
        from understanding.query import QueryFilters
        filters = QueryFilters(pos="v", starts_with="z", max_length=3)
        group = self._call("some query", filters=filters)
        assert group.results == []

    def test_oversampling_when_filter_active(self):
        """Verify search() is called with k=100 when filters are active."""
        from understanding.query import QueryFilters, _run_single_concept
        filters = QueryFilters(pos="n", starts_with=None, max_length=None)
        load_p, embed_p, search_p, rerank_p = _patch_pipeline(MIXED_RESULTS)
        with load_p, embed_p, search_p as mock_search, rerank_p:
            _run_single_concept("query", is_interpretation=False, filters=filters)
            mock_search.assert_called_once()
            _, kwargs = mock_search.call_args
            assert kwargs.get("k", mock_search.call_args[0][1] if len(mock_search.call_args[0]) > 1 else None) == 100

    def test_no_oversampling_without_filter(self):
        """Verify search() is called with k=50 when no filters."""
        from understanding.query import _run_single_concept
        load_p, embed_p, search_p, rerank_p = _patch_pipeline(MIXED_RESULTS)
        with load_p, embed_p, search_p as mock_search, rerank_p:
            _run_single_concept("query", is_interpretation=False, filters=None)
            mock_search.assert_called_once()
            _, kwargs = mock_search.call_args
            k_val = kwargs.get("k") or (mock_search.call_args[0][1] if len(mock_search.call_args[0]) > 1 else None)
            assert k_val == 50


# ---------------------------------------------------------------------------
# query() — filters threaded through single-concept path
# ---------------------------------------------------------------------------

class TestQueryWithFilters:
    def _call(self, text, filters=None, lucky=False):
        from understanding.query import query
        load_p, embed_p, search_p, rerank_p = _patch_pipeline(MIXED_RESULTS)
        with load_p, embed_p, search_p, rerank_p, \
             patch("understanding.classifier.classify", return_value="single"):
            return query(text, filters=filters, lucky=lucky)

    def test_no_filters_returns_all(self):
        response = self._call("some query")
        assert len(response.groups[0].results) == len(MIXED_RESULTS)

    def test_pos_filter_applied(self):
        from understanding.query import QueryFilters
        filters = QueryFilters(pos="v", starts_with=None, max_length=None)
        response = self._call("some query", filters=filters)
        results = response.groups[0].results
        assert all(r.pos == "v" for r in results)

    def test_normalization_applied(self):
        """Padded input should work identically to clean input."""
        from understanding.query import QueryFilters
        filters = QueryFilters(pos="n", starts_with=None, max_length=None)
        r1 = self._call("the smell of rain", filters=filters)
        r2 = self._call("  the smell  of rain. ", filters=filters)
        assert [r.word for r in r1.groups[0].results] == [r.word for r in r2.groups[0].results]

    def test_empty_input_returns_empty(self):
        from understanding.query import query
        # Empty string after normalization — should not crash
        response = query("   ")
        assert response.groups == [{"label": "", "results": []}] or response.groups[0].results == []


# ---------------------------------------------------------------------------
# query() — lucky mode
# ---------------------------------------------------------------------------

class TestLuckyMode:
    def _call(self, lucky):
        from understanding.query import query
        load_p, embed_p, search_p, rerank_p = _patch_pipeline(MIXED_RESULTS)
        with load_p, embed_p, search_p, rerank_p, \
             patch("understanding.classifier.classify", return_value="single"):
            return query("some query", lucky=lucky)

    def test_lucky_false_returns_all(self):
        response = self._call(lucky=False)
        assert len(response.groups[0].results) == len(MIXED_RESULTS)

    def test_lucky_true_returns_one(self):
        response = self._call(lucky=True)
        assert len(response.groups[0].results) == 1

    def test_lucky_true_returns_top_result(self):
        response = self._call(lucky=True)
        assert response.groups[0].results[0].word == "petrichor"  # highest score

    def test_lucky_default_is_false(self):
        from understanding.query import query
        load_p, embed_p, search_p, rerank_p = _patch_pipeline(MIXED_RESULTS)
        with load_p, embed_p, search_p, rerank_p, \
             patch("understanding.classifier.classify", return_value="single"):
            response = query("some query")
        assert len(response.groups[0].results) == len(MIXED_RESULTS)

    def test_lucky_with_grouped_response(self):
        """lucky=True truncates every group to 1 result."""
        from understanding.query import query
        concepts = [("label a", "query a"), ("label b", "query b")]
        load_p, embed_p, search_p, rerank_p = _patch_pipeline(MIXED_RESULTS)
        with load_p, embed_p, search_p, rerank_p, \
             patch("understanding.classifier.classify", return_value="multi"), \
             patch("understanding.decomposer.decompose", return_value=concepts):
            response = query("long passage with two concepts", lucky=True)
        assert all(len(g.results) == 1 for g in response.groups)
