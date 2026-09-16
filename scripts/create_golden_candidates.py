"""Golden Candidate Extraction Script.
Extracts a representative, stratified pool of 220 candidate customer conversations
from the held-out split of @AppleSupport data for human verification into the golden set.
"""

import sys
import json
import logging
from pathlib import Path
from collections import defaultdict

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.data.loader import load_processed_conversations
from src.preprocessing.text_cleaner import clean_for_embedding

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def categorize_preliminary(text: str) -> str:
    """Preliminary heuristic stratification bucket."""
    t = clean_for_embedding(text).lower()
    if any(k in t for k in ["apple id", "icloud", "locked", "password", "verification code", "2fa"]):
        return "Account_Access_Security"
    elif any(k in t for k in ["refund", "charged", "charge", "subscription", "bill", "itunes", "payment"]):
        return "Billing_Subscriptions"
    elif any(k in t for k in ["battery", "drain", "draining", "overheat", "charging"]):
        return "Device_Performance_Battery"
    elif any(k in t for k in ["sim", "wifi", "bluetooth", "cracked", "speaker"]):
        return "Connectivity_Hardware"
    elif any(k in t for k in ["ios", "update", "bug", "freeze", "crash"]):
        return "Software_Bug_OS_Update"
    else:
        return "General_Product_Inquiry"


def create_candidates(
    input_file: str = "data/processed/apple_conversations.jsonl",
    output_file: str = "data/golden/candidates_for_review.jsonl",
    held_out_offset: int = 3500
):
    convs = load_processed_conversations(input_file)
    held_out_pool = convs[held_out_offset:]
    logger.info(f"Held-out pool size: {len(held_out_pool)} conversations.")

    # Target quotas for candidate pool of ~220
    quotas = {
        "Account_Access_Security": 32,
        "Billing_Subscriptions": 32,
        "Device_Performance_Battery": 42,
        "Connectivity_Hardware": 36,
        "Software_Bug_OS_Update": 45,
        "General_Product_Inquiry": 33
    }

    by_bucket = defaultdict(list)
    seen_texts = set()

    for c in held_out_pool:
        clean_text = clean_for_embedding(c.customer_query).strip()
        if len(clean_text.split()) < 5 or clean_text in seen_texts:
            continue

        seen_texts.add(clean_text)
        bucket = categorize_preliminary(c.customer_query)
        if len(by_bucket[bucket]) < quotas.get(bucket, 35):
            by_bucket[bucket].append(c)

    candidates = []
    for bucket, items in by_bucket.items():
        for item in items:
            candidates.append({
                "candidate_id": f"cand_{len(candidates) + 1:03d}",
                "conversation_id": item.conversation_id,
                "customer_message": item.customer_query,
                "historical_reply": item.support_reply,
                "preliminary_bucket": bucket,
                "turns_count": item.num_turns,
                "review_notes": "",
                "verified": False
            })

    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for item in candidates:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    logger.info(f"Generated {len(candidates)} stratified candidate examples saved to {output_file}.")
    for b, items in by_bucket.items():
        logger.info(f"  {b}: {len(items)}")


if __name__ == "__main__":
    create_candidates()
