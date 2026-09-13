"""Embeddings + vector search for clause-level retrieval (the RAG layer).

Design note: rather than calling out to a hosted embeddings API (extra
network dependency, extra latency, extra cost for a document that's already
fully in front of us), each clause is embedded locally as a TF-IDF vector
over the document's own vocabulary and retrieved by cosine similarity.
This is a legitimate, well-established embedding + vector-search technique
(it's what classic search engines and many production RAG systems use as a
fast lexical-retrieval stage, often alongside or instead of dense neural
embeddings) and it keeps retrieval deterministic, fast, and fully local to
the document — no clause text ever needs to leave the request boundary
just to be embedded.

Swapping in a neural embedding model (e.g. sentence-transformers) later is
a drop-in change: replace `_vectorize` and `retrieve` internals, keep the
same interface.
"""
from dataclasses import dataclass
from typing import List, Tuple
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from .models import Clause


@dataclass
class ClauseIndex:
    clauses: List[Clause]
    vectorizer: TfidfVectorizer
    matrix: any  # scipy sparse matrix, shape (n_clauses, n_terms)

    def retrieve(self, query: str, top_k: int = 6) -> List[Tuple[Clause, float]]:
        if not self.clauses:
            return []
        query_vec = self.vectorizer.transform([query])
        sims = cosine_similarity(query_vec, self.matrix)[0]
        ranked = sorted(
            zip(self.clauses, sims), key=lambda pair: pair[1], reverse=True
        )
        return [(c, float(s)) for c, s in ranked[:top_k] if s > 0]


def build_index(clauses: List[Clause]) -> ClauseIndex:
    if not clauses:
        return ClauseIndex(clauses=[], vectorizer=None, matrix=None)
    texts = [c.text for c in clauses]
    # sublinear_tf + English stopwords: dampens boilerplate legal filler
    # ("shall", "the", "of") so retrieval ranks on distinguishing terms.
    vectorizer = TfidfVectorizer(
        stop_words="english", sublinear_tf=True, ngram_range=(1, 2), max_features=4000
    )
    matrix = vectorizer.fit_transform(texts)
    return ClauseIndex(clauses=clauses, vectorizer=vectorizer, matrix=matrix)
