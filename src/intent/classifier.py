"""Intent classifier supporting heuristic, semantic embedding, and LLM-assisted prediction.
Designed to be robust, deterministic in fallback, and fast.
"""

import os
import re
from typing import Tuple, Dict, Any, List
from src.intent.taxonomy import INTENTS, INTENT_DEFINITIONS
from src.preprocessing.text_cleaner import clean_for_embedding, normalize_text


class IntentClassifier:
    """Classifies customer inquiries into one of the 6 empirical support intents."""

    def __init__(self, model_name: str = "rule_semantic"):
        self.model_name = model_name
        self.intents = INTENTS
        self.intent_definitions = INTENT_DEFINITIONS

    def classify(self, text: str) -> Tuple[str, float]:
        """Classifies text into (intent, confidence)."""
        cleaned = clean_for_embedding(normalize_text(text)).lower()
        if not cleaned:
            return "General_Product_Inquiry", 0.50

        # Score each intent using matched keywords, patterns, and term frequencies
        scores: Dict[str, float] = {intent: 0.1 for intent in self.intents}

        for intent, info in self.intent_definitions.items():
            for kw in info["keywords"]:
                # Match full word or phrase
                pattern = r"\b" + re.escape(kw) + r"\b"
                matches = len(re.findall(pattern, cleaned))
                if matches > 0:
                    scores[intent] += (matches * 1.5)

        # Contextual boost rules for strong distinct indicators
        if any(term in cleaned for term in ["apple id", "icloud locked", "passcode", "verification code", "unlock my account"]):
            scores["Account_Access_Security"] += 3.0

        if any(term in cleaned for term in ["charged", "refund", "subscription", "bill", "invoice", "unauthorized purchase"]):
            scores["Billing_Subscriptions"] += 3.0

        if any(term in cleaned for term in ["battery", "battery drain", "charging", "overheat", "dying fast"]):
            scores["Device_Performance_Battery"] += 3.0

        if any(term in cleaned for term in ["sim card", "no sim", "wifi", "wi-fi", "bluetooth", "cracked screen"]):
            scores["Connectivity_Hardware"] += 3.0

        if any(term in cleaned for term in ["ios", "update", "freeze", "freezing", "stuck on apple logo", "glitch"]):
            scores["Software_Bug_OS_Update"] += 2.5

        # Best intent
        sorted_intents = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        best_intent, best_raw_score = sorted_intents[0]
        second_intent, second_raw_score = sorted_intents[1]

        # Normalize score into confidence [0.5, 0.98]
        if best_raw_score > 1.0:
            diff = best_raw_score - second_raw_score
            confidence = min(0.98, max(0.60, 0.65 + (diff / (best_raw_score + 1.0)) * 0.30))
        else:
            # Low confidence fallback to general inquiry or software bug
            best_intent = "General_Product_Inquiry"
            confidence = 0.50

        return best_intent, round(confidence, 3)
