"""
ML Inference Routes - Custom model inference endpoints
Real-time ML model serving for medical applications
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
import logging
from typing import Dict, Any, List, Optional
import numpy as np
import time
import json

from ml.custom_embeddings import EmbeddingModelManager
from ml.vector_database import VectorDatabaseManager
from ml.custom_rag_pipeline import CustomRAGPipeline, RAGQuery, RAGDocument
from ml.model_training import MedicalModelTrainer, TrainingConfig

logger = logging.getLogger(__name__)

ml_inference_bp = Blueprint('ml_inference', __name__)

# Global ML components (initialized on first use)
embedding_manager = None
vector_db_manager = None
rag_pipeline = None
model_trainer = None

def get_embedding_manager():
    """Get or initialize embedding manager"""
    global embedding_manager
    if embedding_manager is None:
        try:
            embedding_manager = EmbeddingModelManager()
            embedding_manager.initialize_models()
            logger.info("Embedding manager initialized for inference")
        except Exception as e:
            logger.error(f"Failed to initialize embedding manager: {str(e)}")
            raise
    return embedding_manager

def get_vector_db_manager():
    """Get or initialize vector database manager"""
    global vector_db_manager
    if vector_db_manager is None:
        try:
            vector_db_manager = VectorDatabaseManager(embedding_dim=768)
            vector_db_manager.load_all_databases()
            logger.info("Vector database manager initialized for inference")
        except Exception as e:
            logger.error(f"Failed to initialize vector database manager: {str(e)}")
            raise
    return vector_db_manager

def get_rag_pipeline():
    """Get or initialize RAG pipeline"""
    global rag_pipeline
    if rag_pipeline is None:
        try:
            rag_pipeline = CustomRAGPipeline()
            rag_pipeline.initialize()
            logger.info("RAG pipeline initialized for inference")
        except Exception as e:
            logger.error(f"Failed to initialize RAG pipeline: {str(e)}")
            raise
    return rag_pipeline

def get_model_trainer():
    """Get or initialize model trainer"""
    global model_trainer
    if model_trainer is None:
        try:
            config = TrainingConfig()
            model_trainer = MedicalModelTrainer(config)
            logger.info("Model trainer initialized")
        except Exception as e:
            logger.error(f"Failed to initialize model trainer: {str(e)}")
            raise
    return model_trainer

@ml_inference_bp.route('/embeddings', methods=['POST'])
@jwt_required()
def generate_embeddings():
    """
    Generate embeddings for text using custom models
    """
    try:
        data = request.get_json()
        texts = data.get('texts', [])
        model_type = data.get('model_type', 'biobert')  # biobert, sentence_bert, word2vec
        
        if not texts or not isinstance(texts, list):
            return jsonify({'error': 'Texts array is required'}), 400
        
        if len(texts) > 100:
            return jsonify({'error': 'Maximum 100 texts allowed per request'}), 400
        
        # Get embedding manager
        emb_manager = get_embedding_manager()
        
        # Generate embeddings
        start_time = time.time()
        embeddings = emb_manager.get_embeddings(texts, model_type)
        processing_time = (time.time() - start_time) * 1000
        
        return jsonify({
            'success': True,
            'embeddings': [emb.tolist() for emb in embeddings],
            'model_type': model_type,
            'embedding_dimension': len(embeddings[0]) if embeddings else 0,
            'processing_time_ms': round(processing_time, 2),
            'text_count': len(texts)
        })
        
    except Exception as e:
        logger.error(f"Embedding generation failed: {str(e)}")
        return jsonify({'error': 'Failed to generate embeddings'}), 500

@ml_inference_bp.route('/similarity', methods=['POST'])
@jwt_required()
def compute_similarity():
    """
    Compute similarity between texts using custom embeddings
    """
    try:
        data = request.get_json()
        text1 = data.get('text1', '').strip()
        text2 = data.get('text2', '').strip()
        model_type = data.get('model_type', 'biobert')
        
        if not text1 or not text2:
            return jsonify({'error': 'Both text1 and text2 are required'}), 400
        
        # Get embedding manager
        emb_manager = get_embedding_manager()
        
        # Generate embeddings and compute similarity
        start_time = time.time()
        
        embeddings = emb_manager.get_embeddings([text1, text2], model_type)
        similarity_score = emb_manager.compute_similarity(embeddings[0], embeddings[1])
        
        processing_time = (time.time() - start_time) * 1000
        
        return jsonify({
            'success': True,
            'text1': text1,
            'text2': text2,
            'similarity_score': float(similarity_score),
            'model_type': model_type,
            'processing_time_ms': round(processing_time, 2)
        })
        
    except Exception as e:
        logger.error(f"Similarity computation failed: {str(e)}")
        return jsonify({'error': 'Failed to compute similarity'}), 500

@ml_inference_bp.route('/vector-search', methods=['POST'])
@jwt_required()
def vector_search():
    """
    Perform vector similarity search
    """
    try:
        data = request.get_json()
        query_text = data.get('query_text', '').strip()
        k = min(data.get('k', 5), 50)  # Limit to 50 results
        database_type = data.get('database_type', 'ensemble')  # faiss, annoy, hnswlib, ensemble
        
        if not query_text:
            return jsonify({'error': 'Query text is required'}), 400
        
        # Get components
        emb_manager = get_embedding_manager()
        vector_db_manager = get_vector_db_manager()
        
        # Generate query embedding
        start_time = time.time()
        query_embedding = emb_manager.get_embeddings([query_text], 'biobert')[0]
        
        # Perform search
        if database_type == 'ensemble':
            results = vector_db_manager.ensemble_search(query_embedding, k)
        else:
            if database_type == 'faiss':
                results = vector_db_manager.faiss_db.search(query_embedding, k)
            elif database_type == 'annoy':
                results = vector_db_manager.annoy_db.search(query_embedding, k)
            elif database_type == 'hnswlib':
                results = vector_db_manager.hnswlib_db.search(query_embedding, k)
            else:
                return jsonify({'error': 'Invalid database type'}), 400
        
        processing_time = (time.time() - start_time) * 1000
        
        return jsonify({
            'success': True,
            'query_text': query_text,
            'database_type': database_type,
            'results': [
                {
                    'doc_id': result.doc_id,
                    'score': result.score,
                    'metadata': result.metadata
                }
                for result in results
            ],
            'processing_time_ms': round(processing_time, 2),
            'results_count': len(results)
        })
        
    except Exception as e:
        logger.error(f"Vector search failed: {str(e)}")
        return jsonify({'error': 'Failed to perform vector search'}), 500

@ml_inference_bp.route('/rag-query', methods=['POST'])
@jwt_required()
def rag_query():
    """
    Perform RAG query with custom pipeline
    """
    try:
        data = request.get_json()
        query_text = data.get('query_text', '').strip()
        query_type = data.get('query_type', 'general')
        max_results = min(data.get('max_results', 5), 20)
        user_context = data.get('user_context', {})
        
        if not query_text:
            return jsonify({'error': 'Query text is required'}), 400
        
        # Get RAG pipeline
        pipeline = get_rag_pipeline()
        
        # Create RAG query
        rag_query_obj = RAGQuery(
            text=query_text,
            user_context=user_context,
            query_type=query_type,
            max_results=max_results
        )
        
        # Process query
        response = pipeline.query(rag_query_obj)
        
        return jsonify({
            'success': True,
            'query': response.query,
            'answer': response.answer,
            'confidence_score': response.confidence_score,
            'response_time_ms': response.response_time_ms,
            'model_version': response.model_version,
            'retrieved_documents': [
                {
                    'doc_id': doc.doc_id,
                    'score': doc.score,
                    'metadata': doc.metadata
                }
                for doc in response.retrieved_documents
            ]
        })
        
    except Exception as e:
        logger.error(f"RAG query failed: {str(e)}")
        return jsonify({'error': 'Failed to process RAG query'}), 500

@ml_inference_bp.route('/add-documents', methods=['POST'])
@jwt_required()
def add_documents():
    """
    Add custom documents to the knowledge base
    """
    try:
        data = request.get_json()
        documents_data = data.get('documents', [])
        
        if not documents_data or not isinstance(documents_data, list):
            return jsonify({'error': 'Documents array is required'}), 400
        
        if len(documents_data) > 50:
            return jsonify({'error': 'Maximum 50 documents allowed per request'}), 400
        
        # Convert to RAGDocument objects
        documents = []
        for doc_data in documents_data:
            if not all(key in doc_data for key in ['doc_id', 'title', 'content', 'doc_type']):
                return jsonify({'error': 'Each document must have doc_id, title, content, and doc_type'}), 400
            
            documents.append(RAGDocument(
                doc_id=doc_data['doc_id'],
                title=doc_data['title'],
                content=doc_data['content'],
                doc_type=doc_data['doc_type'],
                metadata=doc_data.get('metadata', {})
            ))
        
        # Add documents to RAG pipeline
        pipeline = get_rag_pipeline()
        pipeline.add_custom_documents(documents)
        
        return jsonify({
            'success': True,
            'message': f'Added {len(documents)} documents to knowledge base',
            'document_count': len(documents)
        })
        
    except Exception as e:
        logger.error(f"Failed to add documents: {str(e)}")
        return jsonify({'error': 'Failed to add documents'}), 500

@ml_inference_bp.route('/model-stats', methods=['GET'])
@jwt_required()
def get_model_stats():
    """
    Get comprehensive ML model statistics
    """
    try:
        stats = {}
        
        # Embedding manager stats
        try:
            emb_manager = get_embedding_manager()
            stats['embedding_models'] = {
                'available_models': ['biobert', 'sentence_bert', 'word2vec'],
                'default_model': 'biobert',
                'embedding_dimension': 768
            }
        except:
            stats['embedding_models'] = {'status': 'not_initialized'}
        
        # Vector database stats
        try:
            vector_db_manager = get_vector_db_manager()
            stats['vector_databases'] = vector_db_manager.get_statistics()
        except:
            stats['vector_databases'] = {'status': 'not_initialized'}
        
        # RAG pipeline stats
        try:
            pipeline = get_rag_pipeline()
            stats['rag_pipeline'] = pipeline.get_pipeline_statistics()
        except:
            stats['rag_pipeline'] = {'status': 'not_initialized'}
        
        return jsonify({
            'success': True,
            'stats': stats,
            'timestamp': time.time()
        })
        
    except Exception as e:
        logger.error(f"Failed to get model stats: {str(e)}")
        return jsonify({'error': 'Failed to retrieve model statistics'}), 500

@ml_inference_bp.route('/health-check', methods=['GET'])
def ml_health_check():
    """
    Health check for ML inference services
    """
    try:
        health_status = {
            'status': 'healthy',
            'timestamp': time.time(),
            'services': {}
        }
        
        # Check embedding manager
        try:
            emb_manager = get_embedding_manager()
            test_embedding = emb_manager.get_embeddings(['test'], 'biobert')
            health_status['services']['embedding_manager'] = 'healthy'
        except Exception as e:
            health_status['services']['embedding_manager'] = f'unhealthy: {str(e)}'
            health_status['status'] = 'degraded'
        
        # Check vector databases
        try:
            vector_db_manager = get_vector_db_manager()
            stats = vector_db_manager.get_statistics()
            health_status['services']['vector_databases'] = 'healthy'
        except Exception as e:
            health_status['services']['vector_databases'] = f'unhealthy: {str(e)}'
            health_status['status'] = 'degraded'
        
        # Check RAG pipeline
        try:
            pipeline = get_rag_pipeline()
            health_status['services']['rag_pipeline'] = 'healthy'
        except Exception as e:
            health_status['services']['rag_pipeline'] = f'unhealthy: {str(e)}'
            health_status['status'] = 'degraded'
        
        return jsonify(health_status)
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': time.time()
        }), 500

@ml_inference_bp.route('/benchmark', methods=['POST'])
@jwt_required()
def run_benchmark():
    """
    Run performance benchmark on ML models
    """
    try:
        data = request.get_json()
        test_queries = data.get('test_queries', [
            'What is acetaminophen?',
            'Is ibuprofen safe during pregnancy?',
            'Side effects of aspirin'
        ])
        
        if len(test_queries) > 20:
            return jsonify({'error': 'Maximum 20 test queries allowed'}), 400
        
        # Get components
        emb_manager = get_embedding_manager()
        pipeline = get_rag_pipeline()
        
        benchmark_results = {
            'total_queries': len(test_queries),
            'results': [],
            'summary': {}
        }
        
        total_embedding_time = 0
        total_rag_time = 0
        
        for i, query in enumerate(test_queries):
            # Benchmark embedding generation
            start_time = time.time()
            embedding = emb_manager.get_embeddings([query], 'biobert')[0]
            embedding_time = (time.time() - start_time) * 1000
            total_embedding_time += embedding_time
            
            # Benchmark RAG query
            start_time = time.time()
            rag_query_obj = RAGQuery(text=query, max_results=3)
            response = pipeline.query(rag_query_obj)
            rag_time = (time.time() - start_time) * 1000
            total_rag_time += rag_time
            
            benchmark_results['results'].append({
                'query_index': i,
                'query': query,
                'embedding_time_ms': round(embedding_time, 2),
                'rag_time_ms': round(rag_time, 2),
                'confidence_score': response.confidence_score,
                'retrieved_docs': len(response.retrieved_documents)
            })
        
        # Calculate summary statistics
        benchmark_results['summary'] = {
            'avg_embedding_time_ms': round(total_embedding_time / len(test_queries), 2),
            'avg_rag_time_ms': round(total_rag_time / len(test_queries), 2),
            'total_embedding_time_ms': round(total_embedding_time, 2),
            'total_rag_time_ms': round(total_rag_time, 2),
            'avg_confidence_score': round(
                sum(r['confidence_score'] for r in benchmark_results['results']) / len(test_queries), 3
            )
        }
        
        return jsonify({
            'success': True,
            'benchmark_results': benchmark_results
        })
        
    except Exception as e:
        logger.error(f"Benchmark failed: {str(e)}")
        return jsonify({'error': 'Failed to run benchmark'}), 500

@ml_inference_bp.route('/retrain-model', methods=['POST'])
@jwt_required()
def retrain_model():
    """
    Trigger model retraining (for admin users)
    """
    try:
        data = request.get_json()
        model_type = data.get('model_type', 'classification')  # classification, similarity
        training_data = data.get('training_data', [])
        
        if not training_data:
            return jsonify({'error': 'Training data is required'}), 400
        
        # Get model trainer
        trainer = get_model_trainer()
        
        # Start training (this would typically be done asynchronously)
        if model_type == 'classification':
            from ml.model_training import MedicalTrainingExample
            examples = [
                MedicalTrainingExample(
                    text=item['text'],
                    label=item['label'],
                    metadata=item.get('metadata', {})
                )
                for item in training_data
            ]
            result = trainer.train_classification_model(examples)
        elif model_type == 'similarity':
            pairs = [
                (item['text1'], item['text2'], item['similarity'])
                for item in training_data
            ]
            result = trainer.train_similarity_model(pairs)
        else:
            return jsonify({'error': 'Invalid model type'}), 400
        
        return jsonify({
            'success': True,
            'message': f'{model_type} model retraining completed',
            'result': result
        })
        
    except Exception as e:
        logger.error(f"Model retraining failed: {str(e)}")
        return jsonify({'error': 'Failed to retrain model'}), 500