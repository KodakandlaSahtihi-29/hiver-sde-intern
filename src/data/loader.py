"""Data loading and train/test splitting utilities with strict leakage prevention.
"""

import json
import logging
from pathlib import Path
from typing import List, Tuple, Dict, Any
import pandas as pd

from src.data.schema import SupportConversation, GoldenExample
from src.preprocessing.text_cleaner import parse_conversation

logger = logging.getLogger(__name__)


def load_raw_parquet(file_path: str) -> pd.DataFrame:
    """Loads parquet file into a pandas DataFrame."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    return pd.read_parquet(path)


def process_raw_dataset(df: pd.DataFrame, company_filter: str = "AppleSupport") -> List[SupportConversation]:
    """Filters by brand and parses conversations into structured SupportConversation models."""
    if "company" in df.columns:
        filtered_df = df[df["company"] == company_filter]
    else:
        filtered_df = df

    conversations: List[SupportConversation] = []
    for _, row in filtered_df.iterrows():
        cid = str(row["conversation_id"])
        comp = str(row.get("company", company_filter))
        conv_text = str(row.get("conversation", ""))
        parsed = parse_conversation(cid, comp, conv_text)
        if parsed:
            conversations.append(parsed)

    logger.info(f"Loaded {len(conversations)} valid customer-support pairs from {len(filtered_df)} raw records.")
    return conversations


def save_processed_conversations(conversations: List[SupportConversation], output_file: str) -> None:
    """Saves processed conversations to JSONL."""
    path = Path(output_file)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for c in conversations:
            f.write(c.model_dump_json() + "\n")
    logger.info(f"Saved {len(conversations)} conversations to {output_file}")


def load_processed_conversations(file_path: str) -> List[SupportConversation]:
    """Loads processed conversations from JSONL."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    conversations = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                conversations.append(SupportConversation.model_validate_json(line))
    return conversations


def load_golden_set(file_path: str) -> List[GoldenExample]:
    """Loads the human-verified golden set from JSONL."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Golden set not found: {file_path}")
    examples = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                examples.append(GoldenExample.model_validate_json(line))
    return examples


def split_corpus_prevent_leakage(
    conversations: List[SupportConversation],
    golden_conversation_ids: List[str]
) -> Tuple[List[SupportConversation], List[SupportConversation]]:
    """Splits conversations into retrieval knowledge base and evaluation candidates,
    strictly guaranteeing that NO golden conversation ID exists in the retrieval knowledge base.
    """
    golden_id_set = set(golden_conversation_ids)
    retrieval_corpus: List[SupportConversation] = []
    held_out_pool: List[SupportConversation] = []

    for c in conversations:
        if c.conversation_id in golden_id_set:
            held_out_pool.append(c)
        else:
            retrieval_corpus.append(c)

    return retrieval_corpus, held_out_pool
