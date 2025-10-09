"""
Health profile routes for personalized medical information
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, User, HealthProfile
import logging

logger = logging.getLogger(__name__)
bp = Blueprint('health_profile', __name__)

@bp.route('/profile', methods=['GET'])
@jwt_required()
def get_health_profile():
    """Get user's health profile"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        health_profile = user.health_profile
        if not health_profile:
            # Create empty health profile if it doesn't exist
            health_profile = HealthProfile(user_id=user_id)
            db.session.add(health_profile)
            db.session.commit()
        
        return jsonify({
            'health_profile': health_profile.to_dict()
        }), 200
        
    except Exception as e:
        logger.error(f"Health profile fetch error: {str(e)}")
        return jsonify({'error': 'Failed to fetch health profile'}), 500

@bp.route('/profile', methods=['PUT'])
@jwt_required()
def update_health_profile():
    """Update user's health profile"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        health_profile = user.health_profile
        if not health_profile:
            health_profile = HealthProfile(user_id=user_id)
            db.session.add(health_profile)
        
        data = request.get_json()
        
        # Update basic information
        if 'age' in data:
            health_profile.age = data['age']
        if 'gender' in data:
            health_profile.gender = data['gender']
        if 'weight_kg' in data:
            health_profile.weight_kg = data['weight_kg']
        if 'height_cm' in data:
            health_profile.height_cm = data['height_cm']
        
        # Update medical conditions
        if 'allergies' in data:
            health_profile.set_allergies(data['allergies'])
        if 'chronic_conditions' in data:
            health_profile.set_chronic_conditions(data['chronic_conditions'])
        if 'current_medications' in data:
            health_profile.set_current_medications(data['current_medications'])
        
        # Update special conditions
        if 'is_pregnant' in data:
            health_profile.is_pregnant = data['is_pregnant']
        if 'is_breastfeeding' in data:
            health_profile.is_breastfeeding = data['is_breastfeeding']
        if 'pregnancy_trimester' in data:
            health_profile.pregnancy_trimester = data['pregnancy_trimester']
        
        # Update emergency contacts
        if 'emergency_contact_name' in data:
            health_profile.emergency_contact_name = data['emergency_contact_name']
        if 'emergency_contact_phone' in data:
            health_profile.emergency_contact_phone = data['emergency_contact_phone']
        
        db.session.commit()
        
        logger.info(f"Health profile updated for user: {user.email}")
        
        return jsonify({
            'message': 'Health profile updated successfully',
            'health_profile': health_profile.to_dict()
        }), 200
        
    except Exception as e:
        logger.error(f"Health profile update error: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Failed to update health profile'}), 500

@bp.route('/allergies', methods=['POST'])
@jwt_required()
def add_allergy():
    """Add a new allergy to user's profile"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        health_profile = user.health_profile
        if not health_profile:
            health_profile = HealthProfile(user_id=user_id)
            db.session.add(health_profile)
        
        data = request.get_json()
        allergy = data.get('allergy', '').strip()
        
        if not allergy:
            return jsonify({'error': 'Allergy name is required'}), 400
        
        # Get current allergies and add new one
        current_allergies = health_profile.get_allergies()
        if allergy not in current_allergies:
            current_allergies.append(allergy)
            health_profile.set_allergies(current_allergies)
            db.session.commit()
        
        return jsonify({
            'message': 'Allergy added successfully',
            'allergies': health_profile.get_allergies()
        }), 200
        
    except Exception as e:
        logger.error(f"Add allergy error: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Failed to add allergy'}), 500

@bp.route('/allergies/<allergy>', methods=['DELETE'])
@jwt_required()
def remove_allergy(allergy):
    """Remove an allergy from user's profile"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user or not user.health_profile:
            return jsonify({'error': 'Health profile not found'}), 404
        
        health_profile = user.health_profile
        current_allergies = health_profile.get_allergies()
        
        if allergy in current_allergies:
            current_allergies.remove(allergy)
            health_profile.set_allergies(current_allergies)
            db.session.commit()
        
        return jsonify({
            'message': 'Allergy removed successfully',
            'allergies': health_profile.get_allergies()
        }), 200
        
    except Exception as e:
        logger.error(f"Remove allergy error: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Failed to remove allergy'}), 500

@bp.route('/medications', methods=['POST'])
@jwt_required()
def add_current_medication():
    """Add a current medication to user's profile"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        health_profile = user.health_profile
        if not health_profile:
            health_profile = HealthProfile(user_id=user_id)
            db.session.add(health_profile)
        
        data = request.get_json()
        medication = data.get('medication', '').strip()
        
        if not medication:
            return jsonify({'error': 'Medication name is required'}), 400
        
        # Get current medications and add new one
        current_medications = health_profile.get_current_medications()
        if medication not in current_medications:
            current_medications.append(medication)
            health_profile.set_current_medications(current_medications)
            db.session.commit()
        
        return jsonify({
            'message': 'Medication added successfully',
            'current_medications': health_profile.get_current_medications()
        }), 200
        
    except Exception as e:
        logger.error(f"Add medication error: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Failed to add medication'}), 500

@bp.route('/medications/<medication>', methods=['DELETE'])
@jwt_required()
def remove_current_medication(medication):
    """Remove a current medication from user's profile"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user or not user.health_profile:
            return jsonify({'error': 'Health profile not found'}), 404
        
        health_profile = user.health_profile
        current_medications = health_profile.get_current_medications()
        
        if medication in current_medications:
            current_medications.remove(medication)
            health_profile.set_current_medications(current_medications)
            db.session.commit()
        
        return jsonify({
            'message': 'Medication removed successfully',
            'current_medications': health_profile.get_current_medications()
        }), 200
        
    except Exception as e:
        logger.error(f"Remove medication error: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Failed to remove medication'}), 500

@bp.route('/safety-check', methods=['POST'])
@jwt_required()
def safety_check():
    """Perform safety check for a medication against user's health profile"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user or not user.health_profile:
            return jsonify({'error': 'Health profile not found'}), 404
        
        data = request.get_json()
        medication_name = data.get('medication_name', '').strip()
        
        if not medication_name:
            return jsonify({'error': 'Medication name is required'}), 400
        
        health_profile = user.health_profile
        warnings = []
        
        # Check pregnancy warnings
        if health_profile.is_pregnant:
            warnings.append({
                'type': 'pregnancy',
                'severity': 'high',
                'message': f'⚠️ PREGNANCY ALERT: Please consult your doctor before taking {medication_name} during pregnancy.'
            })
        
        # Check breastfeeding warnings
        if health_profile.is_breastfeeding:
            warnings.append({
                'type': 'breastfeeding',
                'severity': 'medium',
                'message': f'⚠️ BREASTFEEDING ALERT: Please consult your doctor before taking {medication_name} while breastfeeding.'
            })
        
        # Check age restrictions (basic example)
        if health_profile.age and health_profile.age < 18:
            warnings.append({
                'type': 'age',
                'severity': 'medium',
                'message': f'⚠️ AGE ALERT: {medication_name} may have special dosing considerations for patients under 18.'
            })
        
        # Check allergies (basic keyword matching)
        allergies = health_profile.get_allergies()
        for allergy in allergies:
            if allergy.lower() in medication_name.lower():
                warnings.append({
                    'type': 'allergy',
                    'severity': 'critical',
                    'message': f'🚨 ALLERGY ALERT: You have a known allergy to {allergy}. DO NOT take {medication_name}!'
                })
        
        # Check current medications for basic interactions
        current_medications = health_profile.get_current_medications()
        if current_medications:
            warnings.append({
                'type': 'interaction',
                'severity': 'medium',
                'message': f'⚠️ INTERACTION CHECK: You are currently taking other medications. Please consult your pharmacist about potential interactions with {medication_name}.'
            })
        
        return jsonify({
            'medication_name': medication_name,
            'warnings': warnings,
            'safety_score': 'high' if not warnings else 'medium' if len(warnings) <= 2 else 'low',
            'recommendation': 'Safe to proceed' if not warnings else 'Consult healthcare provider' if len(warnings) <= 2 else 'Do not take without medical supervision'
        }), 200
        
    except Exception as e:
        logger.error(f"Safety check error: {str(e)}")
        return jsonify({'error': 'Failed to perform safety check'}), 500