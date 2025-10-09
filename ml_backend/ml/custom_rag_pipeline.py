"""
Custom RAG Pipeline Implementation
On-premise RAG system using custom embeddings and vector databases
No external API dependencies - fully self-contained ML system
"""

import numpy as np
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import time
import json
from pathlib import Path

from .custom_embeddings import EmbeddingModelManager
from .vector_database import VectorDatabaseManager, DocumentVector, VectorSearchResult

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
    query_type: str = 'general'  # 'medicine', 'safety', 'interaction', 'general'
    max_results: int = 5

@dataclass
class RAGResponse:
    """Response from RAG system"""
    query: str
    answer: str
    retrieved_documents: List[VectorSearchResult]
    confidence_score: float
    response_time_ms: int
    model_version: str

class MedicalKnowledgeBase:
    """
    Medical knowledge base with structured medical information
    """
    
    def __init__(self, data_dir: str = './medical_data'):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        # Medical knowledge categories
        self.medicine_db = {}
        self.condition_db = {}
        self.interaction_db = {}
        self.safety_db = {}
        
        self._load_medical_data()
    
    def _load_medical_data(self):
        """Load medical knowledge from structured data"""
        try:
            # Sample medical data - in production, load from comprehensive medical databases
            self.medicine_db = {
                'acetaminophen': {
                    'generic_name': 'acetaminophen',
                    'brand_names': ['Tylenol', 'Panadol'],
                    'drug_class': 'analgesic',
                    'indications': ['pain relief', 'fever reduction'],
                    'contraindications': ['severe liver disease', 'alcohol dependency'],
                    'pregnancy_category': 'B',
                    'breastfeeding_safe': True,
                    'max_daily_dose': '4000mg',
                    'side_effects': ['nausea', 'liver damage (overdose)'],
                    'interactions': ['warfarin', 'alcohol']
                },
                'ibuprofen': {
                    'generic_name': 'ibuprofen',
                    'brand_names': ['Advil', 'Motrin'],
                    'drug_class': 'NSAID',
                    'indications': ['pain relief', 'inflammation', 'fever'],
                    'contraindications': ['peptic ulcer', 'kidney disease', 'heart failure'],
                    'pregnancy_category': 'C',
                    'breastfeeding_safe': True,
                    'max_daily_dose': '3200mg',
                    'side_effects': ['stomach upset', 'kidney problems', 'cardiovascular risk'],
                    'interactions': ['warfarin', 'ACE inhibitors', 'lithium']
                },
                'aspirin': {
                    'generic_name': 'aspirin',
                    'brand_names': ['Bayer', 'Bufferin'],
                    'drug_class': 'NSAID',
                    'indications': ['pain relief', 'fever', 'cardiovascular protection'],
                    'contraindications': ['bleeding disorders', 'peptic ulcer', 'children with viral infections'],
                    'pregnancy_category': 'D',
                    'breastfeeding_safe': False,
                    'max_daily_dose': '4000mg',
                    'side_effects': ['stomach bleeding', 'tinnitus', 'Reye syndrome (children)'],
                    'interactions': ['warfarin', 'methotrexate', 'alcohol']
                }
            }
            
            # Safety warnings database
            self.safety_db = {
                'pregnancy_warnings': {
                    'category_A': 'Safe during pregnancy',
                    'category_B': 'Probably safe during pregnancy',
                    'category_C': 'Use only if benefits outweigh risks',
                    'category_D': 'Evidence of risk, use only if life-threatening',
                    'category_X': 'Contraindicated in pregnancy'
                },
                'age_restrictions': {
                    'aspirin_children': 'Do not give aspirin to children under 16 with viral infections due to Reye syndrome risk',
                    'ibuprofen_infants': 'Do not give ibuprofen to infants under 6 months'
                }
            }
            
            # Drug interactions database
            self.interaction_db = {
                'warfarin': {
                    'interacts_with': ['acetaminophen', 'ibuprofen', 'aspirin'],
                    'severity': 'major',
                    'description': 'Increased bleeding risk'
                },
                'alcohol': {
                    'interacts_with': ['acetaminophen', 'aspirin', 'ibuprofen'],
                    'severity': 'moderate',
                    'description': 'Increased liver toxicity and stomach bleeding risk'
                }
            }
            
            logger.info("Medical knowledge base loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load medical data: {str(e)}")
    
    def get_medicine_info(self, medicine_name: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive medicine information"""
        medicine_name = medicine_name.lower().strip()
        
        # Direct lookup
        if medicine_name in self.medicine_db:
            return self.medicine_db[medicine_name]
        
        # Search by brand name
        for generic, info in self.medicine_db.items():
            brand_names = [name.lower() for name in info.get('brand_names', [])]
            if medicine_name in brand_names:
                return info
        
        return None
    
    def check_drug_interactions(self, medicine1: str, medicine2: str) -> Optional[Dict[str, Any]]:
        """Check for drug interactions"""
        for drug, interaction_info in self.interaction_db.items():
            if medicine1.lower() in interaction_info['interacts_with'] and medicine2.lower() in interaction_info['interacts_with']:
                return interaction_info
        return None
    
    def get_safety_warnings(self, medicine_name: str, user_profile: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get personalized safety warnings"""
        warnings = []
        medicine_info = self.get_medicine_info(medicine_name)
        
        if not medicine_info:
            return warnings
        
        # Pregnancy warnings
        if user_profile.get('is_pregnant'):
            category = medicine_info.get('pregnancy_category', 'Unknown')
            if category in ['D', 'X']:
                warnings.append({
                    'type': 'pregnancy',
                    'severity': 'critical' if category == 'X' else 'high',
                    'message': f"⚠️ PREGNANCY WARNING: {medicine_name} is category {category} - {self.safety_db['pregnancy_warnings'].get(f'category_{category}', 'Consult doctor')}"
                })
        
        # Breastfeeding warnings
        if user_profile.get('is_breastfeeding') and not medicine_info.get('breastfeeding_safe', True):
            warnings.append({
                'type': 'breastfeeding',
                'severity': 'high',
                'message': f"⚠️ BREASTFEEDING WARNING: {medicine_name} may not be safe during breastfeeding"
            })
        
        # Age-specific warnings
        age = user_profile.get('age', 0)
        if age < 16 and medicine_name.lower() == 'aspirin':
            warnings.append({
                'type': 'age',
                'severity': 'critical',
                'message': "🚨 AGE WARNING: Aspirin should not be given to children under 16 due to Reye syndrome risk"
            })
        
        return warnings

class CustomRAGPipeline:
    """
    Custom RAG pipeline using on-premise models and vector databases
    """
    
    def __init__(self, embedding_dim: int = 768, models_dir: str = './models', vector_db_dir: str = './vector_db'):
        self.embedding_dim = embedding_dim
        self.models_dir = Path(models_dir)
        self.vector_db_dir = Path(vector_db_dir)
        
        # Initialize components
        self.embedding_manager = EmbeddingModelManager(str(self.models_dir))
        self.vector_db_manager = VectorDatabaseManager(embedding_dim, str(self.vector_db_dir))
        self.knowledge_base = MedicalKnowledgeBase()
        
        # RAG configuration
        self.retrieval_k = 5
        self.similarity_threshold = 0.3
        self.model_version = "custom_medical_rag_v1.0"
        
        # Document store
        self.documents = {}
        self.is_initialized = False
    
    def initialize(self):
        """Initialize the RAG pipeline"""
        try:
            logger.info("Initializing Custom RAG Pipeline...")
            
            # Initialize embedding models
            self.embedding_manager.initialize_models()
            
            # Load existing vector databases if available
            try:
                self.vector_db_manager.load_all_databases()
                logger.info("Loaded existing vector databases")
            except:
                logger.info("No existing vector databases found - will create new ones")
            
            # Index medical knowledge if databases are empty
            if self._is_database_empty():
                logger.info("Indexing medical knowledge base...")
                self._index_medical_knowledge()
            
            self.is_initialized = True
            logger.info("Custom RAG Pipeline initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize RAG pipeline: {str(e)}")
            raise
    
    def _is_database_empty(self) -> bool:
        """Check if vector databases are empty"""
        stats = self.vector_db_manager.get_statistics()
        return all(db_stats.get('total_vectors', 0) == 0 for db_stats in stats.values())
    
    def _index_medical_knowledge(self):
        """Index medical knowledge into vector databases"""
        try:
            documents = []
            
            # Index medicine information
            for medicine_name, info in self.knowledge_base.medicine_db.items():
                # Create comprehensive text for embedding
                text_content = f"""
                Medicine: {medicine_name}
                Generic Name: {info.get('generic_name', '')}
                Brand Names: {', '.join(info.get('brand_names', []))}
                Drug Class: {info.get('drug_class', '')}
                Indications: {', '.join(info.get('indications', []))}
                Contraindications: {', '.join(info.get('contraindications', []))}
                Pregnancy Category: {info.get('pregnancy_category', '')}
                Side Effects: {', '.join(info.get('side_effects', []))}
                Interactions: {', '.join(info.get('interactions', []))}
                Max Daily Dose: {info.get('max_daily_dose', '')}
                Breastfeeding Safe: {'Yes' if info.get('breastfeeding_safe') else 'No'}
                """.strip()
                
                doc_id = f"medicine_{medicine_name}"
                
                # Get embedding
                embedding = self.embedding_manager.get_embeddings([text_content], 'biobert')[0]
                
                # Create document vector
                doc_vector = DocumentVector(
                    doc_id=doc_id,
                    content=text_content,
                    vector=embedding,
                    metadata={
                        'type': 'medicine',
                        'medicine_name': medicine_name,
                        'drug_class': info.get('drug_class', ''),
                        'pregnancy_category': info.get('pregnancy_category', ''),
                        'breastfeeding_safe': info.get('breastfeeding_safe', False)
                    }
                )
                
                documents.append(doc_vector)
                self.documents[doc_id] = {
                    'title': f"Medicine: {medicine_name}",
                    'content': text_content,
                    'type': 'medicine',
                    'metadata': doc_vector.metadata
                }
            
            # Index safety information
            for category, warnings in self.knowledge_base.safety_db.items():
                if isinstance(warnings, dict):
                    for warning_id, warning_text in warnings.items():
                        text_content = f"Safety Warning - {category}: {warning_id} - {warning_text}"
                        doc_id = f"safety_{category}_{warning_id}"
                        
                        embedding = self.embedding_manager.get_embeddings([text_content], 'biobert')[0]
                        
                        doc_vector = DocumentVector(
                            doc_id=doc_id,
                            content=text_content,
                            vector=embedding,
                            metadata={
                                'type': 'safety',
                                'category': category,
                                'warning_id': warning_id
                            }
                        )
                        
                        documents.append(doc_vector)
                        self.documents[doc_id] = {
                            'title': f"Safety: {warning_id}",
                            'content': text_content,
                            'type': 'safety',
                            'metadata': doc_vector.metadata
                        }
            
            # Add documents to all vector databases
            if documents:
                self.vector_db_manager.add_documents(documents, 'faiss')
                self.vector_db_manager.add_documents(documents, 'annoy')
                self.vector_db_manager.add_documents(documents, 'hnswlib')
                
                # Build Annoy index
                self.vector_db_manager.annoy_db.build_index()
                
                # Save all databases
                self.vector_db_manager.save_all_databases()
                
                logger.info(f"Indexed {len(documents)} medical documents")
            
        except Exception as e:
            logger.error(f"Failed to index medical knowledge: {str(e)}")
            raise
    
    def add_custom_documents(self, documents: List[RAGDocument]):
        """Add custom medical documents to the knowledge base"""
        try:
            doc_vectors = []
            
            for doc in documents:
                # Get embedding
                embedding = self.embedding_manager.get_embeddings([doc.content], 'biobert')[0]
                
                # Create document vector
                doc_vector = DocumentVector(
                    doc_id=doc.doc_id,
                    content=doc.content,
                    vector=embedding,
                    metadata=doc.metadata
                )
                
                doc_vectors.append(doc_vector)
                self.documents[doc.doc_id] = {
                    'title': doc.title,
                    'content': doc.content,
                    'type': doc.doc_type,
                    'metadata': doc.metadata
                }
            
            # Add to vector databases
            self.vector_db_manager.add_documents(doc_vectors, 'faiss')
            self.vector_db_manager.add_documents(doc_vectors, 'annoy')
            self.vector_db_manager.add_documents(doc_vectors, 'hnswlib')
            
            # Rebuild Annoy index
            self.vector_db_manager.annoy_db.build_index()
            
            # Save databases
            self.vector_db_manager.save_all_databases()
            
            logger.info(f"Added {len(documents)} custom documents to knowledge base")
            
        except Exception as e:
            logger.error(f"Failed to add custom documents: {str(e)}")
            raise
    
    def retrieve_relevant_documents(self, query: RAGQuery) -> List[VectorSearchResult]:
        """Retrieve relevant documents for a query"""
        try:
            # Get query embedding
            query_embedding = self.embedding_manager.get_embeddings([query.text], 'biobert')[0]
            
            # Search using ensemble method for best results
            results = self.vector_db_manager.ensemble_search(
                query_embedding, 
                k=query.max_results * 2  # Get more results for filtering
            )
            
            # Filter by similarity threshold
            filtered_results = [
                result for result in results 
                if result.score >= self.similarity_threshold
            ]
            
            # Apply query-type specific filtering
            if query.query_type != 'general':
                filtered_results = [
                    result for result in filtered_results
                    if result.metadata.get('type') == query.query_type
                ]
            
            return filtered_results[:query.max_results]
            
        except Exception as e:
            logger.error(f"Document retrieval failed: {str(e)}")
            return []
    
    def generate_response(self, query: RAGQuery, retrieved_docs: List[VectorSearchResult]) -> str:
        """
        Generate response using retrieved documents and medical knowledge
        Custom response generation without external LLM APIs
        """
        try:
            if not retrieved_docs:
                return "I don't have enough information to answer your question. Please consult a healthcare professional."
            
            # Analyze query intent
            query_lower = query.text.lower()
            
            # Medicine information query
            if any(word in query_lower for word in ['what is', 'tell me about', 'information about']):
                return self._generate_medicine_info_response(query, retrieved_docs)
            
            # Safety/interaction query
            elif any(word in query_lower for word in ['safe', 'pregnancy', 'breastfeeding', 'interaction']):
                return self._generate_safety_response(query, retrieved_docs)
            
            # Dosage query
            elif any(word in query_lower for word in ['dose', 'dosage', 'how much', 'how many']):
                return self._generate_dosage_response(query, retrieved_docs)
            
            # Side effects query
            elif any(word in query_lower for word in ['side effect', 'adverse', 'reaction']):
                return self._generate_side_effects_response(query, retrieved_docs)
            
            # General response
            else:
                return self._generate_general_response(query, retrieved_docs)
                
        except Exception as e:
            logger.error(f"Response generation failed: {str(e)}")
            return "I encountered an error while processing your question. Please try again or consult a healthcare professional."
    
    def _generate_medicine_info_response(self, query: RAGQuery, docs: List[VectorSearchResult]) -> str:
        """Generate medicine information response"""
        if not docs:
            return "I don't have information about that medicine."
        
        doc = docs[0]  # Use most relevant document
        
        # Extract medicine name from metadata
        medicine_name = doc.metadata.get('medicine_name', 'this medicine')
        
        response = f"Here's information about {medicine_name}:\n\n"
        
        # Parse content for structured information
        content_lines = doc.content.split('\n')
        for line in content_lines:
            if line.strip() and ':' in line:
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip()
                
                if value and value != 'None' and value != '':
                    if key in ['Indications', 'Side Effects', 'Contraindications']:
                        response += f"• {key}: {value}\n"
                    elif key in ['Pregnancy Category', 'Max Daily Dose']:
                        response += f"• {key}: {value}\n"
        
        response += "\n⚠️ Always consult your healthcare provider before taking any medication."
        return response
    
    def _generate_safety_response(self, query: RAGQuery, docs: List[VectorSearchResult]) -> str:
        """Generate safety-focused response"""
        response = "Safety Information:\n\n"
        
        # Check user context for personalized warnings
        if query.user_context:
            medicine_name = self._extract_medicine_name(query.text)
            if medicine_name:
                warnings = self.knowledge_base.get_safety_warnings(medicine_name, query.user_context)
                if warnings:
                    response += "⚠️ PERSONALIZED WARNINGS:\n"
                    for warning in warnings:
                        response += f"• {warning['message']}\n"
                    response += "\n"
        
        # Add retrieved safety information
        for doc in docs[:3]:  # Top 3 most relevant
            if doc.metadata.get('type') == 'safety':
                response += f"• {doc.content}\n"
        
        response += "\n🏥 Always consult your healthcare provider for personalized medical advice."
        return response
    
    def _generate_dosage_response(self, query: RAGQuery, docs: List[VectorSearchResult]) -> str:
        """Generate dosage information response"""
        medicine_name = self._extract_medicine_name(query.text)
        
        if medicine_name:
            medicine_info = self.knowledge_base.get_medicine_info(medicine_name)
            if medicine_info:
                max_dose = medicine_info.get('max_daily_dose', 'Not specified')
                response = f"Dosage information for {medicine_name}:\n\n"
                response += f"• Maximum daily dose: {max_dose}\n"
                response += f"• Drug class: {medicine_info.get('drug_class', 'Not specified')}\n\n"
                response += "⚠️ IMPORTANT: This is general information only. Your actual dose should be determined by your healthcare provider based on your specific condition, age, weight, and other factors."
                return response
        
        return "I need more specific information about the medicine to provide dosage guidance. Please consult your healthcare provider or pharmacist for proper dosing instructions."
    
    def _generate_side_effects_response(self, query: RAGQuery, docs: List[VectorSearchResult]) -> str:
        """Generate side effects information response"""
        medicine_name = self._extract_medicine_name(query.text)
        
        if medicine_name:
            medicine_info = self.knowledge_base.get_medicine_info(medicine_name)
            if medicine_info:
                side_effects = medicine_info.get('side_effects', [])
                response = f"Potential side effects of {medicine_name}:\n\n"
                
                if side_effects:
                    for effect in side_effects:
                        response += f"• {effect}\n"
                else:
                    response += "• No specific side effects listed\n"
                
                response += "\n⚠️ This is not a complete list. Contact your healthcare provider if you experience any unusual symptoms."
                return response
        
        return "Please specify the medicine name to get side effect information. Always report any unusual symptoms to your healthcare provider."
    
    def _generate_general_response(self, query: RAGQuery, docs: List[VectorSearchResult]) -> str:
        """Generate general response from retrieved documents"""
        if not docs:
            return "I don't have enough information to answer your question."
        
        response = "Based on the medical information available:\n\n"
        
        # Combine information from top documents
        for i, doc in enumerate(docs[:2]):  # Use top 2 documents
            if doc.content.strip():
                # Extract key information
                content_summary = doc.content[:200] + "..." if len(doc.content) > 200 else doc.content
                response += f"• {content_summary}\n\n"
        
        response += "🏥 For personalized medical advice, please consult your healthcare provider."
        return response
    
    def _extract_medicine_name(self, text: str) -> Optional[str]:
        """Extract medicine name from query text"""
        text_lower = text.lower()
        
        # Check against known medicines
        for medicine_name in self.knowledge_base.medicine_db.keys():
            if medicine_name in text_lower:
                return medicine_name
        
        # Check against brand names
        for medicine_name, info in self.knowledge_base.medicine_db.items():
            for brand_name in info.get('brand_names', []):
                if brand_name.lower() in text_lower:
                    return medicine_name
        
        return None
    
    def query(self, query: RAGQuery) -> RAGResponse:
        """Main query method for RAG pipeline"""
        start_time = time.time()
        
        try:
            if not self.is_initialized:
                self.initialize()
            
            # Retrieve relevant documents
            retrieved_docs = self.retrieve_relevant_documents(query)
            
            # Generate response
            answer = self.generate_response(query, retrieved_docs)
            
            # Calculate confidence score
            confidence_score = self._calculate_confidence_score(query, retrieved_docs)
            
            # Calculate response time
            response_time_ms = int((time.time() - start_time) * 1000)
            
            return RAGResponse(
                query=query.text,
                answer=answer,
                retrieved_documents=retrieved_docs,
                confidence_score=confidence_score,
                response_time_ms=response_time_ms,
                model_version=self.model_version
            )
            
        except Exception as e:
            logger.error(f"RAG query failed: {str(e)}")
            return RAGResponse(
                query=query.text,
                answer="I encountered an error while processing your question. Please try again.",
                retrieved_documents=[],
                confidence_score=0.0,
                response_time_ms=int((time.time() - start_time) * 1000),
                model_version=self.model_version
            )
    
    def _calculate_confidence_score(self, query: RAGQuery, docs: List[VectorSearchResult]) -> float:
        """Calculate confidence score for the response"""
        if not docs:
            return 0.0
        
        # Base confidence on similarity scores
        avg_similarity = sum(doc.score for doc in docs) / len(docs)
        
        # Boost confidence if we have multiple relevant documents
        doc_count_boost = min(0.2, len(docs) * 0.05)
        
        # Boost confidence for specific medicine queries
        if self._extract_medicine_name(query.text):
            medicine_boost = 0.1
        else:
            medicine_boost = 0.0
        
        confidence = min(1.0, avg_similarity + doc_count_boost + medicine_boost)
        return round(confidence, 3)
    
    def get_pipeline_statistics(self) -> Dict[str, Any]:
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