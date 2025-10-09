"""
Database models for RAG Medical Assistant
"""

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import json

db = SQLAlchemy()

class User(db.Model):
    """User model for authentication and profile management"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    health_profile = db.relationship('HealthProfile', backref='user', uselist=False, cascade='all, delete-orphan')
    medicine_records = db.relationship('MedicineRecord', backref='user', cascade='all, delete-orphan')
    chat_history = db.relationship('ChatHistory', backref='user', cascade='all, delete-orphan')
    
    def set_password(self, password):
        """Set password hash"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check password against hash"""
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class HealthProfile(db.Model):
    """Health profile model for personalized medical information"""
    __tablename__ = 'health_profiles'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Basic information
    age = db.Column(db.Integer)
    gender = db.Column(db.String(20))
    weight_kg = db.Column(db.Float)
    height_cm = db.Column(db.Float)
    
    # Medical conditions
    allergies = db.Column(db.Text)  # JSON string of allergies list
    chronic_conditions = db.Column(db.Text)  # JSON string of conditions
    current_medications = db.Column(db.Text)  # JSON string of medications
    
    # Special conditions
    is_pregnant = db.Column(db.Boolean, default=False)
    is_breastfeeding = db.Column(db.Boolean, default=False)
    pregnancy_trimester = db.Column(db.Integer)  # 1, 2, or 3
    
    # Emergency contacts
    emergency_contact_name = db.Column(db.String(100))
    emergency_contact_phone = db.Column(db.String(20))
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def get_allergies(self):
        """Get allergies as list"""
        if self.allergies:
            try:
                return json.loads(self.allergies)
            except json.JSONDecodeError:
                return []
        return []
    
    def set_allergies(self, allergies_list):
        """Set allergies from list"""
        self.allergies = json.dumps(allergies_list) if allergies_list else None
    
    def get_chronic_conditions(self):
        """Get chronic conditions as list"""
        if self.chronic_conditions:
            try:
                return json.loads(self.chronic_conditions)
            except json.JSONDecodeError:
                return []
        return []
    
    def set_chronic_conditions(self, conditions_list):
        """Set chronic conditions from list"""
        self.chronic_conditions = json.dumps(conditions_list) if conditions_list else None
    
    def get_current_medications(self):
        """Get current medications as list"""
        if self.current_medications:
            try:
                return json.loads(self.current_medications)
            except json.JSONDecodeError:
                return []
        return []
    
    def set_current_medications(self, medications_list):
        """Set current medications from list"""
        self.current_medications = json.dumps(medications_list) if medications_list else None
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'age': self.age,
            'gender': self.gender,
            'weight_kg': self.weight_kg,
            'height_cm': self.height_cm,
            'allergies': self.get_allergies(),
            'chronic_conditions': self.get_chronic_conditions(),
            'current_medications': self.get_current_medications(),
            'is_pregnant': self.is_pregnant,
            'is_breastfeeding': self.is_breastfeeding,
            'pregnancy_trimester': self.pregnancy_trimester,
            'emergency_contact_name': self.emergency_contact_name,
            'emergency_contact_phone': self.emergency_contact_phone,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class MedicineRecord(db.Model):
    """Medicine record model for digital medicine cabinet"""
    __tablename__ = 'medicine_records'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Medicine information
    name = db.Column(db.String(200), nullable=False)
    generic_name = db.Column(db.String(200))
    brand_name = db.Column(db.String(200))
    dosage = db.Column(db.String(100))
    form = db.Column(db.String(50))  # tablet, capsule, liquid, etc.
    
    # Recognition data
    image_path = db.Column(db.String(500))
    recognition_confidence = db.Column(db.Float)
    ml_model_version = db.Column(db.String(50))
    
    # Medical information
    active_ingredients = db.Column(db.Text)  # JSON string
    indications = db.Column(db.Text)  # JSON string
    contraindications = db.Column(db.Text)  # JSON string
    side_effects = db.Column(db.Text)  # JSON string
    interactions = db.Column(db.Text)  # JSON string
    
    # Safety information
    pregnancy_category = db.Column(db.String(10))
    breastfeeding_safe = db.Column(db.Boolean)
    age_restrictions = db.Column(db.String(100))
    
    # Inventory
    quantity = db.Column(db.Integer, default=0)
    expiry_date = db.Column(db.Date)
    lot_number = db.Column(db.String(50))
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def get_active_ingredients(self):
        """Get active ingredients as list"""
        if self.active_ingredients:
            try:
                return json.loads(self.active_ingredients)
            except json.JSONDecodeError:
                return []
        return []
    
    def set_active_ingredients(self, ingredients_list):
        """Set active ingredients from list"""
        self.active_ingredients = json.dumps(ingredients_list) if ingredients_list else None
    
    def get_indications(self):
        """Get indications as list"""
        if self.indications:
            try:
                return json.loads(self.indications)
            except json.JSONDecodeError:
                return []
        return []
    
    def set_indications(self, indications_list):
        """Set indications from list"""
        self.indications = json.dumps(indications_list) if indications_list else None
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'generic_name': self.generic_name,
            'brand_name': self.brand_name,
            'dosage': self.dosage,
            'form': self.form,
            'active_ingredients': self.get_active_ingredients(),
            'indications': self.get_indications(),
            'pregnancy_category': self.pregnancy_category,
            'breastfeeding_safe': self.breastfeeding_safe,
            'quantity': self.quantity,
            'expiry_date': self.expiry_date.isoformat() if self.expiry_date else None,
            'recognition_confidence': self.recognition_confidence,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class ChatHistory(db.Model):
    """Chat history model for RAG conversations"""
    __tablename__ = 'chat_history'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Conversation data
    session_id = db.Column(db.String(100), nullable=False, index=True)
    message_type = db.Column(db.String(20), nullable=False)  # 'user' or 'assistant'
    content = db.Column(db.Text, nullable=False)
    
    # RAG metadata
    retrieved_documents = db.Column(db.Text)  # JSON string of retrieved docs
    similarity_scores = db.Column(db.Text)  # JSON string of scores
    model_version = db.Column(db.String(50))
    response_time_ms = db.Column(db.Integer)
    
    # Context
    health_context_used = db.Column(db.Boolean, default=False)
    medicine_context_used = db.Column(db.Boolean, default=False)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def get_retrieved_documents(self):
        """Get retrieved documents as list"""
        if self.retrieved_documents:
            try:
                return json.loads(self.retrieved_documents)
            except json.JSONDecodeError:
                return []
        return []
    
    def set_retrieved_documents(self, docs_list):
        """Set retrieved documents from list"""
        self.retrieved_documents = json.dumps(docs_list) if docs_list else None
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'session_id': self.session_id,
            'message_type': self.message_type,
            'content': self.content,
            'retrieved_documents': self.get_retrieved_documents(),
            'model_version': self.model_version,
            'response_time_ms': self.response_time_ms,
            'health_context_used': self.health_context_used,
            'medicine_context_used': self.medicine_context_used,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class VectorIndex(db.Model):
    """Vector index metadata for FAISS database"""
    __tablename__ = 'vector_indices'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Index information
    index_name = db.Column(db.String(100), nullable=False, unique=True)
    index_type = db.Column(db.String(50), nullable=False)  # 'faiss', 'annoy', 'hnswlib'
    dimension = db.Column(db.Integer, nullable=False)
    total_vectors = db.Column(db.Integer, default=0)
    
    # Model information
    embedding_model = db.Column(db.String(100), nullable=False)
    model_version = db.Column(db.String(50))
    
    # File paths
    index_file_path = db.Column(db.String(500))
    metadata_file_path = db.Column(db.String(500))
    
    # Performance metrics
    build_time_seconds = db.Column(db.Float)
    index_size_mb = db.Column(db.Float)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'index_name': self.index_name,
            'index_type': self.index_type,
            'dimension': self.dimension,
            'total_vectors': self.total_vectors,
            'embedding_model': self.embedding_model,
            'model_version': self.model_version,
            'build_time_seconds': self.build_time_seconds,
            'index_size_mb': self.index_size_mb,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }