"""Baseline models for comparative benchmarking against the proposed AI Support Agent.
Baseline 1: Trivial Majority-Class Predictor.
Baseline 2: Simple TF-IDF + Logistic Regression Classifier.
"""

from typing import List, Dict, Any, Tuple
import numpy as np
from collections import Counter
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

from src.preprocessing.text_cleaner import clean_for_embedding


class MajorityClassBaseline:
    """Trivial Baseline: Predicts the most frequent intent and escalation decision in training data."""

    def __init__(self):
        self.majority_intent: str = "General_Product_Inquiry"
        self.majority_decision: str = "AUTO_HANDLE"

    def fit(self, texts: List[str], intents: List[str], decisions: List[str]) -> None:
        if intents:
            self.majority_intent = Counter(intents).most_common(1)[0][0]
        if decisions:
            self.majority_decision = Counter(decisions).most_common(1)[0][0]

    def predict_intent(self, texts: List[str]) -> List[str]:
        return [self.majority_intent for _ in texts]

    def predict_decision(self, texts: List[str]) -> List[str]:
        return [self.majority_decision for _ in texts]


class TfidfLogisticBaseline:
    """Simple ML Baseline: TF-IDF feature extraction with Logistic Regression."""

    def __init__(self, max_features: int = 5000):
        self.vectorizer = TfidfVectorizer(max_features=max_features, stop_words="english")
        self.intent_clf = LogisticRegression(max_iter=1000, random_state=42)
        self.decision_clf = LogisticRegression(max_iter=1000, random_state=42)
        self.is_fitted = False

    def fit(self, texts: List[str], intents: List[str], decisions: List[str]) -> None:
        cleaned_texts = [clean_for_embedding(t) for t in texts]
        X = self.vectorizer.fit_transform(cleaned_texts)
        self.intent_clf.fit(X, intents)
        self.decision_clf.fit(X, decisions)
        self.is_fitted = True

    def predict_intent(self, texts: List[str]) -> List[str]:
        if not self.is_fitted:
            raise RuntimeError("Model is not fitted. Call fit() first.")
        cleaned_texts = [clean_for_embedding(t) for t in texts]
        X = self.vectorizer.transform(cleaned_texts)
        return list(self.intent_clf.predict(X))

    def predict_decision(self, texts: List[str]) -> List[str]:
        if not self.is_fitted:
            raise RuntimeError("Model is not fitted. Call fit() first.")
        cleaned_texts = [clean_for_embedding(t) for t in texts]
        X = self.vectorizer.transform(cleaned_texts)
        return list(self.decision_clf.predict(X))
