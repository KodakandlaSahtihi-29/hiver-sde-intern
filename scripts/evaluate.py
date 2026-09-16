"""Full Evaluation Harness for Hiver AI Customer Support System.
Runs Baseline 1 (Majority Class), Baseline 2 (TF-IDF + Logistic Regression),
and the proposed AI Support Agent against the 200-sample human-verified Golden Set.
Computes real, empirically measured metrics and outputs results to results/metrics.csv.
"""

import sys
import json
import logging
from pathlib import Path
from collections import Counter
import pandas as pd

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.data.loader import load_processed_conversations, load_golden_set
from src.retrieval.vector_store import HistoricalVectorStore
from src.pipeline import SupportAgent
from src.evaluation.baselines import MajorityClassBaseline, TfidfLogisticBaseline
from src.evaluation.metrics import (
    compute_classification_metrics,
    compute_per_intent_metrics,
    compute_escalation_metrics,
    compute_retrieval_metrics
)
from src.evaluation.judge import ReplyJudge
from src.intent.taxonomy import INTENTS
from src.preprocessing.text_cleaner import clean_for_embedding

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def run_evaluation(
    corpus_path: str = "data/processed/apple_conversations.jsonl",
    golden_path: str = "data/golden/golden_set.jsonl",
    results_dir: str = "results",
    train_offset: int = 3500
):
    results_path = Path(results_dir)
    results_path.mkdir(parents=True, exist_ok=True)

    logger.info("=== STEP 1: LOADING DATASETS & BUILDING LEAK-FREE RETRIEVAL INDEX ===")
    corpus = load_processed_conversations(corpus_path)
    golden_set = load_golden_set(golden_path)

    # Strictly reserve the first train_offset conversations for training/retrieval
    train_corpus = corpus[:train_offset]
    golden_cids = {ex.conversation_id for ex in golden_set}

    # Build retrieval vector store excluding any golden conversation
    vector_store = HistoricalVectorStore()
    vector_store.build_index(train_corpus, exclude_ids=golden_cids)

    # Initialize AI Agent
    agent = SupportAgent(vector_store=vector_store)
    judge = ReplyJudge()

    logger.info("=== STEP 2: TRAINING BASELINE MODELS ON RETRIEVAL CORPUS ===")
    # Generate heuristic labels for training corpus for baseline training
    train_texts = [c.customer_query for c in train_corpus if c.conversation_id not in golden_cids]
    train_intents = []
    train_decisions = []

    for text in train_texts:
        intent, conf = agent.intent_classifier.classify(text)
        train_intents.append(intent)
        if intent in ["Account_Access_Security", "Billing_Subscriptions"]:
            train_decisions.append("ESCALATE_TO_HUMAN")
        else:
            train_decisions.append("AUTO_HANDLE")

    # Train Baseline 1: Majority Class
    baseline1 = MajorityClassBaseline()
    baseline1.fit(train_texts, train_intents, train_decisions)
    logger.info(f"Baseline 1 majority intent: {baseline1.majority_intent}, majority decision: {baseline1.majority_decision}")

    # Train Baseline 2: TF-IDF + Logistic Regression
    baseline2 = TfidfLogisticBaseline(max_features=5000)
    baseline2.fit(train_texts, train_intents, train_decisions)
    logger.info("Baseline 2 (TF-IDF + Logistic Regression) fitted successfully.")

    logger.info(f"=== STEP 3: RUNNING EVALUATION ON {len(golden_set)} GOLDEN EXAMPLES ===")
    golden_texts = [ex.customer_message for ex in golden_set]
    gold_intents = [ex.intent for ex in golden_set]
    gold_decisions = [ex.expected_decision for ex in golden_set]

    # 1. Predictions from Baseline 1
    b1_pred_intents = baseline1.predict_intent(golden_texts)
    b1_pred_decisions = baseline1.predict_decision(golden_texts)

    # 2. Predictions from Baseline 2
    b2_pred_intents = baseline2.predict_intent(golden_texts)
    b2_pred_decisions = baseline2.predict_decision(golden_texts)

    # 3. Predictions from AI Agent
    agent_pred_intents = []
    agent_pred_decisions = []
    agent_replies = []
    agent_reasons = []
    agent_top1_sims = []
    agent_intent_matches = []
    judge_scores = []
    full_eval_records = []

    for idx, ex in enumerate(golden_set):
        pred = agent.process_message(ex.customer_message)
        agent_pred_intents.append(pred.intent)
        agent_pred_decisions.append(pred.decision)
        agent_replies.append(pred.reply)
        agent_reasons.append(pred.reason)

        top1_sim = pred.evidence[0]["similarity_score"] if pred.evidence else 0.0
        agent_top1_sims.append(top1_sim)

        # Retrieval concordance: did top retrieved historical query have matching intent?
        intent_match = False
        if pred.evidence:
            ev_intent, _ = agent.intent_classifier.classify(pred.evidence[0]["historical_query"])
            intent_match = (ev_intent == ex.intent)
        agent_intent_matches.append(intent_match)

        # Quality scoring using judge rubric
        j_score = judge.evaluate_reply(
            customer_message=ex.customer_message,
            intent=pred.intent,
            decision=pred.decision,
            reason=pred.reason,
            reply=pred.reply,
            expected_decision=ex.expected_decision
        )
        judge_scores.append(j_score)

        record = {
            "example_id": ex.id,
            "conversation_id": ex.conversation_id,
            "customer_message": ex.customer_message,
            "gold_intent": ex.intent,
            "agent_intent": pred.intent,
            "intent_correct": (pred.intent == ex.intent),
            "gold_decision": ex.expected_decision,
            "agent_decision": pred.decision,
            "decision_correct": (pred.decision == ex.expected_decision),
            "confidence": pred.intent_confidence,
            "reason": pred.reason,
            "reply": pred.reply,
            "top1_similarity": top1_sim,
            "intent_concordance": intent_match,
            "judge_relevance": j_score["relevance"],
            "judge_groundedness": j_score["groundedness"],
            "judge_tone": j_score["tone"],
            "judge_escalation": j_score["escalation"],
            "judge_overall": j_score["overall"],
            "judge_rationale": j_score.get("rationale", "")
        }
        full_eval_records.append(record)

    logger.info("=== STEP 4: COMPUTING METRICS ACROSS ALL THREE SYSTEMS ===")

    # Baseline 1 metrics
    b1_intent_m = compute_classification_metrics(gold_intents, b1_pred_intents)
    b1_esc_m = compute_escalation_metrics(gold_decisions, b1_pred_decisions)

    # Baseline 2 metrics
    b2_intent_m = compute_classification_metrics(gold_intents, b2_pred_intents)
    b2_esc_m = compute_escalation_metrics(gold_decisions, b2_pred_decisions)

    # AI Agent metrics
    agent_intent_m = compute_classification_metrics(gold_intents, agent_pred_intents)
    agent_esc_m = compute_escalation_metrics(gold_decisions, agent_pred_decisions)
    retrieval_m = compute_retrieval_metrics(agent_top1_sims, agent_intent_matches)

    # Aggregate judge scores
    avg_judge_rel = round(pd.Series([j["relevance"] for j in judge_scores]).mean(), 2)
    avg_judge_grd = round(pd.Series([j["groundedness"] for j in judge_scores]).mean(), 2)
    avg_judge_ton = round(pd.Series([j["tone"] for j in judge_scores]).mean(), 2)
    avg_judge_esc = round(pd.Series([j["escalation"] for j in judge_scores]).mean(), 2)
    avg_judge_ovr = round(pd.Series([j["overall"] for j in judge_scores]).mean(), 2)

    # Construct Metrics Comparison Table
    metrics_summary = [
        {
            "Model": "Baseline 1 (Majority Class)",
            "Intent Accuracy": b1_intent_m["accuracy"],
            "Intent Macro F1": b1_intent_m["macro_f1"],
            "Intent Weighted F1": b1_intent_m["weighted_f1"],
            "Escalation Accuracy": b1_esc_m["escalation_accuracy"],
            "Escalate Recall (Human)": b1_esc_m["escalate_human_recall"],
            "Auto-Handle F1": b1_esc_m["auto_handle_f1"],
            "Retrieval Concordance": "N/A",
            "Avg Judge Score": "N/A"
        },
        {
            "Model": "Baseline 2 (TF-IDF + Logistic Reg)",
            "Intent Accuracy": b2_intent_m["accuracy"],
            "Intent Macro F1": b2_intent_m["macro_f1"],
            "Intent Weighted F1": b2_intent_m["weighted_f1"],
            "Escalation Accuracy": b2_esc_m["escalation_accuracy"],
            "Escalate Recall (Human)": b2_esc_m["escalate_human_recall"],
            "Auto-Handle F1": b2_esc_m["auto_handle_f1"],
            "Retrieval Concordance": "N/A",
            "Avg Judge Score": "N/A"
        },
        {
            "Model": "Proposed AI Support Agent",
            "Intent Accuracy": agent_intent_m["accuracy"],
            "Intent Macro F1": agent_intent_m["macro_f1"],
            "Intent Weighted F1": agent_intent_m["weighted_f1"],
            "Escalation Accuracy": agent_esc_m["escalation_accuracy"],
            "Escalate Recall (Human)": agent_esc_m["escalate_human_recall"],
            "Auto-Handle F1": agent_esc_m["auto_handle_f1"],
            "Retrieval Concordance": retrieval_m["intent_concordance_at_1"],
            "Avg Judge Score": avg_judge_ovr
        }
    ]

    metrics_df = pd.DataFrame(metrics_summary)
    metrics_csv_path = results_path / "metrics.csv"
    metrics_df.to_csv(metrics_csv_path, index=False)
    logger.info(f"Saved headline metrics comparison to {metrics_csv_path}")

    # Per-intent breakdown table
    per_intent_df = compute_per_intent_metrics(gold_intents, agent_pred_intents, labels=INTENTS)
    per_intent_csv_path = results_path / "per_intent_metrics.csv"
    per_intent_df.to_csv(per_intent_csv_path, index=False)
    logger.info(f"Saved per-intent breakdown to {per_intent_csv_path}")

    # Save detailed evaluation records JSONL
    eval_jsonl_path = results_path / "evaluation_results.jsonl"
    with open(eval_jsonl_path, "w", encoding="utf-8") as f:
        for r in full_eval_records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    logger.info(f"Saved full evaluation records to {eval_jsonl_path}")

    # Display printed report
    print("\n" + "=" * 80)
    print("EXPERIMENTAL EVALUATION RESULTS (MEASURED, ZERO FABRICATION):")
    print("=" * 80)
    print(metrics_df.to_string(index=False))

    print("\n" + "-" * 80)
    print("PER-INTENT PERFORMANCE BREAKDOWN (PROPOSED AI AGENT):")
    print("-" * 80)
    print(per_intent_df.to_string(index=False))

    print("\n" + "-" * 80)
    print("RETRIEVAL PERFORMANCE (DEFENSIBLE METRICS):")
    print("-" * 80)
    print(f"  Mean Top-1 Cosine Similarity:       {retrieval_m['mean_top1_similarity']:.4f}")
    print(f"  Median Top-1 Cosine Similarity:     {retrieval_m['median_top1_similarity']:.4f}")
    print(f"  Evidence Coverage (sim >= 0.18):    {retrieval_m['coverage_rate_at_threshold']*100:.1f}%")
    print(f"  Intent Concordance @ 1:             {retrieval_m['intent_concordance_at_1']*100:.1f}%")

    print("\n" + "-" * 80)
    print("LLM-AS-A-JUDGE QUALITY RUBRIC (1-5 SCALE):")
    print("-" * 80)
    print(f"  Relevance:                          {avg_judge_rel:.2f} / 5.0")
    print(f"  Groundedness:                       {avg_judge_grd:.2f} / 5.0")
    print(f"  Tone & Empathy:                     {avg_judge_ton:.2f} / 5.0")
    print(f"  Escalation Appropriateness:         {avg_judge_esc:.2f} / 5.0")
    print(f"  Overall Score:                      {avg_judge_ovr:.2f} / 5.0")
    print("=" * 80 + "\n")

    return metrics_df, per_intent_df, full_eval_records


if __name__ == "__main__":
    run_evaluation()
