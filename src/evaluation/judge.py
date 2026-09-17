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

    def __init__(self, model_name: str = "gemini-3.1-flash-lite", cache_path: Optional[str] = "results/judge_cache.json"):
        self.api_key = os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY")
        self.provider = os.getenv("LLM_PROVIDER", "gemini" if os.getenv("GEMINI_API_KEY") else "deterministic")
        self.model_name = os.getenv("GEMINI_MODEL", model_name)
        self.cache_path = cache_path
        self.cache: Dict[str, Any] = {}
        if self.cache_path and os.path.exists(self.cache_path):
            try:
                with open(self.cache_path, "r", encoding="utf-8") as f:
                    self.cache = json.load(f)
            except Exception:
                self.cache = {}
        self._last_call_time = 0.0

    def evaluate_reply(
        self,
        customer_message: str,
        intent: str,
        decision: str,
        reason: str,
        reply: str,
        expected_decision: Optional[str] = None,
        cache_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """Evaluates a single reply and returns dimensional scores (1-5)."""
        # If provider is gemini, call the actual LLM judge without falling back to deterministic
        if self.provider == "gemini":
            if not self.api_key:
                raise RuntimeError("GEMINI_API_KEY is not set. Cannot run LLM judge without API key.")
            return self._evaluate_with_llm(customer_message, intent, decision, reason, reply, cache_key=cache_key)

        # Deterministic rule-based judge rubric (only when provider is explicitly deterministic)
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
        reply: str,
        cache_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """Calls Gemini API for LLM-as-a-judge scoring with exponential backoff on transient errors."""
        import time

        if cache_key and cache_key in self.cache:
            return self.cache[cache_key]

        # Rate limiting: ensure at least 3.1s between consecutive calls to stay under 20 RPM free tier limit
        elapsed = time.time() - self._last_call_time
        if elapsed < 3.1:
            time.sleep(3.1 - elapsed)

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent?key={self.api_key}"
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

        max_retries = 5
        last_error = ""

        for attempt in range(max_retries):
            try:
                self._last_call_time = time.time()
                resp = requests.post(url, json=payload, timeout=25)
                if resp.status_code == 200:
                    data = resp.json()
                    if "candidates" not in data or not data["candidates"]:
                        raise ValueError(f"No candidates returned: {data}")
                    raw_text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                    # Strip any markdown code fences if present
                    if raw_text.startswith("```"):
                        raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
                        raw_text = re.sub(r"\s*```$", "", raw_text)
                    parsed = json.loads(raw_text)
                    parsed["judge_method"] = f"llm_{self.model_name.replace('.', '_').replace('-', '_')}"
                    parsed["overall"] = round(
                        (float(parsed["relevance"]) + float(parsed["groundedness"]) + float(parsed["tone"]) + float(parsed["escalation"])) / 4.0, 2
                    )
                    if cache_key:
                        self.cache[cache_key] = parsed
                        if self.cache_path:
                            try:
                                with open(self.cache_path, "w", encoding="utf-8") as f:
                                    json.dump(self.cache, f, indent=2)
                            except Exception:
                                pass
                    return parsed
                elif resp.status_code in [429, 503, 500]:
                    wait_time = (2 ** attempt) + 2
                    # Try to parse exact retry-after seconds if given in error message
                    err_msg = resp.text
                    m = re.search(r"retry in ([\d\.]+)s", err_msg)
                    if m:
                        wait_time = max(wait_time, float(m.group(1)) + 1.0)
                    logger.warning(f"Gemini API returned {resp.status_code}. Retrying in {wait_time:.1f}s (attempt {attempt+1}/{max_retries})...")
                    time.sleep(wait_time)
                    last_error = f"HTTP {resp.status_code}: {resp.text}"
                else:
                    last_error = f"HTTP {resp.status_code}: {resp.text}"
                    break
            except Exception as e:
                wait_time = (2 ** attempt) + 2
                logger.warning(f"Request exception: {e}. Retrying in {wait_time}s...")
                time.sleep(wait_time)
                last_error = str(e)

        raise RuntimeError(f"Judge LLM failed after {max_retries} attempts: {last_error}")
