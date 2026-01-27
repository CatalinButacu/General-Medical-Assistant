import asyncio
import logging
from typing import List, Optional

from ..base import IngestionStrategy, Document, Chunk, StrategyConfig
from ..local_llm import get_llm

logger = logging.getLogger(__name__)


class ContextualEnricher(IngestionStrategy):
    name = "contextual_enrichment"

    def __init__(self, config: Optional[StrategyConfig] = None):
        super().__init__(config)

    async def initialize(self) -> None:
        get_llm()
        self._initialized = True
        logger.info(f"{self.name} initialized with local LLM")

    async def execute(self, document: Document) -> List[Chunk]:
        raise NotImplementedError(
            "ContextualEnricher enriches existing chunks. Use enrich_chunks() instead."
        )

    async def enrich_chunks(
        self,
        chunks: List[Chunk],
        document: Document
    ) -> List[Chunk]:
        if not self._initialized:
            await self.initialize()

        logger.info(f"Enriching {len(chunks)} chunks with contextual prefixes")

        result = []
        for chunk in chunks:
            enriched = self._enrich_single_chunk(chunk, document)
            result.append(enriched)

        logger.info(f"Successfully enriched {len(result)} chunks")
        return result

    def _enrich_single_chunk(
        self,
        chunk: Chunk,
        document: Document
    ) -> Chunk:
        context_prefix = self._generate_context(chunk, document)

        return Chunk(
            content=chunk.content,
            index=chunk.index,
            document_title=chunk.document_title,
            embedding=chunk.embedding,
            metadata=chunk.metadata,
            parent_id=chunk.parent_id,
            context_prefix=context_prefix
        )

    def _generate_context(
        self,
        chunk: Chunk,
        document: Document
    ) -> str:
        document_excerpt = document.content[:2000]

        prompt = f"""<document>
Title: {document.title}
Source: {document.source}

{document_excerpt}
</document>

<chunk>
{chunk.content[:500]}
</chunk>

Provide a brief 1-2 sentence context explaining what this chunk discusses.
Format: "This chunk from [document title] discusses [brief explanation]."
Be concise. Return only the context sentence."""

        try:
            llm = get_llm()
            return llm.generate(prompt, max_tokens=80).strip()

        except Exception as e:
            logger.error(f"Context generation failed: {e}")
            return f"This chunk is from '{document.title}'."

    async def cleanup(self) -> None:
        pass
