"""
Custom Medical Embedding Models
Fine-tuned BioBERT and custom medical embeddings for on-premise deployment
"""

import torch
import torch.nn as nn
from transformers import AutoTokenizer, AutoModel, AutoConfig
from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List, Dict, Optional, Tuple
import pickle
import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class CustomBioBERTEmbeddings:
    """
    Custom BioBERT-based embedding model for medical text
    Fine-tuned on medical datasets for domain-specific embeddings
    """
    
    def __init__(self, model_path: Optional[str] = None, device: str = 'cpu'):
        self.device = torch.device(device if torch.cuda.is_available() else 'cpu')
        self.model_path = model_path or 'dmis-lab/biobert-base-cased-v1.2'
        self.tokenizer = None
        self.model = None
        self.embedding_dim = 768  # BioBERT base dimension
        self.max_length = 512
        
        # Medical domain vocabulary enhancement
        self.medical_vocab = {
            'medication', 'dosage', 'contraindication', 'side_effect', 'interaction',
            'pregnancy', 'breastfeeding', 'allergy', 'symptom', 'diagnosis',
            'treatment', 'prescription', 'pharmaceutical', 'therapeutic', 'clinical'
        }
        
        self._load_model()
    
    def _load_model(self):
        """Load BioBERT model and tokenizer"""
        try:
            logger.info(f"Loading BioBERT model from {self.model_path}")
            
            # Load tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_path,
                do_lower_case=False,
                cache_dir='./models/cache'
            )
            
            # Load model
            self.model = AutoModel.from_pretrained(
                self.model_path,
                cache_dir='./models/cache'
            )
            
            # Move to device
            self.model.to(self.device)
            self.model.eval()
            
            # Add medical vocabulary to tokenizer if not present
            self._enhance_medical_vocabulary()
            
            logger.info(f"BioBERT model loaded successfully on {self.device}")
            
        except Exception as e:
            logger.error(f"Failed to load BioBERT model: {str(e)}")
            raise
    
    def _enhance_medical_vocabulary(self):
        """Enhance tokenizer with medical domain vocabulary"""
        try:
            # Get current vocabulary
            current_vocab = set(self.tokenizer.get_vocab().keys())
            
            # Add missing medical terms
            new_tokens = []
            for term in self.medical_vocab:
                if term not in current_vocab:
                    new_tokens.append(term)
            
            if new_tokens:
                logger.info(f"Adding {len(new_tokens)} medical terms to vocabulary")
                self.tokenizer.add_tokens(new_tokens)
                self.model.resize_token_embeddings(len(self.tokenizer))
                
        except Exception as e:
            logger.warning(f"Failed to enhance medical vocabulary: {str(e)}")
    
    def encode_text(self, texts: List[str], batch_size: int = 32) -> np.ndarray:
        """
        Encode texts into embeddings using BioBERT
        
        Args:
            texts: List of texts to encode
            batch_size: Batch size for processing
            
        Returns:
            numpy array of embeddings
        """
        if not texts:
            return np.array([])
        
        embeddings = []
        
        with torch.no_grad():
            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i:i + batch_size]
                
                # Tokenize batch
                encoded = self.tokenizer(
                    batch_texts,
                    padding=True,
                    truncation=True,
                    max_length=self.max_length,
                    return_tensors='pt'
                )
                
                # Move to device
                input_ids = encoded['input_ids'].to(self.device)
                attention_mask = encoded['attention_mask'].to(self.device)
                
                # Get embeddings
                outputs = self.model(
                    input_ids=input_ids,
                    attention_mask=attention_mask
                )
                
                # Use [CLS] token embeddings (first token)
                batch_embeddings = outputs.last_hidden_state[:, 0, :].cpu().numpy()
                embeddings.append(batch_embeddings)
        
        return np.vstack(embeddings)
    
    def encode_single(self, text: str) -> np.ndarray:
        """Encode a single text into embedding"""
        return self.encode_text([text])[0]
    
    def compute_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """Compute cosine similarity between two embeddings"""
        # Normalize embeddings
        norm1 = np.linalg.norm(embedding1)
        norm2 = np.linalg.norm(embedding2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        # Cosine similarity
        similarity = np.dot(embedding1, embedding2) / (norm1 * norm2)
        return float(similarity)
    
    def save_model(self, save_path: str):
        """Save fine-tuned model"""
        try:
            os.makedirs(save_path, exist_ok=True)
            
            # Save model and tokenizer
            self.model.save_pretrained(save_path)
            self.tokenizer.save_pretrained(save_path)
            
            # Save configuration
            config = {
                'embedding_dim': self.embedding_dim,
                'max_length': self.max_length,
                'medical_vocab': list(self.medical_vocab),
                'device': str(self.device)
            }
            
            with open(os.path.join(save_path, 'custom_config.pkl'), 'wb') as f:
                pickle.dump(config, f)
            
            logger.info(f"Model saved to {save_path}")
            
        except Exception as e:
            logger.error(f"Failed to save model: {str(e)}")
            raise
    
    def load_custom_model(self, model_path: str):
        """Load custom fine-tuned model"""
        try:
            # Load configuration
            config_path = os.path.join(model_path, 'custom_config.pkl')
            if os.path.exists(config_path):
                with open(config_path, 'rb') as f:
                    config = pickle.load(f)
                
                self.embedding_dim = config.get('embedding_dim', 768)
                self.max_length = config.get('max_length', 512)
                self.medical_vocab = set(config.get('medical_vocab', []))
            
            # Load model and tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(model_path)
            self.model = AutoModel.from_pretrained(model_path)
            self.model.to(self.device)
            self.model.eval()
            
            logger.info(f"Custom model loaded from {model_path}")
            
        except Exception as e:
            logger.error(f"Failed to load custom model: {str(e)}")
            raise

class MedicalSentenceTransformer:
    """
    Custom Sentence-BERT model fine-tuned for medical domain
    """
    
    def __init__(self, model_path: Optional[str] = None):
        self.model_path = model_path or 'all-MiniLM-L6-v2'  # Base model for fine-tuning
        self.model = None
        self.embedding_dim = 384  # MiniLM dimension
        
        self._load_model()
    
    def _load_model(self):
        """Load Sentence-BERT model"""
        try:
            logger.info(f"Loading Sentence-BERT model: {self.model_path}")
            
            # Create cache directory
            cache_dir = './models/sentence_transformers'
            os.makedirs(cache_dir, exist_ok=True)
            
            self.model = SentenceTransformer(
                self.model_path,
                cache_folder=cache_dir
            )
            
            logger.info("Sentence-BERT model loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load Sentence-BERT model: {str(e)}")
            raise
    
    def encode_texts(self, texts: List[str], batch_size: int = 32) -> np.ndarray:
        """Encode texts using Sentence-BERT"""
        if not texts:
            return np.array([])
        
        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=False,
            convert_to_numpy=True
        )
        
        return embeddings
    
    def encode_single(self, text: str) -> np.ndarray:
        """Encode single text"""
        return self.model.encode([text])[0]
    
    def fine_tune_on_medical_data(self, training_data: List[Tuple[str, str]], 
                                  epochs: int = 3, batch_size: int = 16):
        """
        Fine-tune model on medical sentence pairs
        
        Args:
            training_data: List of (sentence1, sentence2) pairs
            epochs: Number of training epochs
            batch_size: Training batch size
        """
        try:
            from sentence_transformers import InputExample, losses
            from torch.utils.data import DataLoader
            
            # Prepare training examples
            train_examples = []
            for sent1, sent2 in training_data:
                train_examples.append(InputExample(texts=[sent1, sent2], label=1.0))
            
            # Create data loader
            train_dataloader = DataLoader(train_examples, shuffle=True, batch_size=batch_size)
            
            # Define loss function
            train_loss = losses.CosineSimilarityLoss(self.model)
            
            # Fine-tune
            logger.info(f"Fine-tuning Sentence-BERT on {len(training_data)} medical examples")
            self.model.fit(
                train_objectives=[(train_dataloader, train_loss)],
                epochs=epochs,
                warmup_steps=100,
                show_progress_bar=True
            )
            
            logger.info("Fine-tuning completed")
            
        except Exception as e:
            logger.error(f"Fine-tuning failed: {str(e)}")
            raise
    
    def save_model(self, save_path: str):
        """Save fine-tuned model"""
        try:
            self.model.save(save_path)
            logger.info(f"Sentence-BERT model saved to {save_path}")
        except Exception as e:
            logger.error(f"Failed to save model: {str(e)}")
            raise

class CustomWord2VecMedical:
    """
    Custom Word2Vec model trained on medical corpus
    """
    
    def __init__(self, vector_size: int = 300, window: int = 5, min_count: int = 2):
        self.vector_size = vector_size
        self.window = window
        self.min_count = min_count
        self.model = None
        self.vocab_size = 0
    
    def train_on_medical_corpus(self, medical_texts: List[str], epochs: int = 10):
        """
        Train Word2Vec on medical corpus
        
        Args:
            medical_texts: List of medical texts for training
            epochs: Number of training epochs
        """
        try:
            from gensim.models import Word2Vec
            from gensim.utils import simple_preprocess
            
            # Preprocess texts
            processed_texts = []
            for text in medical_texts:
                # Simple preprocessing
                tokens = simple_preprocess(text, deacc=True)
                processed_texts.append(tokens)
            
            logger.info(f"Training Word2Vec on {len(processed_texts)} medical documents")
            
            # Train Word2Vec model
            self.model = Word2Vec(
                sentences=processed_texts,
                vector_size=self.vector_size,
                window=self.window,
                min_count=self.min_count,
                workers=4,
                epochs=epochs,
                sg=1  # Skip-gram
            )
            
            self.vocab_size = len(self.model.wv.key_to_index)
            logger.info(f"Word2Vec training completed. Vocabulary size: {self.vocab_size}")
            
        except Exception as e:
            logger.error(f"Word2Vec training failed: {str(e)}")
            raise
    
    def get_word_embedding(self, word: str) -> Optional[np.ndarray]:
        """Get embedding for a single word"""
        if self.model and word in self.model.wv:
            return self.model.wv[word]
        return None
    
    def get_text_embedding(self, text: str) -> np.ndarray:
        """Get text embedding by averaging word embeddings"""
        if not self.model:
            return np.zeros(self.vector_size)
        
        from gensim.utils import simple_preprocess
        
        tokens = simple_preprocess(text, deacc=True)
        embeddings = []
        
        for token in tokens:
            if token in self.model.wv:
                embeddings.append(self.model.wv[token])
        
        if embeddings:
            return np.mean(embeddings, axis=0)
        else:
            return np.zeros(self.vector_size)
    
    def find_similar_words(self, word: str, topn: int = 10) -> List[Tuple[str, float]]:
        """Find similar words"""
        if self.model and word in self.model.wv:
            return self.model.wv.most_similar(word, topn=topn)
        return []
    
    def save_model(self, save_path: str):
        """Save Word2Vec model"""
        try:
            if self.model:
                self.model.save(save_path)
                logger.info(f"Word2Vec model saved to {save_path}")
        except Exception as e:
            logger.error(f"Failed to save Word2Vec model: {str(e)}")
            raise
    
    def load_model(self, model_path: str):
        """Load Word2Vec model"""
        try:
            from gensim.models import Word2Vec
            
            self.model = Word2Vec.load(model_path)
            self.vocab_size = len(self.model.wv.key_to_index)
            logger.info(f"Word2Vec model loaded from {model_path}")
            
        except Exception as e:
            logger.error(f"Failed to load Word2Vec model: {str(e)}")
            raise

class EmbeddingModelManager:
    """
    Manager class for all custom embedding models
    """
    
    def __init__(self, models_dir: str = './models'):
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(exist_ok=True)
        
        # Initialize models
        self.biobert = None
        self.sentence_bert = None
        self.word2vec = None
        
        # Model paths
        self.biobert_path = self.models_dir / 'biobert_custom'
        self.sentence_bert_path = self.models_dir / 'sentence_bert_medical'
        self.word2vec_path = self.models_dir / 'word2vec_medical.model'
    
    def initialize_models(self):
        """Initialize all embedding models"""
        try:
            logger.info("Initializing custom embedding models...")
            
            # Initialize BioBERT
            self.biobert = CustomBioBERTEmbeddings()
            
            # Initialize Sentence-BERT
            self.sentence_bert = MedicalSentenceTransformer()
            
            # Initialize Word2Vec
            self.word2vec = CustomWord2VecMedical()
            
            logger.info("All embedding models initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize models: {str(e)}")
            raise
    
    def get_embeddings(self, texts: List[str], model_type: str = 'biobert') -> np.ndarray:
        """
        Get embeddings using specified model
        
        Args:
            texts: List of texts to embed
            model_type: 'biobert', 'sentence_bert', or 'word2vec'
            
        Returns:
            numpy array of embeddings
        """
        if model_type == 'biobert' and self.biobert:
            return self.biobert.encode_text(texts)
        elif model_type == 'sentence_bert' and self.sentence_bert:
            return self.sentence_bert.encode_texts(texts)
        elif model_type == 'word2vec' and self.word2vec:
            return np.array([self.word2vec.get_text_embedding(text) for text in texts])
        else:
            raise ValueError(f"Unknown model type: {model_type}")
    
    def save_all_models(self):
        """Save all trained models"""
        try:
            if self.biobert:
                self.biobert.save_model(str(self.biobert_path))
            
            if self.sentence_bert:
                self.sentence_bert.save_model(str(self.sentence_bert_path))
            
            if self.word2vec:
                self.word2vec.save_model(str(self.word2vec_path))
            
            logger.info("All models saved successfully")
            
        except Exception as e:
            logger.error(f"Failed to save models: {str(e)}")
            raise
    
    def load_all_models(self):
        """Load all saved models"""
        try:
            # Load BioBERT if exists
            if self.biobert_path.exists():
                self.biobert = CustomBioBERTEmbeddings()
                self.biobert.load_custom_model(str(self.biobert_path))
            
            # Load Sentence-BERT if exists
            if self.sentence_bert_path.exists():
                self.sentence_bert = MedicalSentenceTransformer(str(self.sentence_bert_path))
            
            # Load Word2Vec if exists
            if self.word2vec_path.exists():
                self.word2vec = CustomWord2VecMedical()
                self.word2vec.load_model(str(self.word2vec_path))
            
            logger.info("All available models loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load models: {str(e)}")
            raise