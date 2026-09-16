"""Unit tests for historical vector retrieval and leakage prevention.
"""

import pytest
from src.data.schema import SupportConversation
from src.retrieval.vector_store import HistoricalVectorStore


@pytest.fixture
def sample_corpus():
    return [
        SupportConversation(
            conversation_id="conv_101",
            company="AppleSupport",
            customer_query="My iPhone battery drains within an hour of use.",
            support_reply="We'd love to help. Check battery health in Settings > Battery.",
            num_turns=2
        ),
        SupportConversation(
            conversation_id="conv_102",
            company="AppleSupport",
            customer_query="Cannot connect to Wi-Fi network on my iPad.",
            support_reply="Try resetting network settings under Settings > General > Reset.",
            num_turns=2
        ),
        SupportConversation(
            conversation_id="conv_103",
            company="AppleSupport",
            customer_query="Apple ID is locked due to security questions.",
            support_reply="Visit iforgot.apple.com to unlock your account.",
            num_turns=2
        )
    ]


def test_vector_store_indexing_and_exclusion(sample_corpus):
    vs = HistoricalVectorStore()
    # Exclude conv_103
    count = vs.build_index(sample_corpus, exclude_ids={"conv_103"})
    assert count == 2
    assert vs.is_indexed is True

    # Retrieve battery query
    results = vs.retrieve("Why is my battery draining so quickly?", top_k=2)
    assert len(results) > 0
    assert results[0].conversation_id == "conv_101"
    # Verify excluded ID never appears
    retrieved_cids = [r.conversation_id for r in results]
    assert "conv_103" not in retrieved_cids


def test_evidence_sufficiency(sample_corpus):
    vs = HistoricalVectorStore()
    vs.build_index(sample_corpus)

    # Relevant query
    results = vs.retrieve("iPhone battery dying too fast", top_k=1)
    status, reason = vs.assess_evidence_sufficiency("iPhone battery dying too fast", results)
    assert status == "adequate"

    # Extremely vague query
    status_vague, _ = vs.assess_evidence_sufficiency("hi", [])
    assert status_vague == "insufficient"
