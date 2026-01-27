import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


@dataclass
class RAGExperimentConfig:
    llm_model: str = "mistralai/Ministral-3b-instruct"
    fallback_llm_model: str = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    medical_embedding_model: str = "pritamdeka/S-PubMedBert-MS-MARCO"
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    chunk_size: int = 512
    chunk_overlap: int = 50
    max_tokens: int = 512
    top_k: int = 5
    rerank_candidates: int = 20
    device: str = "auto"
    use_medical_embeddings: bool = False
    enable_caching: bool = True
    log_level: str = "INFO"

    @classmethod
    def from_env(cls) -> "RAGExperimentConfig":
        return cls(
            llm_model=os.getenv(
                "RAG_LLM_MODEL",
                "mistralai/Ministral-3b-instruct"
            ),
            fallback_llm_model=os.getenv(
                "RAG_FALLBACK_LLM",
                "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
            ),
            embedding_model=os.getenv(
                "RAG_EMBEDDING_MODEL",
                "sentence-transformers/all-MiniLM-L6-v2"
            ),
            medical_embedding_model=os.getenv(
                "RAG_MEDICAL_EMBEDDING",
                "pritamdeka/S-PubMedBert-MS-MARCO"
            ),
            reranker_model=os.getenv(
                "RAG_RERANKER_MODEL",
                "cross-encoder/ms-marco-MiniLM-L-6-v2"
            ),
            chunk_size=int(os.getenv("RAG_CHUNK_SIZE", "512")),
            chunk_overlap=int(os.getenv("RAG_CHUNK_OVERLAP", "50")),
            device=os.getenv("RAG_DEVICE", "auto"),
            use_medical_embeddings=os.getenv(
                "RAG_USE_MEDICAL_EMBEDDINGS", "false"
            ).lower() == "true",
            enable_caching=os.getenv("RAG_ENABLE_CACHING", "true").lower() == "true",
            log_level=os.getenv("RAG_LOG_LEVEL", "INFO")
        )

    def validate(self) -> list[str]:
        errors = []
        if self.chunk_size <= 0:
            errors.append("chunk_size must be positive")
        if self.chunk_overlap >= self.chunk_size:
            errors.append("chunk_overlap must be less than chunk_size")
        return errors


_config: Optional[RAGExperimentConfig] = None


def get_config() -> RAGExperimentConfig:
    global _config
    if _config is None:
        _config = RAGExperimentConfig.from_env()
    return _config


def set_config(config: RAGExperimentConfig) -> None:
    global _config
    _config = config
