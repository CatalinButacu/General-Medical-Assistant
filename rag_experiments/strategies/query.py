import asyncio
import logging
import time
from typing import List, Optional, Dict, Any
import numpy as np

from ..base import (
    QueryStrategy,
    StrategyResult,
    RetrievalResult,
    Chunk,
    StrategyConfig
)
from ..local_llm import get_llm

logger = logging.getLogger(__name__)


class QueryExpander(QueryStrategy):
    name = "query_expansion"

    def __init__(self, config: Optional[StrategyConfig] = None):
        super().__init__(config)

    async def initialize(self) -> None:
        get_llm()
        self._initialized = True
        logger.info(f"{self.name} initialized with local LLM")

    async def expand(self, query: str, num_variations: int = 3) -> List[str]:
        if not self._initialized:
            await self.initialize()

        prompt = f"""Generate {num_variations} different variations of this search query.
Each variation should capture a different perspective or phrasing while maintaining the same intent.

Original query: {query}

Return only the {num_variations} variations, one per line, without numbers or bullets."""

        try:
            llm = get_llm()
            response = llm.generate(prompt, max_tokens=150)

            variations = [v.strip() for v in response.split('\n') if v.strip()]
            return [query] + variations[:num_variations]

        except Exception as e:
            logger.error(f"Query expansion failed: {e}")
            return [query]

    async def execute(
        self,
        query: str,
        chunks: List[Chunk],
        top_k: Optional[int] = None
    ) -> StrategyResult:
        start_time = time.time()
        expanded_queries = await self.expand(query)

        return StrategyResult(
            results=[],
            query=query,
            strategy_name=self.name,
            latency_ms=(time.time() - start_time) * 1000,
            metadata={"expanded_queries": expanded_queries}
        )


class MultiQuerySearcher(QueryStrategy):
    name = "multi_query"

    def __init__(self, config: Optional[StrategyConfig] = None):
        super().__init__(config)
        self._expander: Optional[QueryExpander] = None
        self._embedder = None

    async def initialize(self) -> None:
        from .embeddings import LocalEmbedder

        self._expander = QueryExpander(self.config)
        await self._expander.initialize()
        self._embedder = LocalEmbedder(self.config)
        await self._embedder.initialize()
        self._initialized = True
        logger.info(f"{self.name} initialized")

    async def execute(
        self,
        query: str,
        chunks: List[Chunk],
        top_k: Optional[int] = None
    ) -> StrategyResult:
        if not self._initialized:
            await self.initialize()

        start_time = time.time()
        top_k = top_k or self.config.top_k
        expanded_queries = await self._expander.expand(query)

        logger.info(f"Multi-query search with {len(expanded_queries)} variations")

        query_embeddings = await self._embedder.execute(expanded_queries)

        all_results: Dict[int, RetrievalResult] = {}

        for q_idx, q_embedding in enumerate(query_embeddings):
            scored = self._score_chunks(chunks, q_embedding, expanded_queries[q_idx])

            for result in scored:
                chunk_id = result.chunk.index
                if chunk_id not in all_results or result.score > all_results[chunk_id].score:
                    all_results[chunk_id] = result

        sorted_results = sorted(
            all_results.values(),
            key=lambda x: x.score,
            reverse=True
        )[:top_k]

        return StrategyResult(
            results=sorted_results,
            query=query,
            strategy_name=self.name,
            latency_ms=(time.time() - start_time) * 1000,
            metadata={
                "query_count": len(expanded_queries),
                "total_candidates": len(all_results)
            }
        )

    def _score_chunks(
        self,
        chunks: List[Chunk],
        query_embedding: List[float],
        query_text: str
    ) -> List[RetrievalResult]:
        results = []
        q_arr = np.array(query_embedding)

        for chunk in chunks:
            if chunk.embedding is None:
                continue

            c_arr = np.array(chunk.embedding)
            similarity = np.dot(q_arr, c_arr) / (
                np.linalg.norm(q_arr) * np.linalg.norm(c_arr) + 1e-8
            )

            results.append(RetrievalResult(
                chunk=chunk,
                score=float(similarity),
                strategy_used=self.name,
                metadata={"matched_query": query_text}
            ))

        return results


class ReRanker(QueryStrategy):
    name = "reranking"

    def __init__(self, config: Optional[StrategyConfig] = None):
        super().__init__(config)
        self._cross_encoder = None
        self._embedder = None

    async def initialize(self) -> None:
        from sentence_transformers import CrossEncoder
        from .embeddings import LocalEmbedder

        logger.info(f"Loading cross-encoder: {self.config.reranker_model}")
        self._cross_encoder = CrossEncoder(self.config.reranker_model)
        self._embedder = LocalEmbedder(self.config)
        await self._embedder.initialize()
        self._initialized = True
        logger.info(f"{self.name} initialized")

    async def execute(
        self,
        query: str,
        chunks: List[Chunk],
        top_k: Optional[int] = None
    ) -> StrategyResult:
        if not self._initialized:
            await self.initialize()

        start_time = time.time()
        top_k = top_k or self.config.top_k
        candidate_limit = min(self.config.rerank_candidates, len(chunks))

        query_embedding = await self._embedder.embed_query(query)
        candidates = self._get_initial_candidates(chunks, query_embedding, candidate_limit)

        logger.info(f"Re-ranking {len(candidates)} candidates")

        pairs = [[query, c.chunk.enriched_content] for c in candidates]
        scores = self._cross_encoder.predict(pairs)

        reranked = sorted(
            zip(candidates, scores),
            key=lambda x: x[1],
            reverse=True
        )[:top_k]

        results = [
            RetrievalResult(
                chunk=result.chunk,
                score=float(score),
                strategy_used=self.name,
                metadata={
                    "initial_score": result.score,
                    "rerank_score": float(score)
                }
            )
            for result, score in reranked
        ]

        return StrategyResult(
            results=results,
            query=query,
            strategy_name=self.name,
            latency_ms=(time.time() - start_time) * 1000,
            metadata={
                "candidates_considered": len(candidates),
                "reranker_model": self.config.reranker_model
            }
        )

    def _get_initial_candidates(
        self,
        chunks: List[Chunk],
        query_embedding: List[float],
        limit: int
    ) -> List[RetrievalResult]:
        q_arr = np.array(query_embedding)
        scored = []

        for chunk in chunks:
            if chunk.embedding is None:
                continue

            c_arr = np.array(chunk.embedding)
            similarity = np.dot(q_arr, c_arr) / (
                np.linalg.norm(q_arr) * np.linalg.norm(c_arr) + 1e-8
            )

            scored.append(RetrievalResult(
                chunk=chunk,
                score=float(similarity),
                strategy_used="initial_retrieval"
            ))

        return sorted(scored, key=lambda x: x.score, reverse=True)[:limit]
