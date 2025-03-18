from fastapi import FastAPI, HTTPException, Request, UploadFile, File, Depends, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.security import HTTPBearer
from starlette.middleware.sessions import SessionMiddleware
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from .models.models import DataStructure, Shop, Category, Zone, DeviceRegistration
from pydantic import BaseModel
import json
from typing import List, Optional
import os
from dotenv import load_dotenv
from .utils.working_hours import parse_legacy_working_hours, is_shop_open, format_working_hours, parse_time
from datetime import time
import secrets
from .utils.security import authenticate_user, create_access_token, get_current_user, ACCESS_TOKEN_EXPIRE_MINUTES, validate_device_uuid
from datetime import timedelta
import jwt
from jose import JWTError
from uuid import uuid4
from datetime import datetime

# Load environment variables from .env file
load_dotenv()

# Import storage after loading environment variables
from .utils.storage import CloudStorage

# Get security variables
ALGORITHM = "HS256"
SECRET_KEY = os.getenv("SECRET_KEY")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")

# Get environment
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
IS_PRODUCTION = ENVIRONMENT == "production"

app = FastAPI(title="Mayoristas Paraguay Backend")
storage = CloudStorage()

# Add session middleware for CSRF protection
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SECRET_KEY"),
    session_cookie="session",
    max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # in seconds
)

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Initialize templates
templates = Jinja2Templates(directory="app/templates")

DATA_FILE = "data.json"

# Modelos para las solicitudes
class ImageUrl(BaseModel):
    url: str = ""

# Device Management Models
class DeviceCreate(BaseModel):
    device_name: str
    uuid: Optional[str] = None  # Make UUID optional in creation
    expires_at: Optional[str] = None
    notes: Optional[str] = None

class DeviceUpdate(DeviceCreate):
    uuid: str

class DeviceToggle(BaseModel):
    enable: bool

def load_data() -> DataStructure:
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
        return DataStructure(**data)

def save_data(data: DataStructure):
    def time_handler(obj):
        if hasattr(obj, 'model_dump'):
            return obj.model_dump()
        if isinstance(obj, (datetime, time)):
            return obj.isoformat()
        raise TypeError(f'Object of type {type(obj).__name__} is not JSON serializable')

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data.model_dump(), f, indent=2, ensure_ascii=False, default=time_handler)

# Load initial data
data_structure = load_data()

# Authentication routes
@app.get("/", response_class=HTMLResponse)
async def login_page(request: Request):
    print("DEBUG: Checking authentication at root path")  # Debug print
    # Check if user is already authenticated
    try:
        auth_cookie = request.cookies.get("Authorization")
        if auth_cookie and auth_cookie.startswith("Bearer "):
            token = auth_cookie.replace("Bearer ", "")
            print(f"DEBUG: Found token: {token[:20]}...")  # Debug print
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            username = payload.get("sub")
            print(f"DEBUG: Decoded username: {username}")  # Debug print
            if username == ADMIN_USERNAME:
                print("DEBUG: User is authenticated, redirecting to /admin")  # Debug print
                return RedirectResponse(url="/admin", status_code=302)
    except JWTError as e:
        print(f"DEBUG: JWT Error: {str(e)}")  # Debug print
    except Exception as e:
        print(f"DEBUG: Unexpected error: {str(e)}")  # Debug print

    # If not authenticated, show login page
    print("DEBUG: User not authenticated, showing login page")  # Debug print
    csrf_token = secrets.token_hex(32)
    request.session["csrf_token"] = csrf_token
    return templates.TemplateResponse("login.html", {
        "request": request,
        "csrf_token": csrf_token
    })

@app.post("/login")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    csrf_token: str = Form(...)
):
    # Verify CSRF token
    stored_csrf = request.session.get("csrf_token")
    if not stored_csrf or stored_csrf != csrf_token:
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "Invalid CSRF token"
        }, status_code=400)

    if authenticate_user(username, password):
        access_token = create_access_token(
            data={"sub": username},
            expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        )
        # Create a simple redirect response
        response = RedirectResponse(url="/admin", status_code=302)
        
        # Get the host from the request headers
        host = request.headers.get("host", "")
        is_https = request.url.scheme == "https" or IS_PRODUCTION
        
        # Set cookie settings based on environment and protocol
        cookie_settings = {
            "key": "Authorization",
            "value": f"Bearer {access_token}",
            "httponly": True,
            "secure": is_https,
            "samesite": "strict" if is_https else "lax",
            "path": "/",
            "max_age": ACCESS_TOKEN_EXPIRE_MINUTES * 60
        }
        
        # Set the auth cookie with appropriate settings
        response.set_cookie(**cookie_settings)
        
        print("DEBUG: Setting cookie with token:", access_token[:20], "...")  # Debug print
        return response
    
    return templates.TemplateResponse("login.html", {
        "request": request,
        "error": "Invalid username or password",
        "csrf_token": csrf_token
    })

@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/", status_code=303)
    
    # Get request from context
    request = Request(scope={"type": "http"})  # Minimal request object
    is_https = IS_PRODUCTION  # In production, always assume HTTPS
    
    # Delete cookie with matching settings
    response.delete_cookie(
        key="Authorization",
        path="/",
        httponly=True,
        secure=is_https,
        samesite="strict" if is_https else "lax"
    )
    return response

# Admin interface routes - now protected
@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(
    request: Request,
    current_user: str = Depends(get_current_user)
):
    print("DEBUG: Reached admin_dashboard with user:", current_user)  # Debug print
    # Calculate statistics
    total_shops = len(data_structure.shops)
    total_categories = len(data_structure.categories)
    total_zones = len(data_structure.zones)
    total_banners = sum(1 for banner in [
        *data_structure.primary_banner,
        *data_structure.secondary_banner,
        data_structure.recommended_image,
        data_structure.other_businesses
    ] if banner)
    
    # Get branding information
    branding = await get_active_branding()

    return templates.TemplateResponse("admin_dashboard.html", {
        "request": request,
        "total_shops": total_shops,
        "total_categories": total_categories,
        "total_zones": total_zones,
        "total_banners": total_banners,
        "branding": branding,
        "title": "Admin Dashboard"
    })

@app.get("/admin/shops", response_class=HTMLResponse)
async def admin_shops(
    request: Request,
    current_user: str = Depends(get_current_user)
):
    return templates.TemplateResponse("shops.html", {
        "request": request,
        "shops": data_structure.shops,
        "categories": data_structure.categories,
        "zones": data_structure.zones
    })

@app.get("/admin/categories", response_class=HTMLResponse)
async def admin_categories(
    request: Request,
    current_user: str = Depends(get_current_user)
):
    return templates.TemplateResponse("categories.html", {
        "request": request,
        "categories": data_structure.categories
    })

@app.get("/admin/zones", response_class=HTMLResponse)
async def admin_zones(
    request: Request,
    current_user: str = Depends(get_current_user)
):
    return templates.TemplateResponse("zones.html", {
        "request": request,
        "zones": data_structure.zones
    })

@app.get("/admin/banners", response_class=HTMLResponse)
async def admin_banners(
    request: Request,
    current_user: str = Depends(get_current_user)
):
    return templates.TemplateResponse("banners.html", {
        "request": request,
        "primary_banner": data_structure.primary_banner,
        "secondary_banner": data_structure.secondary_banner,
        "recommended_image": data_structure.recommended_image,
        "other_businesses": data_structure.other_businesses
    })

# CRUD Operations for Shops
@app.get("/api/shops", response_model=List[Shop])
async def get_shops(current_user: str = Depends(get_current_user)):
    return data_structure.shops

@app.get("/api/shops/{shop_id}", response_model=Shop)
async def get_shop(shop_id: int, current_user: str = Depends(get_current_user)):
    for shop in data_structure.shops:
        if shop.id == shop_id:
            return shop
    raise HTTPException(status_code=404, detail="Shop not found")

@app.post("/api/shops", response_model=Shop)
async def create_shop(shop: Shop, current_user: str = Depends(get_current_user)):
    # Check if ID already exists
    if any(s.id == shop.id for s in data_structure.shops):
        raise HTTPException(status_code=400, detail="Shop ID already exists")
    
    # Validate categories exist
    for cat_id in shop.categories:
        if not any(c.id == cat_id for c in data_structure.categories):
            raise HTTPException(status_code=400, detail=f"Category ID {cat_id} does not exist")
    
    # Validate zone exists
    if not any(z.id == shop.zone_id for z in data_structure.zones):
        raise HTTPException(status_code=400, detail="Zone ID does not exist")
    
    # Convert working hours time strings to time objects
    if shop.working_hours:
        for day in ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo']:
            day_schedule = getattr(shop.working_hours, day)
            if day_schedule and isinstance(day_schedule.open_time, str):
                try:
                    day_schedule.open_time = parse_time(day_schedule.open_time)
                    day_schedule.close_time = parse_time(day_schedule.close_time)
                except ValueError as e:
                    raise HTTPException(status_code=400, detail=f"Invalid time format for {day}: {str(e)}")
    
    data_structure.shops.append(shop)
    save_data(data_structure)
    return shop

@app.put("/api/shops/{shop_id}", response_model=Shop)
async def update_shop(shop_id: int, updated_shop: Shop):
    for i, shop in enumerate(data_structure.shops):
        if shop.id == shop_id:
            # Validate categories exist
            for cat_id in updated_shop.categories:
                if not any(c.id == cat_id for c in data_structure.categories):
                    raise HTTPException(status_code=400, detail=f"Category ID {cat_id} does not exist")
            
            # Validate zone exists
            if not any(z.id == updated_shop.zone_id for z in data_structure.zones):
                raise HTTPException(status_code=400, detail="Zone ID does not exist")
            
            # Convert working hours time strings to time objects
            if updated_shop.working_hours:
                for day in ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo']:
                    day_schedule = getattr(updated_shop.working_hours, day)
                    if day_schedule and isinstance(day_schedule.open_time, str):
                        try:
                            day_schedule.open_time = parse_time(day_schedule.open_time)
                            day_schedule.close_time = parse_time(day_schedule.close_time)
                        except ValueError as e:
                            raise HTTPException(status_code=400, detail=f"Invalid time format for {day}: {str(e)}")
            
            # If image has changed, delete the old one
            if shop.img and shop.img != updated_shop.img:
                try:
                    await storage.delete_file(shop.img)
                except Exception as e:
                    print(f"Error deleting old image: {e}")
            
            data_structure.shops[i] = updated_shop
            save_data(data_structure)
            return updated_shop
    raise HTTPException(status_code=404, detail="Shop not found")

@app.patch("/api/shops/{shop_id}", response_model=Shop)
async def patch_shop(shop_id: int, updated_fields: dict):
    for i, shop in enumerate(data_structure.shops):
        if shop.id == shop_id:
            # Create a copy of the current shop data
            shop_data = shop.model_dump()
            
            # Update only the provided fields
            for field, value in updated_fields.items():
                if field in shop_data:
                    # If updating image, delete the old one
                    if field == 'img' and shop.img and shop.img != value:
                        try:
                            await storage.delete_file(shop.img)
                        except Exception as e:
                            print(f"Error deleting old image: {e}")
                    shop_data[field] = value
            
            # Create updated shop instance
            updated_shop = Shop(**shop_data)
            data_structure.shops[i] = updated_shop
            save_data(data_structure)
            return updated_shop
            
    raise HTTPException(status_code=404, detail="Shop not found")

@app.delete("/api/shops/{shop_id}")
async def delete_shop(shop_id: int):
    for i, shop in enumerate(data_structure.shops):
        if shop.id == shop_id:
            data_structure.shops.pop(i)
            save_data(data_structure)
            return {"message": "Shop deleted successfully"}
    raise HTTPException(status_code=404, detail="Shop not found")

# CRUD Operations for Categories
@app.get("/api/categories", response_model=List[Category])
async def get_categories(current_user: str = Depends(get_current_user)):
    return data_structure.categories

@app.get("/api/categories/{category_id}", response_model=Category)
async def get_category(category_id: int, current_user: str = Depends(get_current_user)):
    for category in data_structure.categories:
        if category.id == category_id:
            return category
    raise HTTPException(status_code=404, detail="Category not found")

@app.post("/api/categories", response_model=Category)
async def create_category(category: Category, current_user: str = Depends(get_current_user)):
    if any(c.id == category.id for c in data_structure.categories):
        raise HTTPException(status_code=400, detail="Category ID already exists")
    data_structure.categories.append(category)
    save_data(data_structure)
    return category

@app.put("/api/categories/{category_id}", response_model=Category)
async def update_category(category_id: int, updated_category: Category):
    for i, category in enumerate(data_structure.categories):
        if category.id == category_id:
            data_structure.categories[i] = updated_category
            save_data(data_structure)
            return updated_category
    raise HTTPException(status_code=404, detail="Category not found")

@app.delete("/api/categories/{category_id}")
async def delete_category(category_id: int):
    # Check if category is being used by any shop
    for shop in data_structure.shops:
        if category_id in shop.categories:
            raise HTTPException(
                status_code=400,
                detail="Cannot delete category as it is being used by one or more shops"
            )
    
    for i, category in enumerate(data_structure.categories):
        if category.id == category_id:
            data_structure.categories.pop(i)
            save_data(data_structure)
            return {"message": "Category deleted successfully"}
    raise HTTPException(status_code=404, detail="Category not found")

# CRUD Operations for Zones
@app.get("/api/zones", response_model=List[Zone])
async def get_zones(current_user: str = Depends(get_current_user)):
    return data_structure.zones

@app.get("/api/zones/{zone_id}", response_model=Zone)
async def get_zone(zone_id: int, current_user: str = Depends(get_current_user)):
    for zone in data_structure.zones:
        if zone.id == zone_id:
            return zone
    raise HTTPException(status_code=404, detail="Zone not found")

@app.post("/api/zones", response_model=Zone)
async def create_zone(zone: Zone, current_user: str = Depends(get_current_user)):
    if any(z.id == zone.id for z in data_structure.zones):
        raise HTTPException(status_code=400, detail="Zone ID already exists")
    data_structure.zones.append(zone)
    save_data(data_structure)
    return zone

@app.put("/api/zones/{zone_id}", response_model=Zone)
async def update_zone(zone_id: int, updated_zone: Zone):
    for i, zone in enumerate(data_structure.zones):
        if zone.id == zone_id:
            data_structure.zones[i] = updated_zone
            save_data(data_structure)
            return updated_zone
    raise HTTPException(status_code=404, detail="Zone not found")

@app.delete("/api/zones/{zone_id}")
async def delete_zone(zone_id: int):
    # Check if zone is being used by any shop
    for shop in data_structure.shops:
        if shop.zone_id == zone_id:
            raise HTTPException(
                status_code=400,
                detail="Cannot delete zone as it is being used by one or more shops"
            )
    
    for i, zone in enumerate(data_structure.zones):
        if zone.id == zone_id:
            data_structure.zones.pop(i)
            save_data(data_structure)
            return {"message": "Zone deleted successfully"}
    raise HTTPException(status_code=404, detail="Zone not found")

# Banner Management
@app.put("/api/banners/primary")
async def update_primary_banner(urls: List[str]):
    # Replace existing URLs with new ones
    data_structure.primary_banner = urls
    save_data(data_structure)
    return {"message": "Primary banner updated successfully"}

@app.put("/api/banners/secondary")
async def update_secondary_banner(urls: List[str]):
    # Replace existing URLs with new ones
    data_structure.secondary_banner = urls
    save_data(data_structure)
    return {"message": "Secondary banner updated successfully"}

@app.put("/api/images/recommended")
async def update_recommended_image(image: ImageUrl):
    """Update the recommended image URL"""
    print("Datos recibidos:", image)
    print("URL recibida:", image.url)
    # Store the new URL
    data_structure.recommended_image = image.url
    save_data(data_structure)
    return {"message": "Recommended image updated successfully"}

@app.put("/api/images/other-businesses")
async def update_other_businesses_image(image: ImageUrl):
    # Store the new URL
    data_structure.other_businesses = image.url
    save_data(data_structure)
    return {"message": "Other businesses image updated successfully"}

@app.get("/analytics", response_class=HTMLResponse)
async def analytics_dashboard(request: Request, current_user: str = Depends(get_current_user)):
    """Analytics dashboard moved to /analytics and protected with authentication"""
    return """
    <html>
        <head>
            <title>Mayoristas Paraguay Analytics</title>
            <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
        </head>
        <body class="bg-gray-100">
            <div class="container mx-auto px-4 py-8">
                <h1 class="text-4xl font-bold mb-8">Mayoristas Paraguay Analytics</h1>
                <div class="grid grid-cols-1 md:grid-cols-2 gap-8">
                    <iframe src="/shops-by-zone" class="w-full h-96 bg-white rounded-lg shadow-lg"></iframe>
                    <iframe src="/categories-distribution" class="w-full h-96 bg-white rounded-lg shadow-lg"></iframe>
                    <iframe src="/shops-by-category" class="w-full h-96 bg-white rounded-lg shadow-lg"></iframe>
                    <iframe src="/working-hours-distribution" class="w-full h-96 bg-white rounded-lg shadow-lg"></iframe>
                </div>
            </div>
        </body>
    </html>
    """

@app.get("/shops-by-zone")
async def get_shops_by_zone(request: Request):
    # Count shops per zone
    zone_counts = {}
    for shop in data_structure.shops:
        zone_counts[shop.zone_id] = zone_counts.get(shop.zone_id, 0) + 1
    
    # Create zone name mapping
    zone_names = {zone.id: zone.name for zone in data_structure.zones}
    
    # Create DataFrame
    df = pd.DataFrame([
        {"zone": zone_names[zone_id], "count": count}
        for zone_id, count in zone_counts.items()
    ])
    
    # Create figure with dark mode support
    fig = px.bar(df, x="zone", y="count", title="Shops by Zone")
    
    # Update layout for dark mode
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#9CA3AF")  # text-gray-400 in Tailwind
    )
    
    # Update axes for dark mode
    fig.update_xaxes(gridcolor="#374151")  # gray-700 in Tailwind
    fig.update_yaxes(gridcolor="#374151")  # gray-700 in Tailwind
    
    return HTMLResponse(fig.to_html(full_html=False, include_plotlyjs=True))

@app.get("/categories-distribution")
async def get_categories_distribution(request: Request):
    # Count category occurrences
    category_counts = {}
    for shop in data_structure.shops:
        for cat_id in shop.categories:
            category_counts[cat_id] = category_counts.get(cat_id, 0) + 1
    
    # Create category name mapping
    category_names = {cat.id: cat.name for cat in data_structure.categories}
    
    # Get top 10 categories
    top_categories = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    
    df = pd.DataFrame([
        {"category": category_names[cat_id], "count": count}
        for cat_id, count in top_categories
    ])
    
    # Create figure with dark mode support
    fig = px.pie(df, values="count", names="category", title="Top 10 Categories Distribution")
    
    # Update layout for dark mode
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#9CA3AF")  # text-gray-400 in Tailwind
    )
    
    return HTMLResponse(fig.to_html(full_html=False, include_plotlyjs=True))

@app.get("/shops-by-category")
async def get_shops_by_category(request: Request):
    # Count shops per category
    category_shop_counts = {}
    for shop in data_structure.shops:
        for cat_id in shop.categories:
            category_shop_counts[cat_id] = category_shop_counts.get(cat_id, 0) + 1
    
    # Create category name mapping
    category_names = {cat.id: cat.name for cat in data_structure.categories}
    
    # Get top 15 categories
    top_categories = sorted(category_shop_counts.items(), key=lambda x: x[1], reverse=True)[:15]
    
    df = pd.DataFrame([
        {"category": category_names[cat_id], "count": count}
        for cat_id, count in top_categories
    ])
    
    # Create figure with dark mode support
    fig = px.bar(df, x="category", y="count", title="Top 15 Categories by Number of Shops")
    
    # Update layout for dark mode
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#9CA3AF"),  # text-gray-400 in Tailwind
        xaxis_tickangle=-45
    )
    
    # Update axes for dark mode
    fig.update_xaxes(gridcolor="#374151")  # gray-700 in Tailwind
    fig.update_yaxes(gridcolor="#374151")  # gray-700 in Tailwind
    
    return HTMLResponse(fig.to_html(full_html=False, include_plotlyjs=True))

@app.get("/working-hours-distribution")
async def get_working_hours_distribution(request: Request):
    # Count shops with and without working hours
    with_hours = len([shop for shop in data_structure.shops if shop.working_hours])
    without_hours = len(data_structure.shops) - with_hours
    
    # Create figure with dark mode support
    fig = go.Figure(data=[go.Pie(
        labels=['With Working Hours', 'Without Working Hours'],
        values=[with_hours, without_hours],
        title="Working Hours Distribution"
    )])
    
    # Update layout for dark mode
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#9CA3AF")  # text-gray-400 in Tailwind
    )
    
    return HTMLResponse(fig.to_html(full_html=False, include_plotlyjs=True))

@app.get("/api/data")
async def get_data_json():
    return FileResponse(DATA_FILE, media_type="application/json")

# Image Upload Endpoints
@app.post("/api/upload/shop-image")
async def upload_shop_image(file: UploadFile = File(...)):
    """Upload a shop image and return its URL"""
    url = await storage.upload_file(file, folder="shops")
    return {"url": url}

@app.post("/api/upload/primary-banner")
async def upload_primary_banner(file: UploadFile = File(...)):
    """Upload a primary banner image and return its URL"""
    url = await storage.upload_file(file, folder="primary-banners")
    return {"url": url}

@app.post("/api/upload/secondary-banner")
async def upload_secondary_banner(file: UploadFile = File(...)):
    """Upload a secondary banner image and return its URL"""
    url = await storage.upload_file(file, folder="secondary-banners")
    return {"url": url}

@app.post("/api/upload/recommended")
async def upload_recommended_image(file: UploadFile = File(...)):
    """Upload a recommended image and return its URL"""
    url = await storage.upload_file(file, folder="recommended")
    return {"url": url}

@app.post("/api/upload/other-business")
async def upload_other_business_image(file: UploadFile = File(...)):
    """Upload an other business image and return its URL"""
    url = await storage.upload_file(file, folder="other-business")
    return {"url": url}

# Storage Management
@app.delete("/api/storage/delete")
async def delete_storage_file(url: str):
    """Delete a file from storage"""
    try:
        await storage.delete_file(url)
        return {"message": "File deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Add new endpoint for getting open shops
@app.get("/api/shops/open")
async def get_open_shops():
    """Get all currently open shops"""
    return [shop for shop in data_structure.shops if is_shop_open(shop)]

# Branding Management Helper
async def get_active_branding():
    """Helper function to get active branding configuration"""
    data_structure = load_data()
    
    # Get default branding values from environment variables
    default_logo = os.getenv("DEFAULT_BRANDING_LOGO")
    default_copyright = os.getenv("DEFAULT_BRANDING_COPYRIGHT")
    default_contact = os.getenv("DEFAULT_BRANDING_CONTACT")
    
    # Use current year if default_copyright is not provided
    if not default_copyright:
        from datetime import datetime
        current_year = datetime.now().year
        default_copyright = f"© {current_year} Unifica Paraguay. Todos los derechos reservados."
    
    branding = data_structure.branding or {
        "logo": default_logo,
        "client_logo": "",  # Store client logo separately
        "copyright": default_copyright,
        "client_copyright": "",  # Store client copyright separately
        "contact_number": default_contact,
        "client_contact_number": "",  # Store client contact separately
        "active": False,
        "client_name": "",
        "subscription_end_date": ""
    }
    
    # Ensure client_logo field exists
    if "client_logo" not in branding:
        branding["client_logo"] = ""
        
    # Ensure client_copyright field exists
    if "client_copyright" not in branding:
        branding["client_copyright"] = ""
        
    # Ensure client_contact_number field exists
    if "client_contact_number" not in branding:
        branding["client_contact_number"] = ""
    
    # Always ensure the logo, copyright and contact are correct based on active status
    if not branding.get("active", False):
        branding["logo"] = default_logo
        branding["copyright"] = default_copyright
        branding["contact_number"] = default_contact
    else:
        # Use client_logo if it exists
        if branding.get("client_logo"):
            branding["logo"] = branding["client_logo"]
        
        # Use client_copyright if it exists
        if branding.get("client_copyright"):
            branding["copyright"] = branding["client_copyright"]
            
        # Use client_contact_number if it exists
        if branding.get("client_contact_number"):
            branding["contact_number"] = branding["client_contact_number"]
        
    return branding

# Branding Management Page
@app.get("/admin/branding", response_class=HTMLResponse)
async def branding_page(
    request: Request,
    current_user: str = Depends(get_current_user)
):
    """Branding management page"""
    print("DEBUG: Accessing branding page")
    print(f"DEBUG: Headers: {dict(request.headers)}")
    
    # Validate device UUID
    if not await validate_device_uuid(request):
        print("DEBUG: UUID validation failed")
        return templates.TemplateResponse(
            "unauthorized.html",
            {
                "request": request,
                "title": "Unauthorized Access"
            },
            status_code=403
        )
    
    print("DEBUG: UUID validation successful")
    branding = await get_active_branding()
    return templates.TemplateResponse(
        "branding.html",
        {
            "request": request,
            "branding": branding,
            "active_page": "branding"
        }
    )

# Branding API Endpoints
@app.post("/api/branding")
async def update_branding(
    request: Request,
    client_name: str = Form(None),
    subscription_end_date: str = Form(None),
    logo: str = Form(None),
    copyright: str = Form(None),
    client_copyright: str = Form(None),
    client_contact_number: str = Form(None),
    current_user: str = Depends(get_current_user)
):
    """Update branding information"""
    # Validate device UUID
    if not await validate_device_uuid(request):
        return JSONResponse(
            status_code=403,
            content={
                "status": "error",
                "message": "Unauthorized device. Please provide a valid device UUID.",
                "code": "UNAUTHORIZED_DEVICE"
            }
        )
    
    data_structure = load_data()
    
    # Get default branding values
    default_logo = os.getenv("DEFAULT_BRANDING_LOGO")
    default_copyright = os.getenv("DEFAULT_BRANDING_COPYRIGHT")
    default_contact = os.getenv("DEFAULT_BRANDING_CONTACT")
    
    # Use current year if default_copyright is not provided
    if not default_copyright:
        from datetime import datetime
        current_year = datetime.now().year
        default_copyright = f"© {current_year} Unifica Paraguay. Todos los derechos reservados."
    
    # Get existing branding or create new
    branding = data_structure.branding or {
        "logo": default_logo,
        "client_logo": "",
        "copyright": default_copyright,
        "client_copyright": "",
        "contact_number": default_contact,
        "client_contact_number": "",
        "active": False,
        "client_name": "",
        "subscription_end_date": ""
    }
    
    # Ensure client_logo field exists
    if "client_logo" not in branding:
        branding["client_logo"] = ""
    
    # Ensure client_copyright field exists
    if "client_copyright" not in branding:
        branding["client_copyright"] = ""
        
    # Ensure client_contact_number field exists
    if "client_contact_number" not in branding:
        branding["client_contact_number"] = ""
    
    # Update fields
    if client_name is not None:
        branding["client_name"] = client_name
    
    if subscription_end_date is not None:
        branding["subscription_end_date"] = subscription_end_date
    
    if logo is not None:
        branding["client_logo"] = logo
        # Update the active logo if client branding is active
        if branding.get("active", False):
            branding["logo"] = logo
    
    if client_copyright is not None:
        # Store the client copyright
        branding["client_copyright"] = client_copyright
        
        # Update active copyright if client branding is active
        if branding.get("active", False):
            branding["copyright"] = client_copyright
        else:
            branding["copyright"] = default_copyright
            
    if client_contact_number is not None:
        # Store the client contact number
        branding["client_contact_number"] = client_contact_number
        
        # Update active contact if client branding is active
        if branding.get("active", False):
            branding["contact_number"] = client_contact_number
        else:
            branding["contact_number"] = default_contact
    
    # Save updated branding
    data_structure.branding = branding
    save_data(data_structure)
    
    return RedirectResponse(url="/admin/branding", status_code=303)

@app.post("/api/branding/enable")
async def enable_client_branding(
    request: Request,
    current_user: str = Depends(get_current_user)
):
    """Enable client branding"""
    # Validate device UUID
    if not await validate_device_uuid(request):
        return JSONResponse(
            status_code=403,
            content={
                "status": "error",
                "message": "Unauthorized device. Please provide a valid device UUID.",
                "code": "UNAUTHORIZED_DEVICE"
            }
        )
    
    data_structure = load_data()
    
    if not data_structure.branding:
        raise HTTPException(status_code=400, detail="Branding not configured")
    
    # Ensure client_logo field exists
    if "client_logo" not in data_structure.branding:
        data_structure.branding["client_logo"] = ""
        
    # Ensure client_copyright field exists
    if "client_copyright" not in data_structure.branding:
        # Generate a default client copyright if not set
        from datetime import datetime
        current_year = datetime.now().year
        client_name = data_structure.branding.get("client_name", "").strip()
        
        if client_name:
            data_structure.branding["client_copyright"] = f"© {current_year} {client_name}. Todos los derechos reservados."
        else:
            data_structure.branding["client_copyright"] = f"© {current_year} Unifica Paraguay. Todos los derechos reservados."
            
    # Ensure client_contact_number field exists
    if "client_contact_number" not in data_structure.branding:
        data_structure.branding["client_contact_number"] = ""
    
    data_structure.branding["active"] = True
    
    # Set the logo to client_logo if available
    if data_structure.branding.get("client_logo"):
        data_structure.branding["logo"] = data_structure.branding["client_logo"]
    
    # Set copyright to client_copyright
    if data_structure.branding.get("client_copyright"):
        data_structure.branding["copyright"] = data_structure.branding["client_copyright"]
        
    # Set contact to client_contact_number
    if data_structure.branding.get("client_contact_number"):
        data_structure.branding["contact_number"] = data_structure.branding["client_contact_number"]
    
    save_data(data_structure)
    
    return RedirectResponse(url="/admin/branding", status_code=303)

@app.post("/api/branding/disable")
async def disable_client_branding(
    request: Request,
    current_user: str = Depends(get_current_user)
):
    """Disable client branding and use default"""
    # Validate device UUID
    if not await validate_device_uuid(request):
        raise HTTPException(
            status_code=403,
            detail="Unauthorized device. Please provide a valid device UUID."
        )
    
    data_structure = load_data()
    
    # Get default branding values from environment variables
    default_logo = os.getenv("DEFAULT_BRANDING_LOGO")
    default_copyright = os.getenv("DEFAULT_BRANDING_COPYRIGHT")
    default_contact = os.getenv("DEFAULT_BRANDING_CONTACT")
    
    # Use current year if default_copyright is not provided
    if not default_copyright:
        from datetime import datetime
        current_year = datetime.now().year
        default_copyright = f"© {current_year} Unifica Paraguay. Todos los derechos reservados."
    
    if not data_structure.branding:
        data_structure.branding = {
            "logo": default_logo,
            "client_logo": "",
            "copyright": default_copyright,
            "client_copyright": "",
            "contact_number": default_contact,
            "client_contact_number": "",
            "active": False,
            "client_name": "",
            "subscription_end_date": ""
        }
    else:
        # Ensure client_logo field exists
        if "client_logo" not in data_structure.branding:
            data_structure.branding["client_logo"] = ""
            
        # Ensure client_copyright field exists
        if "client_copyright" not in data_structure.branding:
            data_structure.branding["client_copyright"] = ""
            
        # Ensure client_contact_number field exists
        if "client_contact_number" not in data_structure.branding:
            data_structure.branding["client_contact_number"] = ""
        
        # Set active to false and switch to default logo, copyright and contact
        data_structure.branding["active"] = False
        data_structure.branding["logo"] = default_logo
        data_structure.branding["copyright"] = default_copyright
        data_structure.branding["contact_number"] = default_contact
        
        # But keep the client_logo, client_name, client_copyright and client_contact_number for later use
        # (don't modify client_logo, client_name, client_copyright or client_contact_number fields)
    
    save_data(data_structure)
    
    return RedirectResponse(url="/admin/branding", status_code=303)

# Logo Upload Endpoint
@app.post("/api/upload/branding-logo")
async def upload_branding_logo(
    request: Request,
    file: UploadFile = File(...),
    current_user: str = Depends(get_current_user)
):
    """Upload a branding logo image and return its URL"""
    # Validate device UUID
    if not await validate_device_uuid(request):
        return JSONResponse(
            status_code=403,
            content={
                "status": "error",
                "message": "Unauthorized device. Please provide a valid device UUID.",
                "code": "UNAUTHORIZED_DEVICE"
            }
        )
    
    url = await storage.upload_file(file, folder="branding")
    
    # If there was a previous logo, delete it
    data_structure = load_data()
    
    # Ensure branding object exists
    if not data_structure.branding:
        data_structure.branding = {}
    
    # Ensure client_logo field exists
    if "client_logo" not in data_structure.branding:
        data_structure.branding["client_logo"] = ""
    
    # Check for existing logo to delete
    if data_structure.branding.get("client_logo"):
        old_logo = data_structure.branding["client_logo"]
        if old_logo and "storage.googleapis.com" in old_logo and "branding" in old_logo:
            try:
                await storage.delete_file(old_logo)
            except Exception:
                # Ignore errors when deleting old logo
                pass
    
    # Store in client_logo
    data_structure.branding["client_logo"] = url
    
    # Also set as active logo if client branding is active
    if data_structure.branding.get("active", False):
        data_structure.branding["logo"] = url
    
    # Update data structure
    save_data(data_structure)
    
    return {"url": url}

# Add this route to get branding info
@app.get("/api/branding")
async def get_branding_info():
    """Get branding information for the site"""
    branding = await get_active_branding()
    
    # The get_active_branding helper now ensures the logo is set correctly
    # based on active status, so we just need to return it
    return {
        "logo": branding.get("logo", ""),
        "copyright": branding.get("copyright", ""),
        "contact_number": branding.get("contact_number", "")
    }

# Favicon endpoint that redirects to current branding logo
@app.get("/favicon.ico")
async def favicon():
    """Redirect to the current branding logo for favicon"""
    branding = await get_active_branding()
    logo_url = branding.get("logo", "")
    
    if logo_url:
        return RedirectResponse(url=logo_url)
    else:
        # Use default Unifica logo if no branding logo is set
        default_logo = os.getenv("DEFAULT_BRANDING_LOGO", "https://unificadesign.com.py/img/unifica/footerIcon.png")
        return RedirectResponse(url=default_logo)

# Device Management Routes
@app.get("/admin/devices", response_class=HTMLResponse)
async def device_management(
    request: Request,
    current_user: str = Depends(get_current_user)
):
    """Device management page"""
    data_structure = load_data()
    return templates.TemplateResponse(
        "device_management.html",
        {
            "request": request,
            "devices": data_structure.device_registrations,
            "active_page": "devices"
        }
    )

@app.get("/api/devices/{uuid}")
async def get_device(
    uuid: str,
    current_user: str = Depends(get_current_user)
):
    """Get device details"""
    data_structure = load_data()
    device = next((d for d in data_structure.device_registrations if d.uuid == uuid), None)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return device

@app.post("/api/devices")
async def create_device(
    device: DeviceCreate,
    request: Request,
    current_user: str = Depends(get_current_user)
):
    """Create a new device registration"""
    data_structure = load_data()
    
    # Use provided UUID or generate new one
    device_uuid = device.uuid if device.uuid else str(uuid4())
    
    # Check if UUID already exists
    if any(d.uuid == device_uuid for d in data_structure.device_registrations):
        raise HTTPException(status_code=400, detail="Device UUID already exists")
    
    # Parse expiration date if provided
    expires_at = None
    if device.expires_at:
        try:
            expires_at = datetime.fromisoformat(device.expires_at)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid expiration date format")
    
    # Create new device registration
    new_device = DeviceRegistration(
        uuid=device_uuid,
        device_name=device.device_name,
        expires_at=expires_at,
        created_by=current_user,
        notes=device.notes,
        ip_address=request.client.host
    )
    
    data_structure.device_registrations.append(new_device)
    save_data(data_structure)
    
    return new_device

@app.put("/api/devices")
async def update_device(
    device: DeviceUpdate,
    current_user: str = Depends(get_current_user)
):
    """Update device registration"""
    data_structure = load_data()
    
    # Find existing device
    existing_device = next((d for d in data_structure.device_registrations if d.uuid == device.uuid), None)
    if not existing_device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    # Parse expiration date if provided
    expires_at = None
    if device.expires_at:
        try:
            expires_at = datetime.fromisoformat(device.expires_at)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid expiration date format")
    
    # Update device fields
    existing_device.device_name = device.device_name
    existing_device.expires_at = expires_at
    existing_device.notes = device.notes
    
    save_data(data_structure)
    return existing_device

@app.post("/api/devices/{uuid}/toggle")
async def toggle_device(
    uuid: str,
    toggle: DeviceToggle,
    current_user: str = Depends(get_current_user)
):
    """Toggle device active status"""
    data_structure = load_data()
    
    # Find existing device
    device = next((d for d in data_structure.device_registrations if d.uuid == uuid), None)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    # Update active status
    device.is_active = toggle.enable
    
    save_data(data_structure)
    return device

@app.delete("/api/devices/{uuid}")
async def delete_device(
    uuid: str,
    current_user: str = Depends(get_current_user)
):
    """Delete device registration"""
    data_structure = load_data()
    
    # Find and remove device
    device = next((d for d in data_structure.device_registrations if d.uuid == uuid), None)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    data_structure.device_registrations = [d for d in data_structure.device_registrations if d.uuid != uuid]
    save_data(data_structure)
    
    return {"status": "success"}

@app.get("/api/devices")
async def get_devices(
    current_user: str = Depends(get_current_user)
):
    """Get all device registrations"""
    data_structure = load_data()
    return data_structure.device_registrations 