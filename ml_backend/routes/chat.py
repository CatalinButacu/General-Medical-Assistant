"""
Chat routes for RAG-powered medical assistance
"""

from flask import Blueprint, request, jsonify, stream_template
from flask_jwt_extended import jwt_required, get_jwt_identity
import logging
import json
from datetime import datetime

from ..models import db, User, ChatSession, ChatMessage
from ..ml.custom_rag_pipeline import MedicalRAGPipeline

logger = logging.getLogger(__name__)

chat_bp = Blueprint('chat', __name__, url_prefix='/api/chat')

# Initialize RAG pipeline (will be loaded on first use)
rag_pipeline = None


def get_rag_pipeline():
    """Get or initialize RAG pipeline"""
    global rag_pipeline
    if rag_pipeline is None:
        try:
            rag_pipeline = MedicalRAGPipeline()
            logger.info("RAG pipeline initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize RAG pipeline: {str(e)}")
            raise
    return rag_pipeline


@chat_bp.route('/sessions', methods=['GET'])
@jwt_required()
def get_chat_sessions():
    """Get all chat sessions for the current user"""
    try:
        current_user_id = get_jwt_identity()
        sessions = ChatSession.query.filter_by(user_id=current_user_id).order_by(
            ChatSession.updated_at.desc()
        ).all()
        
        return jsonify({
            'sessions': [session.to_dict() for session in sessions]
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching chat sessions: {str(e)}")
        return jsonify({'error': 'Failed to fetch chat sessions'}), 500


@chat_bp.route('/sessions', methods=['POST'])
@jwt_required()
def create_chat_session():
    """Create a new chat session"""
    try:
        current_user_id = get_jwt_identity()
        data = request.get_json()
        
        session = ChatSession(
            user_id=current_user_id,
            session_name=data.get('session_name', f'Chat {datetime.now().strftime("%Y-%m-%d %H:%M")}')
        )
        
        db.session.add(session)
        db.session.commit()
        
        logger.info(f"New chat session created: {session.id} for user {current_user_id}")
        
        return jsonify({
            'message': 'Chat session created successfully',
            'session': session.to_dict()
        }), 201
        
    except Exception as e:
        logger.error(f"Error creating chat session: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Failed to create chat session'}), 500


@chat_bp.route('/sessions/<int:session_id>', methods=['GET'])
@jwt_required()
def get_chat_session(session_id):
    """Get a specific chat session with messages"""
    try:
        current_user_id = get_jwt_identity()
        session = ChatSession.query.filter_by(
            id=session_id, 
            user_id=current_user_id
        ).first()
        
        if not session:
            return jsonify({'error': 'Chat session not found'}), 404
        
        messages = ChatMessage.query.filter_by(session_id=session_id).order_by(
            ChatMessage.created_at.asc()
        ).all()
        
        return jsonify({
            'session': session.to_dict(),
            'messages': [message.to_dict() for message in messages]
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching chat session: {str(e)}")
        return jsonify({'error': 'Failed to fetch chat session'}), 500


@chat_bp.route('/sessions/<int:session_id>', methods=['DELETE'])
@jwt_required()
def delete_chat_session(session_id):
    """Delete a chat session"""
    try:
        current_user_id = get_jwt_identity()
        session = ChatSession.query.filter_by(
            id=session_id, 
            user_id=current_user_id
        ).first()
        
        if not session:
            return jsonify({'error': 'Chat session not found'}), 404
        
        db.session.delete(session)
        db.session.commit()
        
        logger.info(f"Chat session deleted: {session_id}")
        
        return jsonify({'message': 'Chat session deleted successfully'}), 200
        
    except Exception as e:
        logger.error(f"Error deleting chat session: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Failed to delete chat session'}), 500


@chat_bp.route('/sessions/<int:session_id>/messages', methods=['POST'])
@jwt_required()
def send_message(session_id):
    """Send a message and get RAG response"""
    try:
        current_user_id = get_jwt_identity()
        data = request.get_json()
        
        # Validate session ownership
        session = ChatSession.query.filter_by(
            id=session_id, 
            user_id=current_user_id
        ).first()
        
        if not session:
            return jsonify({'error': 'Chat session not found'}), 404
        
        if not data.get('message'):
            return jsonify({'error': 'Message content is required'}), 400
        
        user_message = data['message']
        
        # Save user message
        user_msg = ChatMessage(
            session_id=session_id,
            message_type='user',
            content=user_message
        )
        db.session.add(user_msg)
        
        # Get user profile for context
        user = User.query.get(current_user_id)
        user_context = {}
        if user.health_profile:
            user_context = {
                'age': user.health_profile.age,
                'gender': user.health_profile.gender,
                'allergies': user.health_profile.allergies,
                'chronic_conditions': user.health_profile.chronic_conditions,
                'current_medications': user.health_profile.current_medications
            }
        
        # Get RAG response
        try:
            pipeline = get_rag_pipeline()
            rag_response = pipeline.generate_response(
                query=user_message,
                user_context=user_context
            )
            
            assistant_content = rag_response.get('response', 'I apologize, but I encountered an error processing your request.')
            metadata = {
                'sources': rag_response.get('sources', []),
                'confidence': rag_response.get('confidence', 0.0),
                'processing_time': rag_response.get('processing_time', 0.0)
            }
            
        except Exception as e:
            logger.error(f"RAG pipeline error: {str(e)}")
            assistant_content = "I apologize, but I'm currently experiencing technical difficulties. Please try again later."
            metadata = {'error': 'RAG pipeline unavailable'}
        
        # Save assistant message
        assistant_msg = ChatMessage(
            session_id=session_id,
            message_type='assistant',
            content=assistant_content,
            metadata=metadata
        )
        db.session.add(assistant_msg)
        
        # Update session timestamp
        session.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        logger.info(f"Message exchange completed for session {session_id}")
        
        return jsonify({
            'user_message': user_msg.to_dict(),
            'assistant_message': assistant_msg.to_dict()
        }), 200
        
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Failed to process message'}), 500


@chat_bp.route('/sessions/<int:session_id>/messages/<int:message_id>', methods=['DELETE'])
@jwt_required()
def delete_message(session_id, message_id):
    """Delete a specific message"""
    try:
        current_user_id = get_jwt_identity()
        
        # Validate session ownership
        session = ChatSession.query.filter_by(
            id=session_id, 
            user_id=current_user_id
        ).first()
        
        if not session:
            return jsonify({'error': 'Chat session not found'}), 404
        
        message = ChatMessage.query.filter_by(
            id=message_id, 
            session_id=session_id
        ).first()
        
        if not message:
            return jsonify({'error': 'Message not found'}), 404
        
        db.session.delete(message)
        db.session.commit()
        
        logger.info(f"Message deleted: {message_id} from session {session_id}")
        
        return jsonify({'message': 'Message deleted successfully'}), 200
        
    except Exception as e:
        logger.error(f"Error deleting message: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Failed to delete message'}), 500


@chat_bp.route('/quick-query', methods=['POST'])
@jwt_required()
def quick_query():
    """Quick medical query without saving to session"""
    try:
        current_user_id = get_jwt_identity()
        data = request.get_json()
        
        if not data.get('query'):
            return jsonify({'error': 'Query is required'}), 400
        
        # Get user context
        user = User.query.get(current_user_id)
        user_context = {}
        if user.health_profile:
            user_context = {
                'age': user.health_profile.age,
                'gender': user.health_profile.gender,
                'allergies': user.health_profile.allergies,
                'chronic_conditions': user.health_profile.chronic_conditions,
                'current_medications': user.health_profile.current_medications
            }
        
        # Get RAG response
        try:
            pipeline = get_rag_pipeline()
            rag_response = pipeline.generate_response(
                query=data['query'],
                user_context=user_context
            )
            
            return jsonify({
                'response': rag_response.get('response', 'No response generated'),
                'sources': rag_response.get('sources', []),
                'confidence': rag_response.get('confidence', 0.0),
                'processing_time': rag_response.get('processing_time', 0.0)
            }), 200
            
        except Exception as e:
            logger.error(f"RAG pipeline error in quick query: {str(e)}")
            return jsonify({
                'response': "I apologize, but I'm currently experiencing technical difficulties. Please try again later.",
                'error': 'RAG pipeline unavailable'
            }), 503
        
    except Exception as e:
        logger.error(f"Error processing quick query: {str(e)}")
        return jsonify({'error': 'Failed to process query'}), 500


@chat_bp.route('/health', methods=['GET'])
def health_check():
    """Health check for chat service"""
    try:
        # Test RAG pipeline availability
        pipeline_status = "available"
        try:
            get_rag_pipeline()
        except Exception:
            pipeline_status = "unavailable"
        
        return jsonify({
            'status': 'healthy',
            'rag_pipeline': pipeline_status,
            'timestamp': datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Health check error: {str(e)}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 503