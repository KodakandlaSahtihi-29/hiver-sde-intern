"""Unit tests for text preprocessing and conversation parsing.
"""

import pytest
from src.preprocessing.text_cleaner import (
    normalize_text,
    clean_for_embedding,
    extract_turns,
    parse_conversation
)


def test_normalize_text():
    raw = "Here’s a “test” — with   spaces."
    normalized = normalize_text(raw)
    assert normalized == "Here's a \"test\" - with spaces."


def test_clean_for_embedding():
    raw = "@AppleSupport @115858 My iPhone is not charging https://t.co/xyz123"
    cleaned = clean_for_embedding(raw)
    assert "@" not in cleaned
    assert "https://" not in cleaned
    assert "My iPhone is not charging" in cleaned


def test_extract_turns():
    conv_text = (
        "Customer: My screen is frozen.\n"
        "Support: Try doing a hard restart by holding the power button.\n"
        "Customer: That worked, thanks!"
    )
    turns = extract_turns(conv_text)
    assert len(turns) == 3
    assert turns[0].role == "customer"
    assert turns[0].text == "My screen is frozen."
    assert turns[1].role == "support"
    assert "hard restart" in turns[1].text
    assert turns[2].role == "customer"


def test_parse_conversation():
    cid = "test_conv_001"
    company = "AppleSupport"
    conv_text = (
        "Customer: My iPad won't connect to Wi-Fi.\n"
        "Support: We'd love to help. Please DM us your iOS version: https://t.co/GDrqU22YpT"
    )
    parsed = parse_conversation(cid, company, conv_text)
    assert parsed is not None
    assert parsed.conversation_id == cid
    assert parsed.company == company
    assert parsed.has_url is True
    assert parsed.has_dm_request is True
    assert parsed.num_turns == 2
