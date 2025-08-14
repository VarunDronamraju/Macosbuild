import os
import jwt
import requests
from datetime import datetime, timedelta
from typing import Optional, Dict
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from backend.config import settings
from backend.database import SessionLocal, User
import uuid

security = HTTPBearer()

class AuthService:
    def __init__(self):
        self.google_client_id = settings.GOOGLE_CLIENT_ID
        self.google_client_secret = settings.GOOGLE_CLIENT_SECRET
        self.secret_key = settings.SECRET_KEY
        self.algorithm = "HS256"
        self.access_token_expire_minutes = 60 * 24  # 24 hours

    def exchange_code_for_token(self, authorization_code: str) -> Dict:
        """Exchange authorization code for Google access token"""
        token_url = "https://oauth2.googleapis.com/token"
        
        data = {
            'client_id': self.google_client_id,
            'client_secret': self.google_client_secret,
            'code': authorization_code,
            'grant_type': 'authorization_code',
            'redirect_uri': 'http://localhost:8000/auth/callback'
        }
        
        try:
            response = requests.post(token_url, data=data)
            response.raise_for_status()
            
            token_data = response.json()
            
            # Get user info using the access token
            user_info_url = "https://www.googleapis.com/oauth2/v2/userinfo"
            headers = {'Authorization': f"Bearer {token_data['access_token']}"}
            
            user_response = requests.get(user_info_url, headers=headers)
            user_response.raise_for_status()
            
            user_data = user_response.json()
            
            return {
                'google_id': user_data['id'],
                'email': user_data['email'],
                'name': user_data.get('name', ''),
                'picture': user_data.get('picture', ''),
                'verified_email': user_data.get('verified_email', False)
            }
            
        except requests.exceptions.RequestException as e:
            raise HTTPException(status_code=400, detail=f"Failed to exchange code for token: {str(e)}")

    def verify_google_token(self, token: str) -> Dict:
        """Verify Google OAuth token (for direct token auth)"""
        try:
            idinfo = id_token.verify_oauth2_token(
                token, google_requests.Request(), self.google_client_id
            )
            
            if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
                raise ValueError('Wrong issuer.')
                
            return {
                'google_id': idinfo['sub'],
                'email': idinfo['email'],
                'name': idinfo.get('name', ''),
                'picture': idinfo.get('picture', ''),
                'verified_email': idinfo.get('email_verified', False)
            }
        except ValueError as e:
            raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")

    def create_jwt_token(self, user_data: Dict) -> str:
        """Create JWT token"""
        expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        to_encode = {
            "sub": str(user_data["user_id"]),
            "email": user_data["email"],
            "name": user_data["name"],
            "picture": user_data.get("picture", ""),
            "exp": expire,
            "iat": datetime.utcnow(),
            "iss": "rag-companion-ai"
        }
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)

    def validate_jwt_token(self, token: str) -> Dict:
        """Validate JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            print(f"Token expired: {token[:20]}...")
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.JWTError as e:
            print(f"JWT validation error: {e}")
            print(f"Token: {token[:20]}...")
            raise HTTPException(status_code=401, detail="Invalid token")
        except Exception as e:
            print(f"Unexpected error in JWT validation: {e}")
            raise HTTPException(status_code=401, detail="Token validation failed")

    def get_or_create_user(self, google_user_data: Dict) -> User:
        """Get existing user or create new one"""
        db = SessionLocal()
        try:
            # Check if user exists by Google ID
            user = db.query(User).filter(User.google_id == google_user_data['google_id']).first()
            
            if not user:
                # Check if user exists by email (in case they signed up differently)
                user = db.query(User).filter(User.email == google_user_data['email']).first()
                
                if user:
                    # Update existing user with Google ID
                    user.google_id = google_user_data['google_id']
                    user.name = google_user_data['name']
                    user.last_login = datetime.utcnow()
                else:
                    # Create new user
                    user = User(
                        id=uuid.uuid4(),
                        google_id=google_user_data['google_id'],
                        email=google_user_data['email'],
                        name=google_user_data['name']
                    )
                    db.add(user)
                
                db.commit()
                db.refresh(user)
            else:
                # Update existing user's last login
                user.last_login = datetime.utcnow()
                user.name = google_user_data['name']  # Update name in case it changed
                db.commit()
            
            # Extract user data before closing session to avoid SQLAlchemy errors
            user_data = {
                'id': user.id,
                'google_id': user.google_id,
                'email': user.email,
                'name': user.name,
                'created_at': user.created_at,
                'last_login': user.last_login
            }
            
            return user_data
        finally:
            db.close()

    def refresh_token(self, token: str) -> str:
        """Refresh JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm], options={"verify_exp": False})
            
            # Create new token with fresh expiration
            new_payload = {
                "sub": payload["sub"],
                "email": payload["email"],
                "name": payload["name"],
                "picture": payload.get("picture", ""),
                "exp": datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes),
                "iat": datetime.utcnow(),
                "iss": "rag-companion-ai"
            }
            
            return jwt.encode(new_payload, self.secret_key, algorithm=self.algorithm)
            
        except jwt.JWTError:
            raise HTTPException(status_code=401, detail="Invalid token for refresh")

auth_service = AuthService()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    """Get current authenticated user"""
    try:
        print(f"Authentication attempt - token: {credentials.credentials[:20]}...")
        
        token = credentials.credentials
        payload = auth_service.validate_jwt_token(token)
        print(f"Token payload: {payload}")
        
        db = SessionLocal()
        try:
            # Convert string ID to UUID for database query
            import uuid
            user_id = uuid.UUID(payload["sub"])
            print(f"Looking for user with ID: {user_id}")
            
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                print(f"User not found for ID: {user_id}")
                raise HTTPException(status_code=404, detail="User not found")
            
            print(f"User found: {user.email}")
            return user
        finally:
            db.close()
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        print(f"Unexpected error in get_current_user: {e}")
        raise HTTPException(status_code=401, detail="Authentication failed")

def get_current_user_optional(credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))) -> Optional[User]:
    """Get current user if authenticated, otherwise return None"""
    if not credentials:
        return None
    
    try:
        return get_current_user(credentials)
    except HTTPException:
        return None