"""
Routes package initialization
Imports all blueprint modules for the Flask application
"""

from .auth import auth_bp
from .chat import chat_bp
from .health_profile import health_profile_bp
from .medicine import medicine_bp

__all__ = ['auth_bp', 'chat_bp', 'health_profile_bp', 'medicine_bp']
