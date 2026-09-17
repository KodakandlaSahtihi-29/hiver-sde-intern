"""Golden Evaluation Set Validator.
Enforces strict schema validation, sample size boundaries (150-250), category representation,
and cryptographic/ID leak detection against the retrieval training corpus.
"""

import sys
import json
import logging
from pathlib import Path
from collections import Counter

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.data.loader import load_processed_conversations, load_golden_set
from src.intent.taxonomy import INTENTS
from src.preprocessing.text_cleaner import clean_for_embedding

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def validate_golden_set(
    golden_path: str = "data/golden/golden_set.jsonl",
    corpus_path: str = "data/processed/apple_conversations.jsonl",
    train_offset: int = 3500
) -> bool:
    print("\n" + "=" * 60)
    print("RUNNING GOLDEN EVALUATION SET VALIDATION")
    print("=" * 60)

    # 1. Existence and count check
    golden_file = Path(golden_path)
    if not golden_file.exists():
        logger.error(f"Golden set file missing: {golden_path}")
        return False

    golden_examples = load_golden_set(golden_path)
    n = len(golden_examples)
    logger.info(f"Loaded {n} golden examples.")

    if not (150 <= n <= 250):
        logger.error(f"Sample size {n} outside required range [150, 250].")
        return False
    print(f"[PASS] Sample Size Check: {n} examples (within required 150-250 range).")

    # 2. Schema and fields check
    valid_decisions = {"AUTO_HANDLE", "ESCALATE_TO_HUMAN"}
    intents_seen = set()
    decisions_seen = set()
    seen_ids = set()
    seen_cids = set()

    for idx, ex in enumerate(golden_examples):
        if not ex.id or not ex.conversation_id:
            logger.error(f"Row {idx} missing ID or conversation_id.")
            return False
        if ex.id in seen_ids:
            logger.error(f"Duplicate example ID detected in golden set: {ex.id}")
            return False
        if ex.conversation_id in seen_cids:
            logger.error(f"Duplicate conversation ID detected in golden set: {ex.conversation_id}")
            return False
        seen_ids.add(ex.id)
        seen_cids.add(ex.conversation_id)

        if len(ex.customer_message.strip()) < 10:
            logger.error(f"Row {idx} customer message too short.")
            return False
        if not ex.intent or ex.intent not in INTENTS:
            logger.error(f"Row {idx} has invalid or unpopulated intent: '{ex.intent}'")
            return False
        if not ex.expected_decision or ex.expected_decision not in valid_decisions:
            logger.error(f"Row {idx} has invalid or unpopulated decision: '{ex.expected_decision}'")
            return False
        if not ex.human_verified:
            logger.error(f"Row {idx} ({ex.id}) is not marked human_verified=True.")
            return False

        intents_seen.add(ex.intent)
        decisions_seen.add(ex.expected_decision)

    print(f"[PASS] Schema Integrity & Uniqueness: All {n} records unique, typed, and human-verified.")

    # 3. Intent Coverage Check
    missing_intents = set(INTENTS) - intents_seen
    if missing_intents:
        logger.error(f"Missing intents in golden set: {missing_intents}")
        return False
    print(f"[PASS] Category Coverage: All {len(INTENTS)} empirical intents represented.")

    # 4. Decision Coverage Check
    if len(decisions_seen) != 2:
        logger.error("Golden set does not cover both AUTO_HANDLE and ESCALATE_TO_HUMAN.")
        return False
    print("[PASS] Decision Coverage: Both AUTO_HANDLE and ESCALATE_TO_HUMAN represented.")

    # 5. Data Leakage Check against Training Retrieval Corpus
    corpus = load_processed_conversations(corpus_path)
    train_corpus = corpus[:train_offset]
    train_cids = {c.conversation_id for c in train_corpus}
    train_texts = {clean_for_embedding(c.customer_query).strip() for c in train_corpus}

    golden_cids = {ex.conversation_id for ex in golden_examples}
    cid_leaks = golden_cids.intersection(train_cids)

    golden_texts = {clean_for_embedding(ex.customer_message).strip() for ex in golden_examples}
    text_leaks = golden_texts.intersection(train_texts)

    if cid_leaks:
        logger.error(f"DATA LEAKAGE DETECTED: {len(cid_leaks)} conversation IDs overlap with training corpus!")
        return False

    if text_leaks:
        logger.error(f"DATA LEAKAGE DETECTED: {len(text_leaks)} query texts overlap with training corpus!")
        return False

    print(f"[PASS] Leakage Prevention: 0 / {n} golden IDs or texts exist in the {len(train_corpus)} retrieval corpus.")

    intent_dist = Counter(ex.intent for ex in golden_examples)
    decision_dist = Counter(ex.expected_decision for ex in golden_examples)

    print("\nValidated Distribution:")
    for intent, cnt in intent_dist.items():
        print(f"  - {intent:28s}: {cnt:3d} ({cnt/n*100:5.1f}%)")
    print("Decisions:")
    for dec, cnt in decision_dist.items():
        print(f"  - {dec:28s}: {cnt:3d} ({cnt/n*100:5.1f}%)")

    print("=" * 60)
    print("GOLDEN SET VALIDATION PASSED COMPLETELY.")
    print("=" * 60 + "\n")
    return True


if __name__ == "__main__":
    success = validate_golden_set()
    sys.exit(0 if success else 1)
