"""Data schemas for the Hiver AI Customer Support System.
Uses standard Pydantic models for strict type validation and clean serialization.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class ConversationTurn(BaseModel):
    role: str = Field(..., description="Role of the speaker: 'customer' or 'support'")
    text: str = Field(..., description="Text content of the turn")


class SupportConversation(BaseModel):
    conversation_id: str
    company: str
    customer_query: str
    support_reply: str
    turns: List[ConversationTurn] = Field(default_factory=list)
    num_turns: int = 0
    has_url: bool = False
    has_dm_request: bool = False


class GoldenExample(BaseModel):
    id: str
    conversation_id: str
    customer_message: str
    historical_reply: Optional[str] = None
    proposed_intent: Optional[str] = None
    proposed_decision: Optional[str] = None
    intent: str  # Final verified intent
    expected_decision: str  # Final verified decision: 'AUTO_HANDLE' or 'ESCALATE_TO_HUMAN'
    reviewer_notes: str = ""
    human_verified: bool = False

    @property
    def review_notes(self) -> str:
        return self.reviewer_notes


class RetrievedEvidence(BaseModel):
    conversation_id: str
    historical_query: str
    historical_reply: str
    similarity_score: float
    intent: Optional[str] = None


class AgentPrediction(BaseModel):
    intent: str
    intent_confidence: float
    reply: str
    decision: str  # 'AUTO_HANDLE' or 'ESCALATE_TO_HUMAN'
    reason: str
    evidence_sufficiency: str  # 'adequate' or 'insufficient'
    evidence: List[Dict[str, Any]] = Field(default_factory=list)


class EvaluationResult(BaseModel):
    example_id: str
    customer_message: str
    gold_intent: str
    predicted_intent: str
    intent_correct: bool
    gold_decision: str
    predicted_decision: str
    decision_correct: bool
    reply: str
    reason: str
    evidence_sufficiency: str
    retrieval_similarity_top1: float
    retrieval_intent_match: bool
    judge_relevance: Optional[float] = None
    judge_groundedness: Optional[float] = None
    judge_tone: Optional[float] = None
    judge_escalation: Optional[float] = None
    judge_overall: Optional[float] = None
