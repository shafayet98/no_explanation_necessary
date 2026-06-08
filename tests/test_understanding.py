"""Unit tests for Phase 5: classifier, decomposer, and query routing.

All external calls (Anthropic SDK, index/engine, embedder, reranker) are mocked
so these tests pass without a live API key or a loaded index.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

CANARY = (
    "The rain finds me before I'm ready for it, soaking through my collar as I stand "
    "frozen on the pavement, watching the gutters swell into little rivers. And somehow "
    "I don't move—I just let it come, breathing in that strange grey peace, like "
    "the sky finally said the thing I'd been too afraid to."
)

# ---------------------------------------------------------------------------
# classifier
# ---------------------------------------------------------------------------

class TestClassify:
    def test_short_single_concept(self):
        from understanding.classifier import classify
        assert classify("the smell of rain on dry earth") == "single"

    def test_empty_string(self):
        from understanding.classifier import classify
        assert classify("") == "single"

    def test_one_char(self):
        from understanding.classifier import classify
        assert classify("x") == "single"

    def test_canary_is_multi(self):
        from understanding.classifier import classify
        assert classify(CANARY) == "multi"

    def test_long_single_sentence_few_conjunctions(self):
        from understanding.classifier import classify
        # > 150 chars, but 1 sentence and only 1 conjunction → 1 signal → "single"
        text = (
            "the peaceful restorative state of being by oneself, away from other people, "
            "in which silence feels like nourishment for the spirit rather than a sign of isolation"
        )
        assert len(text) > 150
        assert classify(text) == "single"

    def test_multi_sentence_long_text(self):
        from understanding.classifier import classify
        # Two sentences, > 150 chars, multiple conjunctions → should be "multi"
        text = (
            "She sat by the window every evening, watching the trains leave and wondering where they went. "
            "And somehow she never boarded one, just stood there, and felt the weight of all those unlived journeys."
        )
        assert classify(text) == "multi"

    @pytest.mark.parametrize("desc", [
        "a feeling of extreme happiness or cheerfulness",
        "a strong feeling of displeasure or hostility toward someone",
        "the state of being alone without company",
        "strong affection for another person",
        "an unreasonable overestimation of one's own importance",
    ])
    def test_existing_eval_cases_are_single(self, desc):
        from understanding.classifier import classify
        assert classify(desc) == "single"


# ---------------------------------------------------------------------------
# decomposer
# ---------------------------------------------------------------------------

_GOOD_RESPONSE = json.dumps([
    {"label": "the rain smell", "query": "smell of rain on dry earth"},
    {"label": "calm acceptance", "query": "peaceful acceptance of what cannot be changed"},
    {"label": "emotional release", "query": "relief from finally expressing suppressed feeling"},
])


class TestDecompose:
    def _make_mock_client(self, text: str):
        msg = MagicMock()
        msg.content = [MagicMock(text=text)]
        client = MagicMock()
        client.messages.create.return_value = msg
        return client

    def test_parses_valid_response(self):
        from understanding.decomposer import _parse_response
        result = _parse_response(_GOOD_RESPONSE)
        assert len(result) == 3
        assert result[0] == ("the rain smell", "smell of rain on dry earth")
        assert result[1] == ("calm acceptance", "peaceful acceptance of what cannot be changed")

    def test_strips_markdown_fences(self):
        from understanding.decomposer import _parse_response
        fenced = f"```json\n{_GOOD_RESPONSE}\n```"
        result = _parse_response(fenced)
        assert len(result) == 3

    def test_raises_on_empty_list(self):
        from understanding.decomposer import _parse_response
        with pytest.raises(ValueError):
            _parse_response("[]")

    def test_raises_on_missing_label(self):
        from understanding.decomposer import _parse_response
        bad = json.dumps([{"query": "something"}])
        with pytest.raises(ValueError):
            _parse_response(bad)

    def test_raises_on_missing_query(self):
        from understanding.decomposer import _parse_response
        bad = json.dumps([{"label": "something"}])
        with pytest.raises(ValueError):
            _parse_response(bad)

    def test_raises_runtime_error_without_api_key(self):
        from understanding import decomposer
        import os
        original = os.environ.pop("ANTHROPIC_API_KEY", None)
        # Also reset the cached client so it tries to create a new one
        decomposer._client = None
        try:
            with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
                from understanding.decomposer import decompose
                decompose("some text")
        finally:
            if original:
                os.environ["ANTHROPIC_API_KEY"] = original
            decomposer._client = None

    def test_decompose_with_mocked_client(self):
        from understanding import decomposer

        mock_client = self._make_mock_client(_GOOD_RESPONSE)
        decomposer._client = mock_client
        try:
            from understanding.decomposer import decompose
            result = decompose(CANARY)
            assert len(result) == 3
            assert all(isinstance(label, str) and isinstance(q, str) for label, q in result)
            assert all(label and q for label, q in result)
        finally:
            decomposer._client = None

    def test_decompose_retries_on_bad_json(self):
        from understanding import decomposer

        call_count = [0]
        def side_effect(**kwargs):
            call_count[0] += 1
            text = "not json at all" if call_count[0] == 1 else _GOOD_RESPONSE
            msg = MagicMock()
            msg.content = [MagicMock(text=text)]
            return msg

        mock_client = MagicMock()
        mock_client.messages.create.side_effect = side_effect
        decomposer._client = mock_client
        try:
            from understanding.decomposer import decompose
            result = decompose(CANARY)
            assert len(result) == 3
            assert call_count[0] == 2
        finally:
            decomposer._client = None


# ---------------------------------------------------------------------------
# query routing
# ---------------------------------------------------------------------------

def _make_fake_search_result(word="petrichor", score=0.9):
    from data.models import WordRecord
    record = WordRecord(id=0, word=word, sense=0, pos="n", definition="test def", embed_text=f"{word}: test def")
    sr = MagicMock()
    sr.record = record
    sr.score = score
    return sr


class TestQueryRouting:
    def _patch_single_concept_deps(self):
        fake_sr = _make_fake_search_result()
        engine_mock = MagicMock()
        embed_mock = MagicMock(return_value=[[0.1] * 384])
        rerank_mock = MagicMock(return_value=[fake_sr] * 10)
        return engine_mock, embed_mock, rerank_mock

    def test_single_concept_path_returns_single_mode(self):
        from understanding.query import query
        engine_mock, embed_mock, rerank_mock = self._patch_single_concept_deps()

        with patch("understanding.classifier.classify", return_value="single"), \
             patch("index.engine.load"), \
             patch("index.engine.search", return_value=[_make_fake_search_result()] * 50), \
             patch("embedding.embedder.embed", return_value=[[0.1] * 384]), \
             patch("understanding.reranker.rerank", return_value=[_make_fake_search_result()] * 10):
            response = query("the smell of rain on dry earth")

        assert response.mode == "single"
        assert len(response.groups) == 1
        assert all(not rr.is_interpretation for rr in response.groups[0].results)

    def test_multi_concept_path_returns_grouped_mode(self):
        from understanding.query import query
        from understanding import decomposer

        fake_concepts = [
            ("the rain smell", "smell of rain on dry earth"),
            ("calm acceptance", "peaceful acceptance of the uncontrollable"),
        ]

        with patch("understanding.classifier.classify", return_value="multi"), \
             patch("understanding.decomposer.decompose", return_value=fake_concepts), \
             patch("index.engine.load"), \
             patch("index.engine.search", return_value=[_make_fake_search_result()] * 50), \
             patch("embedding.embedder.embed", return_value=[[0.1] * 384]), \
             patch("understanding.reranker.rerank", return_value=[_make_fake_search_result()] * 10):
            response = query(CANARY)

        assert response.mode == "grouped"
        assert len(response.groups) == 2
        assert response.groups[0].label == "the rain smell"
        assert response.groups[1].label == "calm acceptance"

    def test_multi_concept_all_results_are_interpretations(self):
        from understanding.query import query

        fake_concepts = [("concept", "clean query")]

        with patch("understanding.classifier.classify", return_value="multi"), \
             patch("understanding.decomposer.decompose", return_value=fake_concepts), \
             patch("index.engine.load"), \
             patch("index.engine.search", return_value=[_make_fake_search_result()] * 50), \
             patch("embedding.embedder.embed", return_value=[[0.1] * 384]), \
             patch("understanding.reranker.rerank", return_value=[_make_fake_search_result()] * 10):
            response = query(CANARY)

        assert all(rr.is_interpretation for g in response.groups for rr in g.results)

    def test_fallback_to_single_when_api_key_missing(self):
        from understanding.query import query

        with patch("understanding.classifier.classify", return_value="multi"), \
             patch("understanding.decomposer.decompose", side_effect=RuntimeError("no key")), \
             patch("index.engine.load"), \
             patch("index.engine.search", return_value=[_make_fake_search_result()] * 50), \
             patch("embedding.embedder.embed", return_value=[[0.1] * 384]), \
             patch("understanding.reranker.rerank", return_value=[_make_fake_search_result()] * 10):
            response = query(CANARY)

        assert response.mode == "single"
