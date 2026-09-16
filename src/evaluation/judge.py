"""LLM-as-a-Judge and heuristic quality evaluation module.
Evaluates agent replies across Relevance, Groundedness, Support Tone, and Escalation Appropriateness on a 1-5 scale.
"""

import os
import re
import json
import logging
from typing import Dict, Any, Optional
import requests

logger = logging.getLogger(__name__)

JUDGE_RUBRIC_PROMPT = """You are an expert QA evaluator for customer support systems.
Evaluate the following customer support interaction on a 1 to 5 scale across 4 dimensions:

Dimensions:
1. Relevance (1-5): Does the reply directly address the specific customer issue?
2. Groundedness (1-5): Is the reply grounded in realistic support procedures without hallucinating fake policies or unsupported guarantees?
3. Tone (1-5): Is the tone courteous, professional, and empathetic (consistent with Apple Support voice)?
4. Escalation Appropriateness (1-5): Did the agent correctly choose between self-service resolution and human escalation given the issue type?

Scoring Scale:
5 = Excellent: Fully accurate, grounded, courteous, and perfectly routed.
4 = Good: Accurate and helpful with minor phrasing or conciseness issues.
3 = Acceptable: Addresses the core issue but lacks specific detail or optimal routing.
2 = Poor: Partially off-topic, ungrounded advice, or incorrect escalation.
1 = Very Poor: Completely irrelevant, misleading, hallucinated, or unsafe.

Customer Query: "{customer_message}"
Predicted Intent: {intent}
Decision Taken: {decision} (Reason: {reason})
Agent Reply: "{reply}"

Respond ONLY with valid JSON in this format:
{{
  "relevance": <int 1-5>,
  "groundedness": <int 1-5>,
  "tone": <int 1-5>,
  "escalation": <int 1-5>,
  "rationale": "<brief 1-sentence rationale>"
}}
"""


class ReplyJudge:
    """Evaluates agent responses using an LLM or deterministic rule rubric."""

    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY")
        self.provider = os.getenv("LLM_PROVIDER", "gemini" if os.getenv("GEMINI_API_KEY") else "deterministic")

    def evaluate_reply(
        self,
        customer_message: str,
        intent: str,
        decision: str,
        reason: str,
        reply: str,
        expected_decision: Optional[str] = None
    ) -> Dict[str, Any]:
        """Evaluates a single reply and returns dimensional scores (1-5)."""
        # If API key is available, attempt LLM call
        if self.api_key and self.provider == "gemini":
            try:
                return self._evaluate_with_llm(customer_message, intent, decision, reason, reply)
            except Exception as e:
                logger.warning(f"Judge LLM API failed ({e}), using deterministic evaluation rubric.")

        # Deterministic rule-based judge rubric (reproducible, zero-cost, transparent)
        return self._evaluate_deterministic(customer_message, intent, decision, reason, reply, expected_decision)

    def _evaluate_deterministic(
        self,
        customer_message: str,
        intent: str,
        decision: str,
        reason: str,
        reply: str,
        expected_decision: Optional[str] = None
    ) -> Dict[str, Any]:
        """Transparent, rule-anchored rubric for reply quality."""
        reply_lower = reply.lower()
        query_lower = customer_message.lower()

        # 1. Relevance: Lexical and semantic connection to customer query
        relevance_score = 4.0
        query_words = set(re.findall(r"\b\w{4,}\b", query_lower))
        reply_words = set(re.findall(r"\b\w{4,}\b", reply_lower))
        overlap = query_words.intersection(reply_words)
        if len(overlap) >= 2 or intent.lower().split("_")[0] in reply_lower:
            relevance_score = 4.5
        elif len(overlap) == 0:
            relevance_score = 3.0

        # 2. Groundedness: Check for hallucinations, fabricated domains, or unsubstantiated claims
        groundedness_score = 4.5
        # Prohibited hallucinated domains
        if any(fake in reply_lower for fake in ["apple-support-free-fix.com", "guaranteed cash refund", "tomorrow at 9am"]):
            groundedness_score = 1.0
        elif "iforgot.apple.com" in reply_lower or "reportaproblem.apple.com" in reply_lower or "support" in reply_lower:
            groundedness_score = 5.0

        # 3. Tone: Courtesy and brand voice markers
        tone_score = 4.0
        courtesy_markers = ["understand", "help", "happy to", "we're here", "reach out", "thanks"]
        marker_count = sum(1 for m in courtesy_markers if m in reply_lower)
        if marker_count >= 2:
            tone_score = 5.0
        elif marker_count == 1:
            tone_score = 4.0
        else:
            tone_score = 3.0

        # 4. Escalation Appropriateness
        escalation_score = 4.0
        if expected_decision:
            if decision == expected_decision:
                escalation_score = 5.0
            else:
                # Conservative bias penalty: escalating a safe query is acceptable (3.0),
                # but auto-handling a high-risk security/billing issue is poor (1.5).
                if expected_decision == "ESCALATE_TO_HUMAN" and decision == "AUTO_HANDLE":
                    escalation_score = 1.5
                else:
                    escalation_score = 3.5

        overall = round((relevance_score + groundedness_score + tone_score + escalation_score) / 4.0, 2)

        return {
            "relevance": relevance_score,
            "groundedness": groundedness_score,
            "tone": tone_score,
            "escalation": escalation_score,
            "overall": overall,
            "judge_method": "deterministic_rubric",
            "rationale": f"Rule-evaluated: overlap={len(overlap)}, escalation_match={decision == expected_decision if expected_decision else 'N/A'}"
        }

    def _evaluate_with_llm(
        self,
        customer_message: str,
        intent: str,
        decision: str,
        reason: str,
        reply: str
    ) -> Dict[str, Any]:
        """Calls Gemini API for LLM-as-a-judge scoring."""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.api_key}"
        prompt = JUDGE_RUBRIC_PROMPT.format(
            customer_message=customer_message,
            intent=intent,
            decision=decision,
            reason=reason,
            reply=reply
        )
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.1, "responseMimeType": "application/json"}
        }
        resp = requests.post(url, json=payload, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            raw_text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
            parsed = json.loads(raw_text)
            parsed["judge_method"] = "llm_gemini_flash"
            parsed["overall"] = round(
                (parsed["relevance"] + parsed["groundedness"] + parsed["tone"] + parsed["escalation"]) / 4.0, 2
            )
            return parsed

        raise RuntimeError(f"Judge LLM failed with status {resp.status_code}")
