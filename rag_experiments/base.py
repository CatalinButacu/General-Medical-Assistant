from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
from datetime import datetime


class StrategyType(Enum):
    INGESTION = "ingestion"
    QUERY = "query"
    EMBEDDING = "embedding"


@dataclass
class Document:
    content: str
    title: str
    source: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Chunk:
    content: str
    index: int
    document_title: str
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    parent_id: Optional[str] = None
    context_prefix: Optional[str] = None

    @property
    def enriched_content(self) -> str:
        if self.context_prefix:
            return f"{self.context_prefix}\n\n{self.content}"
        return self.content


@dataclass
class RetrievalResult:
    chunk: Chunk
    score: float
    strategy_used: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StrategyResult:
    results: List[RetrievalResult]
    query: str
    strategy_name: str
    latency_ms: float
    token_usage: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def top_result(self) -> Optional[RetrievalResult]:
        return self.results[0] if self.results else None


@dataclass
class StrategyConfig:
    llm_model: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-small"
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    chunk_size: int = 512
    chunk_overlap: int = 50
    max_tokens: int = 512
    top_k: int = 5
    rerank_candidates: int = 20
    enable_caching: bool = True


class RAGStrategy(ABC):
    strategy_type: StrategyType
    name: str

    def __init__(self, config: Optional[StrategyConfig] = None):
        self.config = config or StrategyConfig()
        self._initialized = False

    @abstractmethod
    async def initialize(self) -> None:
        pass

    @abstractmethod
    async def execute(self, *args, **kwargs) -> Any:
        pass

    async def cleanup(self) -> None:
        pass


class IngestionStrategy(RAGStrategy):
    strategy_type = StrategyType.INGESTION

    @abstractmethod
    async def execute(self, document: Document) -> List[Chunk]:
        pass


class QueryStrategy(RAGStrategy):
    strategy_type = StrategyType.QUERY

    @abstractmethod
    async def execute(
        self,
        query: str,
        chunks: List[Chunk],
        top_k: Optional[int] = None
    ) -> StrategyResult:
        pass


class EmbeddingStrategy(RAGStrategy):
    strategy_type = StrategyType.EMBEDDING

    @abstractmethod
    async def execute(self, texts: List[str]) -> List[List[float]]:
        pass

    @abstractmethod
    async def embed_query(self, query: str) -> List[float]:
        pass
