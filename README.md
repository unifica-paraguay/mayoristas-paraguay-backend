# Mayoristas Paraguay Backend

This is a FastAPI backend application that provides data management and visualization for the Mayoristas Paraguay platform. The application provides CRUD operations for shops, categories, and zones, as well as various data visualizations.

## Features

- Complete CRUD API for shops, categories, and zones
- Banner and image management
- Data visualization dashboard
- Interactive charts using Plotly
- Modern, responsive UI using Tailwind CSS

## Requirements

- Python 3.8+
- pip (Python package installer)

## Installation

1. Clone the repository:
```bash
git clone git@github.com:unifica-paraguay/mayoristas-paraguay-backend.git
cd mayoristas-paraguay-backend
```

2. Create a virtual environment (optional but recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows, use: venv\Scripts\activate
```

3. Install the required packages:
```bash
pip install -r requirements.txt
```

## Running the Application

1. Make sure you're in the project directory and your virtual environment is activated (if you created one).

2. Start the FastAPI server:
```bash
uvicorn app.main:app --reload
```

3. Open your web browser and navigate to:
```
http://localhost:8000
```

## Docker Support

You can also run the application using Docker:

1. Build the Docker image:
```bash
docker build -t mayoristas-backend .
```

2. Run the container:
```bash
docker run -p 8000:8000 -v $(pwd)/data.json:/app/data.json mayoristas-backend
```

## API Endpoints

### Shops

- `GET /api/shops` - Get all shops
- `GET /api/shops/{shop_id}` - Get a specific shop
- `POST /api/shops` - Create a new shop
- `PUT /api/shops/{shop_id}` - Update a shop
- `DELETE /api/shops/{shop_id}` - Delete a shop

### Categories

- `GET /api/categories` - Get all categories
- `GET /api/categories/{category_id}` - Get a specific category
- `POST /api/categories` - Create a new category
- `PUT /api/categories/{category_id}` - Update a category
- `DELETE /api/categories/{category_id}` - Delete a category

### Zones

- `GET /api/zones` - Get all zones
- `GET /api/zones/{zone_id}` - Get a specific zone
- `POST /api/zones` - Create a new zone
- `PUT /api/zones/{zone_id}` - Update a zone
- `DELETE /api/zones/{zone_id}` - Delete a zone

### Banner Management

- `PUT /api/banners/primary` - Update primary banner URLs
- `PUT /api/banners/secondary` - Update secondary banner URLs
- `PUT /api/images/recommended` - Update recommended image URL
- `PUT /api/images/other-businesses` - Update other businesses image URL

### Data Access

- `GET /api/data` - Get the complete data.json file

### Visualization Endpoints

- `/` - Main dashboard with all visualizations
- `/shops-by-zone` - Bar chart showing distribution of shops across zones
- `/categories-distribution` - Pie chart showing top 10 categories
- `/shops-by-category` - Bar chart showing top 15 categories by number of shops
- `/working-hours-distribution` - Pie chart showing shops with/without working hours

## API Examples

### Creating a New Shop

```bash
curl -X POST "http://localhost:8000/api/shops" \
     -H "Content-Type: application/json" \
     -d '{
       "id": 12,
       "name": "New Shop",
       "owner": "John Doe",
       "contact_number": "595991234567",
       "categories": [1, 2],
       "city": "Ciudad del Este",
       "zone_id": 2,
       "categorie_pages": ["recommended", "see_all"],
       "img": "https://example.com/image.jpg"
     }'
```

### Updating a Category

```bash
curl -X PUT "http://localhost:8000/api/categories/1" \
     -H "Content-Type: application/json" \
     -d '{
       "id": 1,
       "name": "Updated Category Name",
       "icon": "LucideIcon"
     }'
```

## Data Validation

The API includes several validation checks:

- Prevents duplicate IDs when creating new items
- Validates that referenced categories exist when creating/updating shops
- Validates that referenced zones exist when creating/updating shops
- Prevents deletion of categories and zones that are in use by shops

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a new Pull Request
