# Mayoristas Paraguay Backend

This is a FastAPI backend application that provides data visualization for the Mayoristas Paraguay platform. The application creates various graphs and charts to analyze the distribution of shops, categories, and other metrics.

## Features

- Visualization of shops by zone
- Distribution of top 10 categories
- Analysis of shops by category
- Working hours distribution
- Modern, responsive UI using Tailwind CSS
- Interactive charts using Plotly

## Requirements

- Python 3.8+
- pip (Python package installer)

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
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

## API Endpoints

- `/`: Main dashboard with all visualizations
- `/shops-by-zone`: Bar chart showing distribution of shops across zones
- `/categories-distribution`: Pie chart showing top 10 categories
- `/shops-by-category`: Bar chart showing top 15 categories by number of shops
- `/working-hours-distribution`: Pie chart showing shops with/without working hours

## Data Structure

The application uses a JSON data structure that includes:
- Shops with their details
- Categories with icons
- Zones
- Banner images

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a new Pull Request 