"""Human Review and Annotation Workflow for Golden Evaluation Set.
Allows reviewing candidate customer queries, confirming proposed labels or editing them,
and compiling only genuinely human-verified records into data/golden/golden_set.jsonl.
"""

import sys
import json
import csv
import argparse
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.intent.taxonomy import INTENTS
from src.preprocessing.text_cleaner import clean_for_embedding

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

VALID_DECISIONS = ["AUTO_HANDLE", "ESCALATE_TO_HUMAN"]


def generate_review_queue(
    candidates_path: str = "data/golden/candidates_for_review.jsonl",
    output_csv: str = "data/golden/review_queue.csv",
    output_jsonl: str = "data/golden/review_queue.jsonl",
    target_count: int = 200
):
    """Generates a transparent review queue with proposed machine labels and BLANK final verification fields."""
    with open(candidates_path, "r", encoding="utf-8") as f:
        candidates = [json.loads(line) for line in f if line.strip()]

    by_bucket = {}
    for c in candidates:
        bucket = c.get("preliminary_bucket", "General_Product_Inquiry")
        by_bucket.setdefault(bucket, []).append(c)

    target_quotas = {
        "Software_Bug_OS_Update": 40,
        "Device_Performance_Battery": 42,
        "Connectivity_Hardware": 32,
        "General_Product_Inquiry": 25,
        "Account_Access_Security": 32,
        "Billing_Subscriptions": 29
    }

    selected_200 = []
    for bucket, count in target_quotas.items():
        items = by_bucket.get(bucket, [])
        selected_200.extend(items[:count])

    if len(selected_200) < target_count:
        remaining = [c for c in candidates if c not in selected_200]
        selected_200.extend(remaining[:target_count - len(selected_200)])

    review_records = []
    for idx, c in enumerate(selected_200):
        raw_text = c["customer_message"]
        clean_text = clean_for_embedding(raw_text).lower()

        proposed_intent = c.get("preliminary_bucket", "General_Product_Inquiry")
        proposed_decision = "AUTO_HANDLE"

        if proposed_intent in ["Account_Access_Security", "Billing_Subscriptions"]:
            proposed_decision = "ESCALATE_TO_HUMAN"
        elif proposed_intent == "Connectivity_Hardware":
            if any(dmg in clean_text for dmg in ["cracked", "broken", "shattered", "water damage", "dropped"]):
                proposed_decision = "ESCALATE_TO_HUMAN"

        record = {
            "example_id": f"gold_{idx + 1:03d}",
            "conversation_id": c["conversation_id"],
            "customer_message": raw_text,
            "historical_reply": c.get("historical_reply", ""),
            "proposed_intent": proposed_intent,
            "proposed_decision": proposed_decision,
            "final_intent": "",        # Kept blank until reviewed
            "final_decision": "",      # Kept blank until reviewed
            "human_verified": False,   # Must be set True by reviewer
            "reviewer_notes": ""       # Empty until reviewer comments
        }
        review_records.append(record)

    csv_path = Path(output_csv)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(review_records[0].keys()))
        writer.writeheader()
        writer.writerows(review_records)

    jsonl_path = Path(output_jsonl)
    with open(jsonl_path, "w", encoding="utf-8") as f:
        for r in review_records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    logger.info(f"Created unverified review queue with {len(review_records)} records at {output_csv}")
    print(f"\n[OK] Review queue created at {output_csv}")
    print("Columns: example_id, conversation_id, customer_message, historical_reply, proposed_intent, proposed_decision, final_intent, final_decision, human_verified, reviewer_notes")
    print("Open the CSV in Excel / VS Code, review the records, fill in final_intent, final_decision, and set human_verified to True.")
    return review_records


def import_reviewed_csv(
    csv_path: str = "data/golden/review_queue.csv",
    output_golden_path: str = "data/golden/golden_set.jsonl"
) -> int:
    """Reads the reviewed CSV file and exports ONLY genuinely verified rows to golden_set.jsonl."""
    p = Path(csv_path)
    if not p.exists():
        logger.error(f"Review CSV not found: {csv_path}")
        return 0

    verified_records = []
    with open(p, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader):
            verified_flag = str(row.get("human_verified", "")).strip().lower() in ["true", "1", "yes"]
            f_intent = str(row.get("final_intent", "")).strip()
            f_decision = str(row.get("final_decision", "")).strip()

            intent_lookup = {k.lower(): k for k in INTENTS}
            f_intent_norm = intent_lookup.get(f_intent.lower(), f_intent)
            f_decision_norm = f_decision.upper()

            if verified_flag:
                if not f_intent or not f_decision:
                    logger.warning(f"Row {idx+1} ({row.get('example_id')}) marked verified but final_intent or final_decision is blank.")
                    continue
                if f_intent_norm not in INTENTS:
                    logger.warning(f"Row {idx+1} ({row.get('example_id')}) has invalid intent: '{f_intent}'. Valid options: {INTENTS}")
                    continue
                if f_decision_norm not in VALID_DECISIONS:
                    logger.warning(f"Row {idx+1} ({row.get('example_id')}) has invalid decision: '{f_decision}'. Valid: {VALID_DECISIONS}")
                    continue

                verified_records.append({
                    "id": row.get("example_id", f"gold_{len(verified_records)+1:03d}"),
                    "conversation_id": row["conversation_id"],
                    "customer_message": row["customer_message"],
                    "historical_reply": row.get("historical_reply", ""),
                    "proposed_intent": row.get("proposed_intent", ""),
                    "proposed_decision": row.get("proposed_decision", ""),
                    "intent": f_intent_norm,
                    "expected_decision": f_decision_norm,
                    "reviewer_notes": row.get("reviewer_notes", ""),
                    "human_verified": True
                })

    n = len(verified_records)
    print(f"\nVerified records found in CSV: {n} / 200")

    if n < 150:
        logger.error(f"Cannot build golden set: Only {n} records verified. Hiver requires 150-250 hand-labelled examples.")
        print("Please complete reviewing at least 150 records in the CSV before compiling.")
        return n

    out_p = Path(output_golden_path)
    with open(out_p, "w", encoding="utf-8") as f:
        for item in verified_records:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    logger.info(f"Successfully compiled {n} human-verified golden examples to {output_golden_path}")
    print(f"[SUCCESS] Exported {n} verified records to {output_golden_path}")
    return n


def interactive_review(
    csv_path: str = "data/golden/review_queue.csv",
    output_golden_path: str = "data/golden/golden_set.jsonl"
):
    """Terminal-based interactive review tool to quickly inspect and confirm records."""
    p = Path(csv_path)
    if not p.exists():
        generate_review_queue()

    with open(p, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    print("\n" + "=" * 70)
    print("INTERACTIVE GOLDEN SET REVIEW TOOL")
    print("Instructions:")
    print("  [Enter]         : Accept machine-proposed intent and decision")
    print("  [i <1-6>]       : Change intent (1:Account, 2:Billing, 3:Battery, 4:Hardware, 5:Bug, 6:General)")
    print("  [d <1-2>]       : Change decision (1:AUTO_HANDLE, 2:ESCALATE_TO_HUMAN)")
    print("  [s]             : Skip row")
    print("  [q]             : Save and Quit")
    print("=" * 70 + "\n")

    intent_map = {
        "1": "Account_Access_Security",
        "2": "Billing_Subscriptions",
        "3": "Device_Performance_Battery",
        "4": "Connectivity_Hardware",
        "5": "Software_Bug_OS_Update",
        "6": "General_Product_Inquiry"
    }

    for idx, r in enumerate(rows):
        if r.get("human_verified") == "True" and r.get("final_intent"):
            continue

        print(f"\n--- Record {idx+1}/{len(rows)} [{r['example_id']}] ---")
        print(f"Customer:  {r['customer_message']}")
        print(f"Proposed:  Intent={r['proposed_intent']} | Decision={r['proposed_decision']}")

        choice = input("Accept [Enter] or modify: ").strip().lower()
        if choice == "q":
            break
        elif choice == "s":
            continue
        elif choice == "":
            r["final_intent"] = r["proposed_intent"]
            r["final_decision"] = r["proposed_decision"]
            r["human_verified"] = "True"
        else:
            # Parse modifications e.g. i 1 or d 2
            # Accept defaults if not specified
            final_i = r["proposed_intent"]
            final_d = r["proposed_decision"]
            parts = choice.split()
            for i, part in enumerate(parts):
                if part == "i" and i + 1 < len(parts) and parts[i+1] in intent_map:
                    final_i = intent_map[parts[i+1]]
                elif part == "d" and i + 1 < len(parts):
                    final_d = "AUTO_HANDLE" if parts[i+1] == "1" else "ESCALATE_TO_HUMAN"
            r["final_intent"] = final_i
            r["final_decision"] = final_d
            r["human_verified"] = "True"

    # Write back to CSV
    with open(p, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nProgress saved to {csv_path}.")
    import_reviewed_csv(csv_path, output_golden_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Golden Set Human Review Tool")
    parser.add_argument("--generate-queue", action="store_true", help="Generate/reset review queue CSV with blank final fields")
    parser.add_argument("--interactive", action="store_true", help="Launch interactive CLI review tool")
    parser.add_argument("--import-csv", type=str, default="data/golden/review_queue.csv", help="Import reviewed CSV into golden_set.jsonl")
    args = parser.parse_args()

    if args.generate_queue:
        generate_review_queue()
    elif args.interactive:
        interactive_review()
    else:
        import_reviewed_csv(args.import_csv)
