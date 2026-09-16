"""Reproducible data sampling script.
Allows sampling a custom subset of conversations for experimentation with fixed random seed.
"""

import sys
import argparse
import logging
from pathlib import Path
import pandas as pd

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.data.loader import process_raw_dataset, save_processed_conversations

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def sample_dataset(input_parquet: str, output_jsonl: str, n_samples: int = 1000, seed: int = 42) -> None:
    raw_path = Path(input_parquet)
    if not raw_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_parquet}")

    df = pd.read_parquet(raw_path)
    logger.info(f"Loaded {len(df)} records from {input_parquet}")

    if n_samples < len(df):
        df_sampled = df.sample(n=n_samples, random_state=seed)
        logger.info(f"Sampled {len(df_sampled)} records with random seed {seed}")
    else:
        df_sampled = df

    conversations = process_raw_dataset(df_sampled, company_filter="AppleSupport")
    save_processed_conversations(conversations, output_jsonl)
    logger.info(f"Saved {len(conversations)} sampled conversations to {output_jsonl}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sample customer support conversations")
    parser.add_argument("--input", type=str, default="data/raw/apple_sample.parquet")
    parser.add_argument("--output", type=str, default="data/processed/apple_conversations_sample.jsonl")
    parser.add_argument("--n", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    sample_dataset(args.input, args.output, args.n, args.seed)
