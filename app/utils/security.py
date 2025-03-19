from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import bcrypt
from typing import Callable, List
import uuid
from .data_handler import DataHandler

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

def get_device_uuid(request: Request) -> str:
    """
    Get device UUID from request headers.
    Returns None if no UUID is found.
    """
    if "X-Device-UUID" in request.headers:
        return request.headers["X-Device-UUID"]
    elif "device_uuid" in request.cookies:
        return request.cookies["device_uuid"]

def validate_device_uuid(request: Request, data_handler: DataHandler) -> bool:
    """
    Validate device UUID from headers.
    Returns True if the device is authorized.
    """
    device_uuid = get_device_uuid(request)
    
    if not device_uuid:
        return False
    
    # Check if device exists and is active
    for device in data_handler.data.device_registrations:
        if device.uuid == device_uuid and device.is_active:
            # Update last_used timestamp
            device.last_used = datetime.now()
            data_handler.save_data()
            return True
    
    return False

def validate_feature_access(request: Request, data_handler: DataHandler, feature_id: str) -> bool:
    """
    Validate if the current device has access to a specific feature.
    Returns True if:
    1. The feature doesn't require device auth
    2. The feature requires device auth and the current device is authorized
    """
    print("\n=== validate_feature_access START ===")
    print(f"Checking access for feature: {feature_id}")
    
    # Get feature access settings
    feature_access = next(
        (f for f in data_handler.data.feature_access if f.feature_id == feature_id),
        None
    )
    
    print(f"Feature access settings: {feature_access}")
    
    # If feature not found or disabled, deny access
    if not feature_access or not feature_access.is_enabled:
        print(f"Access denied: Feature not found or disabled")
        print("=== validate_feature_access END ===\n")
        return False
    
    # Get device UUID from request headers
    device_uuid = get_device_uuid(request)
    print(f"Device UUID from request: {device_uuid}")
    print(f"Authorized devices for feature: {feature_access.authorized_devices}")
    
    if not device_uuid:
        print(f"Access denied: No device UUID found")
        print("=== validate_feature_access END ===\n")
        return False
    
    # First check if the device exists and is active
    device = next((d for d in data_handler.data.device_registrations if d.uuid == device_uuid), None)
    print(f"Found device in registrations: {device}")
    
    if not device or not device.is_active:
        print(f"Access denied: Device not found or not active")
        print("=== validate_feature_access END ===\n")
        return False
    
    # If feature requires device auth, check if device is authorized
    if feature_access.requires_device_auth:
        if device_uuid not in feature_access.authorized_devices:
            print(f"Access denied: Device {device_uuid} not in authorized devices list")
            print("=== validate_feature_access END ===\n")
            return False
        print(f"Access granted: Device {device_uuid} is authorized for feature {feature_id}")
    else:
        print(f"Access granted: Feature doesn't require device auth")
    
    print("=== validate_feature_access END ===\n")
    return True

def get_authorized_features(request: Request, data_handler: DataHandler) -> List[str]:
    """
    Get a list of feature IDs that the current device has access to.
    """
    print("\n=== get_authorized_features START ===")
    authorized_features = []
    
    # Get device UUID from request headers
    device_uuid = get_device_uuid(request)
    print(f"Device UUID from request: {device_uuid}")
    
    # If no device UUID is present, return empty list
    if not device_uuid:
        print("No device UUID found, returning empty list")
        print("=== get_authorized_features END ===\n")
        return authorized_features
    
    # First check if the device exists and is active
    device = next((d for d in data_handler.data.device_registrations if d.uuid == device_uuid), None)
    print(f"Found device in registrations: {device}")
    
    if not device or not device.is_active:
        print(f"Device not found or not active, returning empty list")
        print("=== get_authorized_features END ===\n")
        return authorized_features
    
    # Get all features
    for feature in data_handler.data.feature_access:
        print(f"\nChecking feature: {feature.feature_id}")
        print(f"Feature settings: {feature}")
        
        if not feature.is_enabled:
            print(f"Feature {feature.feature_id} is not enabled, skipping")
            continue
            
        # Special case for device_management - always accessible if user is authenticated
        # if feature.feature_id == "device_management":
        #     print(f"Feature device_management is always accessible if authenticated")
        #     authorized_features.append(feature.feature_id)
        #     continue
            
        # For features that require device auth, check if device is authorized
        if feature.requires_device_auth:
            if device_uuid in feature.authorized_devices:
                print(f"Device {device_uuid} is authorized for feature {feature.feature_id}, adding to authorized features")
                authorized_features.append(feature.feature_id)
            else:
                print(f"Device {device_uuid} is not authorized for feature {feature.feature_id}, skipping")
            continue
            
        # For features that don't require device auth, device still needs to be registered and active
        print(f"Feature {feature.feature_id} doesn't require device auth, adding to authorized features")
        authorized_features.append(feature.feature_id)
    
    print(f"\nFinal authorized features for device {device_uuid}: {authorized_features}")
    print("=== get_authorized_features END ===\n")
    return authorized_features

# Dependency for protected routes
require_auth = get_auth_dependency()