"""Unified End-to-End Support Agent Pipeline.
Combines Intent Classification, Semantic Retrieval, Evidence Sufficiency,
Grounded Reply Generation, and Conservative Escalation Decisioning.
"""

from typing import Dict, Any, List, Optional
from src.data.schema import AgentPrediction, RetrievedEvidence, SupportConversation
from src.intent.classifier import IntentClassifier
from src.retrieval.vector_store import HistoricalVectorStore
from src.generation.generator import GroundedReplyGenerator
from src.escalation.policy import EscalationPolicyEngine


class SupportAgent:
    """End-to-End AI Support Agent for @AppleSupport."""

    def __init__(
        self,
        intent_classifier: Optional[IntentClassifier] = None,
        vector_store: Optional[HistoricalVectorStore] = None,
        reply_generator: Optional[GroundedReplyGenerator] = None,
        escalation_engine: Optional[EscalationPolicyEngine] = None
    ):
        self.intent_classifier = intent_classifier or IntentClassifier()
        self.vector_store = vector_store or HistoricalVectorStore()
        self.reply_generator = reply_generator or GroundedReplyGenerator()
        self.escalation_engine = escalation_engine or EscalationPolicyEngine()

    def process_message(self, customer_message: str, top_k: int = 3) -> AgentPrediction:
        """Executes the full 5-stage support pipeline on an incoming customer query."""
        # Stage 1: Intent Classification
        intent, confidence = self.intent_classifier.classify(customer_message)

        # Stage 2: Historical Conversation Retrieval
        evidence: List[RetrievedEvidence] = []
        if self.vector_store.is_indexed:
            evidence = self.vector_store.retrieve(customer_message, top_k=top_k)

        # Stage 3: Evidence Sufficiency Assessment
        evidence_status, evidence_reason = self.vector_store.assess_evidence_sufficiency(
            customer_message, evidence
        )

        # Stage 4: Conservative Escalation Decision
        decision, reason, trigger = self.escalation_engine.evaluate(
            customer_message=customer_message,
            intent=intent,
            intent_confidence=confidence,
            evidence=evidence,
            evidence_status=evidence_status
        )

        # Stage 5: Grounded Reply Generation
        reply = self.reply_generator.generate(
            customer_message=customer_message,
            intent=intent,
            evidence=evidence,
            decision=decision,
            reason=reason
        )

        evidence_payload = [
            {
                "conversation_id": e.conversation_id,
                "historical_query": e.historical_query,
                "historical_reply": e.historical_reply,
                "similarity_score": e.similarity_score
            }
            for e in evidence
        ]

        return AgentPrediction(
            intent=intent,
            intent_confidence=confidence,
            reply=reply,
            decision=decision,
            reason=reason,
            evidence_sufficiency=evidence_status,
            evidence=evidence_payload
        )
