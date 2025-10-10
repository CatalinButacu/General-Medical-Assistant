"""Custom RAG Pipeline for Medical Assistant
Combines BioBERT embeddings with FAISS vector search and medical knowledge
"""

import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from .custom_embeddings import MedicalEmbeddingManager
from .vector_database import VectorDatabaseManager

logger = logging.getLogger(__name__)


@dataclass
class RAGDocument:
    """Document for RAG system"""
    doc_id: str
    title: str
    content: str
    doc_type: str  # 'medicine', 'condition', 'interaction', 'safety'
    metadata: Dict[str, Any]


@dataclass
class RAGQuery:
    """Query for RAG system"""
    text: str
    user_context: Optional[Dict[str, Any]] = None
    query_type: str = 'general'
    max_results: int = 5


@dataclass
class RAGResponse:
    """Response from RAG system"""
    query: str
    answer: str
    retrieved_documents: List[Dict[str, Any]]
    confidence_score: float
    response_time_ms: int


class MedicalKnowledgeBase:
    """Medical knowledge base for RAG system"""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.medicine_db = {}
        self.safety_db = {}
        self.interaction_db = {}
        self._load_knowledge_base()

    def _load_knowledge_base(self):
        """Load medical knowledge base from files"""
        try:
            # Load medicine data
            medicine_file = self.data_dir / "medical_classification.json"
            if medicine_file.exists():
                with open(medicine_file, 'r') as f:
                    medicines = json.load(f)
                    for med in medicines:
                        self.medicine_db[med['medicine_name']] = med

            # Load safety data
            safety_file = self.data_dir / "medical_safety.json"
            if safety_file.exists():
                with open(safety_file, 'r') as f:
                    self.safety_db = json.load(f)

            # Load interaction data
            interaction_file = self.data_dir / "medical_interactions.json"
            if interaction_file.exists():
                with open(interaction_file, 'r') as f:
                    self.interaction_db = json.load(f)

            logger.info("Medical knowledge base loaded successfully")

        except Exception as e:
            logger.error(f"Failed to load knowledge base: {str(e)}")

    def get_medicine_info(self, medicine_name: str) -> Optional[Dict]:
        """Get medicine information"""
        return self.medicine_db.get(medicine_name.lower())

    def check_safety(self, medicine: str, condition: str) -> Dict:
        """Check safety information"""
        safety_key = f"{medicine.lower()}_{condition.lower()}"
        return self.safety_db.get(safety_key, {
            'safe': True,
            'warnings': [],
            'contraindications': []
        })

    def check_interactions(self, medicines: List[str]) -> List[Dict]:
        """Check drug interactions"""
        interactions = []
        for i, med1 in enumerate(medicines):
            for med2 in medicines[i + 1:]:
                interaction_key = f"{med1.lower()}_{med2.lower()}"
                reverse_key = f"{med2.lower()}_{med1.lower()}"

                interaction = (
                    self.interaction_db.get(interaction_key) or
                    self.interaction_db.get(reverse_key)
                )

                if interaction:
                    interactions.append(interaction)

        return interactions


class CustomRAGPipeline:
    """
    Custom RAG Pipeline for medical queries
    Uses local embeddings and vector database
    """

    def __init__(self, data_dir: str = "data", models_dir: str = "models"):
        self.data_dir = Path(data_dir)
        self.models_dir = Path(models_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.models_dir.mkdir(exist_ok=True)

        # Initialize components
        self.embedding_manager = MedicalEmbeddingManager(str(self.models_dir))
        self.vector_db_manager = VectorDatabaseManager()
        self.knowledge_base = MedicalKnowledgeBase(str(self.data_dir))

        # Pipeline state
        self.is_initialized = False
        self.documents = []
        self.model_version = "1.0.0"
        self.embedding_dim = 768

    def initialize(self):
        """Initialize the RAG pipeline"""
        try:
            logger.info("Initializing RAG pipeline...")

            # Initialize embedding manager
            self.embedding_manager.initialize()

            # Initialize vector database
            self.vector_db_manager.initialize()

            # Load existing documents
            self._load_documents()

            self.is_initialized = True
            logger.info("RAG pipeline initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize RAG pipeline: {str(e)}")
            raise

    def _load_documents(self):
        """Load documents from data directory"""
        try:
            documents_file = self.data_dir / "medical_knowledge_base.json"
            if documents_file.exists():
                with open(documents_file, 'r') as f:
                    docs_data = json.load(f)

                for doc_data in docs_data:
                    doc = RAGDocument(
                        doc_id=doc_data['id'],
                        title=doc_data['title'],
                        content=doc_data['content'],
                        doc_type=doc_data.get('category', 'general'),
                        metadata=doc_data.get('metadata', {})
                    )
                    self.documents.append(doc)

                logger.info(f"Loaded {len(self.documents)} documents")

        except Exception as e:
            logger.error(f"Failed to load documents: {str(e)}")

    def add_document(self, document: RAGDocument):
        """Add document to the pipeline"""
        if not self.is_initialized:
            self.initialize()

        try:
            # Generate embedding
            embedding = self.embedding_manager.encode_text(
                document.content, model_type='biobert'
            )

            # Add to vector database
            self.vector_db_manager.add_document(
                doc_id=document.doc_id,
                content=document.content,
                embedding=embedding,
                metadata={
                    'title': document.title,
                    'doc_type': document.doc_type,
                    **document.metadata
                }
            )

            # Add to documents list
            self.documents.append(document)

            logger.info(f"Added document: {document.doc_id}")

        except Exception as e:
            logger.error(f"Failed to add document: {str(e)}")
            raise

    def search_documents(
        self, query: str, max_results: int = 5
    ) -> List[Dict[str, Any]]:
        """Search documents using vector similarity"""
        if not self.is_initialized:
            self.initialize()

        try:
            # Generate query embedding
            query_embedding = self.embedding_manager.encode_text(
                query, model_type='biobert'
            )

            # Search vector database
            results = self.vector_db_manager.search(
                query_embedding=query_embedding,
                top_k=max_results
            )

            # Format results
            formatted_results = []
            for result in results:
                content = result.content
                if len(content) > 500:
                    content = content[:500] + "..."

                formatted_results.append({
                    'doc_id': result.doc_id,
                    'content': content,
                    'score': result.score,
                    'metadata': result.metadata
                })

            return formatted_results

        except Exception as e:
            logger.error(f"Failed to search documents: {str(e)}")
            raise

    def query(self, query: RAGQuery) -> RAGResponse:
        """Process RAG query and generate response"""
        if not self.is_initialized:
            self.initialize()

        start_time = time.time()

        try:
            # Search relevant documents
            retrieved_docs = self.search_documents(
                query.text, query.max_results
            )

            # Generate answer based on retrieved documents
            answer = self._generate_answer(query, retrieved_docs)

            # Calculate confidence score
            confidence = self._calculate_confidence(query, retrieved_docs)

            # Calculate response time
            response_time = int((time.time() - start_time) * 1000)

            return RAGResponse(
                query=query.text,
                answer=answer,
                retrieved_documents=retrieved_docs,
                confidence_score=confidence,
                response_time_ms=response_time
            )

        except Exception as e:
            logger.error(f"Failed to process query: {str(e)}")
            raise

    def _generate_answer(
        self, query: RAGQuery, docs: List[Dict[str, Any]]
    ) -> str:
        """Generate answer based on retrieved documents"""
        if not docs:
            return (
                "I don't have enough information to answer your question. "
                "Please consult with a healthcare professional."
            )

        # Extract medicine name if present
        medicine_name = self._extract_medicine_name(query.text)

        # Check for specific medicine information
        if medicine_name:
            medicine_info = self.knowledge_base.get_medicine_info(
                medicine_name
            )
            if medicine_info:
                return self._format_medicine_response(
                    medicine_info, query, docs
                )

        # Generate general response based on documents
        return self._format_general_response(query, docs)

    def _extract_medicine_name(self, text: str) -> Optional[str]:
        """Extract medicine name from query text"""
        text_lower = text.lower()
        for medicine in self.knowledge_base.medicine_db.keys():
            if medicine.lower() in text_lower:
                return medicine
        return None

    def _format_medicine_response(
        self, medicine_info: Dict, query: RAGQuery, docs: List[Dict]
    ) -> str:
        """Format response for medicine-specific queries"""
        response_parts = []

        # Basic medicine information
        response_parts.append(
            f"{medicine_info['medicine_name']} is a "
            f"{medicine_info['category'].lower()} medication."
        )

        if 'description' in medicine_info:
            response_parts.append(medicine_info['description'])

        # Add relevant document information
        if docs:
            response_parts.append(
                "Additional information from medical sources:"
            )
            for doc in docs[:2]:  # Limit to top 2 documents
                response_parts.append(f" {doc['content'][:200]}...")

        # Safety reminder
        response_parts.append(
            "Please consult with a healthcare professional before "
            "taking any medication."
        )

        return " ".join(response_parts)

    def _format_general_response(
        self, query: RAGQuery, docs: List[Dict]
    ) -> str:
        """Format general response based on documents"""
        if not docs:
            return (
                "I don't have specific information about your query. "
                "Please consult with a healthcare professional."
            )

        # Combine information from top documents
        response_parts = []
        for doc in docs[:3]:  # Use top 3 documents
            content = doc['content']
            if len(content) > 300:
                content = content[:300] + "..."
            response_parts.append(content)

        response = " ".join(response_parts)

        # Add safety disclaimer
        response += (
            " Please consult with a healthcare professional for "
            "personalized medical advice."
        )

        return response

    def _calculate_confidence(
        self, query: RAGQuery, docs: List[Dict]
    ) -> float:
        """Calculate confidence score for the response"""
        if not docs:
            return 0.1

        # Base confidence on similarity scores
        avg_similarity = sum(doc['score'] for doc in docs) / len(docs)

        # Boost confidence if we have multiple relevant documents
        doc_count_boost = min(0.2, len(docs) * 0.05)

        # Boost confidence for specific medicine queries
        if self._extract_medicine_name(query.text):
            medicine_boost = 0.1
        else:
            medicine_boost = 0.0

        confidence = min(1.0, avg_similarity + doc_count_boost + medicine_boost)
        return round(confidence, 3)

    def get_statistics(self) -> Dict[str, Any]:
        """Get pipeline statistics"""
        return {
            'model_version': self.model_version,
            'is_initialized': self.is_initialized,
            'total_documents': len(self.documents),
            'embedding_dimension': self.embedding_dim,
            'vector_db_stats': self.vector_db_manager.get_statistics(),
            'knowledge_base_stats': {
                'medicines': len(self.knowledge_base.medicine_db),
                'safety_categories': len(self.knowledge_base.safety_db),
                'interactions': len(self.knowledge_base.interaction_db)
            }
        }
