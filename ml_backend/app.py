"""
Flask ML Backend for RAG Medical Assistant
Custom ML-powered backend with BioBERT, FAISS, and custom RAG pipeline
"""

import os
import logging
from flask import Flask, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = os.getenv(
    'SECRET_KEY', 'dev-secret-key-change-in-production'
)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
    'DATABASE_URL', 'sqlite:///medical_rag.db'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = os.getenv(
    'JWT_SECRET_KEY', 'jwt-secret-change-in-production'
)

# Initialize extensions
db = SQLAlchemy(app)
migrate = Migrate(app, db)
jwt = JWTManager(app)
CORS(app, origins=["http://localhost:3000", "http://localhost:5173"])

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import models and routes after app initialization
try:
    from routes import (
        auth, health_profile, medicine, chat, ml_inference
    )
except ImportError as e:
    logger.warning(f"Could not import models/routes: {e}")

# Register blueprints
try:
    app.register_blueprint(auth.bp)
    app.register_blueprint(health_profile.bp)
    app.register_blueprint(medicine.bp)
    app.register_blueprint(chat.bp)
    app.register_blueprint(ml_inference.bp)
except Exception as e:
    logger.warning(f"Could not register blueprints: {e}")


@app.route('/')
def index():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'message': 'RAG Medical Assistant ML Backend is running',
        'version': '1.0.0'
    })


@app.route('/health')
def health_check():
    """Detailed health check endpoint"""
    try:
        # Test database connection
        db.session.execute('SELECT 1')
        db_status = 'connected'
    except Exception as e:
        db_status = f'error: {str(e)}'
        logger.error(f"Database health check failed: {e}")

    return jsonify({
        'status': 'healthy',
        'database': db_status,
        'ml_backend': 'operational',
        'timestamp': os.getenv('TIMESTAMP', 'unknown')
    })


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({'error': 'Endpoint not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    logger.error(f"Internal server error: {error}")
    return jsonify({'error': 'Internal server error'}), 500


if __name__ == '__main__':
    # Create database tables
    with app.app_context():
        try:
            db.create_all()
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Failed to create database tables: {e}")

    # Run the application
    debug_mode = os.getenv('FLASK_ENV') == 'development'
    app.run(
        host='0.0.0.0',
        port=int(os.getenv('PORT', 5000)),
        debug=debug_mode
    )
