from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

class DeviceRegistration(BaseModel):
    uuid: str
    device_name: str
    expires_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.now)
    last_used: Optional[datetime] = None
    is_active: bool = True
    created_by: Optional[str] = None
    notes: Optional[str] = None
    ip_address: Optional[str] = None

class BrandingData(BaseModel):
    logo_url: Optional[str] = None
    primary_color: Optional[str] = None
    secondary_color: Optional[str] = None
    accent_color: Optional[str] = None
    font_family: Optional[str] = None
    custom_css: Optional[str] = None

class DataStructure(BaseModel):
    branding: BrandingData = Field(default_factory=BrandingData)
    device_registrations: List[DeviceRegistration] = Field(default_factory=list)
    last_modified: datetime = Field(default_factory=datetime.now) 