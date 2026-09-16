"""Comprehensive automated evaluation metrics for Intent, Escalation, and Retrieval.
Computes Accuracy, Precision, Recall, Macro-F1, per-intent breakdowns, and confusion matrices.
"""

from typing import List, Dict, Any, Tuple
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    precision_recall_fscore_support,
    confusion_matrix,
    classification_report
)


def compute_classification_metrics(y_true: List[str], y_pred: List[str]) -> Dict[str, Any]:
    """Computes standard multiclass metrics including Macro and Weighted averages."""
    accuracy = accuracy_score(y_true, y_pred)
    macro_p, macro_r, macro_f1, _ = precision_recall_fscore_support(
        y_true, y_pred, average="macro", zero_division=0
    )
    weighted_p, weighted_r, weighted_f1, _ = precision_recall_fscore_support(
        y_true, y_pred, average="weighted", zero_division=0
    )

    return {
        "accuracy": round(float(accuracy), 4),
        "macro_precision": round(float(macro_p), 4),
        "macro_recall": round(float(macro_r), 4),
        "macro_f1": round(float(macro_f1), 4),
        "weighted_f1": round(float(weighted_f1), 4)
    }


def compute_per_intent_metrics(y_true: List[str], y_pred: List[str], labels: List[str]) -> pd.DataFrame:
    """Computes detailed per-intent precision, recall, f1-score, and support."""
    precision, recall, f1, support = precision_recall_fscore_support(
        y_true, y_pred, labels=labels, zero_division=0
    )

    df = pd.DataFrame({
        "intent": labels,
        "precision": [round(float(p), 4) for p in precision],
        "recall": [round(float(r), 4) for r in recall],
        "f1_score": [round(float(f), 4) for f in f1],
        "support": [int(s) for s in support]
    })
    return df


def compute_escalation_metrics(y_true: List[str], y_pred: List[str]) -> Dict[str, Any]:
    """Computes binary escalation metrics focusing on ESCALATE_TO_HUMAN and AUTO_HANDLE."""
    accuracy = accuracy_score(y_true, y_pred)

    # Detailed report for binary classes
    p, r, f1, support = precision_recall_fscore_support(
        y_true, y_pred, labels=["AUTO_HANDLE", "ESCALATE_TO_HUMAN"], zero_division=0
    )

    cm = confusion_matrix(y_true, y_pred, labels=["AUTO_HANDLE", "ESCALATE_TO_HUMAN"])

    return {
        "escalation_accuracy": round(float(accuracy), 4),
        "auto_handle_precision": round(float(p[0]), 4),
        "auto_handle_recall": round(float(r[0]), 4),
        "auto_handle_f1": round(float(f1[0]), 4),
        "escalate_human_precision": round(float(p[1]), 4),
        "escalate_human_recall": round(float(r[1]), 4),
        "escalate_human_f1": round(float(f1[1]), 4),
        "confusion_matrix": cm.tolist()
    }


def compute_retrieval_metrics(
    similarities: List[float],
    intent_matches: List[bool],
    threshold: float = 0.18
) -> Dict[str, Any]:
    """Computes defensible retrieval metrics without fabricated labels."""
    if not similarities:
        return {"mean_top1_similarity": 0.0, "coverage_rate": 0.0, "intent_concordance": 0.0}

    mean_sim = float(pd.Series(similarities).mean())
    median_sim = float(pd.Series(similarities).median())
    coverage = float(sum(s >= threshold for s in similarities) / len(similarities))
    concordance = float(sum(intent_matches) / len(intent_matches)) if intent_matches else 0.0

    return {
        "mean_top1_similarity": round(mean_sim, 4),
        "median_top1_similarity": round(median_sim, 4),
        "coverage_rate_at_threshold": round(coverage, 4),
        "intent_concordance_at_1": round(concordance, 4)
    }
