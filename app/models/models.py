from typing import Dict, List, Optional
from pydantic import BaseModel

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
    working_hours: Optional[Dict[str, str]] = None
    city: str
    zone_id: int
    categorie_pages: List[str]
    img: str

class DataStructure(BaseModel):
    shops: List[Shop]
    categories: List[Category]
    zones: List[Zone]
    primary_banner: List[str]
    secondary_banner: List[str]
    recommended_image: str
    other_businesses: str 