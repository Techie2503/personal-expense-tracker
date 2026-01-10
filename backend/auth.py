"""
Google OAuth Authentication
Handles Google login and token verification
"""
import os
from typing import Optional, Dict
from google.oauth2 import id_token
from google.auth.transport import requests
import logging

logger = logging.getLogger(__name__)

# Google OAuth client ID (from environment)
GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID', '')


def verify_google_token(token: str) -> Optional[Dict]:
    """
    Verify Google ID token and return user info
    Returns: {user_id, email, name} or None if invalid
    """
    if not GOOGLE_CLIENT_ID:
        logger.error("GOOGLE_CLIENT_ID not configured")
        # For local dev without Google OAuth, return dummy user
        if os.getenv('ENVIRONMENT') == 'local':
            return {
                'user_id': 'local_user_123',
                'email': 'local@example.com',
                'name': 'Local User'
            }
        return None
    
    try:
        # Verify the token
        idinfo = id_token.verify_oauth2_token(
            token,
            requests.Request(),
            GOOGLE_CLIENT_ID
        )
        
        # Extract user information
        user_data = {
            'user_id': idinfo['sub'],  # Google user ID
            'email': idinfo['email'],
            'name': idinfo.get('name', idinfo['email']),
            'picture': idinfo.get('picture', '')
        }
        
        logger.info(f"Verified token for user: {user_data['email']}")
        return user_data
        
    except Exception as e:
        logger.error(f"Token verification failed: {e}")
        return None
