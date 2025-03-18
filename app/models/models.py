from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from datetime import time, datetime

class WorkingDay(BaseModel):
    open_time: time
    close_time: time
    is_open: bool = True

    def model_dump(self, **kwargs):
        data = super().model_dump(**kwargs)
        if isinstance(data['open_time'], time):
            data['open_time'] = data['open_time'].strftime("%H:%M")
        if isinstance(data['close_time'], time):
            data['close_time'] = data['close_time'].strftime("%H:%M")
        return data

class WorkingHours(BaseModel):
    lunes: Optional[WorkingDay] = None
    martes: Optional[WorkingDay] = None
    miércoles: Optional[WorkingDay] = None
    jueves: Optional[WorkingDay] = None
    viernes: Optional[WorkingDay] = None
    sábado: Optional[WorkingDay] = None
    domingo: Optional[WorkingDay] = None

    def model_dump(self, **kwargs):
        data = {}
        for day in ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo']:
            day_schedule = getattr(self, day)
            if day_schedule:
                data[day] = day_schedule.model_dump()
            else:
                data[day] = None
        return data

class Category(BaseModel):
    id: int
    name: str
    icon: Optional[str] = None

class Zone(BaseModel):
    id: int
    name: str

class Shop(BaseModel):
    id: int
    name: str
    owner: str
    contact_number: str
    categories: List[int]
    working_hours: Optional[WorkingHours] = None
    city: str
    zone_id: int
    categorie_pages: List[str]
    img: str
    description: Optional[str] = None

    def model_dump(self, **kwargs):
        data = super().model_dump(**kwargs)
        if self.working_hours:
            data['working_hours'] = self.working_hours.model_dump()
        return data

class ClientBranding(BaseModel):
    logo: str
    client_logo: Optional[str] = None
    copyright: str
    client_copyright: Optional[str] = None
    active: bool = False
    client_name: Optional[str] = None
    subscription_end_date: Optional[str] = None
    contact_number: Optional[str] = None
    client_contact_number: Optional[str] = None

class DeviceRegistration(BaseModel):
    uuid: str
    device_name: str
    expires_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.now)
    last_used: Optional[datetime] = None
    is_active: bool = True
    created_by: str
    notes: Optional[str] = None
    ip_address: Optional[str] = None

class DataStructure(BaseModel):
    shops: List[Shop]
    categories: List[Category]
    zones: List[Zone]
    primary_banner: List[str]
    secondary_banner: List[str]
    recommended_image: str
    other_businesses: str
    branding: Optional[Dict] = None
    device_registrations: List[DeviceRegistration] = Field(default_factory=list) 