from __future__ import annotations

import math
import re
import numpy as np
from dataclasses import dataclass
from typing import Iterable
import faiss
from sentence_transformers import SentenceTransformer

from .data_loader import Example

_TOKEN_RE = re.compile(r"[a-zA-Z0-9_]+")

def _tokenize(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN_RE.findall(text)]

class HybridRetriever:
    def __init__(self, examples: Iterable[Example], model_name: str = "all-MiniLM-L6-v2"):
        self.examples = list(examples)
        
        # 1. TF-IDF 初始化
        self.df: dict[str, int] = {}
        tokenized = []
        for ex in self.examples:
            tokens = _tokenize(ex.question)
            tokenized.append(tokens)
            for token in set(tokens):
                self.df[token] = self.df.get(token, 0) + 1
        
        n_docs = max(len(self.examples), 1)
        self.idf = {t: math.log((1 + n_docs) / (1 + freq)) + 1 for t, freq in self.df.items()}
        
        self.tfidf_vectors = []
        self.tfidf_norms = []
        for tokens in tokenized:
            tf = {}
            for t in tokens: tf[t] = tf.get(t, 0) + 1
            vec = {t: (count / len(tokens)) * self.idf.get(t, 0.0) for t, count in tf.items()}
            norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
            self.tfidf_vectors.append(vec)
            self.tfidf_norms.append(norm)

        # 2. Vector 初始化
        self.model = SentenceTransformer(model_name)
        questions = [ex.question for ex in self.examples]
        embeddings = self.model.encode(questions, show_progress_bar=False)
        embeddings = np.array(embeddings).astype("float32")
        faiss.normalize_L2(embeddings)
        self.vector_index = faiss.IndexFlatIP(embeddings.shape[1])
        self.vector_index.add(embeddings)

    def search(self, query: str, k: int = 5) -> list[Example]:
        if not self.examples: return []
        
        # TF-IDF 检索
        q_tokens = _tokenize(query)
        q_tf = {}
        for t in q_tokens: q_tf[t] = q_tf.get(t, 0) + 1
        q_vec = {t: (count / max(len(q_tokens), 1)) * self.idf.get(t, 0.0) for t, count in q_tf.items()}
        q_norm = math.sqrt(sum(v * v for v in q_vec.values())) or 1.0
        
        tfidf_scores = []
        for vec, norm in zip(self.tfidf_vectors, self.tfidf_norms):
            dot = sum(q_vec.get(t, 0.0) * vec.get(t, 0.0) for t in q_vec)
            tfidf_scores.append(dot / (q_norm * norm))
        
        # Vector 检索
        q_emb = self.model.encode([query], show_progress_bar=False)
        q_emb = np.array(q_emb).astype("float32")
        faiss.normalize_L2(q_emb)
        _, v_indices = self.vector_index.search(q_emb, k * 2)
        
        # 合并结果 (Hybrid)
        top_tfidf_idx = np.argsort(tfidf_scores)[::-1][:k*2]
        combined_idx = list(top_tfidf_idx) + list(v_indices[0])
        
        results = []
        seen = set()
        for idx in combined_idx:
            if idx != -1 and idx < len(self.examples) and idx not in seen:
                results.append(self.examples[idx])
                seen.add(idx)
        return results[:k]
