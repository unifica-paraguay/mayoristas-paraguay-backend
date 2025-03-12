from google.cloud import storage
from google.oauth2 import service_account
import os
import magic
import uuid
from fastapi import HTTPException, UploadFile
from typing import Optional

# Configuration
BUCKET_NAME = os.getenv('GCP_BUCKET_NAME')
if not BUCKET_NAME:
    raise ValueError("GCP_BUCKET_NAME environment variable is not set")

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

class CloudStorage:
    def __init__(self):
        try:
            # Get credentials path from environment variable
            credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
            if not credentials_path:
                raise ValueError("GOOGLE_APPLICATION_CREDENTIALS environment variable is not set")
            
            if not os.path.exists(credentials_path):
                raise FileNotFoundError(f"Credentials file not found at: {credentials_path}")
            
            # Create credentials object
            credentials = service_account.Credentials.from_service_account_file(credentials_path)
            if not credentials:
                raise ValueError("Failed to load credentials from file")
            
            # Initialize client with explicit credentials
            self.client = storage.Client(credentials=credentials, project=credentials.project_id)
            self.bucket = self.client.bucket(BUCKET_NAME)
            
            # Verify bucket exists
            if not self.bucket.exists():
                raise ValueError(f"Bucket {BUCKET_NAME} does not exist")
                
        except Exception as e:
            print(f"Error initializing Cloud Storage: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Storage service initialization failed: {str(e)}"
            )

    def _validate_file(self, file: UploadFile) -> None:
        """Validate file type and size"""
        # Check file size
        file.file.seek(0, 2)  # Seek to end of file
        size = file.file.tell()
        file.file.seek(0)  # Reset file pointer
        
        if size > MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail="File too large")

        # Check file type
        content = file.file.read(2048)  # Read first 2048 bytes for mime detection
        file.file.seek(0)  # Reset file pointer
        
        mime = magic.Magic(mime=True)
        file_type = mime.from_buffer(content)
        
        if not file_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="File type not allowed")
        
        extension = file.filename.split('.')[-1].lower()
        if extension not in ALLOWED_EXTENSIONS:
            raise HTTPException(status_code=400, detail="File extension not allowed")

    async def upload_file(self, file: UploadFile, folder: Optional[str] = None) -> str:
        """Upload a file to Google Cloud Storage and return its public URL"""
        try:
            self._validate_file(file)
            
            # Generate unique filename
            extension = file.filename.split('.')[-1].lower()
            unique_filename = f"{uuid.uuid4()}.{extension}"
            
            # Add folder prefix if provided
            if folder:
                unique_filename = f"{folder}/{unique_filename}"
            
            # Upload file
            blob = self.bucket.blob(unique_filename)
            content = await file.read()
            blob.upload_from_string(
                content,
                content_type=file.content_type
            )
            
            # Return the public URL
            return f"https://storage.googleapis.com/{BUCKET_NAME}/{unique_filename}"
            
        except HTTPException:
            raise
        except Exception as e:
            print(f"Error uploading file: {e}")
            raise HTTPException(status_code=500, detail=f"Could not upload file: {str(e)}")

    def delete_file(self, url: str) -> None:
        """Delete a file from Google Cloud Storage using its URL"""
        try:
            # Extract blob name from URL
            blob_name = url.split(f'{BUCKET_NAME}/')[-1]
            blob = self.bucket.blob(blob_name)
            
            if blob.exists():
                blob.delete()
            
        except Exception as e:
            print(f"Error deleting file: {e}")
            raise HTTPException(status_code=500, detail="Could not delete file") 