from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import bcrypt
from typing import Callable
import uuid

# Load environment variables
load_dotenv()

# Constants
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 12  # 12 hour

# Get credentials from environment variables
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
SECRET_KEY = os.getenv("SECRET_KEY")
ALLOWED_DEVICE_UUIDS = [uuid.strip() for uuid in os.getenv("ALLOWED_DEVICE_UUID", "").split(",") if uuid.strip()]

# Debug print environment variables
print("DEBUG Environment Variables:")
print(f"ADMIN_USERNAME set: {bool(ADMIN_USERNAME)}")
print(f"ADMIN_PASSWORD set: {bool(ADMIN_PASSWORD)}")
print(f"SECRET_KEY set: {bool(SECRET_KEY)}")
print(f"SECRET_KEY length: {len(SECRET_KEY) if SECRET_KEY else 0}")
print(f"ALLOWED_DEVICE_UUIDS count: {len(ALLOWED_DEVICE_UUIDS)}")
print(f"ALLOWED_DEVICE_UUIDS: {ALLOWED_DEVICE_UUIDS}")

# Security scheme
bearer_scheme = HTTPBearer(auto_error=False)  # Don't auto-raise errors

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    try:
        # If the password in env is not hashed, hash it first
        if not hashed_password.startswith('$2b$'):
            return plain_password == hashed_password
        return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())
    except Exception:
        # Fallback to direct comparison if any error occurs
        return plain_password == hashed_password

def authenticate_user(username: str, password: str) -> bool:
    """Authenticate a user."""
    if username != ADMIN_USERNAME:
        return False
    return verify_password(password, ADMIN_PASSWORD)

def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    """Create a new JWT token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(request: Request) -> str:
    """Get the current user from the JWT token in cookie."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_302_FOUND,
        detail="Not authenticated",
        headers={"Location": "/"}
    )
    
    # Get token from cookie
    auth_cookie = request.cookies.get("Authorization")
    if not auth_cookie:
        print("DEBUG: No Authorization cookie found")
        raise credentials_exception
    
    if not auth_cookie.startswith("Bearer "):
        print("DEBUG: Invalid cookie format")
        raise credentials_exception
    
    token = auth_cookie.replace("Bearer ", "")
    
    try:
        print(f"DEBUG: Attempting to decode token: {token[:20]}...")
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        print(f"DEBUG: Successfully decoded token payload: {payload}")
        username: str = payload.get("sub")
        if username is None:
            print("DEBUG: No username in payload")
            raise credentials_exception
        if username != ADMIN_USERNAME:
            print(f"DEBUG: Username mismatch: {username} != {ADMIN_USERNAME}")
            raise credentials_exception
        print(f"DEBUG: Authentication successful for {username}")
        return username
    except JWTError as e:
        print(f"DEBUG: JWT Error: {str(e)}")
        raise credentials_exception
    except Exception as e:
        print(f"DEBUG: Unexpected error in get_current_user: {str(e)}")
        raise credentials_exception

def get_auth_dependency() -> Callable:
    """Returns the authentication dependency."""
    return Depends(get_current_user)

async def validate_device_uuid(request: Request) -> bool:
    """Validate the device UUID from the request headers, cookies, or query parameters against registered devices."""
    from ..main import load_data
    
    # Get device UUID from request
    device_uuid = request.headers.get("X-Device-UUID")
    if not device_uuid:
        device_uuid = request.cookies.get("X-Device-UUID")
    if not device_uuid:
        device_uuid = request.query_params.get("uuid")
    
    print(f"DEBUG: Received device UUID: {device_uuid}")
    
    if not device_uuid:
        print("DEBUG: No device UUID found in headers, cookies, or query parameters")
        return False
    
    # Load registered devices
    data_structure = load_data()
    
    # Find matching device registration
    device = next((d for d in data_structure.device_registrations if d.uuid == device_uuid), None)
    
    if not device:
        print(f"DEBUG: Device UUID {device_uuid} not found in registrations")
        return False
    
    if not device.is_active:
        print(f"DEBUG: Device UUID {device_uuid} is inactive")
        return False
    
    # Check expiration
    if device.expires_at and device.expires_at < datetime.now():
        print(f"DEBUG: Device UUID {device_uuid} has expired")
        return False
    
    # Update last used timestamp
    device.last_used = datetime.now()
    from ..main import save_data
    save_data(data_structure)
    
    print(f"DEBUG: Device UUID {device_uuid} validated successfully")
    return True

# Dependency for protected routes
require_auth = get_auth_dependency()