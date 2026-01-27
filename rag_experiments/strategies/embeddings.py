import logging
from typing import List, Optional
import numpy as np
from sentence_transformers import SentenceTransformer

from ..base import EmbeddingStrategy, StrategyConfig

logger = logging.getLogger(__name__)


class LocalEmbedder(EmbeddingStrategy):
    name = "local_embeddings"

    def __init__(
        self,
        config: Optional[StrategyConfig] = None,
        model_id: str = "sentence-transformers/all-MiniLM-L6-v2"
    ):
        super().__init__(config)
        self.model_id = model_id
        self._model: Optional[SentenceTransformer] = None

    async def initialize(self) -> None:
        if self._initialized:
            return

        logger.info(f"Loading embedding model: {self.model_id}")
        self._model = SentenceTransformer(self.model_id)
        self._initialized = True
        logger.info(f"Embedding model loaded (dim={self._model.get_sentence_embedding_dimension()})")

    async def execute(self, texts: List[str]) -> List[List[float]]:
        if not self._initialized:
            await self.initialize()

        if not texts:
            return []

        embeddings = self._model.encode(texts, convert_to_numpy=True)
        return embeddings.tolist()

    async def embed_query(self, query: str) -> List[float]:
        embeddings = await self.execute([query])
        return embeddings[0] if embeddings else []

    async def cleanup(self) -> None:
        self._model = None


class MedicalEmbedder(EmbeddingStrategy):
    name = "medical_embeddings"

    MEDICAL_MODELS = [
        "pritamdeka/S-PubMedBert-MS-MARCO",
        "dmis-lab/biobert-base-cased-v1.2",
        "sentence-transformers/all-mpnet-base-v2"
    ]

    def __init__(
        self,
        config: Optional[StrategyConfig] = None,
        model_id: Optional[str] = None
    ):
        super().__init__(config)
        self.model_id = model_id or self.MEDICAL_MODELS[0]
        self._model: Optional[SentenceTransformer] = None

    async def initialize(self) -> None:
        if self._initialized:
            return

        for model_id in ([self.model_id] + self.MEDICAL_MODELS):
            try:
                logger.info(f"Loading medical embedding model: {model_id}")
                self._model = SentenceTransformer(model_id)
                self.model_id = model_id
                self._initialized = True
                logger.info(f"Medical embedder ready (dim={self._model.get_sentence_embedding_dimension()})")
                return
            except Exception as e:
                logger.warning(f"Failed to load {model_id}: {e}")

        raise RuntimeError("Could not load any medical embedding model")

    async def execute(self, texts: List[str]) -> List[List[float]]:
        if not self._initialized:
            await self.initialize()

        if not texts:
            return []

        embeddings = self._model.encode(texts, convert_to_numpy=True)
        return embeddings.tolist()

    async def embed_query(self, query: str) -> List[float]:
        embeddings = await self.execute([query])
        return embeddings[0] if embeddings else []

    async def cleanup(self) -> None:
        self._model = None


_embedder_instance: Optional[EmbeddingStrategy] = None


async def get_embedder(medical: bool = False) -> EmbeddingStrategy:
    global _embedder_instance

    if _embedder_instance is None:
        if medical:
            _embedder_instance = MedicalEmbedder()
        else:
            _embedder_instance = LocalEmbedder()

        await _embedder_instance.initialize()

    return _embedder_instance
