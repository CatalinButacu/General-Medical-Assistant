"""
Chat Routes - Custom RAG-powered medical chat interface
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
import logging
from typing import Dict, Any, List
from datetime import datetime

from ml.custom_rag_pipeline import CustomRAGPipeline, RAGQuery
from models import db, ChatHistory, User

logger = logging.getLogger(__name__)

chat_bp = Blueprint('chat', __name__)

# Initialize RAG pipeline (will be loaded on first use)
rag_pipeline = None

def get_rag_pipeline():
    """Get or initialize RAG pipeline"""
    global rag_pipeline
    if rag_pipeline is None:
        try:
            rag_pipeline = CustomRAGPipeline()
            rag_pipeline.initialize()
            logger.info("RAG pipeline initialized for chat")
        except Exception as e:
            logger.error(f"Failed to initialize RAG pipeline: {str(e)}")
            raise
    return rag_pipeline

@chat_bp.route('/message', methods=['POST'])
@jwt_required()
def send_message():
    """
    Send a message to the custom RAG-powered medical assistant
    """
    try:
        data = request.get_json()
        message = data.get('message', '').strip()
        
        if not message:
            return jsonify({'error': 'Message is required'}), 400
        
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        # Get user context for personalized responses
        user_context = {}
        if user and user.health_profile:
            user_context = {
                'age': user.health_profile.age,
                'gender': user.health_profile.gender,
                'is_pregnant': user.health_profile.is_pregnant,
                'is_breastfeeding': user.health_profile.is_breastfeeding,
                'allergies': user.health_profile.allergies or [],
                'current_medications': user.health_profile.current_medications or [],
                'medical_conditions': user.health_profile.medical_conditions or []
            }
        
        # Determine query type based on message content
        message_lower = message.lower()
        if any(word in message_lower for word in ['safe', 'pregnancy', 'breastfeeding', 'allergy', 'interaction']):
            query_type = 'safety'
        elif any(word in message_lower for word in ['medicine', 'drug', 'medication', 'pill', 'tablet']):
            query_type = 'medicine'
        else:
            query_type = 'general'
        
        # Create RAG query
        rag_query = RAGQuery(
            text=message,
            user_context=user_context,
            query_type=query_type,
            max_results=5
        )
        
        # Get response from RAG pipeline
        pipeline = get_rag_pipeline()
        response = pipeline.query(rag_query)
        
        # Save chat history
        chat_record = ChatHistory(
            user_id=user_id,
            user_message=message,
            ai_response=response.answer,
            confidence_score=response.confidence_score,
            response_time_ms=response.response_time_ms,
            model_version=response.model_version,
            retrieved_documents=[
                {
                    'doc_id': doc.doc_id,
                    'score': doc.score,
                    'metadata': doc.metadata
                }
                for doc in response.retrieved_documents
            ]
        )
        db.session.add(chat_record)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message_id': chat_record.id,
            'response': response.answer,
            'confidence_score': response.confidence_score,
            'response_time_ms': response.response_time_ms,
            'model_version': response.model_version,
            'query_type': query_type,
            'retrieved_sources': len(response.retrieved_documents)
        })
        
    except Exception as e:
        logger.error(f"Chat message processing failed: {str(e)}")
        return jsonify({'error': 'Failed to process message'}), 500

@chat_bp.route('/history', methods=['GET'])
@jwt_required()
def get_chat_history():
    """
    Get user's chat history with the medical assistant
    """
    try:
        user_id = get_jwt_identity()
        
        # Get pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 50, type=int), 100)
        
        # Query chat history
        chats = ChatHistory.query.filter_by(user_id=user_id)\
            .order_by(ChatHistory.created_at.desc())\
            .paginate(page=page, per_page=per_page, error_out=False)
        
        return jsonify({
            'success': True,
            'chats': [
                {
                    'id': chat.id,
                    'user_message': chat.user_message,
                    'ai_response': chat.ai_response,
                    'confidence_score': chat.confidence_score,
                    'response_time_ms': chat.response_time_ms,
                    'model_version': chat.model_version,
                    'created_at': chat.created_at.isoformat(),
                    'sources_count': len(chat.retrieved_documents) if chat.retrieved_documents else 0
                }
                for chat in chats.items
            ],
            'pagination': {
                'page': chats.page,
                'pages': chats.pages,
                'per_page': chats.per_page,
                'total': chats.total,
                'has_next': chats.has_next,
                'has_prev': chats.has_prev
            }
        })
        
    except Exception as e:
        logger.error(f"Failed to get chat history: {str(e)}")
        return jsonify({'error': 'Failed to retrieve chat history'}), 500

@chat_bp.route('/conversation/<int:chat_id>', methods=['GET'])
@jwt_required()
def get_conversation_details():
    """
    Get detailed information about a specific conversation
    """
    try:
        user_id = get_jwt_identity()
        chat_id = request.view_args['chat_id']
        
        # Get chat record
        chat = ChatHistory.query.filter_by(id=chat_id, user_id=user_id).first()
        
        if not chat:
            return jsonify({'error': 'Chat not found'}), 404
        
        return jsonify({
            'success': True,
            'chat': {
                'id': chat.id,
                'user_message': chat.user_message,
                'ai_response': chat.ai_response,
                'confidence_score': chat.confidence_score,
                'response_time_ms': chat.response_time_ms,
                'model_version': chat.model_version,
                'created_at': chat.created_at.isoformat(),
                'retrieved_documents': chat.retrieved_documents or []
            }
        })
        
    except Exception as e:
        logger.error(f"Failed to get conversation details: {str(e)}")
        return jsonify({'error': 'Failed to retrieve conversation details'}), 500

@chat_bp.route('/feedback', methods=['POST'])
@jwt_required()
def submit_feedback():
    """
    Submit feedback for a chat response to improve the model
    """
    try:
        data = request.get_json()
        chat_id = data.get('chat_id')
        rating = data.get('rating')  # 1-5 scale
        feedback_text = data.get('feedback', '').strip()
        
        if not chat_id or not rating:
            return jsonify({'error': 'Chat ID and rating are required'}), 400
        
        if not (1 <= rating <= 5):
            return jsonify({'error': 'Rating must be between 1 and 5'}), 400
        
        user_id = get_jwt_identity()
        
        # Verify chat belongs to user
        chat = ChatHistory.query.filter_by(id=chat_id, user_id=user_id).first()
        if not chat:
            return jsonify({'error': 'Chat not found'}), 404
        
        # Update chat with feedback
        chat.user_feedback = {
            'rating': rating,
            'feedback_text': feedback_text,
            'submitted_at': datetime.utcnow().isoformat()
        }
        db.session.commit()
        
        logger.info(f"Feedback submitted for chat {chat_id}: rating={rating}")
        
        return jsonify({
            'success': True,
            'message': 'Feedback submitted successfully'
        })
        
    except Exception as e:
        logger.error(f"Failed to submit feedback: {str(e)}")
        return jsonify({'error': 'Failed to submit feedback'}), 500

@chat_bp.route('/suggestions', methods=['GET'])
@jwt_required()
def get_chat_suggestions():
    """
    Get suggested questions/topics for the medical assistant
    """
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        # Base suggestions
        suggestions = [
            "What are the side effects of acetaminophen?",
            "Is ibuprofen safe during pregnancy?",
            "How do I know if I'm allergic to a medication?",
            "What should I do if I miss a dose?",
            "Can I take multiple pain relievers together?",
            "What are the signs of medication overdose?",
            "How should I store my medications?",
            "What information should I tell my doctor about my medications?"
        ]
        
        # Personalized suggestions based on user profile
        if user and user.health_profile:
            profile = user.health_profile
            
            if profile.is_pregnant:
                suggestions.extend([
                    "Which medications are safe during pregnancy?",
                    "What pain relievers can I take while pregnant?",
                    "Are there any medications I should avoid during pregnancy?"
                ])
            
            if profile.is_breastfeeding:
                suggestions.extend([
                    "Which medications are safe while breastfeeding?",
                    "Can medications affect breast milk?",
                    "What should I avoid while nursing?"
                ])
            
            if profile.allergies:
                suggestions.extend([
                    f"Are there alternatives to medications I'm allergic to?",
                    "How can I identify medications that might cause allergic reactions?",
                    "What should I do if I have an allergic reaction to a medication?"
                ])
            
            if profile.current_medications:
                suggestions.extend([
                    "Can my current medications interact with new ones?",
                    "What should I monitor while taking multiple medications?",
                    "How can I manage my medication schedule?"
                ])
        
        # Shuffle and limit suggestions
        import random
        random.shuffle(suggestions)
        suggestions = suggestions[:8]  # Return up to 8 suggestions
        
        return jsonify({
            'success': True,
            'suggestions': suggestions
        })
        
    except Exception as e:
        logger.error(f"Failed to get chat suggestions: {str(e)}")
        return jsonify({'error': 'Failed to get suggestions'}), 500

@chat_bp.route('/clear-history', methods=['DELETE'])
@jwt_required()
def clear_chat_history():
    """
    Clear user's chat history
    """
    try:
        user_id = get_jwt_identity()
        
        # Delete all chat history for the user
        deleted_count = ChatHistory.query.filter_by(user_id=user_id).delete()
        db.session.commit()
        
        logger.info(f"Cleared {deleted_count} chat records for user {user_id}")
        
        return jsonify({
            'success': True,
            'message': f'Cleared {deleted_count} chat messages',
            'deleted_count': deleted_count
        })
        
    except Exception as e:
        logger.error(f"Failed to clear chat history: {str(e)}")
        return jsonify({'error': 'Failed to clear chat history'}), 500

@chat_bp.route('/export', methods=['GET'])
@jwt_required()
def export_chat_history():
    """
    Export user's chat history as JSON
    """
    try:
        user_id = get_jwt_identity()
        
        # Get all chat history
        chats = ChatHistory.query.filter_by(user_id=user_id)\
            .order_by(ChatHistory.created_at.asc()).all()
        
        # Format for export
        export_data = {
            'export_date': datetime.utcnow().isoformat(),
            'user_id': user_id,
            'total_conversations': len(chats),
            'conversations': [
                {
                    'id': chat.id,
                    'timestamp': chat.created_at.isoformat(),
                    'user_message': chat.user_message,
                    'ai_response': chat.ai_response,
                    'confidence_score': chat.confidence_score,
                    'response_time_ms': chat.response_time_ms,
                    'model_version': chat.model_version,
                    'user_feedback': chat.user_feedback
                }
                for chat in chats
            ]
        }
        
        return jsonify({
            'success': True,
            'export_data': export_data
        })
        
    except Exception as e:
        logger.error(f"Failed to export chat history: {str(e)}")
        return jsonify({'error': 'Failed to export chat history'}), 500