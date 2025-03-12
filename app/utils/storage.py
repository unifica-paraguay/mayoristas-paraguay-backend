from google.cloud import storage
from google.oauth2 import service_account
import os
import magic
import uuid
from fastapi import HTTPException, UploadFile
from typing import Optional
import base64
import json
import tempfile

# Configuration
BUCKET_NAME = os.getenv('GCP_BUCKET_NAME')
if not BUCKET_NAME:
    raise ValueError("GCP_BUCKET_NAME environment variable is not set")

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

class CloudStorage:
    def __init__(self):
        """Initialize Google Cloud Storage client with credentials from environment variables"""
        self.bucket_name = os.getenv('GCP_BUCKET_NAME', 'mayoristas-paraguay')
        self.allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
        self.max_size = 5 * 1024 * 1024  # 5MB

        # Get base64 encoded credentials from environment variable
        credentials_base64 = os.getenv('GOOGLE_CREDENTIALS_BASE64')
        if not credentials_base64:
            raise ValueError("GOOGLE_CREDENTIALS_BASE64 environment variable is not set")

        try:
            # Decode base64 credentials
            credentials_json = base64.b64decode(credentials_base64).decode('utf-8')
            credentials_info = json.loads(credentials_json)

            # Create temporary file to store credentials
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as temp_file:
                json.dump(credentials_info, temp_file)
                temp_credentials_path = temp_file.name

            # Initialize storage client with decoded credentials
            credentials = service_account.Credentials.from_service_account_file(temp_credentials_path)
            self.client = storage.Client(credentials=credentials)
            
            # Delete temporary credentials file
            os.unlink(temp_credentials_path)

        except Exception as e:
            raise ValueError(f"Error initializing Google Cloud Storage: {str(e)}")

        # Get bucket
        try:
            self.bucket = self.client.bucket(self.bucket_name)
        except Exception as e:
            raise ValueError(f"Error accessing bucket: {str(e)}")

    def _validate_file(self, file: UploadFile) -> None:
        """Validate file type and size"""
        # Check file size
        file.file.seek(0, 2)  # Seek to end of file
        size = file.file.tell()  # Get current position (file size)
        file.file.seek(0)  # Reset file position
        
        if size > self.max_size:
            raise HTTPException(
                status_code=400,
                detail=f"File size exceeds maximum allowed size of {self.max_size/1024/1024}MB"
            )
        
        # Check file type
        content = file.file.read(2048)  # Read first 2048 bytes for mime detection
        file.file.seek(0)  # Reset file position
        
        mime = magic.Magic(mime=True)
        file_type = mime.from_buffer(content)
        
        if not file_type.startswith('image/'):
            raise HTTPException(
                status_code=400,
                detail="File must be an image"
            )
        
        extension = file.filename.split('.')[-1].lower()
        if extension not in self.allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"File extension not allowed. Allowed extensions: {', '.join(self.allowed_extensions)}"
            )

    async def upload_file(self, file: UploadFile, folder: Optional[str] = None) -> str:
        """Upload a file to Google Cloud Storage and return its public URL"""
        self._validate_file(file)
        
        # Generate unique filename
        extension = file.filename.split('.')[-1].lower()
        filename = f"{uuid.uuid4()}.{extension}"
        
        # Add folder to path if specified
        if folder:
            filename = f"{folder}/{filename}"
        
        # Upload file
        blob = self.bucket.blob(filename)
        content = await file.read()
        blob.upload_from_string(content, content_type=file.content_type)
        
        # Return the public URL (assuming the bucket has public access configured)
        return f"https://storage.googleapis.com/{self.bucket_name}/{filename}"

    def delete_file(self, url: str) -> None:
        """Delete a file from Google Cloud Storage using its public URL"""
        try:
            # Extract the path after the bucket name from the URL
            # Example URL: https://storage.googleapis.com/bucket-name/folder/file.jpg
            parts = url.split('storage.googleapis.com/')
            if len(parts) != 2:
                raise ValueError("Invalid Google Cloud Storage URL")
            
            # Remove bucket name from path
            path = parts[1].split('/', 1)[1]
            
            # Delete the blob
            blob = self.bucket.blob(path)
            blob.delete()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error deleting file: {str(e)}") 