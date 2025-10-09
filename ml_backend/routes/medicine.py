"""
Medicine Routes - Custom ML-powered medicine information and analysis
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
import logging
from typing import Dict, Any, List
import base64
import io
from PIL import Image
import numpy as np

from ml.custom_rag_pipeline import CustomRAGPipeline, RAGQuery
from ml.custom_embeddings import EmbeddingModelManager
from models import db, MedicineRecord, User

logger = logging.getLogger(__name__)

medicine_bp = Blueprint('medicine', __name__)

# Initialize ML components (will be loaded on first use)
rag_pipeline = None
embedding_manager = None

def get_rag_pipeline():
    """Get or initialize RAG pipeline"""
    global rag_pipeline
    if rag_pipeline is None:
        try:
            rag_pipeline = CustomRAGPipeline()
            rag_pipeline.initialize()
            logger.info("RAG pipeline initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize RAG pipeline: {str(e)}")
            raise
    return rag_pipeline

def get_embedding_manager():
    """Get or initialize embedding manager"""
    global embedding_manager
    if embedding_manager is None:
        try:
            embedding_manager = EmbeddingModelManager()
            embedding_manager.initialize_models()
            logger.info("Embedding manager initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize embedding manager: {str(e)}")
            raise
    return embedding_manager

@medicine_bp.route('/search', methods=['POST'])
@jwt_required()
def search_medicine():
    """
    Search for medicine information using custom RAG pipeline
    """
    try:
        data = request.get_json()
        query_text = data.get('query', '').strip()
        
        if not query_text:
            return jsonify({'error': 'Query text is required'}), 400
        
        # Get user context
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        user_context = {}
        if user and user.health_profile:
            user_context = {
                'age': user.health_profile.age,
                'is_pregnant': user.health_profile.is_pregnant,
                'is_breastfeeding': user.health_profile.is_breastfeeding,
                'allergies': user.health_profile.allergies or [],
                'current_medications': user.health_profile.current_medications or []
            }
        
        # Create RAG query
        rag_query = RAGQuery(
            text=query_text,
            user_context=user_context,
            query_type=data.get('query_type', 'general'),
            max_results=data.get('max_results', 5)
        )
        
        # Get RAG pipeline and process query
        pipeline = get_rag_pipeline()
        response = pipeline.query(rag_query)
        
        # Save search to database
        medicine_record = MedicineRecord(
            user_id=user_id,
            medicine_name=query_text,
            search_query=query_text,
            ai_response=response.answer,
            confidence_score=response.confidence_score,
            response_time_ms=response.response_time_ms
        )
        db.session.add(medicine_record)
        db.session.commit()
        
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
        logger.error(f"Medicine search failed: {str(e)}")
        return jsonify({'error': 'Failed to process medicine search'}), 500

@medicine_bp.route('/analyze-image', methods=['POST'])
@jwt_required()
def analyze_medicine_image():
    """
    Analyze medicine image using custom ML models
    """
    try:
        data = request.get_json()
        image_data = data.get('image')
        
        if not image_data:
            return jsonify({'error': 'Image data is required'}), 400
        
        # Decode base64 image
        try:
            # Remove data URL prefix if present
            if ',' in image_data:
                image_data = image_data.split(',')[1]
            
            image_bytes = base64.b64decode(image_data)
            image = Image.open(io.BytesIO(image_bytes))
            
            # Convert to RGB if necessary
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
        except Exception as e:
            logger.error(f"Image decoding failed: {str(e)}")
            return jsonify({'error': 'Invalid image data'}), 400
        
        # For now, return a placeholder response
        # In a full implementation, you would use OCR and image classification models
        analysis_result = {
            'detected_text': 'Sample Medicine Name',  # Would use OCR
            'medicine_type': 'tablet',  # Would use image classification
            'confidence': 0.85,
            'suggestions': [
                'This appears to be a tablet medication',
                'Consider verifying the medicine name with a healthcare provider',
                'Check expiration date and storage instructions'
            ]
        }
        
        # Get user context for safety analysis
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        user_context = {}
        if user and user.health_profile:
            user_context = {
                'age': user.health_profile.age,
                'is_pregnant': user.health_profile.is_pregnant,
                'is_breastfeeding': user.health_profile.is_breastfeeding,
                'allergies': user.health_profile.allergies or [],
                'current_medications': user.health_profile.current_medications or []
            }
        
        # Perform safety analysis if medicine is detected
        safety_analysis = None
        if analysis_result['detected_text']:
            try:
                pipeline = get_rag_pipeline()
                safety_query = RAGQuery(
                    text=f"Safety information for {analysis_result['detected_text']}",
                    user_context=user_context,
                    query_type='safety',
                    max_results=3
                )
                
                safety_response = pipeline.query(safety_query)
                safety_analysis = {
                    'safety_info': safety_response.answer,
                    'confidence': safety_response.confidence_score
                }
                
            except Exception as e:
                logger.error(f"Safety analysis failed: {str(e)}")
        
        # Save analysis to database
        medicine_record = MedicineRecord(
            user_id=user_id,
            medicine_name=analysis_result['detected_text'],
            image_analysis=analysis_result,
            ai_response=safety_analysis['safety_info'] if safety_analysis else None,
            confidence_score=analysis_result['confidence']
        )
        db.session.add(medicine_record)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'analysis': analysis_result,
            'safety_analysis': safety_analysis,
            'record_id': medicine_record.id
        })
        
    except Exception as e:
        logger.error(f"Image analysis failed: {str(e)}")
        return jsonify({'error': 'Failed to analyze image'}), 500

@medicine_bp.route('/similarity', methods=['POST'])
@jwt_required()
def check_medicine_similarity():
    """
    Check similarity between medicines using custom embeddings
    """
    try:
        data = request.get_json()
        medicine1 = data.get('medicine1', '').strip()
        medicine2 = data.get('medicine2', '').strip()
        
        if not medicine1 or not medicine2:
            return jsonify({'error': 'Both medicine names are required'}), 400
        
        # Get embedding manager
        emb_manager = get_embedding_manager()
        
        # Calculate similarity using different embedding models
        similarities = {}
        
        # BioBERT similarity
        biobert_emb1 = emb_manager.get_embeddings([medicine1], 'biobert')[0]
        biobert_emb2 = emb_manager.get_embeddings([medicine2], 'biobert')[0]
        biobert_similarity = emb_manager.compute_similarity(biobert_emb1, biobert_emb2)
        similarities['biobert'] = float(biobert_similarity)
        
        # Sentence-BERT similarity
        try:
            sbert_emb1 = emb_manager.get_embeddings([medicine1], 'sentence_bert')[0]
            sbert_emb2 = emb_manager.get_embeddings([medicine2], 'sentence_bert')[0]
            sbert_similarity = emb_manager.compute_similarity(sbert_emb1, sbert_emb2)
            similarities['sentence_bert'] = float(sbert_similarity)
        except:
            similarities['sentence_bert'] = None
        
        # Word2Vec similarity
        try:
            w2v_emb1 = emb_manager.get_embeddings([medicine1], 'word2vec')[0]
            w2v_emb2 = emb_manager.get_embeddings([medicine2], 'word2vec')[0]
            w2v_similarity = emb_manager.compute_similarity(w2v_emb1, w2v_emb2)
            similarities['word2vec'] = float(w2v_similarity)
        except:
            similarities['word2vec'] = None
        
        # Calculate ensemble similarity
        valid_similarities = [s for s in similarities.values() if s is not None]
        ensemble_similarity = sum(valid_similarities) / len(valid_similarities) if valid_similarities else 0.0
        
        # Interpret similarity
        if ensemble_similarity > 0.8:
            interpretation = "Very similar medicines - likely same or closely related"
        elif ensemble_similarity > 0.6:
            interpretation = "Moderately similar - may be in same drug class"
        elif ensemble_similarity > 0.4:
            interpretation = "Some similarity - may have related uses"
        else:
            interpretation = "Low similarity - likely different types of medicines"
        
        return jsonify({
            'success': True,
            'medicine1': medicine1,
            'medicine2': medicine2,
            'similarities': similarities,
            'ensemble_similarity': ensemble_similarity,
            'interpretation': interpretation
        })
        
    except Exception as e:
        logger.error(f"Similarity check failed: {str(e)}")
        return jsonify({'error': 'Failed to check medicine similarity'}), 500

@medicine_bp.route('/history', methods=['GET'])
@jwt_required()
def get_medicine_history():
    """
    Get user's medicine search and analysis history
    """
    try:
        user_id = get_jwt_identity()
        
        # Get pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        
        # Query medicine records
        records = MedicineRecord.query.filter_by(user_id=user_id)\
            .order_by(MedicineRecord.created_at.desc())\
            .paginate(page=page, per_page=per_page, error_out=False)
        
        return jsonify({
            'success': True,
            'records': [
                {
                    'id': record.id,
                    'medicine_name': record.medicine_name,
                    'search_query': record.search_query,
                    'ai_response': record.ai_response,
                    'confidence_score': record.confidence_score,
                    'response_time_ms': record.response_time_ms,
                    'image_analysis': record.image_analysis,
                    'created_at': record.created_at.isoformat()
                }
                for record in records.items
            ],
            'pagination': {
                'page': records.page,
                'pages': records.pages,
                'per_page': records.per_page,
                'total': records.total,
                'has_next': records.has_next,
                'has_prev': records.has_prev
            }
        })
        
    except Exception as e:
        logger.error(f"Failed to get medicine history: {str(e)}")
        return jsonify({'error': 'Failed to retrieve medicine history'}), 500

@medicine_bp.route('/stats', methods=['GET'])
@jwt_required()
def get_ml_stats():
    """
    Get ML pipeline statistics and performance metrics
    """
    try:
        # Get RAG pipeline statistics
        pipeline = get_rag_pipeline()
        pipeline_stats = pipeline.get_pipeline_statistics()
        
        # Get user-specific statistics
        user_id = get_jwt_identity()
        user_records_count = MedicineRecord.query.filter_by(user_id=user_id).count()
        
        # Calculate average confidence and response time
        user_records = MedicineRecord.query.filter_by(user_id=user_id).all()
        
        if user_records:
            avg_confidence = sum(r.confidence_score or 0 for r in user_records) / len(user_records)
            avg_response_time = sum(r.response_time_ms or 0 for r in user_records) / len(user_records)
        else:
            avg_confidence = 0
            avg_response_time = 0
        
        return jsonify({
            'success': True,
            'pipeline_stats': pipeline_stats,
            'user_stats': {
                'total_queries': user_records_count,
                'average_confidence': round(avg_confidence, 3),
                'average_response_time_ms': round(avg_response_time, 2)
            }
        })
        
    except Exception as e:
        logger.error(f"Failed to get ML stats: {str(e)}")
        return jsonify({'error': 'Failed to retrieve ML statistics'}), 500