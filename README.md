# Mayoristas Paraguay Backend

A comprehensive backend system for the Mayoristas Paraguay platform - a digital marketplace connecting wholesalers in Paraguay with their customers. This system provides secure administration of shops, product categories, and geographical zones, along with data visualization and analytics capabilities.

This is a FastAPI backend application that provides data management and visualization for the Mayoristas Paraguay platform. The application provides CRUD operations for shops, categories, and zones, as well as various data visualizations.

## License

This software is proprietary and confidential. Unauthorized copying, modification, distribution, or use of this software, via any medium, is strictly prohibited. This software is owned exclusively by Unifica and is protected by copyright law and international treaties.

For licensing inquiries, please contact Unifica at info@unifica.com.py.

## Features

- Complete CRUD API for shops, categories, and zones with authentication
- Secure admin interface with login system
- Banner and image management with Google Cloud Storage integration
- Data visualization dashboard with real-time analytics
- Interactive charts using Plotly
- Modern, responsive UI using Tailwind CSS
- Protected API endpoints with JWT authentication
- Flexible deployment options (Docker/SaaS)

## System Architecture

### Data Storage
- JSON-based data storage for business data (shops, categories, zones)
- Google Cloud Storage for image and banner storage
- Environment-based configuration for easy deployment
- JWT-based session management

### Security
- Role-based access control
- CSRF protection
- Secure cookie handling
- Protected API endpoints
- Environment variable configuration

## Requirements

- Python 3.8+
- pip (Python package installer)
- Google Cloud Storage account (for image storage)
- Environment variables configured

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

4. Set up environment variables:
   - Copy `.env.example` to `.env`
   - Update the values in `.env` with your configuration:
     - Set up Google Cloud Storage credentials
     - Configure admin username and password
     - Set a secure secret key for JWT authentication

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

4. Log in with your admin credentials (configured in `.env`)

## Authentication

The application uses JWT-based authentication with the following features:
- Secure login system with CSRF protection
- HttpOnly cookies for JWT storage
- Protected API endpoints requiring authentication
- Automatic redirection to login for unauthenticated users
- Session persistence across browser tabs
- Configurable session expiration

## Deployment Options

### Docker Deployment
Recommended for self-hosted installations:

1. Build the Docker image:
```bash
docker build -t mayoristas-backend .
```

2. Run the container:
```bash
docker run -p 8000:8000 -v $(pwd)/data.json:/app/data.json --env-file .env mayoristas-backend
```

### SaaS Deployment
For managed hosting by Unifica:
- Fully managed cloud deployment
- Automatic updates and maintenance
- Dedicated support
- Data backup and recovery
- Contact Unifica for pricing and setup

## Data Management

### File Structure
- `data.json`: Main data store for shops, categories, and zones
- Images and banners: Stored in Google Cloud Storage
- Environment variables: Stored in `.env` file

### Backup and Recovery
- Regular automated backups of data.json
- Google Cloud Storage redundancy for images
- Easy data import/export functionality

## API Endpoints

All API endpoints require authentication. You must first log in through the web interface to obtain the necessary authentication token.

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

### Admin Interface

- `/` - Login page (when not authenticated) or redirect to admin dashboard
- `/admin` - Main admin dashboard
- `/admin/shops` - Shop management interface
- `/admin/categories` - Category management interface
- `/admin/zones` - Zone management interface
- `/admin/banners` - Banner management interface
- `/analytics` - Data visualization dashboard

### Visualization Endpoints

- `/shops-by-zone` - Bar chart showing distribution of shops across zones
- `/categories-distribution` - Pie chart showing top 10 categories
- `/shops-by-category` - Bar chart showing top 15 categories by number of shops
- `/working-hours-distribution` - Pie chart showing shops with/without working hours

## API Examples

### Creating a New Shop (with Authentication)

```bash
# First, log in through the web interface to get the authentication cookie
curl -X POST "http://localhost:8000/api/shops" \
     -H "Content-Type: application/json" \
     -H "Cookie: Authorization=Bearer your_jwt_token" \
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

### Updating a Category (with Authentication)

```bash
curl -X PUT "http://localhost:8000/api/categories/1" \
     -H "Content-Type: application/json" \
     -H "Cookie: Authorization=Bearer your_jwt_token" \
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
- Validates authentication tokens and user permissions

## Security Features

- JWT-based authentication
- CSRF protection for forms
- HttpOnly cookies for token storage
- Secure session management
- Protected API endpoints
- Environment-based configuration

## Maintenance and Updates

### Version Updates
- Regular security updates
- Feature additions
- Bug fixes
- Performance improvements

### Support
For technical support or inquiries:
- Email: dev@unificadesign.com.py
- Phone: +595 984 637337
- Business hours: Monday to Friday, 9:00 - 18:00 PYT

## Contact Information

Unifica
- Website: https://unificadesign.com.py
- Email: dev@unificadesign.com.py
- Address: Asunción, Paraguay
- Phone: +595 984 637337
