from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from .models.models import DataStructure
import json

app = FastAPI(title="Mayoristas Paraguay Backend")

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Load the data
with open("data.json", "r", encoding="utf-8") as f:
    data = json.load(f)
    data_structure = DataStructure(**data)

@app.get("/", response_class=HTMLResponse)
async def root():
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
async def get_shops_by_zone():
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
    
    fig = px.bar(df, x="zone", y="count", title="Shops by Zone")
    return HTMLResponse(fig.to_html())

@app.get("/categories-distribution")
async def get_categories_distribution():
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
    
    fig = px.pie(df, values="count", names="category", title="Top 10 Categories Distribution")
    return HTMLResponse(fig.to_html())

@app.get("/shops-by-category")
async def get_shops_by_category():
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
    
    fig = px.bar(df, x="category", y="count", title="Top 15 Categories by Number of Shops")
    fig.update_layout(xaxis_tickangle=-45)
    return HTMLResponse(fig.to_html())

@app.get("/working-hours-distribution")
async def get_working_hours_distribution():
    # Count shops with and without working hours
    with_hours = len([shop for shop in data_structure.shops if shop.working_hours])
    without_hours = len(data_structure.shops) - with_hours
    
    fig = go.Figure(data=[go.Pie(
        labels=['With Working Hours', 'Without Working Hours'],
        values=[with_hours, without_hours],
        title="Working Hours Distribution"
    )])
    return HTMLResponse(fig.to_html()) 