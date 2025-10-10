"""
Health Profile Management Routes.

This module provides endpoints for managing user health profiles,
including medical history, conditions, medications, and health metrics.
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime
import logging

from ..models import db, User, HealthProfile
from ..ml.custom_rag_pipeline import CustomRAGPipeline

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

health_profile_bp = Blueprint(
    'health_profile', __name__, url_prefix='/api/health-profile'
)

# Initialize RAG pipeline for health recommendations
rag_pipeline = None

try:
    rag_pipeline = CustomRAGPipeline()
    logger.info("RAG pipeline initialized for health profile recommendations")
except Exception as e:
    logger.error(f"Failed to initialize RAG pipeline: {e}")


@health_profile_bp.route('/', methods=['GET'])
@jwt_required()
def get_health_profile():
    """Get user's health profile."""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        if not user:
            return jsonify({'error': 'User not found'}), 404

        health_profile = HealthProfile.query.filter_by(
            user_id=user_id
        ).first()

        if not health_profile:
            return jsonify({'message': 'No health profile found'}), 404

        return jsonify({
            'id': health_profile.id,
            'age': health_profile.age,
            'gender': health_profile.gender,
            'height': health_profile.height,
            'weight': health_profile.weight,
            'blood_type': health_profile.blood_type,
            'allergies': health_profile.allergies,
            'chronic_conditions': health_profile.chronic_conditions,
            'current_medications': health_profile.current_medications,
            'emergency_contact': health_profile.emergency_contact,
            'medical_history': health_profile.medical_history,
            'created_at': health_profile.created_at.isoformat(),
            'updated_at': health_profile.updated_at.isoformat()
        }), 200

    except Exception as e:
        logger.error(f"Error retrieving health profile: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@health_profile_bp.route('/', methods=['POST'])
@jwt_required()
def create_health_profile():
    """Create or update user's health profile."""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        if not user:
            return jsonify({'error': 'User not found'}), 404

        data = request.get_json()

        # Validate required fields
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        # Check if profile already exists
        existing_profile = HealthProfile.query.filter_by(user_id=user_id).first()

        if existing_profile:
            # Update existing profile
            existing_profile.age = data.get('age', existing_profile.age)
            existing_profile.gender = data.get('gender', existing_profile.gender)
            existing_profile.height = data.get(
                'height', existing_profile.height
            )
            existing_profile.weight = data.get(
                'weight', existing_profile.weight
            )
            existing_profile.blood_type = data.get(
                'blood_type', existing_profile.blood_type
            )
            existing_profile.allergies = data.get(
                'allergies', existing_profile.allergies
            )
            existing_profile.chronic_conditions = data.get(
                'chronic_conditions', existing_profile.chronic_conditions
            )
            existing_profile.current_medications = data.get(
                'current_medications', existing_profile.current_medications
            )
            existing_profile.emergency_contact = data.get('emergency_contact', existing_profile.emergency_contact)
            existing_profile.medical_history = data.get('medical_history', existing_profile.medical_history)
            existing_profile.updated_at = datetime.utcnow()

            db.session.commit()

            return jsonify({
                'message': 'Health profile updated successfully',
                'profile_id': existing_profile.id
            }), 200
        else:
            # Create new profile
            health_profile = HealthProfile(
                user_id=user_id,
                age=data.get('age'),
                gender=data.get('gender'),
                height=data.get('height'),
                weight=data.get('weight'),
                blood_type=data.get('blood_type'),
                allergies=data.get('allergies', []),
                chronic_conditions=data.get('chronic_conditions', []),
                current_medications=data.get('current_medications', []),
                emergency_contact=data.get('emergency_contact'),
                medical_history=data.get('medical_history', [])
            )

            db.session.add(health_profile)
            db.session.commit()

            return jsonify({
                'message': 'Health profile created successfully',
                'profile_id': health_profile.id
            }), 201

    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Database error creating/updating health profile: {e}")
        return jsonify({'error': 'Database error'}), 500
    except Exception as e:
        logger.error(f"Error creating/updating health profile: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@health_profile_bp.route('/', methods=['PUT'])
@jwt_required()
def update_health_profile():
    """Update user's health profile."""
    try:
        user_id = get_jwt_identity()
        health_profile = HealthProfile.query.filter_by(user_id=user_id).first()

        if not health_profile:
            return jsonify({'error': 'Health profile not found'}), 404

        data = request.get_json()

        if not data:
            return jsonify({'error': 'No data provided'}), 400

        # Update fields
        health_profile.age = data.get('age', health_profile.age)
        health_profile.gender = data.get('gender', health_profile.gender)
        health_profile.height = data.get('height', health_profile.height)
        health_profile.weight = data.get('weight', health_profile.weight)
        health_profile.blood_type = data.get('blood_type', health_profile.blood_type)
        health_profile.allergies = data.get('allergies', health_profile.allergies)
        health_profile.chronic_conditions = data.get(
            'chronic_conditions', health_profile.chronic_conditions
        )
        health_profile.current_medications = data.get(
            'current_medications', health_profile.current_medications
        )
        health_profile.emergency_contact = data.get(
            'emergency_contact', health_profile.emergency_contact
        )
        health_profile.medical_history = data.get(
            'medical_history', health_profile.medical_history
        )
        health_profile.updated_at = datetime.utcnow()

        db.session.commit()

        return jsonify({'message': 'Health profile updated successfully'}), 200

    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Database error updating health profile: {e}")
        return jsonify({'error': 'Database error'}), 500
    except Exception as e:
        logger.error(f"Error updating health profile: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@health_profile_bp.route('/', methods=['DELETE'])
@jwt_required()
def delete_health_profile():
    """Delete user's health profile."""
    try:
        user_id = get_jwt_identity()
        health_profile = HealthProfile.query.filter_by(user_id=user_id).first()

        if not health_profile:
            return jsonify({'error': 'Health profile not found'}), 404

        db.session.delete(health_profile)
        db.session.commit()

        return jsonify({'message': 'Health profile deleted successfully'}), 200

    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(
            f"Database error deleting health profile: {e}"
        )
        return jsonify({'error': 'Database error'}), 500
    except Exception as e:
        logger.error(
            f"Error deleting health profile: {e}"
        )
        return jsonify({'error': 'Internal server error'}), 500


@health_profile_bp.route('/recommendations', methods=['GET'])
@jwt_required()
def get_health_recommendations():
    """Get personalized health recommendations based on user's profile."""
    try:
        user_id = get_jwt_identity()
        health_profile = HealthProfile.query.filter_by(user_id=user_id).first()

        if not health_profile:
            return jsonify({'error': 'Health profile not found'}), 404

        if not rag_pipeline:
            return jsonify({'error': 'RAG pipeline not available'}), 503

        # Create context from health profile
        context = f"""
        Age: {health_profile.age}
        Gender: {health_profile.gender}
        Chronic conditions: {', '.join(health_profile.chronic_conditions) if health_profile.chronic_conditions else 'None'}
        Current medications: {', '.join(health_profile.current_medications) if health_profile.current_medications else 'None'}
        Allergies: {', '.join(health_profile.allergies) if health_profile.allergies else 'None'}
        """

        # Generate recommendations
        query = "Provide personalized health recommendations based on my profile"
        recommendations = rag_pipeline.generate_response(
            query, context
        )

        return jsonify({
            'recommendations': recommendations,
            'generated_at': datetime.utcnow().isoformat()
        }), 200

    except Exception as e:
        logger.error(
            f"Error generating health recommendations: {e}"
        )
        return jsonify({'error': 'Internal server error'}), 500


@health_profile_bp.route('/bmi', methods=['GET'])
@jwt_required()
def calculate_bmi():
    """Calculate and return user's BMI."""
    try:
        user_id = get_jwt_identity()
        health_profile = HealthProfile.query.filter_by(user_id=user_id).first()

        if not health_profile:
            return jsonify({'error': 'Health profile not found'}), 404

        if not health_profile.height or not health_profile.weight:
            return jsonify({'error': 'Height and weight required for BMI calculation'}), 400

        # Calculate BMI (weight in kg / height in m^2)
        height_m = health_profile.height / 100  # Convert cm to m
        bmi = health_profile.weight / (height_m ** 2)

        # Determine BMI category
        if bmi < 18.5:
            category = "Underweight"
        elif bmi < 25:
            category = "Normal weight"
        elif bmi < 30:
            category = "Overweight"
        else:
            category = "Obese"

        return jsonify({
            'bmi': round(bmi, 2),
            'category': category,
            'height': health_profile.height,
            'weight': health_profile.weight
        }), 200

    except Exception as e:
        logger.error(
            f"Error calculating BMI: {e}"
        )
        return jsonify({'error': 'Internal server error'}), 500


@health_profile_bp.route('/health-check', methods=['GET'])
def health_check():
    """Health check endpoint for the health profile service."""
    return jsonify({
        'status': 'healthy',
        'service': 'health-profile',
        'timestamp': datetime.utcnow().isoformat()
    }), 200
