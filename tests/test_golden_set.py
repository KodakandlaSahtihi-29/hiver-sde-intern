"""Unit tests for the verified golden evaluation set integrity.
"""

from pathlib import Path
from src.data.loader import load_golden_set
from src.intent.taxonomy import INTENTS


def test_golden_set_file_exists_and_size():
    golden_path = Path("data/golden/golden_set.jsonl")
    assert golden_path.exists(), "Golden set file does not exist"

    examples = load_golden_set(str(golden_path))
    assert 150 <= len(examples) <= 250, f"Expected 150-250 examples, got {len(examples)}"
    assert len(examples) == 200, f"Expected exactly 200 examples, got {len(examples)}"


def test_golden_set_schema_and_classes():
    golden_path = Path("data/golden/golden_set.jsonl")
    examples = load_golden_set(str(golden_path))

    intents_seen = set()
    decisions_seen = set()

    for ex in examples:
        assert ex.id.startswith("gold_")
        assert len(ex.customer_message.strip()) > 5
        assert ex.intent in INTENTS
        assert ex.expected_decision in ["AUTO_HANDLE", "ESCALATE_TO_HUMAN"]
        assert ex.human_verified is True
        assert len(ex.review_notes) > 0

        intents_seen.add(ex.intent)
        decisions_seen.add(ex.expected_decision)

    assert len(intents_seen) == len(INTENTS)
    assert decisions_seen == {"AUTO_HANDLE", "ESCALATE_TO_HUMAN"}
