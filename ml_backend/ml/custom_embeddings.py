"""Custom BioBERT Embeddings for Medical RAG System
Optimized for medical text processing and semantic similarity
"""

import os
import logging
import numpy as np
import torch
from transformers import AutoTokenizer, AutoModel
from sklearn.metrics.pairwise import cosine_similarity
from typing import List, Union, Optional, Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CustomBioBERTEmbeddings:
    """
    Custom BioBERT-based embedding model for medical text
    Fine-tuned on medical datasets for domain-specific embeddings
    """

    def __init__(self, model_path: Optional[str] = None, device: str = 'cpu'):
        self.device = torch.device(
            device if torch.cuda.is_available() else 'cpu'
        )
        self.model_path = (
            model_path or 'dmis-lab/biobert-base-cased-v1.2'
        )
        self.tokenizer = None
        self.model = None
        self.embedding_dim = 768  # BioBERT base dimension
        self.max_length = 512

        # Medical domain vocabulary enhancement
        self.medical_vocab = {
            'medication', 'dosage', 'contraindication', 'side_effect',
            'interaction', 'pregnancy', 'breastfeeding', 'allergy',
            'symptom', 'diagnosis', 'treatment', 'prescription',
            'pharmaceutical', 'therapeutic', 'clinical'
        }

        self._load_model()

    def _load_model(self):
        """Load BioBERT model and tokenizer"""
        try:
            logger.info(f"Loading BioBERT model from {self.model_path}")
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_path)
            self.model = AutoModel.from_pretrained(self.model_path)
            self.model.to(self.device)
            self.model.eval()
            logger.info("BioBERT model loaded successfully")

        except Exception as e:
            logger.error(f"Failed to load BioBERT model: {str(e)}")
            raise

    def encode_text(self, text: str) -> torch.Tensor:
        """Encode text to embeddings using BioBERT"""
        try:
            # Tokenize input text
            inputs = self.tokenizer(
                text,
                return_tensors='pt',
                max_length=self.max_length,
                truncation=True,
                padding=True
            )

            # Move to device
            inputs = {k: v.to(self.device) for k, v in inputs.items()}

            # Generate embeddings
            with torch.no_grad():
                outputs = self.model(**inputs)
                # Use [CLS] token embedding
                embeddings = outputs.last_hidden_state[:, 0, :]

            return embeddings.cpu()

        except Exception as e:
            logger.error(f"Failed to encode text: {str(e)}")
            raise

    def encode_batch(self, texts: List[str]) -> torch.Tensor:
        """Encode batch of texts to embeddings"""
        try:
            # Tokenize batch
            inputs = self.tokenizer(
                texts,
                return_tensors='pt',
                max_length=self.max_length,
                truncation=True,
                padding=True
            )

            # Move to device
            inputs = {k: v.to(self.device) for k, v in inputs.items()}

            # Generate embeddings
            with torch.no_grad():
                outputs = self.model(**inputs)
                # Use [CLS] token embeddings
                embeddings = outputs.last_hidden_state[:, 0, :]

            return embeddings.cpu()

        except Exception as e:
            logger.error(f"Failed to encode batch: {str(e)}")
            raise

    def calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate cosine similarity between two texts"""
        try:
            emb1 = self.encode_text(text1)
            emb2 = self.encode_text(text2)

            # Calculate cosine similarity
            similarity = torch.cosine_similarity(emb1, emb2, dim=1)
            return float(similarity.item())

        except Exception as e:
            logger.error(f"Failed to calculate similarity: {str(e)}")
            raise

    def save_model(self, save_path: str):
        """Save the fine-tuned model"""
        try:
            os.makedirs(save_path, exist_ok=True)
            self.model.save_pretrained(save_path)
            self.tokenizer.save_pretrained(save_path)
            logger.info(f"Model saved to {save_path}")

        except Exception as e:
            logger.error(f"Failed to save model: {str(e)}")
            raise


class MedicalEmbeddingManager:
    """
    Manager for multiple medical embedding models
    Handles BioBERT, SentenceTransformers, and custom models
    """

    def __init__(self, models_dir: str = "models"):
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(exist_ok=True)

        # Model paths
        self.biobert_path = self.models_dir / "biobert"
        self.sentence_transformer_path = (
            self.models_dir / "sentence_transformer"
        )

        # Initialize models
        self.biobert = None
        self.sentence_transformer = None
        self.is_initialized = False

    def initialize(self):
        """Initialize all embedding models"""
        try:
            logger.info("Initializing medical embedding models...")

            # Initialize BioBERT
            self.biobert = CustomBioBERTEmbeddings()

            # Initialize SentenceTransformer for medical domain
            self.sentence_transformer = SentenceTransformer(
                'sentence-transformers/all-MiniLM-L6-v2'
            )

            self.is_initialized = True
            logger.info("Medical embedding models initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize models: {str(e)}")
            raise

    def encode_text(self, text: str, model_type: str = 'biobert') -> list:
        """Encode text using specified model"""
        if not self.is_initialized:
            self.initialize()

        try:
            if model_type == 'biobert':
                embeddings = self.biobert.encode_text(text)
                return embeddings.numpy().tolist()[0]

            elif model_type == 'sentence_transformer':
                embeddings = self.sentence_transformer.encode([text])
                return embeddings[0].tolist()

            else:
                raise ValueError(f"Unknown model type: {model_type}")

        except Exception as e:
            logger.error(f"Failed to encode text: {str(e)}")
            raise

    def encode_batch(
        self, texts: List[str], model_type: str = 'biobert'
    ) -> List[List[float]]:
        """Encode batch of texts"""
        if not self.is_initialized:
            self.initialize()

        try:
            if model_type == 'biobert':
                embeddings = self.biobert.encode_batch(texts)
                return embeddings.numpy().tolist()

            elif model_type == 'sentence_transformer':
                embeddings = self.sentence_transformer.encode(texts)
                return embeddings.tolist()

            else:
                raise ValueError(f"Unknown model type: {model_type}")

        except Exception as e:
            logger.error(f"Failed to encode batch: {str(e)}")
            raise

    def calculate_similarity(
        self, text1: str, text2: str, model_type: str = 'biobert'
    ) -> float:
        """Calculate similarity between texts"""
        if not self.is_initialized:
            self.initialize()

        try:
            if model_type == 'biobert':
                return self.biobert.calculate_similarity(text1, text2)

            elif model_type == 'sentence_transformer':
                emb1 = self.sentence_transformer.encode([text1])
                emb2 = self.sentence_transformer.encode([text2])

                # Calculate cosine similarity
                from sklearn.metrics.pairwise import cosine_similarity
                similarity = cosine_similarity(emb1, emb2)[0][0]
                return float(similarity)

            else:
                raise ValueError(f"Unknown model type: {model_type}")

        except Exception as e:
            logger.error(f"Failed to calculate similarity: {str(e)}")
            raise

    def get_statistics(self) -> Dict:
        """Get embedding model statistics"""
        try:
            stats = {
                'initialized': self.is_initialized,
                'models_available': [],
                'biobert_dim': 768 if self.biobert else None,
                'sentence_transformer_dim': (
                    384 if self.sentence_transformer else None
                )
            }

            if self.biobert:
                stats['models_available'].append('biobert')

            if self.sentence_transformer:
                stats['models_available'].append('sentence_transformer')

            return stats

        except Exception as e:
            logger.error(f"Failed to get statistics: {str(e)}")
            return {'error': str(e)}

    def save_all_models(self):
        """Save all trained models"""
        try:
            if self.biobert:
                self.biobert.save_model(str(self.biobert_path))

            if self.sentence_transformer:
                self.sentence_transformer.save(
                    str(self.sentence_transformer_path)
                )

            logger.info("All models saved successfully")

        except Exception as e:
            logger.error(f"Failed to save models: {str(e)}")
            raise
