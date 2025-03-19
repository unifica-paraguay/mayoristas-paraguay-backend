from typing import List, Optional
from ..models.models import DataStructure, FeatureAccess
import json
from datetime import datetime, time

class DataHandler:
    """Class for managing data operations."""
    def __init__(self, data_file: str = "data.json"):
        self.data_file = data_file
        self.data = self.load_data()

    def load_data(self) -> DataStructure:
        """Load data from JSON file."""
        try:
            with open(self.data_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return DataStructure(**data)
        except FileNotFoundError:
            # Return empty data structure if file doesn't exist
            return DataStructure(
                shops=[],
                categories=[],
                zones=[],
                primary_banner=[],
                secondary_banner=[],
                recommended_image="",
                other_businesses="",
                branding=None,
                device_registrations=[],
                feature_access=[]
            )

    def save_data(self):
        """Save data to JSON file."""
        def time_handler(obj):
            if hasattr(obj, 'model_dump'):
                return obj.model_dump()
            if isinstance(obj, (datetime, time)):
                return obj.isoformat()
            raise TypeError(f'Object of type {type(obj).__name__} is not JSON serializable')

        with open(self.data_file, "w", encoding="utf-8") as f:
            json.dump(self.data.model_dump(), f, indent=2, ensure_ascii=False, default=time_handler)

    def get_feature(self, feature_id: str) -> Optional[FeatureAccess]:
        """Get a feature by its ID."""
        return next((f for f in self.data.feature_access if f.feature_id == feature_id), None)

    def update_feature(self, feature: FeatureAccess):
        """Update a feature in the data."""
        for i, f in enumerate(self.data.feature_access):
            if f.feature_id == feature.feature_id:
                self.data.feature_access[i] = feature
                self.save_data()
                return
        # If feature not found, append it
        self.data.feature_access.append(feature)
        self.save_data() 