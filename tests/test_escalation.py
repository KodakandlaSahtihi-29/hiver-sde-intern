"""Unit tests for the evidence-aware escalation policy engine.
"""

import pytest
from src.escalation.policy import EscalationPolicyEngine
from src.data.schema import RetrievedEvidence


def test_account_security_escalation():
    engine = EscalationPolicyEngine()
    ev = [
        RetrievedEvidence(
            conversation_id="c1",
            historical_query="Account locked",
            historical_reply="Go to iforgot.apple.com",
            similarity_score=0.85
        )
    ]
    dec, reason, trigger = engine.evaluate(
        customer_message="My Apple ID is locked and I cannot reset my passcode",
        intent="Account_Access_Security",
        intent_confidence=0.90,
        evidence=ev,
        evidence_status="adequate"
    )
    assert dec == "ESCALATE_TO_HUMAN"
    assert "POLICY_RULE_ACCOUNT_SECURITY" in trigger


def test_billing_refund_escalation():
    engine = EscalationPolicyEngine()
    ev = [
        RetrievedEvidence(
            conversation_id="c2",
            historical_query="Refund request",
            historical_reply="Contact support",
            similarity_score=0.75
        )
    ]
    dec, reason, trigger = engine.evaluate(
        customer_message="I was charged for an app I didn't buy and I want a refund",
        intent="Billing_Subscriptions",
        intent_confidence=0.85,
        evidence=ev,
        evidence_status="adequate"
    )
    assert dec == "ESCALATE_TO_HUMAN"
    assert "POLICY_RULE_BILLING_DISPUTE" in trigger


def test_safe_auto_handle():
    engine = EscalationPolicyEngine()
    ev = [
        RetrievedEvidence(
            conversation_id="c3",
            historical_query="Battery health",
            historical_reply="Check settings > battery",
            similarity_score=0.55
        )
    ]
    dec, reason, trigger = engine.evaluate(
        customer_message="How can I check battery health on my iPhone?",
        intent="Device_Performance_Battery",
        intent_confidence=0.88,
        evidence=ev,
        evidence_status="adequate"
    )
    assert dec == "AUTO_HANDLE"
    assert trigger == "POLICY_RULE_SAFE_AUTO_HANDLE"


def test_insufficient_evidence_escalation():
    engine = EscalationPolicyEngine()
    dec, reason, trigger = engine.evaluate(
        customer_message="Weird glitch happening on my device",
        intent="Software_Bug_OS_Update",
        intent_confidence=0.60,
        evidence=[],
        evidence_status="insufficient"
    )
    assert dec == "ESCALATE_TO_HUMAN"
    assert trigger == "POLICY_RULE_INSUFFICIENT_EVIDENCE"
