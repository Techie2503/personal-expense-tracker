"""
User Sheet Mapping
Stores user_id → {categories_sheet_id, expenses_sheet_id, income_categories_sheet_id, cashflows_sheet_id} mapping
Persists in a simple JSON file (or can be extended to use a database)
"""
import json
import os
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)

MAPPING_FILE = "user_sheets_mapping.json"


class UserSheetMapping:
    """Manages mapping between users and their Google Sheets"""
    
    def __init__(self):
        """Initialize and load existing mappings"""
        self.mappings = self._load_mappings()
    
    def _load_mappings(self) -> Dict:
        """Load mappings from file"""
        if os.path.exists(MAPPING_FILE):
            try:
                with open(MAPPING_FILE, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading mappings: {e}")
                return {}
        return {}
    
    def _save_mappings(self):
        """Save mappings to file"""
        try:
            with open(MAPPING_FILE, 'w') as f:
                json.dump(self.mappings, f, indent=2)
            logger.info("Saved user sheet mappings")
        except Exception as e:
            logger.error(f"Error saving mappings: {e}")
    
    def get_user_sheets(self, user_id: str) -> Optional[Dict[str, str]]:
        """Get sheet IDs for a user"""
        return self.mappings.get(user_id)
    
    def set_user_sheets(
        self, 
        user_id: str, 
        categories_sheet_id: str, 
        expenses_sheet_id: str,
        income_categories_sheet_id: Optional[str] = None,
        cashflows_sheet_id: Optional[str] = None
    ):
        """Set sheet IDs for a user"""
        if user_id not in self.mappings:
            self.mappings[user_id] = {}
        
        self.mappings[user_id]["categories_sheet_id"] = categories_sheet_id
        self.mappings[user_id]["expenses_sheet_id"] = expenses_sheet_id
        
        if income_categories_sheet_id:
            self.mappings[user_id]["income_categories_sheet_id"] = income_categories_sheet_id
        if cashflows_sheet_id:
            self.mappings[user_id]["cashflows_sheet_id"] = cashflows_sheet_id
        
        self._save_mappings()
        logger.info(f"Stored sheet mapping for user {user_id}")
    
    def set_income_sheets(self, user_id: str, income_categories_sheet_id: str, cashflows_sheet_id: str):
        """Set income-related sheet IDs for existing user"""
        if user_id not in self.mappings:
            logger.error(f"Cannot set income sheets for non-existent user {user_id}")
            return
        
        self.mappings[user_id]["income_categories_sheet_id"] = income_categories_sheet_id
        self.mappings[user_id]["cashflows_sheet_id"] = cashflows_sheet_id
        self._save_mappings()
        logger.info(f"Stored income sheet mapping for user {user_id}")
    
    def user_exists(self, user_id: str) -> bool:
        """Check if user has sheets configured"""
        return user_id in self.mappings


# Global instance
user_sheet_mapping = UserSheetMapping()
