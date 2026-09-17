import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

with open("results/evaluation_results.jsonl", "r", encoding="utf-8") as f:
    records = [json.loads(line) for line in f]

print("=== Failure Mode 1: Billing Misclassified and Auto-Handled ===")
count = 0
for r in records:
    if r["gold_intent"] == "Billing_Subscriptions" and not r["intent_correct"]:
        print("Example ID:", r["example_id"])
        print("Customer Message:", r["customer_message"][:120])
        print("Gold:", r["gold_intent"], "| Pred:", r["agent_intent"])
        print("Gold Dec:", r["gold_decision"], "| Pred Dec:", r["agent_decision"])
        print("Reply:", r["reply"][:120])
        print("-" * 50)
        count += 1
        if count >= 2: break

print("\n=== Failure Mode 2: Over-Escalation of Safe General Inquiries ===")
count = 0
for r in records:
    if r["gold_decision"] == "AUTO_HANDLE" and r["agent_decision"] == "ESCALATE_TO_HUMAN" and r["gold_intent"] == "General_Product_Inquiry":
        print("Example ID:", r["example_id"])
        print("Customer Message:", r["customer_message"][:120])
        print("Reason:", r["reason"])
        print("-" * 50)
        count += 1
        if count >= 2: break

print("\n=== Failure Mode 3: Connectivity/Hardware Confounded with OS Update ===")
count = 0
for r in records:
    if r["gold_intent"] == "Connectivity_Hardware" and r["agent_intent"] == "Software_Bug_OS_Update":
        print("Example ID:", r["example_id"])
        print("Customer Message:", r["customer_message"][:120])
        print("Gold:", r["gold_intent"], "| Pred:", r["agent_intent"])
        print("-" * 50)
        count += 1
        if count >= 2: break

print("\n=== Failure Mode 4: Account Security False Negative Auto-Handled ===")
count = 0
for r in records:
    if r["gold_intent"] == "Account_Access_Security" and not r["intent_correct"]:
        print("Example ID:", r["example_id"])
        print("Customer Message:", r["customer_message"][:120])
        print("Gold:", r["gold_intent"], "| Pred:", r["agent_intent"])
        print("Decision:", r["agent_decision"])
        print("-" * 50)
        count += 1
        if count >= 2: break

print("\n=== Failure Mode 5: Retrieval Semantic Drift / Low Concordance ===")
count = 0
for r in records:
    if not r["intent_concordance"] and r["intent_correct"]:
        print("Example ID:", r["example_id"])
        print("Customer Message:", r["customer_message"][:120])
        print("Intent:", r["gold_intent"])
        print("Top1 Similarity:", r["top1_similarity"])
        print("-" * 50)
        count += 1
        if count >= 2: break
