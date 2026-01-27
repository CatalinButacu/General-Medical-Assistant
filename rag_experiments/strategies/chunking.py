import re
import logging
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

from ..base import IngestionStrategy, Document, Chunk, StrategyConfig

logger = logging.getLogger(__name__)


class ContextAwareChunker(IngestionStrategy):
    name = "context_aware_chunking"

    def __init__(self, config: Optional[StrategyConfig] = None):
        super().__init__(config)
        self.heading_pattern = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)
        self.paragraph_pattern = re.compile(r'\n\n+')

    async def initialize(self) -> None:
        self._initialized = True
        logger.info(f"{self.name} initialized")

    async def execute(self, document: Document) -> List[Chunk]:
        sections = self._split_by_structure(document.content)
        chunks = []

        for idx, section in enumerate(sections):
            if len(section["content"].strip()) < 10:
                continue

            chunk = Chunk(
                content=section["content"],
                index=idx,
                document_title=document.title,
                metadata={
                    "heading": section.get("heading", ""),
                    "heading_level": section.get("level", 0),
                    "source": document.source,
                    **document.metadata
                }
            )
            chunks.append(chunk)

        logger.info(f"Created {len(chunks)} context-aware chunks from {document.title}")
        return chunks

    def _split_by_structure(self, content: str) -> List[Dict[str, Any]]:
        sections = []
        current_heading = ""
        current_level = 0
        current_content = []

        lines = content.split('\n')

        for line in lines:
            heading_match = self.heading_pattern.match(line)

            if heading_match:
                if current_content:
                    sections.append({
                        "heading": current_heading,
                        "level": current_level,
                        "content": '\n'.join(current_content).strip()
                    })
                    current_content = []

                current_level = len(heading_match.group(1))
                current_heading = heading_match.group(2)
                current_content.append(line)
            else:
                current_content.append(line)

        if current_content:
            sections.append({
                "heading": current_heading,
                "level": current_level,
                "content": '\n'.join(current_content).strip()
            })

        return self._merge_small_sections(sections)

    def _merge_small_sections(self, sections: List[Dict]) -> List[Dict]:
        if not sections:
            return []

        merged = []
        buffer = None

        for section in sections:
            content_len = len(section["content"])

            if content_len < self.config.chunk_size // 2:
                if buffer is None:
                    buffer = section.copy()
                else:
                    buffer["content"] += "\n\n" + section["content"]
            else:
                if buffer:
                    if len(buffer["content"]) >= self.config.chunk_size // 4:
                        merged.append(buffer)
                    buffer = None
                merged.append(section)

        if buffer and len(buffer["content"]) >= self.config.chunk_size // 4:
            merged.append(buffer)

        return merged


class HierarchicalChunker(IngestionStrategy):
    name = "hierarchical_chunking"

    def __init__(self, config: Optional[StrategyConfig] = None):
        super().__init__(config)
        self.parent_chunk_size = (config or StrategyConfig()).chunk_size * 3
        self.child_chunk_size = (config or StrategyConfig()).chunk_size

    async def initialize(self) -> None:
        self._initialized = True
        logger.info(f"{self.name} initialized")

    async def execute(self, document: Document) -> List[Chunk]:
        parent_chunks = self._create_parent_chunks(document)
        all_chunks = []

        for parent in parent_chunks:
            all_chunks.append(parent)
            children = self._create_child_chunks(parent, document)
            all_chunks.extend(children)

        logger.info(
            f"Created {len(all_chunks)} hierarchical chunks "
            f"({len(parent_chunks)} parents) from {document.title}"
        )
        return all_chunks

    def _create_parent_chunks(self, document: Document) -> List[Chunk]:
        content = document.content
        chunks = []
        start = 0
        idx = 0

        while start < len(content):
            end = min(start + self.parent_chunk_size, len(content))

            if end < len(content):
                paragraph_end = content.rfind('\n\n', start, end)
                if paragraph_end > start:
                    end = paragraph_end

            chunk_content = content[start:end].strip()
            if chunk_content:
                chunks.append(Chunk(
                    content=chunk_content,
                    index=idx,
                    document_title=document.title,
                    metadata={
                        "chunk_type": "parent",
                        "parent_id": f"parent_{idx}",
                        "source": document.source
                    }
                ))
                idx += 1

            start = end

        return chunks

    def _create_child_chunks(self, parent: Chunk, document: Document) -> List[Chunk]:
        content = parent.content
        parent_id = parent.metadata.get("parent_id", f"parent_{parent.index}")
        chunks = []
        start = 0
        idx = 0

        while start < len(content):
            end = min(start + self.child_chunk_size, len(content))

            if end < len(content):
                sentence_end = max(
                    content.rfind('. ', start, end),
                    content.rfind('! ', start, end),
                    content.rfind('? ', start, end)
                )
                if sentence_end > start:
                    end = sentence_end + 1

            chunk_content = content[start:end].strip()
            if chunk_content:
                chunks.append(Chunk(
                    content=chunk_content,
                    index=parent.index * 100 + idx,
                    document_title=document.title,
                    parent_id=parent_id,
                    metadata={
                        "chunk_type": "child",
                        "parent_id": parent_id,
                        "child_index": idx,
                        "source": document.source
                    }
                ))
                idx += 1

            start = end

        return chunks


class SemanticChunker(IngestionStrategy):
    name = "semantic_chunking"

    def __init__(self, config: Optional[StrategyConfig] = None):
        super().__init__(config)
        self._embedder = None

    async def initialize(self) -> None:
        from .embeddings import OpenAIEmbedder
        self._embedder = OpenAIEmbedder(self.config)
        await self._embedder.initialize()
        self._initialized = True
        logger.info(f"{self.name} initialized")

    async def execute(self, document: Document) -> List[Chunk]:
        sentences = self._split_into_sentences(document.content)

        if len(sentences) < 3:
            return [Chunk(
                content=document.content,
                index=0,
                document_title=document.title,
                metadata={"source": document.source}
            )]

        embeddings = await self._embedder.execute(sentences)
        breakpoints = self._find_semantic_breakpoints(embeddings)
        chunks = self._create_chunks_from_breakpoints(
            sentences, breakpoints, document
        )

        logger.info(f"Created {len(chunks)} semantic chunks from {document.title}")
        return chunks

    def _split_into_sentences(self, content: str) -> List[str]:
        sentence_pattern = re.compile(r'(?<=[.!?])\s+')
        sentences = sentence_pattern.split(content)
        return [s.strip() for s in sentences if s.strip()]

    def _find_semantic_breakpoints(
        self,
        embeddings: List[List[float]],
        threshold: float = 0.3
    ) -> List[int]:
        import numpy as np

        breakpoints = []

        for i in range(1, len(embeddings)):
            prev_emb = np.array(embeddings[i - 1])
            curr_emb = np.array(embeddings[i])

            similarity = np.dot(prev_emb, curr_emb) / (
                np.linalg.norm(prev_emb) * np.linalg.norm(curr_emb)
            )

            if similarity < threshold:
                breakpoints.append(i)

        return breakpoints

    def _create_chunks_from_breakpoints(
        self,
        sentences: List[str],
        breakpoints: List[int],
        document: Document
    ) -> List[Chunk]:
        chunks = []
        start = 0

        all_breaks = breakpoints + [len(sentences)]

        for idx, end in enumerate(all_breaks):
            chunk_sentences = sentences[start:end]
            chunk_content = ' '.join(chunk_sentences)

            if chunk_content:
                chunks.append(Chunk(
                    content=chunk_content,
                    index=idx,
                    document_title=document.title,
                    metadata={
                        "chunk_type": "semantic",
                        "sentence_count": len(chunk_sentences),
                        "source": document.source
                    }
                ))

            start = end

        return chunks
