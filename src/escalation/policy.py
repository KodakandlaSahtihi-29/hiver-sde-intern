"""Evidence-aware escalation policy engine.
Distinguishes between observed historical customer service patterns and our conservative engineering rules.
"""

from typing import Tuple, List, Dict, Any, Optional
from src.data.schema import RetrievedEvidence
from src.preprocessing.text_cleaner import clean_for_embedding


class EscalationPolicyEngine:
    """Evaluates customer message, intent confidence, and retrieved evidence
    to determine whether an inquiry can be safely AUTO_HANDLED or must ESCALATE_TO_HUMAN.
    """

    def __init__(self, min_confidence_threshold: float = 0.55, min_similarity_threshold: float = 0.18):
        self.min_confidence_threshold = min_confidence_threshold
        self.min_similarity_threshold = min_similarity_threshold

    def evaluate(
        self,
        customer_message: str,
        intent: str,
        intent_confidence: float,
        evidence: List[RetrievedEvidence],
        evidence_status: str
    ) -> Tuple[str, str, str]:
        """Returns (decision: 'AUTO_HANDLE' | 'ESCALATE_TO_HUMAN', reason: str, trigger: str).
        """
        cleaned = clean_for_embedding(customer_message).lower()

        # Rule 1: High-Stakes Account Access & Security
        if intent == "Account_Access_Security" or any(kw in cleaned for kw in ["apple id", "locked icloud", "passcode reset", "2fa code", "security lockout"]):
            return (
                "ESCALATE_TO_HUMAN",
                "Account access and identity verification require human agent review or authenticated recovery channel.",
                "POLICY_RULE_ACCOUNT_SECURITY"
            )

        # Rule 2: Financial Disputes and Billing Transactions
        if intent == "Billing_Subscriptions" and any(kw in cleaned for kw in ["refund", "charge", "charged", "unauthorized", "dispute", "cancel subscription", "bill"]):
            return (
                "ESCALATE_TO_HUMAN",
                "Financial transactions, unauthorized charges, and refund requests require verified account lookup.",
                "POLICY_RULE_BILLING_DISPUTE"
            )

        # Rule 3: Insufficient Historical Evidence
        if evidence_status == "insufficient":
            return (
                "ESCALATE_TO_HUMAN",
                "Retrieved historical precedent is insufficient to guarantee an accurate automated resolution.",
                "POLICY_RULE_INSUFFICIENT_EVIDENCE"
            )

        # Rule 4: Low Intent Confidence / Ambiguity
        if intent_confidence < self.min_confidence_threshold:
            return (
                "ESCALATE_TO_HUMAN",
                f"Intent classification confidence ({intent_confidence:.2f}) is below safe automation threshold ({self.min_confidence_threshold:.2f}).",
                "POLICY_RULE_LOW_CONFIDENCE"
            )

        # Rule 5: Extremely Vague / Unactionable Message
        if len(cleaned.split()) < 4 and not any(kw in cleaned for kw in ["wifi", "battery", "sim", "sound", "ios"]):
            return (
                "ESCALATE_TO_HUMAN",
                "Customer inquiry lacks sufficient diagnostic detail for automated self-service resolution.",
                "POLICY_RULE_VAGUE_INQUIRY"
            )

        # Rule 6: Hardware Physical Damage Requiring In-Person Repair
        if intent == "Connectivity_Hardware" and any(kw in cleaned for kw in ["cracked", "broken", "water damage", "dropped in water", "shattered"]):
            return (
                "ESCALATE_TO_HUMAN",
                "Physical hardware damage requires authorized service center inspection and repair scheduling.",
                "POLICY_RULE_PHYSICAL_HARDWARE"
            )

        # Default Safe Automation for Documented Technical Guidance
        return (
            "AUTO_HANDLE",
            "Inquiry matches standard self-service technical guidance with adequate historical precedent.",
            "POLICY_RULE_SAFE_AUTO_HANDLE"
        )
