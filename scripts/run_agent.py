"""CLI and Interactive Runner for the @AppleSupport AI Agent.
Allows querying the agent from the terminal or entering an interactive customer session.
"""

import sys
import json
import argparse
import logging
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.data.loader import load_processed_conversations, load_golden_set
from src.retrieval.vector_store import HistoricalVectorStore
from src.pipeline import SupportAgent

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def setup_agent(corpus_path: str = "data/processed/apple_conversations.jsonl", golden_path: str = "data/golden/golden_set.jsonl") -> SupportAgent:
    """Initializes vector store and agent with strict exclusion of golden set IDs."""
    logger.info("Initializing knowledge corpus and vector index...")
    corpus = load_processed_conversations(corpus_path)

    exclude_ids = set()
    golden_file = Path(golden_path)
    if golden_file.exists():
        golden_exs = load_golden_set(golden_path)
        exclude_ids = {ex.conversation_id for ex in golden_exs}

    # Use first 3500 training conversations
    train_corpus = corpus[:3500]

    vector_store = HistoricalVectorStore()
    vector_store.build_index(train_corpus, exclude_ids=exclude_ids)

    agent = SupportAgent(vector_store=vector_store)
    return agent


def format_agent_output(result) -> str:
    """Pretty prints the structured agent output."""
    output = {
        "intent": result.intent,
        "intent_confidence": result.intent_confidence,
        "reply": result.reply,
        "decision": result.decision,
        "reason": result.reason,
        "evidence_sufficiency": result.evidence_sufficiency,
        "evidence": result.evidence
    }
    return json.dumps(output, indent=2, ensure_ascii=False)


def main():
    parser = argparse.ArgumentParser(description="Run the @AppleSupport AI Agent")
    parser.add_argument("--query", type=str, help="Customer inquiry string")
    parser.add_argument("--interactive", action="store_true", help="Launch interactive support session")
    args = parser.parse_args()

    agent = setup_agent()

    if args.query:
        print(f"\nProcessing Customer Query: '{args.query}'\n")
        res = agent.process_message(args.query)
        print(format_agent_output(res))

    elif args.interactive:
        print("\n" + "=" * 60)
        print("AppleSupport AI Agent - Interactive Session")
        print("Type your inquiry and press Enter. Type 'exit' or 'quit' to end.")
        print("=" * 60 + "\n")

        while True:
            try:
                query = input("\nCustomer: ").strip()
                if query.lower() in ["exit", "quit", "q"]:
                    print("Ending session.")
                    break
                if not query:
                    continue

                res = agent.process_message(query)
                print(f"\nIntent:   {res.intent} (confidence: {res.intent_confidence:.2f})")
                print(f"Decision: {res.decision} ({res.reason})")
                print(f"Reply:\n{res.reply}")
                if res.evidence:
                    print(f"\nTop Historical Evidence [sim={res.evidence[0]['similarity_score']:.2f}]:")
                    print(f"  Historical Query: {res.evidence[0]['historical_query'][:100]}...")
                    print(f"  Historical Reply: {res.evidence[0]['historical_reply'][:100]}...")
            except (KeyboardInterrupt, EOFError):
                break
    else:
        # Default demo query
        default_query = "My icloud account has been locked for security reasons. Can't receive confirmation code."
        print(f"No query specified. Running default query:\n'{default_query}'\n")
        res = agent.process_message(default_query)
        print(format_agent_output(res))


if __name__ == "__main__":
    main()
