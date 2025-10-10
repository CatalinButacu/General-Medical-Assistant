"""
Medicine Cabinet Management Routes.

This module provides endpoints for managing user medicine cabinets,
including medication tracking, dosage schedules, and drug interactions.
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime, timedelta
import logging

from ..models import db, User, MedicineCabinet
from ..ml.custom_rag_pipeline import CustomRAGPipeline

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

medicine_bp = Blueprint('medicine', __name__, url_prefix='/api/medicine')

# Initialize RAG pipeline for drug information and interactions
rag_pipeline = None

try:
    rag_pipeline = CustomRAGPipeline()
    logger.info("RAG pipeline initialized for medicine information")
except Exception as e:
    logger.error(f"Failed to initialize RAG pipeline: {e}")


@medicine_bp.route('/', methods=['GET'])
@jwt_required()
def get_medicine_cabinet():
    """Get user's medicine cabinet."""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
            
        medicines = MedicineCabinet.query.filter_by(user_id=user_id).all()
        
        medicine_list = []
        for medicine in medicines:
            medicine_list.append({
                'id': medicine.id,
                'name': medicine.name,
                'dosage': medicine.dosage,
                'frequency': medicine.frequency,
                'start_date': medicine.start_date.isoformat() if medicine.start_date else None,
                'end_date': medicine.end_date.isoformat() if medicine.end_date else None,
                'notes': medicine.notes,
                'is_active': medicine.is_active,
                'created_at': medicine.created_at.isoformat(),
                'updated_at': medicine.updated_at.isoformat()
            })
            
        return jsonify({
            'medicines': medicine_list,
            'total_count': len(medicine_list)
        }), 200
        
    except Exception as e:
        logger.error(f"Error retrieving medicine cabinet: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@medicine_bp.route('/', methods=['POST'])
@jwt_required()
def add_medicine():
    """Add a new medicine to user's cabinet."""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
            
        data = request.get_json()
        
        # Validate required fields
        if not data or not data.get('name'):
            return jsonify({'error': 'Medicine name is required'}), 400
            
        # Parse dates if provided
        start_date = None
        end_date = None
        
        if data.get('start_date'):
            try:
                start_date = datetime.fromisoformat(data['start_date'].replace('Z', '+00:00'))
            except ValueError:
                return jsonify({'error': 'Invalid start_date format'}), 400
                
        if data.get('end_date'):
            try:
                end_date = datetime.fromisoformat(data['end_date'].replace('Z', '+00:00'))
            except ValueError:
                return jsonify({'error': 'Invalid end_date format'}), 400
                
        # Create new medicine entry
        medicine = MedicineCabinet(
            user_id=user_id,
            name=data['name'],
            dosage=data.get('dosage'),
            frequency=data.get('frequency'),
            start_date=start_date,
            end_date=end_date,
            notes=data.get('notes'),
            is_active=data.get('is_active', True)
        )
        
        db.session.add(medicine)
        db.session.commit()
        
        return jsonify({
            'message': 'Medicine added successfully',
            'medicine_id': medicine.id
        }), 201
        
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Database error adding medicine: {e}")
        return jsonify({'error': 'Database error'}), 500
    except Exception as e:
        logger.error(f"Error adding medicine: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@medicine_bp.route('/<int:medicine_id>', methods=['GET'])
@jwt_required()
def get_medicine(medicine_id):
    """Get specific medicine details."""
    try:
        user_id = get_jwt_identity()
        medicine = MedicineCabinet.query.filter_by(
            id=medicine_id, 
            user_id=user_id
        ).first()
        
        if not medicine:
            return jsonify({'error': 'Medicine not found'}), 404
            
        return jsonify({
            'id': medicine.id,
            'name': medicine.name,
            'dosage': medicine.dosage,
            'frequency': medicine.frequency,
            'start_date': medicine.start_date.isoformat() if medicine.start_date else None,
            'end_date': medicine.end_date.isoformat() if medicine.end_date else None,
            'notes': medicine.notes,
            'is_active': medicine.is_active,
            'created_at': medicine.created_at.isoformat(),
            'updated_at': medicine.updated_at.isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Error retrieving medicine: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@medicine_bp.route('/<int:medicine_id>', methods=['PUT'])
@jwt_required()
def update_medicine(medicine_id):
    """Update medicine details."""
    try:
        user_id = get_jwt_identity()
        medicine = MedicineCabinet.query.filter_by(
            id=medicine_id, 
            user_id=user_id
        ).first()
        
        if not medicine:
            return jsonify({'error': 'Medicine not found'}), 404
            
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        # Update fields
        medicine.name = data.get('name', medicine.name)
        medicine.dosage = data.get('dosage', medicine.dosage)
        medicine.frequency = data.get('frequency', medicine.frequency)
        medicine.notes = data.get('notes', medicine.notes)
        medicine.is_active = data.get('is_active', medicine.is_active)
        
        # Update dates if provided
        if 'start_date' in data:
            if data['start_date']:
                try:
                    medicine.start_date = datetime.fromisoformat(
                        data['start_date'].replace('Z', '+00:00')
                    )
                except ValueError:
                    return jsonify({'error': 'Invalid start_date format'}), 400
            else:
                medicine.start_date = None
                
        if 'end_date' in data:
            if data['end_date']:
                try:
                    medicine.end_date = datetime.fromisoformat(
                        data['end_date'].replace('Z', '+00:00')
                    )
                except ValueError:
                    return jsonify({'error': 'Invalid end_date format'}), 400
            else:
                medicine.end_date = None
                
        medicine.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({'message': 'Medicine updated successfully'}), 200
        
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Database error updating medicine: {e}")
        return jsonify({'error': 'Database error'}), 500
    except Exception as e:
        logger.error(f"Error updating medicine: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@medicine_bp.route('/<int:medicine_id>', methods=['DELETE'])
@jwt_required()
def delete_medicine(medicine_id):
    """Delete medicine from cabinet."""
    try:
        user_id = get_jwt_identity()
        medicine = MedicineCabinet.query.filter_by(
            id=medicine_id, 
            user_id=user_id
        ).first()
        
        if not medicine:
            return jsonify({'error': 'Medicine not found'}), 404
            
        db.session.delete(medicine)
        db.session.commit()
        
        return jsonify({'message': 'Medicine deleted successfully'}), 200
        
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Database error deleting medicine: {e}")
        return jsonify({'error': 'Database error'}), 500
    except Exception as e:
        logger.error(f"Error deleting medicine: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@medicine_bp.route('/interactions', methods=['POST'])
@jwt_required()
def check_drug_interactions():
    """Check for potential drug interactions."""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        if not data or not data.get('medicines'):
            return jsonify({'error': 'Medicine list is required'}), 400
            
        medicines = data['medicines']
        
        if not rag_pipeline:
            return jsonify({'error': 'RAG pipeline not available'}), 503
            
        # Create query for drug interactions
        medicine_list = ', '.join(medicines)
        query = f"Check for drug interactions between these medications: {medicine_list}"
        
        # Get interaction information from RAG pipeline
        interaction_info = rag_pipeline.generate_response(query, "")
        
        return jsonify({
            'medicines': medicines,
            'interaction_analysis': interaction_info,
            'checked_at': datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Error checking drug interactions: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@medicine_bp.route('/schedule', methods=['GET'])
@jwt_required()
def get_medication_schedule():
    """Get user's medication schedule for today."""
    try:
        user_id = get_jwt_identity()
        today = datetime.utcnow().date()
        
        # Get active medicines
        medicines = MedicineCabinet.query.filter_by(
            user_id=user_id, 
            is_active=True
        ).filter(
            (MedicineCabinet.start_date <= today) | (MedicineCabinet.start_date.is_(None))
        ).filter(
            (MedicineCabinet.end_date >= today) | (MedicineCabinet.end_date.is_(None))
        ).all()
        
        schedule = []
        for medicine in medicines:
            if medicine.frequency:
                # Parse frequency and create schedule entries
                # This is a simplified version - in production, you'd want more sophisticated scheduling
                frequency_parts = medicine.frequency.lower().split()
                
                if 'daily' in medicine.frequency.lower() or 'day' in medicine.frequency.lower():
                    times_per_day = 1
                    if any(char.isdigit() for char in medicine.frequency):
                        # Extract number from frequency string
                        import re
                        numbers = re.findall(r'\d+', medicine.frequency)
                        if numbers:
                            times_per_day = int(numbers[0])
                    
                    # Create schedule entries
                    for i in range(times_per_day):
                        hour = 8 + (i * (12 // times_per_day))  # Distribute throughout day
                        schedule.append({
                            'medicine_id': medicine.id,
                            'medicine_name': medicine.name,
                            'dosage': medicine.dosage,
                            'scheduled_time': f"{hour:02d}:00",
                            'taken': False  # This would be tracked in a separate table in production
                        })
        
        return jsonify({
            'date': today.isoformat(),
            'schedule': schedule,
            'total_medications': len(schedule)
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting medication schedule: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@medicine_bp.route('/search', methods=['GET'])
@jwt_required()
def search_medicine_info():
    """Search for medicine information using RAG pipeline."""
    try:
        medicine_name = request.args.get('name')
        
        if not medicine_name:
            return jsonify({'error': 'Medicine name is required'}), 400
            
        if not rag_pipeline:
            return jsonify({'error': 'RAG pipeline not available'}), 503
            
        # Query for medicine information
        query = f"Provide detailed information about the medication {medicine_name}, including uses, dosage, side effects, and precautions"
        
        medicine_info = rag_pipeline.generate_response(query, "")
        
        return jsonify({
            'medicine_name': medicine_name,
            'information': medicine_info,
            'searched_at': datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Error searching medicine info: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@medicine_bp.route('/health-check', methods=['GET'])
def health_check():
    """Health check endpoint for the medicine service."""
    return jsonify({
        'status': 'healthy',
        'service': 'medicine',
        'timestamp': datetime.utcnow().isoformat()
    }), 200