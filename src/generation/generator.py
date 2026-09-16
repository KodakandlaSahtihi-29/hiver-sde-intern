"""Grounded support reply generator.
Employs strict grounding in retrieved historical resolutions, anti-hallucination guardrails,
and configurable LLM provider integration with deterministic fallback.
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional
import requests

from src.data.schema import RetrievedEvidence
from src.preprocessing.text_cleaner import clean_for_embedding

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """You are an AI customer support specialist for Apple Support.
Your role is to draft helpful, courteous, and accurate responses grounded STRICTLY in historical Apple support resolutions.

CRITICAL INSTRUCTIONS:
1. Grounding: Rely ONLY on the provided historical support examples.
2. Anti-Hallucination: Do NOT invent policies, fake URLs, unannounced product release dates, or refund guarantees.
3. Tone: Be professional, empathetic, concise, and helpful.
4. Escalation: If the issue involves account security (Apple ID lock, 2FA), billing/refund dispute, or physical damage, acknowledge the issue and state clearly that an authorized human specialist or secure portal must verify the account.
"""


class GroundedReplyGenerator:
    """Generates grounded customer support replies using retrieved historical evidence."""

    def __init__(self, provider: Optional[str] = None):
        self.provider = provider or os.getenv("LLM_PROVIDER", "grounded_synthesis")
        self.api_key = os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY")

    def generate(
        self,
        customer_message: str,
        intent: str,
        evidence: List[RetrievedEvidence],
        decision: str,
        reason: str
    ) -> str:
        """Generates a grounded response based on customer query, intent, evidence, and escalation decision."""
        # 1. If external LLM API key is present and configured, use it
        if self.api_key and self.provider in ["gemini", "openai"]:
            try:
                return self._call_llm_api(customer_message, intent, evidence, decision, reason)
            except Exception as e:
                logger.warning(f"LLM API call failed ({e}), falling back to deterministic grounded synthesis.")

        # 2. Grounded deterministic synthesis (always available, reproducible, zero hallucination)
        return self._synthesize_grounded_reply(customer_message, intent, evidence, decision, reason)

    def _synthesize_grounded_reply(
        self,
        customer_message: str,
        intent: str,
        evidence: List[RetrievedEvidence],
        decision: str,
        reason: str
    ) -> str:
        """Grounded synthesis using historical resolution templates from AppleSupport evidence."""
        # Escalation responses
        if decision == "ESCALATE_TO_HUMAN":
            if intent == "Account_Access_Security":
                return (
                    "We understand this Apple ID / account security issue is urgent. Because account and identity verification "
                    "involves sensitive personal data, our automated system cannot modify account credentials. "
                    "Please follow the secure recovery steps at https://iforgot.apple.com or contact an Apple Support specialist directly."
                )
            elif intent == "Billing_Subscriptions":
                return (
                    "We understand you have a question regarding billing or charges. To protect your financial information, "
                    "account-specific purchase disputes and refund requests must be verified through reportaproblem.apple.com "
                    "or by speaking with an authorized support advisor."
                )
            elif intent == "Connectivity_Hardware":
                return (
                    "We'd like to help with your device hardware. Because this issue may require physical inspection or repair diagnostics, "
                    "we recommend scheduling an appointment at an Apple Authorized Service Provider or contacting our technical support team."
                )
            else:
                return (
                    "We want to make sure you receive the exact assistance you need. Because your inquiry requires specific verification, "
                    "we are connecting you to an Apple Support specialist who can look into this further."
                )

        # Auto-Handle responses grounded in historical evidence
        if evidence and evidence[0].similarity_score >= 0.15:
            top_evidence = evidence[0]
            hist_reply = top_evidence.historical_reply

            # If historical reply has clean troubleshooting guidance, adapt it
            clean_reply = hist_reply
            # Strip initial Twitter handles from historical template
            if clean_reply.startswith("@"):
                parts = clean_reply.split(" ", 1)
                clean_reply = parts[1] if len(parts) > 1 else clean_reply

            if intent == "Device_Performance_Battery":
                return f"We're here to help optimize your battery performance. Based on standard diagnostic procedures: {clean_reply}"
            elif intent == "Software_Bug_OS_Update":
                return f"We'd love to help resolve this software issue. Recommended steps: {clean_reply}"
            elif intent == "Connectivity_Hardware":
                return f"We'd like to help restore your connection. Recommended steps: {clean_reply}"
            elif intent == "General_Product_Inquiry":
                return f"Thank you for reaching out! Information regarding your inquiry: {clean_reply}"
            else:
                return clean_reply

        # Fallback for general inquiries
        return (
            "Thanks for reaching out to Apple Support. We'd like to look into this with you. "
            "Please ensure your device is running the latest software version and restart your device to see if the issue persists."
        )

    def _call_llm_api(
        self,
        customer_message: str,
        intent: str,
        evidence: List[RetrievedEvidence],
        decision: str,
        reason: str
    ) -> str:
        """Optional API caller if external credentials provided."""
        evidence_text = "\n".join([
            f"- Historical Query: {e.historical_query}\n  Historical Resolution: {e.historical_reply}"
            for e in evidence[:3]
        ])

        prompt = f"""Customer Message: "{customer_message}"
Classified Intent: {intent}
Escalation Decision: {decision} (Reason: {reason})

Retrieved Historical Evidence:
{evidence_text}

Draft a grounded Apple Support reply adhering to the system instructions:"""

        # Gemini API call example if configured
        if self.provider == "gemini" and self.api_key:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.api_key}"
            payload = {
                "contents": [{"parts": [{"text": SYSTEM_PROMPT + "\n\n" + prompt}]}]
            }
            resp = requests.post(url, json=payload, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                return data["candidates"][0]["content"]["parts"][0]["text"].strip()

        raise RuntimeError("Configured LLM provider returned no valid completion.")
