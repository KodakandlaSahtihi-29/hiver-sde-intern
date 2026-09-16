"""Text cleaning and conversation parsing utilities for Twitter customer support threads.
"""

import re
from typing import List, Optional
from src.data.schema import ConversationTurn, SupportConversation


URL_REGEX = re.compile(r"https?://\S+|www\.\S+")
MENTION_REGEX = re.compile(r"@\w+")
MULTIPLE_SPACES = re.compile(r"\s+")

# Observed markers in Twitter customer care threads
DM_KEYWORDS = ["dm", "direct message", "send us a dm", "private message", "pm"]


def normalize_text(text: str) -> str:
    """Normalizes quotes, dashes, and redundant whitespace."""
    if not text:
        return ""
    text = text.replace("\u2019", "'").replace("\u2018", "'")
    text = text.replace("\u201c", '"').replace("\u201d", '"')
    text = text.replace("\u2014", " - ").replace("\u2013", " - ")
    text = MULTIPLE_SPACES.sub(" ", text).strip()
    return text


def clean_for_embedding(text: str) -> str:
    """Removes user handles and raw URLs to focus semantic search on the actual problem."""
    if not text:
        return ""
    # Strip user mentions and URLs
    cleaned = MENTION_REGEX.sub("", text)
    cleaned = URL_REGEX.sub("", cleaned)
    cleaned = MULTIPLE_SPACES.sub(" ", cleaned).strip()
    return cleaned


def extract_turns(conversation_text: str) -> List[ConversationTurn]:
    """Parses raw conversation string into sequential turns."""
    if not conversation_text or not isinstance(conversation_text, str):
        return []

    lines = conversation_text.strip().split("\n")
    turns: List[ConversationTurn] = []
    current_role: Optional[str] = None
    current_lines: List[str] = []

    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            continue

        if line_stripped.startswith("Customer:"):
            if current_role and current_lines:
                turns.append(ConversationTurn(role=current_role, text=normalize_text(" ".join(current_lines))))
            current_role = "customer"
            content = line_stripped[len("Customer:"):].strip()
            current_lines = [content] if content else []
        elif line_stripped.startswith("Support:"):
            if current_role and current_lines:
                turns.append(ConversationTurn(role=current_role, text=normalize_text(" ".join(current_lines))))
            current_role = "support"
            content = line_stripped[len("Support:"):].strip()
            current_lines = [content] if content else []
        else:
            if current_role:
                current_lines.append(line_stripped)

    if current_role and current_lines:
        turns.append(ConversationTurn(role=current_role, text=normalize_text(" ".join(current_lines))))

    return turns


def parse_conversation(
    conversation_id: str,
    company: str,
    conversation_text: str
) -> Optional[SupportConversation]:
    """Extracts a valid customer-support pair from conversation text."""
    turns = extract_turns(conversation_text)
    if not turns:
        return None

    # Identify first customer query and first support reply
    customer_queries = [t.text for t in turns if t.role == "customer" and len(clean_for_embedding(t.text)) >= 10]
    support_replies = [t.text for t in turns if t.role == "support" and len(t.text) >= 10]

    if not customer_queries or not support_replies:
        return None

    customer_query = customer_queries[0]
    support_reply = support_replies[0]

    has_url = bool(URL_REGEX.search(support_reply))
    reply_lower = support_reply.lower()
    has_dm_request = any(dm_kw in reply_lower for dm_kw in DM_KEYWORDS)

    return SupportConversation(
        conversation_id=conversation_id,
        company=company,
        customer_query=customer_query,
        support_reply=support_reply,
        turns=turns,
        num_turns=len(turns),
        has_url=has_url,
        has_dm_request=has_dm_request
    )
