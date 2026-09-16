"""Historical conversation vector store and semantic retrieval engine.
Guarantees strict train/test isolation to prevent evaluation data leakage.
"""

import logging
from typing import List, Set, Optional, Tuple, Dict, Any
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from src.data.schema import SupportConversation, RetrievedEvidence
from src.preprocessing.text_cleaner import clean_for_embedding

logger = logging.getLogger(__name__)


class HistoricalVectorStore:
    """Stores and retrieves historical brand resolutions using semantic cosine similarity."""

    def __init__(self, max_features: int = 10000, ngram_range: Tuple[int, int] = (1, 2)):
        self.vectorizer = TfidfVectorizer(
            max_features=max_features,
            ngram_range=ngram_range,
            sublinear_tf=True,
            stop_words="english"
        )
        self.corpus_conversations: List[SupportConversation] = []
        self.tfidf_matrix = None
        self.is_indexed = False

    def build_index(
        self,
        conversations: List[SupportConversation],
        exclude_ids: Optional[Set[str]] = None
    ) -> int:
        """Indexes historical conversations while strictly excluding specified conversation IDs."""
        if exclude_ids is None:
            exclude_ids = set()

        # Filter out excluded IDs to prevent leakage
        valid_conversations = [
            c for c in conversations
            if c.conversation_id not in exclude_ids and len(c.customer_query.strip()) > 10
        ]

        if not valid_conversations:
            raise ValueError("No valid conversations to index after applying exclusions.")

        self.corpus_conversations = valid_conversations
        corpus_texts = [clean_for_embedding(c.customer_query) for c in valid_conversations]

        self.tfidf_matrix = self.vectorizer.fit_transform(corpus_texts)
        self.is_indexed = True

        logger.info(
            f"Built vector index with {len(valid_conversations)} historical conversations. "
            f"Excluded {len(exclude_ids)} held-out/golden IDs."
        )
        return len(valid_conversations)

    def retrieve(self, query: str, top_k: int = 3) -> List[RetrievedEvidence]:
        """Retrieves top_k historical conversation pairs matching the query."""
        if not self.is_indexed or self.tfidf_matrix is None:
            raise RuntimeError("Vector store index has not been built. Call build_index first.")

        cleaned_query = clean_for_embedding(query)
        if not cleaned_query:
            return []

        query_vec = self.vectorizer.transform([cleaned_query])
        similarities = cosine_similarity(query_vec, self.tfidf_matrix)[0]

        top_indices = np.argsort(similarities)[::-1][:top_k]
        results: List[RetrievedEvidence] = []

        for idx in top_indices:
            score = float(similarities[idx])
            conv = self.corpus_conversations[idx]
            results.append(
                RetrievedEvidence(
                    conversation_id=conv.conversation_id,
                    historical_query=conv.customer_query,
                    historical_reply=conv.support_reply,
                    similarity_score=round(score, 4)
                )
            )

        return results

    def assess_evidence_sufficiency(
        self,
        query: str,
        evidence: List[RetrievedEvidence],
        similarity_threshold: float = 0.18
    ) -> Tuple[str, str]:
        """Assesses whether retrieved evidence is sufficient to draft a grounded response.
        Returns (status: 'adequate' | 'insufficient', reason: str).
        """
        cleaned_query = clean_for_embedding(query)
        if len(cleaned_query.split()) < 3:
            return "insufficient", "Query is too brief or vague to establish historical precedent."

        if not evidence:
            return "insufficient", "No historical resolutions found in knowledge corpus."

        top_score = evidence[0].similarity_score
        if top_score < similarity_threshold:
            return "insufficient", f"Top retrieved evidence similarity ({top_score:.2f}) is below confidence threshold ({similarity_threshold:.2f})."

        return "adequate", f"Found high-relevance historical precedent (similarity: {top_score:.2f})."
