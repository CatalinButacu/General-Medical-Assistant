import asyncio
import logging
import time
from typing import List, Optional
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


class SelfReflectiveRAG(QueryStrategy):
    name = "self_reflective"

    def __init__(self, config: Optional[StrategyConfig] = None):
        super().__init__(config)
        self._embedder = None

    async def initialize(self) -> None:
        from .embeddings import LocalEmbedder

        get_llm()
        self._embedder = LocalEmbedder(self.config)
        await self._embedder.initialize()
        self._initialized = True
        logger.info(f"{self.name} initialized with local LLM")

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

        initial_results = await self._search(query, chunks, top_k)

        if not initial_results:
            return StrategyResult(
                results=[],
                query=query,
                strategy_name=self.name,
                latency_ms=(time.time() - start_time) * 1000,
                metadata={"reflection": "No results found"}
            )

        grade, reason = self._grade_results(query, initial_results)
        logger.info(f"Initial results grade: {grade}/5 - {reason}")

        reflection_note = ""
        final_results = initial_results

        if grade < 3:
            refined_query = self._refine_query(query)
            logger.info(f"Refined query: {refined_query}")

            final_results = await self._search(refined_query, chunks, top_k)
            reflection_note = f"Refined from '{query}' to '{refined_query}'"
        else:
            reflection_note = f"Results deemed relevant (score: {grade}/5)"

        return StrategyResult(
            results=final_results,
            query=query,
            strategy_name=self.name,
            latency_ms=(time.time() - start_time) * 1000,
            metadata={
                "initial_grade": grade,
                "grade_reason": reason,
                "reflection": reflection_note
            }
        )

    async def _search(
        self,
        query: str,
        chunks: List[Chunk],
        top_k: int
    ) -> List[RetrievalResult]:
        query_embedding = await self._embedder.embed_query(query)
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
                strategy_used=self.name
            ))

        return sorted(scored, key=lambda x: x.score, reverse=True)[:top_k]

    def _grade_results(
        self,
        query: str,
        results: List[RetrievalResult]
    ) -> tuple[int, str]:
        docs_summary = "\n".join([
            f"{i+1}. {r.chunk.content[:200]}..."
            for i, r in enumerate(results[:5])
        ])

        prompt = f"""Query: {query}

Retrieved Documents:
{docs_summary}

Grade the overall relevance of these documents to the query on a scale of 1-5:
1 = Not relevant at all
2 = Slightly relevant
3 = Moderately relevant
4 = Relevant
5 = Highly relevant

Respond with only a number (1-5) followed by a brief reason (max 20 words)."""

        try:
            llm = get_llm()
            text = llm.generate(prompt, max_tokens=50)

            parts = text.split(maxsplit=1)
            grade = int(parts[0][0]) if parts[0][0].isdigit() else 3
            reason = parts[1] if len(parts) > 1 else ""

            return min(max(grade, 1), 5), reason

        except Exception as e:
            logger.warning(f"Grading failed: {e}")
            return 3, "Default grade due to error"

    def _refine_query(self, query: str) -> str:
        prompt = f"""The query "{query}" returned low-relevance results.
Suggest an improved, more specific query that might find better results.
Respond with only the improved query, nothing else."""

        try:
            llm = get_llm()
            return llm.generate(prompt, max_tokens=50).strip()

        except Exception as e:
            logger.warning(f"Query refinement failed: {e}")
            return query


class AgenticRAG(QueryStrategy):
    name = "agentic"

    STRATEGIES = {
        "basic": "Standard semantic search - fast and reliable",
        "rerank": "Two-stage with cross-encoder - high precision",
        "multi_query": "Multiple query variations - better recall",
        "self_reflective": "Evaluates and refines results - research queries"
    }

    def __init__(self, config: Optional[StrategyConfig] = None):
        super().__init__(config)
        self._strategies: dict = {}

    async def initialize(self) -> None:
        from .query import MultiQuerySearcher, ReRanker

        get_llm()

        self._strategies["multi_query"] = MultiQuerySearcher(self.config)
        self._strategies["rerank"] = ReRanker(self.config)
        self._strategies["self_reflective"] = SelfReflectiveRAG(self.config)

        for strategy in self._strategies.values():
            await strategy.initialize()

        self._initialized = True
        logger.info(f"{self.name} initialized with {len(self._strategies)} strategies")

    async def execute(
        self,
        query: str,
        chunks: List[Chunk],
        top_k: Optional[int] = None
    ) -> StrategyResult:
        if not self._initialized:
            await self.initialize()

        start_time = time.time()

        selected_strategy = self._select_strategy(query)
        logger.info(f"Agent selected strategy: {selected_strategy}")

        if selected_strategy in self._strategies:
            result = await self._strategies[selected_strategy].execute(
                query, chunks, top_k
            )
        else:
            result = await self._basic_search(query, chunks, top_k or self.config.top_k)

        result.metadata["agent_selection"] = selected_strategy
        result.latency_ms = (time.time() - start_time) * 1000

        return result

    def _select_strategy(self, query: str) -> str:
        strategies_desc = "\n".join([
            f"- {name}: {desc}"
            for name, desc in self.STRATEGIES.items()
        ])

        prompt = f"""Select the best retrieval strategy for this query:

Query: "{query}"

Available strategies:
{strategies_desc}

Consider:
- Use "basic" for simple, direct questions
- Use "rerank" for precision-critical queries (medical, legal)
- Use "multi_query" for ambiguous or broad queries
- Use "self_reflective" for complex research questions

Respond with only the strategy name (basic, rerank, multi_query, or self_reflective)."""

        try:
            llm = get_llm()
            selection = llm.generate(prompt, max_tokens=20).strip().lower()

            for strategy_name in self.STRATEGIES:
                if strategy_name in selection:
                    return strategy_name

            return "basic"

        except Exception as e:
            logger.warning(f"Strategy selection failed: {e}")
            return "basic"

    async def _basic_search(
        self,
        query: str,
        chunks: List[Chunk],
        top_k: int
    ) -> StrategyResult:
        from .embeddings import LocalEmbedder

        embedder = LocalEmbedder(self.config)
        await embedder.initialize()

        query_embedding = await embedder.embed_query(query)
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
                strategy_used="basic"
            ))

        results = sorted(scored, key=lambda x: x.score, reverse=True)[:top_k]

        return StrategyResult(
            results=results,
            query=query,
            strategy_name="basic",
            latency_ms=0
        )
