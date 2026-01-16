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

# Default income categories
DEFAULT_INCOME_CATEGORIES = [
    "Salary",
    "Interest on Debt",
    "Stocks / Mutual Funds",
    "Gifts"
]


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
                logger.info(f"✅ Found existing sheets for user {user_id}: {sheet_ids}")
                return sheet_ids
            
            # Create new sheets for new user
            logger.info(f"❌ No existing sheets found, creating new sheets for user {user_id}")
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
            
            logger.info(f"Searching for sheets: '{categories_title}' and '{expenses_title}'")
            
            categories_sheet = None
            expenses_sheet = None
            
            if oauth_access_token:
                # Search in user's Drive
                logger.info("Using OAuth token to search user's Drive")
                oauth_creds = OAuthCredentials(token=oauth_access_token)
                drive = build("drive", "v3", credentials=oauth_creds)
                
                # Search for sheets by name
                query = f"(name='{categories_title}' or name='{expenses_title}') and mimeType='application/vnd.google-apps.spreadsheet' and trashed=false"
                results = drive.files().list(q=query, fields="files(id, name)").execute()
                
                logger.info(f"Found {len(results.get('files', []))} matching files in Drive")
                
                for file in results.get('files', []):
                    logger.info(f"  - {file['name']}: {file['id']}")
                    if file['name'] == categories_title:
                        categories_sheet = file['id']
                    elif file['name'] == expenses_title:
                        expenses_sheet = file['id']
            else:
                # Search in service account's Drive (fallback)
                logger.info("Using Service Account to search")
                for sheet in self.sa_client.openall():
                    if sheet.title == categories_title:
                        categories_sheet = sheet.id
                    elif sheet.title == expenses_title:
                        expenses_sheet = sheet.id
                        
                    if categories_sheet and expenses_sheet:
                        break
            
            if categories_sheet and expenses_sheet:
                logger.info(f"Both sheets found!")
                return {
                    "categories_sheet_id": categories_sheet,
                    "expenses_sheet_id": expenses_sheet
                }
            else:
                logger.info(f"Missing sheets: categories={bool(categories_sheet)}, expenses={bool(expenses_sheet)}")
        except Exception as e:
            logger.error(f"Error finding user sheets: {e}")
            import traceback
            logger.error(traceback.format_exc())
        
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
            expenses_worksheet.update('A1:J1', [['date', 'amount', 'c1_name', 'c2_name', 'payment_mode', 'notes', 'person', 'need_vs_want', 'created_at', 'deleted']])
            
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
            sheet.update('A1:J1', [['date', 'amount', 'c1_name', 'c2_name', 'payment_mode', 'notes', 'person', 'need_vs_want', 'created_at', 'deleted']])
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
                    rows.append([c1_name, c2_name, 'TRUE'])
            
            if rows:
                # Append starting from row 2 (after headers)
                sheet.append_rows(rows)
                logger.info(f"Seeded {len(rows)} categories to sheet {sheet_id}")
                
        except Exception as e:
            logger.error(f"Error seeding categories: {e}")
            import traceback
            logger.error(traceback.format_exc())

    # ======================================================
    # INCOME SHEETS MANAGEMENT
    # ======================================================
    def get_or_create_income_sheets(
        self,
        user_id: str,
        user_email: str,
        oauth_access_token: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Get or create Income-related Google Sheets for a user.
        Returns income_categories_sheet_id and cashflows_sheet_id.
        NEVER recreates if IDs exist in persistent storage.
        """
        if not self.is_available():
            logger.warning("Google Sheets not available - using local-only mode")
            return {"income_categories_sheet_id": "local", "cashflows_sheet_id": "local"}
        
        try:
            # Check if sheets already exist in Drive
            sheet_ids = self._get_income_sheet_ids(user_id, oauth_access_token)
            
            if sheet_ids:
                logger.info(f"✅ Found existing income sheets for user {user_id}: {sheet_ids}")
                return sheet_ids
            
            # Create new sheets for new user
            logger.info(f"❌ No existing income sheets found, creating new sheets for user {user_id}")
            if oauth_access_token:
                return self._create_income_sheets_oauth(user_id, user_email, oauth_access_token)
            else:
                return self._create_income_sheets_sa(user_id, user_email)
            
        except Exception as e:
            logger.error(f"Error in get_or_create_income_sheets: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {"income_categories_sheet_id": "local", "cashflows_sheet_id": "local"}
    
    def _get_income_sheet_ids(self, user_id: str, oauth_access_token: Optional[str] = None) -> Optional[Dict[str, str]]:
        """Find existing income sheets for a user"""
        try:
            income_categories_title = f"{user_id} - ExpenseTracker_IncomeCategories"
            cashflows_title = f"{user_id} - ExpenseTracker_Cashflows"
            
            logger.info(f"Searching for income sheets: '{income_categories_title}' and '{cashflows_title}'")
            
            income_categories_sheet = None
            cashflows_sheet = None
            
            if oauth_access_token:
                # Search in user's Drive
                logger.info("Using OAuth token to search user's Drive for income sheets")
                oauth_creds = OAuthCredentials(token=oauth_access_token)
                drive = build("drive", "v3", credentials=oauth_creds)
                
                # Search for sheets by name
                query = f"(name='{income_categories_title}' or name='{cashflows_title}') and mimeType='application/vnd.google-apps.spreadsheet' and trashed=false"
                results = drive.files().list(q=query, fields="files(id, name)").execute()
                
                logger.info(f"Found {len(results.get('files', []))} matching income files in Drive")
                
                for file in results.get('files', []):
                    logger.info(f"  - {file['name']}: {file['id']}")
                    if file['name'] == income_categories_title:
                        income_categories_sheet = file['id']
                    elif file['name'] == cashflows_title:
                        cashflows_sheet = file['id']
            else:
                # Search in service account's Drive (fallback)
                logger.info("Using Service Account to search for income sheets")
                for sheet in self.sa_client.openall():
                    if sheet.title == income_categories_title:
                        income_categories_sheet = sheet.id
                    elif sheet.title == cashflows_title:
                        cashflows_sheet = sheet.id
                        
                    if income_categories_sheet and cashflows_sheet:
                        break
            
            if income_categories_sheet and cashflows_sheet:
                logger.info(f"Both income sheets found!")
                return {
                    "income_categories_sheet_id": income_categories_sheet,
                    "cashflows_sheet_id": cashflows_sheet
                }
            else:
                logger.info(f"Missing income sheets: categories={bool(income_categories_sheet)}, cashflows={bool(cashflows_sheet)}")
        except Exception as e:
            logger.error(f"Error finding income sheets: {e}")
            import traceback
            logger.error(traceback.format_exc())
        
        return None
    
    def _create_income_sheets_oauth(self, user_id: str, user_email: str, oauth_access_token: str) -> Dict[str, str]:
        """Create new Income Google Sheets for a user using OAuth (in USER's Drive)"""
        try:
            oauth_creds = OAuthCredentials(token=oauth_access_token)
            drive = build("drive", "v3", credentials=oauth_creds)
            
            # Create Income Categories sheet
            income_categories_title = f"{user_id} - ExpenseTracker_IncomeCategories"
            income_categories_file = drive.files().create(
                body={
                    "name": income_categories_title,
                    "mimeType": "application/vnd.google-apps.spreadsheet"
                },
                fields="id"
            ).execute()
            income_categories_id = income_categories_file["id"]
            
            logger.info(f"✅ Created Income Categories sheet in user's Drive: {income_categories_id}")
            
            # Create Cashflows sheet
            cashflows_title = f"{user_id} - ExpenseTracker_Cashflows"
            cashflows_file = drive.files().create(
                body={
                    "name": cashflows_title,
                    "mimeType": "application/vnd.google-apps.spreadsheet"
                },
                fields="id"
            ).execute()
            cashflows_id = cashflows_file["id"]
            
            logger.info(f"✅ Created Cashflows sheet in user's Drive: {cashflows_id}")
            
            # Grant service account editor access so it can read/write
            if self.sa_email:
                for file_id in [income_categories_id, cashflows_id]:
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
            
            # Seed default income categories
            self._seed_income_categories(income_categories_id)
            
            # Initialize cashflows sheet with headers
            self._initialize_cashflows_sheet(cashflows_id)
            
            logger.info("✅ Income sheets created in USER's Drive")
            
            return {
                "income_categories_sheet_id": income_categories_id,
                "cashflows_sheet_id": cashflows_id
            }
            
        except Exception as e:
            logger.error(f"Error creating income sheets with OAuth: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise
    
    def _create_income_sheets_sa(self, user_id: str, user_email: str) -> Dict[str, str]:
        """Create new Income Google Sheets for a user using Service Account (in SA's Drive)"""
        try:
            # Create Income Categories sheet
            income_categories_title = f"{user_id} - ExpenseTracker_IncomeCategories"
            income_categories_sheet = self.sa_client.create(income_categories_title)
            income_categories_worksheet = income_categories_sheet.get_worksheet(0)
            income_categories_worksheet.update('A1:B1', [['c2_name', 'is_active']])
            
            logger.info(f"✅ Created Income Categories sheet: {income_categories_sheet.id}")
            
            # Create Cashflows sheet
            cashflows_title = f"{user_id} - ExpenseTracker_Cashflows"
            cashflows_sheet = self.sa_client.create(cashflows_title)
            cashflows_worksheet = cashflows_sheet.get_worksheet(0)
            cashflows_worksheet.update('A1:G1', [['id', 'date', 'amount', 'c2_name', 'notes', 'created_at', 'is_deleted']])
            
            logger.info(f"✅ Created Cashflows sheet: {cashflows_sheet.id}")
            
            # Seed default income categories
            self._seed_income_categories(income_categories_sheet.id)
            
            return {
                "income_categories_sheet_id": income_categories_sheet.id,
                "cashflows_sheet_id": cashflows_sheet.id
            }
            
        except Exception as e:
            logger.error(f"Error creating income sheets: {e}")
            raise
    
    def _seed_income_categories(self, sheet_id: str):
        """Seed default income categories (ONCE ONLY)"""
        try:
            sheet = self.sa_client.open_by_key(sheet_id).get_worksheet(0)
            
            # Check if headers exist
            first_row = sheet.row_values(1)
            if not first_row or first_row[0] != 'c2_name':
                # Set headers first
                sheet.update('A1:B1', [['c2_name', 'is_active']])
                logger.info(f"Added headers to income categories sheet {sheet_id}")
            
            # Build data rows
            rows = [[cat_name, 'TRUE'] for cat_name in DEFAULT_INCOME_CATEGORIES]
            
            if rows:
                # Append starting from row 2 (after headers)
                sheet.append_rows(rows)
                logger.info(f"✅ Seeded {len(rows)} income categories to sheet {sheet_id}")
                
        except Exception as e:
            logger.error(f"Error seeding income categories: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def _initialize_cashflows_sheet(self, sheet_id: str):
        """Initialize cashflows sheet with headers"""
        try:
            sheet = self.sa_client.open_by_key(sheet_id).get_worksheet(0)
            sheet.update('A1:G1', [['id', 'date', 'amount', 'c2_name', 'notes', 'created_at', 'is_deleted']])
            logger.info(f"Initialized cashflows sheet headers: {sheet_id}")
        except Exception as e:
            logger.error(f"Error initializing cashflows sheet: {e}")

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

    def append_category(self, sheet_id: str, category_data: Dict):
        """Append a new category row to Google Sheets"""
        try:
            sheet = self.sa_client.open_by_key(sheet_id).sheet1
            sheet.append_row([
                category_data.get("c1_name"),
                category_data.get("c2_name"),
                category_data.get("is_active", "TRUE")
            ])
            logger.info(f"Appended category to sheet {sheet_id}")
        except Exception as e:
            logger.error(f"Error appending category: {e}")
            raise

    def append_expense(self, sheet_id: str, expense_data: Dict):
        """Append expense to Google Sheets (matches 10-column header)"""
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
            expense_data.get("created_at"),
            "FALSE"  # deleted - always FALSE for new expenses
        ])

    def update_category_status(self, sheet_id: str, c1_name: str, c2_name: str, is_active: bool):
        """Update the is_active status of a category in Google Sheets"""
        try:
            logger.info(f"Updating category status in Sheets: {c1_name}/{c2_name} → is_active={is_active}")
            sheet = self.sa_client.open_by_key(sheet_id).sheet1
            # Find the row with matching c1_name and c2_name
            all_values = sheet.get_all_values()
            
            logger.debug(f"Searching through {len(all_values)} rows")
            
            for i, row in enumerate(all_values):
                if len(row) >= 3 and row[0] == c1_name and row[1] == c2_name:
                    # Update column C (is_active) - row is 1-indexed
                    new_value = "TRUE" if is_active else "FALSE"
                    sheet.update_cell(i + 1, 3, new_value)
                    logger.info(f"✅ Updated category {c1_name}/{c2_name} is_active to {new_value} at row {i+1}")
                    return
            
            logger.warning(f"❌ Category {c1_name}/{c2_name} not found in sheet {sheet_id}")
        except Exception as e:
            logger.error(f"Error updating category status: {e}")
            import traceback
            logger.error(traceback.format_exc())

    def mark_expense_deleted(self, sheet_id: str, expense_date: str, amount: float, c2_name: str, created_at: str):
        """Mark an expense as deleted in Google Sheets (finds by date+amount+c2+created_at for uniqueness)"""
        try:
            logger.info(f"Marking expense as deleted: date={expense_date}, amount={amount}, c2={c2_name}, created_at={created_at}")
            sheet = self.sa_client.open_by_key(sheet_id).sheet1
            all_values = sheet.get_all_values()
            
            # Skip header row, find matching expense
            for i, row in enumerate(all_values[1:], start=2):  # Start from row 2 (1-indexed)
                if len(row) >= 10:
                    row_date = row[0]
                    row_amount = row[1]
                    row_c2 = row[3]
                    row_created_at = row[8]
                    
                    # Match by date, amount, c2_name, and created_at (unique combo)
                    row_date_part = row_date.split('T')[0] if 'T' in row_date else row_date
                    expense_date_part = expense_date.split('T')[0] if 'T' in expense_date else expense_date
                    date_matches = row_date_part == expense_date_part
                    amount_matches = str(row_amount) == str(amount) or abs(float(row_amount) - float(amount)) < 0.01
                    c2_matches = row_c2 == c2_name
                    created_matches = row_created_at.startswith(created_at.split('.')[0])  # Match without microseconds
                    
                    if date_matches and amount_matches and c2_matches and created_matches:
                        # Update column J (deleted) to "TRUE"
                        sheet.update_cell(i, 10, "TRUE")
                        logger.info(f"✅ Marked expense as deleted at row {i}")
                        return True
            
            logger.warning(f"❌ Expense not found in sheet")
            return False
        except Exception as e:
            logger.error(f"Error marking expense as deleted: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    # ======================================================
    # INCOME CRUD OPERATIONS
    # ======================================================
    def load_income_categories(self, sheet_id: str) -> List[Dict]:
        """Load income categories from Google Sheets"""
        try:
            sheet = self.sa_client.open_by_key(sheet_id).sheet1
            records = sheet.get_all_records()
            logger.info(f"Loaded {len(records)} income categories from sheet {sheet_id}")
            return records
        except Exception as e:
            logger.error(f"Error loading income categories: {e}")
            return []
    
    def add_income_category(self, sheet_id: str, c2_name: str):
        """Add new income category to Google Sheets"""
        try:
            sheet = self.sa_client.open_by_key(sheet_id).sheet1
            sheet.append_row([c2_name, "TRUE"])
            logger.info(f"✅ Added income category '{c2_name}' to sheet {sheet_id}")
        except Exception as e:
            logger.error(f"Error adding income category: {e}")
            raise
    
    def update_income_category_status(self, sheet_id: str, c2_name: str, is_active: bool):
        """Update the is_active status of an income category"""
        try:
            logger.info(f"Updating income category status: {c2_name} → is_active={is_active}")
            sheet = self.sa_client.open_by_key(sheet_id).sheet1
            all_values = sheet.get_all_values()
            
            for i, row in enumerate(all_values):
                if len(row) >= 2 and row[0] == c2_name:
                    # Update column B (is_active)
                    new_value = "TRUE" if is_active else "FALSE"
                    sheet.update_cell(i + 1, 2, new_value)
                    logger.info(f"✅ Updated income category {c2_name} is_active to {new_value} at row {i+1}")
                    return
            
            logger.warning(f"❌ Income category {c2_name} not found in sheet {sheet_id}")
        except Exception as e:
            logger.error(f"Error updating income category status: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def load_cash_inflows(self, sheet_id: str) -> List[Dict]:
        """Load cash inflows from Google Sheets"""
        try:
            sheet = self.sa_client.open_by_key(sheet_id).sheet1
            records = sheet.get_all_records()
            logger.info(f"Loaded {len(records)} cash inflows from sheet {sheet_id}")
            return records
        except Exception as e:
            logger.error(f"Error loading cash inflows: {e}")
            return []
    
    def append_cash_inflow(self, sheet_id: str, inflow_data: Dict):
        """Append cash inflow to Google Sheets (matches 7-column header)"""
        try:
            import uuid
            sheet = self.sa_client.open_by_key(sheet_id).sheet1
            sheet.append_row([
                inflow_data.get("id", str(uuid.uuid4())),  # UUID
                inflow_data.get("date"),
                inflow_data.get("amount"),
                inflow_data.get("c2_name"),  # category name
                inflow_data.get("notes", ""),
                inflow_data.get("created_at"),
                "FALSE"  # is_deleted - always FALSE for new inflows
            ])
            logger.info(f"✅ Appended cash inflow to sheet {sheet_id}")
        except Exception as e:
            logger.error(f"Error appending cash inflow: {e}")
            raise
    
    def soft_delete_cash_inflow(self, sheet_id: str, inflow_id: str):
        """Soft delete a cash inflow by setting is_deleted to TRUE"""
        try:
            logger.info(f"Soft deleting cash inflow: id={inflow_id}")
            sheet = self.sa_client.open_by_key(sheet_id).sheet1
            all_values = sheet.get_all_values()
            
            # Skip header row, find matching inflow by ID
            for i, row in enumerate(all_values[1:], start=2):  # Start from row 2 (1-indexed)
                if len(row) >= 7 and row[0] == inflow_id:
                    # Update column G (is_deleted) to "TRUE"
                    sheet.update_cell(i, 7, "TRUE")
                    logger.info(f"✅ Marked cash inflow as deleted at row {i}")
                    return True
            
            logger.warning(f"❌ Cash inflow {inflow_id} not found in sheet")
            return False
        except Exception as e:
            logger.error(f"Error soft deleting cash inflow: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False


# ==========================================================
# GLOBAL INSTANCE
# ==========================================================
google_sheets_service = GoogleSheetsService()
