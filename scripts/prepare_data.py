"""Data preparation script.
Dynamically calculates dataset statistics, parses multi-turn threads into structured
conversations, and saves the processed dataset without hardcoding counts.
"""

import sys
import logging
from pathlib import Path
import pandas as pd

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.data.loader import process_raw_dataset, save_processed_conversations
from src.preprocessing.text_cleaner import clean_for_embedding

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def main():
    raw_apple_path = Path("data/raw/apple_sample.parquet")
    raw_amazon_path = Path("data/raw/amazon_sample.parquet")
    output_path = Path("data/processed/apple_conversations.jsonl")

    logger.info("=== STEP 1: MEASURING RAW DATASET CHARACTERISTICS ===")
    if not raw_apple_path.exists():
        logger.error(f"Raw Apple dataset not found at {raw_apple_path}")
        sys.exit(1)

    df_apple = pd.read_parquet(raw_apple_path)
    logger.info(f"Loaded Apple raw sample with {len(df_apple)} conversations.")

    if raw_amazon_path.exists():
        df_amazon = pd.read_parquet(raw_amazon_path)
        logger.info(f"Loaded comparative Amazon sample with {len(df_amazon)} conversations.")
    else:
        df_amazon = None

    logger.info("\n=== STEP 2: PROCESSING AND PARSING @AppleSupport CONVERSATIONS ===")
    conversations = process_raw_dataset(df_apple, company_filter="AppleSupport")

    # Measure dynamic conversation metrics
    turn_counts = [c.num_turns for c in conversations]
    customer_query_lens = [len(clean_for_embedding(c.customer_query).split()) for c in conversations]
    has_url_count = sum(1 for c in conversations if c.has_url)
    has_dm_count = sum(1 for c in conversations if c.has_dm_request)

    print("\n" + "=" * 60)
    print("MEASURED DATASET METRICS (DYNAMICALLY COMPUTED):")
    print(f"  Total raw Apple rows:                 {len(df_apple)}")
    print(f"  Valid parsed customer-support pairs:  {len(conversations)}")
    print(f"  Mean conversation turns:             {pd.Series(turn_counts).mean():.2f}")
    print(f"  Median conversation turns:           {pd.Series(turn_counts).median():.1f}")
    print(f"  Mean customer query words:           {pd.Series(customer_query_lens).mean():.2f}")
    print(f"  Support replies containing URLs:     {has_url_count} ({has_url_count / len(conversations) * 100:.1f}%)")
    print(f"  Support replies requesting DM:       {has_dm_count} ({has_dm_count / len(conversations) * 100:.1f}%)")
    print("=" * 60 + "\n")

    logger.info(f"Saving processed dataset to {output_path}...")
    save_processed_conversations(conversations, str(output_path))
    logger.info("Data preparation completed successfully.")


if __name__ == "__main__":
    main()
