"""Unit tests for the end-to-end SupportAgent pipeline.
"""

import pytest
from src.pipeline import SupportAgent
from src.data.schema import SupportConversation
from src.retrieval.vector_store import HistoricalVectorStore


@pytest.fixture
def initialized_agent():
    corpus = [
        SupportConversation(
            conversation_id="conv_a1",
            company="AppleSupport",
            customer_query="My iPhone battery drains rapidly after updating.",
            support_reply="Check your battery usage under Settings > Battery to see which apps are consuming power.",
            num_turns=2
        ),
        SupportConversation(
            conversation_id="conv_a2",
            company="AppleSupport",
            customer_query="Apple ID is locked due to security alert.",
            support_reply="Go to iforgot.apple.com to verify your identity and unlock your account.",
            num_turns=2
        )
    ]
    vs = HistoricalVectorStore()
    vs.build_index(corpus)
    return SupportAgent(vector_store=vs)


def test_agent_structured_output(initialized_agent):
    res = initialized_agent.process_message("My battery is dying very quickly on iPhone")
    assert hasattr(res, "intent")
    assert hasattr(res, "intent_confidence")
    assert hasattr(res, "reply")
    assert hasattr(res, "decision")
    assert hasattr(res, "reason")
    assert hasattr(res, "evidence_sufficiency")
    assert hasattr(res, "evidence")

    assert res.decision in ["AUTO_HANDLE", "ESCALATE_TO_HUMAN"]
    assert res.evidence_sufficiency in ["adequate", "insufficient"]
    assert isinstance(res.evidence, list)


def test_agent_escalation_branch(initialized_agent):
    res = initialized_agent.process_message("My Apple ID is locked and I cannot receive the verification code")
    assert res.intent == "Account_Access_Security"
    assert res.decision == "ESCALATE_TO_HUMAN"
    assert "account" in res.reason.lower() or "verification" in res.reason.lower()
