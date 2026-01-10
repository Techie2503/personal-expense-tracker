"""
Google Sheets Service
Creates Google Sheets using USER OAuth credentials (OWNER = YOU),
and uses Service Account only for read/write operations.
"""

import os
import json
import logging
from typing import List, Dict, Optional

import gspread
from google.oauth2.service_account import Credentials as ServiceAccountCredentials
from google.oauth2.credentials import Credentials as OAuthCredentials
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

# ========================
# SCOPES
# ========================
SERVICE_ACCOUNT_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file"  # Needed to create new sheets
]

OAUTH_SCOPES = [
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/spreadsheets"
]

# ========================
# DEFAULT CATEGORIES
# ========================
DEFAULT_CATEGORIES = {
    "Food": ["Eat Outside", "Groceries", "Office Food", "Snacks", "Beverages"],
    "Transport": ["Scooty Petrol", "Maintenance", "Parking", "Cab/Auto", "Public Transport"],
    "Health & Fitness": ["Gym Membership", "Trainer", "Protein Powder", "Supplements", "Skincare", "Doctor/Medical"],
    "Education & Career": ["Courses", "ChatGPT/AI Tools", "Books", "Certifications", "Workshops"],
    "Home & Living": ["Cooking Supplies", "Utilities", "Rent", "Maintenance", "Household Items"],
    "Family & Relationships": ["Parents Support", "Medical for Family", "Gifts", "Festivals", "Occasions"],
    "Lifestyle": ["Shopping", "Entertainment", "Cafes", "Hobbies", "Self-care"],
    "Subscriptions & Tools": ["Streaming", "Cloud Services", "Software", "Productivity Apps"],
    "Travel": ["Transport", "Stay", "Food (Travel)", "Local Travel", "Activities"],
    "Investments & Loans": ["Mutual Funds", "Stocks", "Loans", "Insurance"],
    "Miscellaneous": ["One-off Expenses", "Unplanned", "Unknown"]
}


# ==========================================================
# GOOGLE SHEETS SERVICE
# ==========================================================
class GoogleSheetsService:

    def __init__(self):
        """
        Initialize SERVICE ACCOUNT client
        (used only for reading/writing existing sheets)
        """
        self.sa_client = None
        self.sa_email = None

        try:
            # Check if JSON credentials are provided directly via environment variable
            sa_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON_KEY", "").strip()

            
            if sa_json:
                # Use JSON string from environment variable (Render deployment)
                logger.info("Using GOOGLE_SERVICE_ACCOUNT_JSON_KEY from environment")
                sa_info = json.loads(sa_json)
            else:
                # Use credentials file path (local development)
                creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
                if not creds_path or not os.path.exists(creds_path):
                    raise RuntimeError("Service account credentials file not found")
                
                logger.info(f"Using GOOGLE_APPLICATION_CREDENTIALS from file: {creds_path}")
                with open(creds_path) as f:
                    sa_info = json.load(f)

            self.sa_email = sa_info["client_email"]

            sa_creds = ServiceAccountCredentials.from_service_account_info(
                sa_info,
                scopes=SERVICE_ACCOUNT_SCOPES
            )

            self.sa_client = gspread.authorize(sa_creds)
            logger.info("✅ Service Account client initialized")

        except Exception as e:
            logger.error(f"❌ Failed to initialize service account: {e}")
            self.sa_client = None

    def is_available(self) -> bool:
        """Check if Google Sheets service is available"""
        return self.sa_client is not None

    # ======================================================
    # PUBLIC ENTRY POINT
    # ======================================================
    def get_or_create_user_sheets(
        self,
        user_id: str,
        user_email: str,
        oauth_access_token: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Get or create Google Sheets for a user.
        If oauth_access_token is provided, creates sheets in USER's Drive.
        Otherwise falls back to service account (or local mode).
        """
        if not self.is_available():
            logger.warning("Google Sheets not available - using local-only mode")
            return {"categories_sheet_id": "local", "expenses_sheet_id": "local"}
        
        try:
            # Check if sheets already exist
            sheet_ids = self._get_user_sheet_ids(user_id, oauth_access_token)
            
            if sheet_ids:
                logger.info(f"Found existing sheets for user {user_id}")
                return sheet_ids
            
            # Create new sheets for new user
            logger.info(f"Creating new sheets for user {user_id}")
            if oauth_access_token:
                return self._create_user_sheets_oauth(user_id, user_email, oauth_access_token)
            else:
                return self._create_user_sheets_sa(user_id, user_email)
            
        except Exception as e:
            logger.error(f"Error in get_or_create_user_sheets: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {"categories_sheet_id": "local", "expenses_sheet_id": "local"}
    
    def _get_user_sheet_ids(self, user_id: str, oauth_access_token: Optional[str] = None) -> Optional[Dict[str, str]]:
        """Find existing sheets for a user"""
        try:
            categories_title = f"{user_id} - Categories"
            expenses_title = f"{user_id} - Expenses"
            
            categories_sheet = None
            expenses_sheet = None
            
            if oauth_access_token:
                # Search in user's Drive
                oauth_creds = OAuthCredentials(token=oauth_access_token)
                drive = build("drive", "v3", credentials=oauth_creds)
                
                # Search for sheets by name
                query = f"(name='{categories_title}' or name='{expenses_title}') and mimeType='application/vnd.google-apps.spreadsheet' and trashed=false"
                results = drive.files().list(q=query, fields="files(id, name)").execute()
                
                for file in results.get('files', []):
                    if file['name'] == categories_title:
                        categories_sheet = file['id']
                    elif file['name'] == expenses_title:
                        expenses_sheet = file['id']
            else:
                # Search in service account's Drive (fallback)
                for sheet in self.sa_client.openall():
                    if sheet.title == categories_title:
                        categories_sheet = sheet.id
                    elif sheet.title == expenses_title:
                        expenses_sheet = sheet.id
                        
                    if categories_sheet and expenses_sheet:
                        break
            
            if categories_sheet and expenses_sheet:
                return {
                    "categories_sheet_id": categories_sheet,
                    "expenses_sheet_id": expenses_sheet
                }
        except Exception as e:
            logger.error(f"Error finding user sheets: {e}")
        
        return None
    
    def _create_user_sheets_sa(self, user_id: str, user_email: str) -> Dict[str, str]:
        """Create new Google Sheets for a user using Service Account (in SA's Drive)"""
        try:
            # Create Categories sheet
            categories_title = f"{user_id} - Categories"
            categories_sheet = self.sa_client.create(categories_title)
            categories_worksheet = categories_sheet.get_worksheet(0)
            categories_worksheet.update('A1:C1', [['c1_name', 'c2_name', 'is_active']])
            
            logger.info(f"Created Categories sheet: {categories_sheet.id}")
            
            # Create Expenses sheet
            expenses_title = f"{user_id} - Expenses"
            expenses_sheet = self.sa_client.create(expenses_title)
            expenses_worksheet = expenses_sheet.get_worksheet(0)
            expenses_worksheet.update('A1:H1', [['date', 'amount', 'c1_name', 'c2_name', 'payment_mode', 'notes', 'person', 'need_vs_want']])
            
            logger.info(f"Created Expenses sheet: {expenses_sheet.id}")
            
            # Seed default categories
            self._seed_categories(categories_sheet.id)
            
            return {
                "categories_sheet_id": categories_sheet.id,
                "expenses_sheet_id": expenses_sheet.id
            }
            
        except Exception as e:
            logger.error(f"Error creating user sheets: {e}")
            raise
    
    def _create_user_sheets_oauth(self, user_id: str, user_email: str, oauth_access_token: str) -> Dict[str, str]:
        """Create new Google Sheets for a user using OAuth (in USER's Drive)"""
        try:
            oauth_creds = OAuthCredentials(token=oauth_access_token)
            drive = build("drive", "v3", credentials=oauth_creds)
            
            # Create Categories sheet
            categories_title = f"{user_id} - Categories"
            categories_file = drive.files().create(
                body={
                    "name": categories_title,
                    "mimeType": "application/vnd.google-apps.spreadsheet"
                },
                fields="id"
            ).execute()
            categories_id = categories_file["id"]
            
            logger.info(f"Created Categories sheet in user's Drive: {categories_id}")
            
            # Create Expenses sheet
            expenses_title = f"{user_id} - Expenses"
            expenses_file = drive.files().create(
                body={
                    "name": expenses_title,
                    "mimeType": "application/vnd.google-apps.spreadsheet"
                },
                fields="id"
            ).execute()
            expenses_id = expenses_file["id"]
            
            logger.info(f"Created Expenses sheet in user's Drive: {expenses_id}")
            
            # Grant service account editor access so it can read/write
            if self.sa_email:
                for file_id in [categories_id, expenses_id]:
                    try:
                        drive.permissions().create(
                            fileId=file_id,
                            body={
                                "type": "user",
                                "role": "writer",
                                "emailAddress": self.sa_email
                            }
                        ).execute()
                        logger.info(f"Granted service account access to {file_id}")
                    except Exception as perm_error:
                        logger.warning(f"Could not grant SA permission to {file_id}: {perm_error}")
            
            # Seed default categories
            self._seed_categories(categories_id)
            
            # Initialize expenses sheet with headers
            self._initialize_expenses_sheet(expenses_id)
            
            logger.info("✅ Sheets created in USER's Drive (quota-safe)")
            
            return {
                "categories_sheet_id": categories_id,
                "expenses_sheet_id": expenses_id
            }
            
        except Exception as e:
            logger.error(f"Error creating user sheets with OAuth: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise
    
    def _initialize_expenses_sheet(self, sheet_id: str):
        """Initialize expenses sheet with headers"""
        try:
            sheet = self.sa_client.open_by_key(sheet_id).get_worksheet(0)
            sheet.update('A1:H1', [['date', 'amount', 'c1_name', 'c2_name', 'payment_mode', 'notes', 'person', 'need_vs_want']])
            logger.info(f"Initialized expenses sheet headers: {sheet_id}")
        except Exception as e:
            logger.error(f"Error initializing expenses sheet: {e}")
    
    def _seed_categories(self, sheet_id: str):
        """Seed default categories to a new categories sheet"""
        try:
            sheet = self.sa_client.open_by_key(sheet_id).get_worksheet(0)
            
            # First, check if headers exist (row 1)
            first_row = sheet.row_values(1)
            if not first_row or first_row[0] != 'c1_name':
                # Set headers first
                sheet.update('A1:C1', [['c1_name', 'c2_name', 'is_active']])
                logger.info(f"Added headers to sheet {sheet_id}")
            
            # Build data rows
            rows = []
            for c1_name, c2_list in DEFAULT_CATEGORIES.items():
                for c2_name in c2_list:
                    rows.append([c1_name, c2_name, 'true'])
            
            if rows:
                # Append starting from row 2 (after headers)
                sheet.append_rows(rows)
                logger.info(f"Seeded {len(rows)} categories to sheet {sheet_id}")
                
        except Exception as e:
            logger.error(f"Error seeding categories: {e}")
            import traceback
            logger.error(traceback.format_exc())

    # ======================================================
    # FIND EXISTING SHEETS
    # ======================================================
    def _find_existing_sheets(self, user_id: str) -> Optional[Dict[str, str]]:
        try:
            categories_id = None
            expenses_id = None

            for sheet in self.sa_client.openall():
                if sheet.title == f"ExpenseTracker_Categories_{user_id}":
                    categories_id = sheet.id
                elif sheet.title == f"ExpenseTracker_Expenses_{user_id}":
                    expenses_id = sheet.id

            if categories_id and expenses_id:
                return {
                    "categories_sheet_id": categories_id,
                    "expenses_sheet_id": expenses_id
                }

        except Exception:
            pass

        return None

    # ======================================================
    # PUBLIC DATA METHODS
    # ======================================================
    def load_categories(self, sheet_id: str) -> List[Dict]:
        return self.sa_client.open_by_key(sheet_id).sheet1.get_all_records()

    def load_expenses(self, sheet_id: str) -> List[Dict]:
        return self.sa_client.open_by_key(sheet_id).sheet1.get_all_records()

    def append_expense(self, sheet_id: str, expense_data: Dict):
        sheet = self.sa_client.open_by_key(sheet_id).sheet1
        sheet.append_row([
            expense_data.get("date"),
            expense_data.get("amount"),
            expense_data.get("c1_name"),
            expense_data.get("c2_name"),
            expense_data.get("payment_mode"),
            expense_data.get("notes"),
            expense_data.get("person"),
            expense_data.get("need_vs_want"),
            expense_data.get("created_at")
        ])

    def update_category_status(self, sheet_id: str, c2_name: str, is_active: bool):
        sheet = self.sa_client.open_by_key(sheet_id).sheet1
        cell = sheet.find(c2_name)
        if cell:
            sheet.update_cell(cell.row, 3, "true" if is_active else "false")


# ==========================================================
# GLOBAL INSTANCE
# ==========================================================
google_sheets_service = GoogleSheetsService()
