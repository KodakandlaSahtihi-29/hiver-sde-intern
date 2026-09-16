import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.data.loader import load_processed_conversations
from src.preprocessing.text_cleaner import clean_for_embedding

convs = load_processed_conversations("data/processed/apple_conversations.jsonl")
held_out = convs[3500:]

counts = {"Account": 0, "Billing": 0, "Battery": 0, "Bug": 0, "Connectivity": 0, "General": 0}
for c in held_out:
    t = clean_for_embedding(c.customer_query).lower()
    if any(k in t for k in ["apple id", "icloud", "locked", "password", "verification code", "2fa"]):
        counts["Account"] += 1
    elif any(k in t for k in ["refund", "charged", "charge", "subscription", "bill", "itunes", "payment"]):
        counts["Billing"] += 1
    elif any(k in t for k in ["battery", "drain", "draining", "overheat", "charging"]):
        counts["Battery"] += 1
    elif any(k in t for k in ["sim", "wifi", "bluetooth", "cracked", "speaker"]):
        counts["Connectivity"] += 1
    elif any(k in t for k in ["ios", "update", "bug", "freeze", "crash"]):
        counts["Bug"] += 1
    else:
        counts["General"] += 1

print("Available in 1,453 held-out conversations:")
for k, v in counts.items():
    print(f"  {k}: {v}")
