from typing import Dict, List, Optional
from pydantic import BaseModel
from datetime import time

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

    def model_dump(self, **kwargs):
        data = super().model_dump(**kwargs)
        if self.working_hours:
            data['working_hours'] = self.working_hours.model_dump()
        return data

class DataStructure(BaseModel):
    shops: List[Shop]
    categories: List[Category]
    zones: List[Zone]
    primary_banner: List[str]
    secondary_banner: List[str]
    recommended_image: str
    other_businesses: str 