import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Type
from datetime import datetime

from .base import (
    Document,
    Chunk,
    StrategyResult,
    IngestionStrategy,
    QueryStrategy,
    StrategyConfig
)
from .strategies.chunking import ContextAwareChunker
from .strategies.enrichment import ContextualEnricher
from .strategies.query import QueryExpander, MultiQuerySearcher, ReRanker
from .strategies.agentic import AgenticRAG, SelfReflectiveRAG
from .strategies.embeddings import LocalEmbedder, MedicalEmbedder

logger = logging.getLogger(__name__)


@dataclass
class ExperimentResult:
    strategy_name: str
    query: str
    latency_ms: float
    result_count: int
    top_score: float
    avg_score: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ComparisonReport:
    query: str
    results: List[ExperimentResult]
    best_strategy: str
    fastest_strategy: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "best_strategy": self.best_strategy,
            "fastest_strategy": self.fastest_strategy,
            "results": [
                {
                    "strategy": r.strategy_name,
                    "latency_ms": round(r.latency_ms, 2),
                    "top_score": round(r.top_score, 4),
                    "avg_score": round(r.avg_score, 4)
                }
                for r in self.results
            ],
            "timestamp": self.timestamp
        }


class ExperimentRunner:
    AVAILABLE_STRATEGIES: Dict[str, Type[QueryStrategy]] = {
        "multi_query": MultiQuerySearcher,
        "rerank": ReRanker,
        "agentic": AgenticRAG,
        "self_reflective": SelfReflectiveRAG
    }

    def __init__(self, config: Optional[StrategyConfig] = None, use_medical: bool = False):
        self.config = config or StrategyConfig()
        self.use_medical = use_medical
        self._strategies: Dict[str, QueryStrategy] = {}
        self._embedder = None
        self._initialized = False

    async def initialize(self, strategies: Optional[List[str]] = None) -> None:
        strategy_names = strategies or list(self.AVAILABLE_STRATEGIES.keys())

        if self.use_medical:
            self._embedder = MedicalEmbedder(self.config)
        else:
            self._embedder = LocalEmbedder(self.config)

        await self._embedder.initialize()

        for name in strategy_names:
            if name in self.AVAILABLE_STRATEGIES:
                strategy = self.AVAILABLE_STRATEGIES[name](self.config)
                await strategy.initialize()
                self._strategies[name] = strategy
                logger.info(f"Initialized strategy: {name}")

        self._initialized = True
        logger.info(f"ExperimentRunner ready with {len(self._strategies)} strategies")

    async def prepare_chunks(
        self,
        documents: List[Document],
        chunker: Optional[IngestionStrategy] = None,
        enrich: bool = False
    ) -> List[Chunk]:
        chunker = chunker or ContextAwareChunker(self.config)
        await chunker.initialize()

        all_chunks = []
        for doc in documents:
            chunks = await chunker.execute(doc)
            all_chunks.extend(chunks)

        if enrich:
            enricher = ContextualEnricher(self.config)
            await enricher.initialize()
            for doc in documents:
                doc_chunks = [c for c in all_chunks if c.document_title == doc.title]
                enriched = await enricher.enrich_chunks(doc_chunks, doc)
                for orig, new in zip(doc_chunks, enriched):
                    orig.context_prefix = new.context_prefix

        chunk_texts = [c.enriched_content for c in all_chunks]
        embeddings = await self._embedder.execute(chunk_texts)

        for chunk, embedding in zip(all_chunks, embeddings):
            chunk.embedding = embedding

        logger.info(f"Prepared {len(all_chunks)} chunks with embeddings")
        return all_chunks

    async def run_strategy(
        self,
        strategy_name: str,
        query: str,
        chunks: List[Chunk],
        top_k: Optional[int] = None
    ) -> ExperimentResult:
        if strategy_name not in self._strategies:
            raise ValueError(f"Unknown strategy: {strategy_name}")

        strategy = self._strategies[strategy_name]
        result = await strategy.execute(query, chunks, top_k)

        scores = [r.score for r in result.results]
        avg_score = sum(scores) / len(scores) if scores else 0.0

        return ExperimentResult(
            strategy_name=strategy_name,
            query=query,
            latency_ms=result.latency_ms,
            result_count=len(result.results),
            top_score=scores[0] if scores else 0.0,
            avg_score=avg_score,
            metadata=result.metadata
        )

    async def compare_strategies(
        self,
        query: str,
        chunks: List[Chunk],
        strategies: Optional[List[str]] = None,
        top_k: Optional[int] = None
    ) -> ComparisonReport:
        strategy_names = strategies or list(self._strategies.keys())

        results = []
        for name in strategy_names:
            if name in self._strategies:
                try:
                    result = await self.run_strategy(name, query, chunks, top_k)
                    results.append(result)
                except Exception as e:
                    logger.error(f"Strategy {name} failed: {e}")

        best = max(results, key=lambda x: x.top_score) if results else None
        fastest = min(results, key=lambda x: x.latency_ms) if results else None

        return ComparisonReport(
            query=query,
            results=results,
            best_strategy=best.strategy_name if best else "none",
            fastest_strategy=fastest.strategy_name if fastest else "none"
        )

    async def cleanup(self) -> None:
        for strategy in self._strategies.values():
            await strategy.cleanup()
        if self._embedder:
            await self._embedder.cleanup()
