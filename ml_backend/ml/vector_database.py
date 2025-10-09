"""
Custom Vector Database Implementation
FAISS, Annoy, and Hnswlib implementations for on-premise vector search
"""

import numpy as np
import faiss
import pickle
import os
import json
import logging
from typing import List, Dict, Tuple, Optional, Any
from pathlib import Path
import time
from dataclasses import dataclass
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

@dataclass
class VectorSearchResult:
    """Result from vector search"""
    doc_id: str
    score: float
    metadata: Dict[str, Any]
    content: str

@dataclass
class DocumentVector:
    """Document with its vector representation"""
    doc_id: str
    content: str
    vector: np.ndarray
    metadata: Dict[str, Any]

class BaseVectorDatabase(ABC):
    """Abstract base class for vector databases"""
    
    @abstractmethod
    def add_vectors(self, documents: List[DocumentVector]) -> None:
        """Add vectors to the database"""
        pass
    
    @abstractmethod
    def search(self, query_vector: np.ndarray, k: int = 10) -> List[VectorSearchResult]:
        """Search for similar vectors"""
        pass
    
    @abstractmethod
    def save_index(self, path: str) -> None:
        """Save index to disk"""
        pass
    
    @abstractmethod
    def load_index(self, path: str) -> None:
        """Load index from disk"""
        pass

class CustomFAISSDatabase(BaseVectorDatabase):
    """
    Custom FAISS-based vector database for medical documents
    Optimized for similarity search with medical embeddings
    """
    
    def __init__(self, dimension: int, index_type: str = 'flat'):
        self.dimension = dimension
        self.index_type = index_type
        self.index = None
        self.documents = {}  # doc_id -> DocumentVector
        self.doc_ids = []    # Ordered list of doc_ids
        self.metadata = {}   # doc_id -> metadata
        
        self._create_index()
    
    def _create_index(self):
        """Create FAISS index based on type"""
        try:
            if self.index_type == 'flat':
                # Exact search using L2 distance
                self.index = faiss.IndexFlatL2(self.dimension)
            elif self.index_type == 'ivf':
                # Inverted file index for faster search
                quantizer = faiss.IndexFlatL2(self.dimension)
                self.index = faiss.IndexIVFFlat(quantizer, self.dimension, 100)
            elif self.index_type == 'hnsw':
                # Hierarchical Navigable Small World
                self.index = faiss.IndexHNSWFlat(self.dimension, 32)
                self.index.hnsw.efConstruction = 200
                self.index.hnsw.efSearch = 100
            elif self.index_type == 'pq':
                # Product Quantization for memory efficiency
                self.index = faiss.IndexPQ(self.dimension, 8, 8)
            else:
                raise ValueError(f"Unknown index type: {self.index_type}")
            
            logger.info(f"Created FAISS index: {self.index_type}, dimension: {self.dimension}")
            
        except Exception as e:
            logger.error(f"Failed to create FAISS index: {str(e)}")
            raise
    
    def add_vectors(self, documents: List[DocumentVector]) -> None:
        """Add document vectors to FAISS index"""
        try:
            if not documents:
                return
            
            # Prepare vectors and metadata
            vectors = []
            for doc in documents:
                if doc.vector.shape[0] != self.dimension:
                    raise ValueError(f"Vector dimension mismatch: expected {self.dimension}, got {doc.vector.shape[0]}")
                
                vectors.append(doc.vector)
                self.documents[doc.doc_id] = doc
                self.doc_ids.append(doc.doc_id)
                self.metadata[doc.doc_id] = doc.metadata
            
            # Convert to numpy array
            vectors_array = np.array(vectors, dtype=np.float32)
            
            # Train index if needed (for IVF)
            if self.index_type == 'ivf' and not self.index.is_trained:
                logger.info("Training IVF index...")
                self.index.train(vectors_array)
            
            # Add vectors to index
            self.index.add(vectors_array)
            
            logger.info(f"Added {len(documents)} vectors to FAISS index. Total: {self.index.ntotal}")
            
        except Exception as e:
            logger.error(f"Failed to add vectors to FAISS: {str(e)}")
            raise
    
    def search(self, query_vector: np.ndarray, k: int = 10) -> List[VectorSearchResult]:
        """Search for similar vectors using FAISS"""
        try:
            if self.index.ntotal == 0:
                return []
            
            # Ensure query vector is correct shape
            if query_vector.ndim == 1:
                query_vector = query_vector.reshape(1, -1)
            
            query_vector = query_vector.astype(np.float32)
            
            # Search
            distances, indices = self.index.search(query_vector, min(k, self.index.ntotal))
            
            # Convert results
            results = []
            for i, (distance, idx) in enumerate(zip(distances[0], indices[0])):
                if idx == -1:  # FAISS returns -1 for invalid results
                    continue
                
                doc_id = self.doc_ids[idx]
                doc = self.documents[doc_id]
                
                # Convert L2 distance to similarity score (0-1)
                similarity_score = 1.0 / (1.0 + distance)
                
                results.append(VectorSearchResult(
                    doc_id=doc_id,
                    score=similarity_score,
                    metadata=doc.metadata,
                    content=doc.content
                ))
            
            return results
            
        except Exception as e:
            logger.error(f"FAISS search failed: {str(e)}")
            return []
    
    def search_with_filter(self, query_vector: np.ndarray, k: int = 10, 
                          metadata_filter: Optional[Dict[str, Any]] = None) -> List[VectorSearchResult]:
        """Search with metadata filtering"""
        try:
            # Get all results first
            all_results = self.search(query_vector, k * 3)  # Get more to account for filtering
            
            if not metadata_filter:
                return all_results[:k]
            
            # Filter results based on metadata
            filtered_results = []
            for result in all_results:
                match = True
                for key, value in metadata_filter.items():
                    if key not in result.metadata or result.metadata[key] != value:
                        match = False
                        break
                
                if match:
                    filtered_results.append(result)
                
                if len(filtered_results) >= k:
                    break
            
            return filtered_results
            
        except Exception as e:
            logger.error(f"Filtered search failed: {str(e)}")
            return []
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics"""
        return {
            'total_vectors': self.index.ntotal if self.index else 0,
            'dimension': self.dimension,
            'index_type': self.index_type,
            'memory_usage_mb': self.index.ntotal * self.dimension * 4 / (1024 * 1024) if self.index else 0
        }
    
    def save_index(self, path: str) -> None:
        """Save FAISS index and metadata to disk"""
        try:
            os.makedirs(path, exist_ok=True)
            
            # Save FAISS index
            index_path = os.path.join(path, 'faiss_index.bin')
            faiss.write_index(self.index, index_path)
            
            # Save metadata
            metadata_path = os.path.join(path, 'metadata.pkl')
            with open(metadata_path, 'wb') as f:
                pickle.dump({
                    'documents': self.documents,
                    'doc_ids': self.doc_ids,
                    'metadata': self.metadata,
                    'dimension': self.dimension,
                    'index_type': self.index_type
                }, f)
            
            # Save configuration
            config_path = os.path.join(path, 'config.json')
            with open(config_path, 'w') as f:
                json.dump({
                    'dimension': self.dimension,
                    'index_type': self.index_type,
                    'total_vectors': self.index.ntotal,
                    'created_at': time.time()
                }, f, indent=2)
            
            logger.info(f"FAISS index saved to {path}")
            
        except Exception as e:
            logger.error(f"Failed to save FAISS index: {str(e)}")
            raise
    
    def load_index(self, path: str) -> None:
        """Load FAISS index and metadata from disk"""
        try:
            # Load FAISS index
            index_path = os.path.join(path, 'faiss_index.bin')
            if not os.path.exists(index_path):
                raise FileNotFoundError(f"FAISS index not found: {index_path}")
            
            self.index = faiss.read_index(index_path)
            
            # Load metadata
            metadata_path = os.path.join(path, 'metadata.pkl')
            with open(metadata_path, 'rb') as f:
                data = pickle.load(f)
                self.documents = data['documents']
                self.doc_ids = data['doc_ids']
                self.metadata = data['metadata']
                self.dimension = data['dimension']
                self.index_type = data['index_type']
            
            logger.info(f"FAISS index loaded from {path}. Total vectors: {self.index.ntotal}")
            
        except Exception as e:
            logger.error(f"Failed to load FAISS index: {str(e)}")
            raise

class CustomAnnoyDatabase(BaseVectorDatabase):
    """
    Custom Annoy-based vector database
    Memory-efficient approximate nearest neighbor search
    """
    
    def __init__(self, dimension: int, metric: str = 'angular', n_trees: int = 10):
        self.dimension = dimension
        self.metric = metric
        self.n_trees = n_trees
        self.index = None
        self.documents = {}
        self.doc_ids = []
        self.is_built = False
        
        self._create_index()
    
    def _create_index(self):
        """Create Annoy index"""
        try:
            from annoy import AnnoyIndex
            
            self.index = AnnoyIndex(self.dimension, self.metric)
            logger.info(f"Created Annoy index: dimension={self.dimension}, metric={self.metric}")
            
        except ImportError:
            logger.error("Annoy not installed. Install with: pip install annoy")
            raise
        except Exception as e:
            logger.error(f"Failed to create Annoy index: {str(e)}")
            raise
    
    def add_vectors(self, documents: List[DocumentVector]) -> None:
        """Add vectors to Annoy index"""
        try:
            if self.is_built:
                raise RuntimeError("Cannot add vectors to built Annoy index. Create new index.")
            
            for i, doc in enumerate(documents):
                if doc.vector.shape[0] != self.dimension:
                    raise ValueError(f"Vector dimension mismatch: expected {self.dimension}, got {doc.vector.shape[0]}")
                
                # Add vector to index
                current_idx = len(self.doc_ids)
                self.index.add_item(current_idx, doc.vector.tolist())
                
                # Store metadata
                self.documents[doc.doc_id] = doc
                self.doc_ids.append(doc.doc_id)
            
            logger.info(f"Added {len(documents)} vectors to Annoy index")
            
        except Exception as e:
            logger.error(f"Failed to add vectors to Annoy: {str(e)}")
            raise
    
    def build_index(self):
        """Build Annoy index (required before searching)"""
        try:
            if not self.doc_ids:
                logger.warning("No vectors to build index")
                return
            
            logger.info(f"Building Annoy index with {self.n_trees} trees...")
            self.index.build(self.n_trees)
            self.is_built = True
            
            logger.info(f"Annoy index built successfully. Total items: {len(self.doc_ids)}")
            
        except Exception as e:
            logger.error(f"Failed to build Annoy index: {str(e)}")
            raise
    
    def search(self, query_vector: np.ndarray, k: int = 10) -> List[VectorSearchResult]:
        """Search using Annoy index"""
        try:
            if not self.is_built:
                self.build_index()
            
            if not self.doc_ids:
                return []
            
            # Search
            indices, distances = self.index.get_nns_by_vector(
                query_vector.tolist(), 
                min(k, len(self.doc_ids)), 
                include_distances=True
            )
            
            # Convert results
            results = []
            for idx, distance in zip(indices, distances):
                doc_id = self.doc_ids[idx]
                doc = self.documents[doc_id]
                
                # Convert distance to similarity score
                if self.metric == 'angular':
                    # Angular distance to cosine similarity
                    similarity_score = 1.0 - (distance / 2.0)
                else:
                    # Euclidean distance to similarity
                    similarity_score = 1.0 / (1.0 + distance)
                
                results.append(VectorSearchResult(
                    doc_id=doc_id,
                    score=max(0.0, similarity_score),
                    metadata=doc.metadata,
                    content=doc.content
                ))
            
            return results
            
        except Exception as e:
            logger.error(f"Annoy search failed: {str(e)}")
            return []
    
    def save_index(self, path: str) -> None:
        """Save Annoy index"""
        try:
            if not self.is_built:
                self.build_index()
            
            os.makedirs(path, exist_ok=True)
            
            # Save Annoy index
            index_path = os.path.join(path, 'annoy_index.ann')
            self.index.save(index_path)
            
            # Save metadata
            metadata_path = os.path.join(path, 'metadata.pkl')
            with open(metadata_path, 'wb') as f:
                pickle.dump({
                    'documents': self.documents,
                    'doc_ids': self.doc_ids,
                    'dimension': self.dimension,
                    'metric': self.metric,
                    'n_trees': self.n_trees
                }, f)
            
            logger.info(f"Annoy index saved to {path}")
            
        except Exception as e:
            logger.error(f"Failed to save Annoy index: {str(e)}")
            raise
    
    def load_index(self, path: str) -> None:
        """Load Annoy index"""
        try:
            from annoy import AnnoyIndex
            
            # Load metadata first
            metadata_path = os.path.join(path, 'metadata.pkl')
            with open(metadata_path, 'rb') as f:
                data = pickle.load(f)
                self.documents = data['documents']
                self.doc_ids = data['doc_ids']
                self.dimension = data['dimension']
                self.metric = data['metric']
                self.n_trees = data['n_trees']
            
            # Load Annoy index
            self.index = AnnoyIndex(self.dimension, self.metric)
            index_path = os.path.join(path, 'annoy_index.ann')
            self.index.load(index_path)
            self.is_built = True
            
            logger.info(f"Annoy index loaded from {path}. Total items: {len(self.doc_ids)}")
            
        except Exception as e:
            logger.error(f"Failed to load Annoy index: {str(e)}")
            raise

class CustomHnswlibDatabase(BaseVectorDatabase):
    """
    Custom Hnswlib-based vector database
    Fast approximate nearest neighbor search
    """
    
    def __init__(self, dimension: int, space: str = 'cosine', max_elements: int = 10000):
        self.dimension = dimension
        self.space = space
        self.max_elements = max_elements
        self.index = None
        self.documents = {}
        self.doc_ids = []
        self.current_count = 0
        
        self._create_index()
    
    def _create_index(self):
        """Create Hnswlib index"""
        try:
            import hnswlib
            
            self.index = hnswlib.Index(space=self.space, dim=self.dimension)
            self.index.init_index(max_elements=self.max_elements, ef_construction=200, M=16)
            self.index.set_ef(50)  # ef should always be > k
            
            logger.info(f"Created Hnswlib index: dimension={self.dimension}, space={self.space}")
            
        except ImportError:
            logger.error("Hnswlib not installed. Install with: pip install hnswlib")
            raise
        except Exception as e:
            logger.error(f"Failed to create Hnswlib index: {str(e)}")
            raise
    
    def add_vectors(self, documents: List[DocumentVector]) -> None:
        """Add vectors to Hnswlib index"""
        try:
            if self.current_count + len(documents) > self.max_elements:
                # Resize index if needed
                new_max = max(self.max_elements * 2, self.current_count + len(documents))
                self.index.resize_index(new_max)
                self.max_elements = new_max
                logger.info(f"Resized Hnswlib index to {new_max} elements")
            
            # Prepare data
            vectors = []
            labels = []
            
            for doc in documents:
                if doc.vector.shape[0] != self.dimension:
                    raise ValueError(f"Vector dimension mismatch: expected {self.dimension}, got {doc.vector.shape[0]}")
                
                vectors.append(doc.vector)
                labels.append(self.current_count)
                
                # Store metadata
                self.documents[doc.doc_id] = doc
                self.doc_ids.append(doc.doc_id)
                self.current_count += 1
            
            # Add to index
            vectors_array = np.array(vectors, dtype=np.float32)
            self.index.add_items(vectors_array, labels)
            
            logger.info(f"Added {len(documents)} vectors to Hnswlib index. Total: {self.current_count}")
            
        except Exception as e:
            logger.error(f"Failed to add vectors to Hnswlib: {str(e)}")
            raise
    
    def search(self, query_vector: np.ndarray, k: int = 10) -> List[VectorSearchResult]:
        """Search using Hnswlib index"""
        try:
            if self.current_count == 0:
                return []
            
            # Ensure ef is larger than k
            self.index.set_ef(max(k + 10, 50))
            
            # Search
            labels, distances = self.index.knn_query(
                query_vector.reshape(1, -1).astype(np.float32), 
                k=min(k, self.current_count)
            )
            
            # Convert results
            results = []
            for label, distance in zip(labels[0], distances[0]):
                doc_id = self.doc_ids[label]
                doc = self.documents[doc_id]
                
                # Convert distance to similarity score
                if self.space == 'cosine':
                    similarity_score = 1.0 - distance
                else:  # l2
                    similarity_score = 1.0 / (1.0 + distance)
                
                results.append(VectorSearchResult(
                    doc_id=doc_id,
                    score=max(0.0, similarity_score),
                    metadata=doc.metadata,
                    content=doc.content
                ))
            
            return results
            
        except Exception as e:
            logger.error(f"Hnswlib search failed: {str(e)}")
            return []
    
    def save_index(self, path: str) -> None:
        """Save Hnswlib index"""
        try:
            os.makedirs(path, exist_ok=True)
            
            # Save Hnswlib index
            index_path = os.path.join(path, 'hnswlib_index.bin')
            self.index.save_index(index_path)
            
            # Save metadata
            metadata_path = os.path.join(path, 'metadata.pkl')
            with open(metadata_path, 'wb') as f:
                pickle.dump({
                    'documents': self.documents,
                    'doc_ids': self.doc_ids,
                    'dimension': self.dimension,
                    'space': self.space,
                    'max_elements': self.max_elements,
                    'current_count': self.current_count
                }, f)
            
            logger.info(f"Hnswlib index saved to {path}")
            
        except Exception as e:
            logger.error(f"Failed to save Hnswlib index: {str(e)}")
            raise
    
    def load_index(self, path: str) -> None:
        """Load Hnswlib index"""
        try:
            import hnswlib
            
            # Load metadata first
            metadata_path = os.path.join(path, 'metadata.pkl')
            with open(metadata_path, 'rb') as f:
                data = pickle.load(f)
                self.documents = data['documents']
                self.doc_ids = data['doc_ids']
                self.dimension = data['dimension']
                self.space = data['space']
                self.max_elements = data['max_elements']
                self.current_count = data['current_count']
            
            # Load Hnswlib index
            self.index = hnswlib.Index(space=self.space, dim=self.dimension)
            index_path = os.path.join(path, 'hnswlib_index.bin')
            self.index.load_index(index_path, max_elements=self.max_elements)
            
            logger.info(f"Hnswlib index loaded from {path}. Total items: {self.current_count}")
            
        except Exception as e:
            logger.error(f"Failed to load Hnswlib index: {str(e)}")
            raise

class VectorDatabaseManager:
    """
    Manager for multiple vector database implementations
    """
    
    def __init__(self, dimension: int, db_dir: str = './vector_db'):
        self.dimension = dimension
        self.db_dir = Path(db_dir)
        self.db_dir.mkdir(exist_ok=True)
        
        # Initialize databases
        self.faiss_db = CustomFAISSDatabase(dimension, 'hnsw')
        self.annoy_db = CustomAnnoyDatabase(dimension, 'angular')
        self.hnswlib_db = CustomHnswlibDatabase(dimension, 'cosine')
        
        self.active_db = 'faiss'  # Default database
    
    def add_documents(self, documents: List[DocumentVector], db_type: str = None):
        """Add documents to specified database"""
        db_type = db_type or self.active_db
        
        if db_type == 'faiss':
            self.faiss_db.add_vectors(documents)
        elif db_type == 'annoy':
            self.annoy_db.add_vectors(documents)
        elif db_type == 'hnswlib':
            self.hnswlib_db.add_vectors(documents)
        else:
            raise ValueError(f"Unknown database type: {db_type}")
    
    def search(self, query_vector: np.ndarray, k: int = 10, db_type: str = None) -> List[VectorSearchResult]:
        """Search in specified database"""
        db_type = db_type or self.active_db
        
        if db_type == 'faiss':
            return self.faiss_db.search(query_vector, k)
        elif db_type == 'annoy':
            return self.annoy_db.search(query_vector, k)
        elif db_type == 'hnswlib':
            return self.hnswlib_db.search(query_vector, k)
        else:
            raise ValueError(f"Unknown database type: {db_type}")
    
    def ensemble_search(self, query_vector: np.ndarray, k: int = 10) -> List[VectorSearchResult]:
        """
        Ensemble search across all databases with score fusion
        """
        try:
            # Get results from all databases
            faiss_results = self.faiss_db.search(query_vector, k)
            annoy_results = self.annoy_db.search(query_vector, k)
            hnswlib_results = self.hnswlib_db.search(query_vector, k)
            
            # Combine and re-rank results
            all_results = {}
            
            # Add FAISS results with weight
            for result in faiss_results:
                if result.doc_id not in all_results:
                    all_results[result.doc_id] = {
                        'result': result,
                        'scores': [],
                        'count': 0
                    }
                all_results[result.doc_id]['scores'].append(result.score * 0.4)  # FAISS weight
                all_results[result.doc_id]['count'] += 1
            
            # Add Annoy results with weight
            for result in annoy_results:
                if result.doc_id not in all_results:
                    all_results[result.doc_id] = {
                        'result': result,
                        'scores': [],
                        'count': 0
                    }
                all_results[result.doc_id]['scores'].append(result.score * 0.3)  # Annoy weight
                all_results[result.doc_id]['count'] += 1
            
            # Add Hnswlib results with weight
            for result in hnswlib_results:
                if result.doc_id not in all_results:
                    all_results[result.doc_id] = {
                        'result': result,
                        'scores': [],
                        'count': 0
                    }
                all_results[result.doc_id]['scores'].append(result.score * 0.3)  # Hnswlib weight
                all_results[result.doc_id]['count'] += 1
            
            # Calculate ensemble scores
            ensemble_results = []
            for doc_id, data in all_results.items():
                # Average score with bonus for appearing in multiple databases
                avg_score = sum(data['scores']) / len(data['scores'])
                ensemble_score = avg_score * (1 + 0.1 * (data['count'] - 1))  # Bonus for consensus
                
                result = data['result']
                result.score = min(1.0, ensemble_score)  # Cap at 1.0
                ensemble_results.append(result)
            
            # Sort by ensemble score and return top k
            ensemble_results.sort(key=lambda x: x.score, reverse=True)
            return ensemble_results[:k]
            
        except Exception as e:
            logger.error(f"Ensemble search failed: {str(e)}")
            # Fallback to FAISS
            return self.faiss_db.search(query_vector, k)
    
    def save_all_databases(self):
        """Save all databases"""
        try:
            self.faiss_db.save_index(str(self.db_dir / 'faiss'))
            self.annoy_db.save_index(str(self.db_dir / 'annoy'))
            self.hnswlib_db.save_index(str(self.db_dir / 'hnswlib'))
            
            logger.info("All vector databases saved successfully")
            
        except Exception as e:
            logger.error(f"Failed to save databases: {str(e)}")
            raise
    
    def load_all_databases(self):
        """Load all databases"""
        try:
            faiss_path = self.db_dir / 'faiss'
            if faiss_path.exists():
                self.faiss_db.load_index(str(faiss_path))
            
            annoy_path = self.db_dir / 'annoy'
            if annoy_path.exists():
                self.annoy_db.load_index(str(annoy_path))
            
            hnswlib_path = self.db_dir / 'hnswlib'
            if hnswlib_path.exists():
                self.hnswlib_db.load_index(str(hnswlib_path))
            
            logger.info("All available vector databases loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load databases: {str(e)}")
            raise
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics for all databases"""
        return {
            'faiss': self.faiss_db.get_statistics(),
            'annoy': {
                'total_vectors': len(self.annoy_db.doc_ids),
                'dimension': self.annoy_db.dimension,
                'metric': self.annoy_db.metric,
                'is_built': self.annoy_db.is_built
            },
            'hnswlib': {
                'total_vectors': self.hnswlib_db.current_count,
                'dimension': self.hnswlib_db.dimension,
                'space': self.hnswlib_db.space,
                'max_elements': self.hnswlib_db.max_elements
            }
        }