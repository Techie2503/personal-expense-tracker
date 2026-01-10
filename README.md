# 💰 Expense Tracker PWA (Multi-User with OAuth)

A complete, offline-first Progressive Web App (PWA) for tracking expenses with **Google OAuth Login**, **user-owned Google Sheets**, automatic sync, charts, and category management. Built with FastAPI backend and vanilla JavaScript frontend.

## ✨ Features

- 🔐 **Google OAuth Login** - Secure authentication with Drive & Sheets access
- ☁️ **Google Sheets in YOUR Drive** - Data stored in your own Google Drive (no quota issues!)
- 👥 **Multi-User Support** - Each user has their own data in their own Drive
- 📱 **PWA** - Installable on mobile devices
- 🔄 **Offline-first** - Works without internet, syncs when online
- 📊 **Charts & Insights** - Monthly trends, category distribution, top expenses
- 🏷️ **Category Management** - Two-level category system (C1 → C2)
- 💾 **IndexedDB** - Local queue for offline expense entry
- 🎨 **Responsive UI** - Mobile-first design
- 🚀 **Fast** - Single-page app with <10 second expense entry
- 🌐 **Single Service** - Backend serves both API and frontend
- ♻️ **Redeploy-safe** - Data survives server restarts and redeployments

## 🛠️ Tech Stack

- **Backend**: FastAPI (Python 3.10+)
- **Database**: SQLite (temporary runtime cache)
- **Persistence**: Google Sheets API (user's Drive)
- **Authentication**: Google OAuth 2.0 with Drive & Sheets scopes
- **Frontend**: HTML, CSS, Vanilla JavaScript
- **Charts**: Chart.js
- **Offline**: IndexedDB + Service Worker
- **Deployment**: Render-ready

## 🔧 Prerequisites

Before setting up the app locally or deploying, you need to:

1. **Python 3.10 or higher**
2. **Google Cloud Console Account**
3. **Google OAuth Client ID** (for user login with Drive/Sheets access)
4. **Google Service Account** (for backend read/write operations)

## 📋 Google Cloud Setup (REQUIRED)

### Step 1: Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (e.g., "Expense Tracker")
3. Note the **Project ID**

### Step 2: Enable Required APIs

Enable these APIs in your project:

1. **Google Sheets API**
   - Go to: APIs & Services → Library
   - Search "Google Sheets API"
   - Click "Enable"

2. **Google Drive API**
   - Search "Google Drive API"
   - Click "Enable"

### Step 3: Create OAuth 2.0 Client ID (for User Login)

1. Go to: APIs & Services → Credentials
2. Click **"Create Credentials"** → **"OAuth client ID"**
3. If prompted, configure the OAuth consent screen:
   - User Type: **External**
   - App name: **Expense Tracker**
   - User support email: **your-email@gmail.com**
   - Developer contact: **your-email@gmail.com**
   - **Scopes**: Add the following scopes:
     - `https://www.googleapis.com/auth/userinfo.email`
     - `https://www.googleapis.com/auth/userinfo.profile`
     - `https://www.googleapis.com/auth/drive.file`
     - `https://www.googleapis.com/auth/spreadsheets`
   - Test users: Add your Gmail address (if app is in "Testing" mode)
   - Save and Continue

4. Create OAuth Client ID:
   - Application type: **Web application**
   - Name: **Expense Tracker Web Client**
   - Authorized JavaScript origins:
     ```
     http://localhost:8000
     https://your-app-name.onrender.com
     ```
   - Authorized redirect URIs:
     ```
     http://localhost:8000
     https://your-app-name.onrender.com
     ```
   - Authorized redirect URIs:
     ```
     http://localhost:8000
     https://your-app-name.onrender.com
     ```
   - Click **Create**

5. **Copy the Client ID** (looks like: `123456789-abcdefg.apps.googleusercontent.com`)
   - Save this for the `GOOGLE_CLIENT_ID` environment variable

### Step 4: Create Service Account (for Backend API Access)

1. Go to: APIs & Services → Credentials
2. Click **"Create Credentials"** → **"Service Account"**
3. Service account details:
   - Name: **expense-tracker-service**
   - ID: (auto-generated)
   - Click **Create and Continue**

4. Grant this service account access (optional, skip):
   - Click **Continue**
   - Click **Done**

5. Create and download the key:
   - Click on the newly created service account
   - Go to **"Keys"** tab
   - Click **"Add Key"** → **"Create new key"**
   - Key type: **JSON**
   - Click **Create**
   - The JSON file will download (e.g., `expense-tracker-service-abc123.json`)

6. **Save this JSON file securely** - you'll need it for the `GOOGLE_APPLICATION_CREDENTIALS` environment variable

⚠️ **IMPORTANT**: Keep this JSON file secret! It provides programmatic access to Google APIs.

### Step 5: Share Sheets Access (will be automatic)

The service account email (found in the JSON file, looks like `expense-tracker-service@your-project.iam.gserviceaccount.com`) will automatically create sheets and give itself access. No manual sharing needed!

---

## 📦 Local Installation & Setup

### Quick Start (3 Steps)

1. **Set up environment variables:**

Create a `.env` file in the project root:

```bash
# .env
GOOGLE_CLIENT_ID=your-client-id-here.apps.googleusercontent.com
GOOGLE_APPLICATION_CREDENTIALS=./path-to-service-account.json
ENVIRONMENT=development
DATABASE_URL=sqlite:///./expenses.db
PORT=8000
```

Replace:
- `GOOGLE_CLIENT_ID` with your OAuth Client ID from Step 3
- `GOOGLE_APPLICATION_CREDENTIALS` with the path to your service account JSON file from Step 4

2. **Run the setup script:**

```bash
chmod +x run_local.sh
./run_local.sh
```

3. **Open your browser:**

```
http://localhost:8000
```

You'll be greeted with the **Google Login** page!

### Manual Setup (Alternative)

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export GOOGLE_CLIENT_ID="your-client-id.apps.googleusercontent.com"
export GOOGLE_APPLICATION_CREDENTIALS="./service-account.json"
export ENVIRONMENT="development"
export DATABASE_URL="sqlite:///./expenses.db"

# Run the server
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## 🚀 Deployment to Render

### Prerequisites
- Render account (free tier works!)
- GitHub repository with this code
- Google Cloud setup completed (Steps 1-5 above)

### Step-by-Step Deployment

1. **Push your code to GitHub**
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin https://github.com/your-username/expense-tracker.git
   git push -u origin main
   ```

2. **Create a New Web Service on Render**
   - Go to [Render Dashboard](https://dashboard.render.com/)
   - Click **"New +"** → **"Web Service"**
   - Connect your GitHub repository
   - Select the `expense_tracker` repository

3. **Configure the Service**
   - **Name**: `expense-tracker` (or your choice)
   - **Region**: Choose closest to you
   - **Branch**: `main`
   - **Runtime**: `Python 3`
   - **Build Command**:
     ```bash
     pip install -r requirements.txt
     ```
   - **Start Command**:
     ```bash
     uvicorn backend.main:app --host 0.0.0.0 --port $PORT
     ```
   - **Instance Type**: `Free` (or paid for better performance)

4. **Set Environment Variables**

   Click **"Advanced"** → **"Add Environment Variable"**

   Add these variables:

   | Key | Value |
   |-----|-------|
   | `GOOGLE_CLIENT_ID` | Your OAuth Client ID from Step 3 |
   | `GOOGLE_APPLICATION_CREDENTIALS` | See note below ⚠️ |
   | `ENVIRONMENT` | `production` |
   | `DATABASE_URL` | `sqlite:////tmp/expenses.db` |
   | `PORT` | `10000` (auto-set by Render) |

   ⚠️ **For `GOOGLE_APPLICATION_CREDENTIALS` on Render:**

   You have two options:

   **Option A: Inline JSON (Simpler)**
   - Copy the ENTIRE contents of your service account JSON file
   - Create an environment variable named `GOOGLE_SERVICE_ACCOUNT_JSON`
   - Paste the JSON content as the value
   - Update `backend/google_sheets_service.py` to read from this env var instead of a file

   **Option B: File Upload (More Secure)**
   - Use Render's persistent disk (see next step)
   - Upload the JSON file to `/data/service-account.json`
   - Set `GOOGLE_APPLICATION_CREDENTIALS=/data/service-account.json`

   For simplicity, I recommend **Option A**. Here's how to modify the code:

   In `backend/google_sheets_service.py`, change the initialization:

   ```python
   import json
   import os
   
   # ... existing imports ...

   def _initialize_service():
       try:
           # Try loading from environment variable first (Render)
           service_account_json = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')
           if service_account_json:
               credentials_dict = json.loads(service_account_json)
               credentials = service_account.Credentials.from_service_account_info(
                   credentials_dict,
                   scopes=SCOPES
               )
           else:
               # Fall back to file (local development)
               credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
               credentials = service_account.Credentials.from_service_account_file(
                   credentials_path,
                   scopes=SCOPES
               )
           # ... rest of initialization ...
   ```

5. **Update OAuth Authorized Origins**
   - Go back to Google Cloud Console → APIs & Services → Credentials
   - Edit your OAuth Client ID
   - Add to **Authorized JavaScript origins**:
     ```
     https://your-app-name.onrender.com
     ```
   - Add to **Authorized redirect URIs**:
     ```
     https://your-app-name.onrender.com
     ```
   - Save

6. **Deploy!**
   - Click **"Create Web Service"**
   - Render will build and deploy your app
   - Wait for the build to complete (2-5 minutes)

7. **First Time Setup**
   - Visit `https://your-app-name.onrender.com`
   - You'll see the Google Login page
   - Sign in with your Google account
   - The app will automatically:
     - Create Google Sheets for you (Categories & Expenses)
     - Seed default categories
     - Load the app

8. **Add Test Users** (if using OAuth consent screen in Testing mode)
   - Go to Google Cloud Console → APIs & Services → OAuth consent screen
   - Add test users (Gmail addresses that can access the app)

---

## 📱 Using the App

### First Login
1. Visit the app URL
2. Click "Sign in with Google"
3. Authorize the app
4. Your account is created with default categories

### Adding Expenses
1. Navigate to **"Add Expense"** tab
2. Fill in:
   - Date (pre-filled with current time)
   - Amount
   - Category (C1)
   - Subcategory (C2) - auto-populated based on C1
   - Payment mode
   - Notes (optional)
3. Click **"Save Expense"**
4. Works offline! Syncs when you're back online.

### Viewing Expenses
- **Expenses** tab: List all expenses, paginated
- Filter by date range
- Delete expenses
- Download CSV export

### Insights
- **Insights** tab shows:
  - Monthly trend (last 12 months)
  - C1 category distribution (pie chart)
  - C2 subcategory breakdown (bar chart)
  - Top 10 expenses
- Filter charts by date range

### Managing Categories
- **Categories** tab:
  - View all C1 and C2 categories
  - Add new categories/subcategories
  - Activate/deactivate categories
  - Categories are synced to Google Sheets

### Settings
- **Settings** tab:
  - Sync queued offline expenses
  - Install app as PWA
  - View sync status

---

## 🏗️ Architecture Overview

### Data Flow

```
┌─────────────────────────────────────────┐
│           User Browser                  │
│  (PWA with IndexedDB for offline)       │
└───────────────┬─────────────────────────┘
                │
                ↓
┌─────────────────────────────────────────┐
│         FastAPI Backend                 │
│     (SQLite as runtime cache)           │
└───────────────┬─────────────────────────┘
                │
                ↓
┌─────────────────────────────────────────┐
│        Google Sheets API                │
│   (Source of truth for all data)        │
└─────────────────────────────────────────┘
```

### Key Principles

1. **Google Sheets = Source of Truth**
   - All data is stored in Google Sheets
   - One "Categories" sheet per user
   - One "Expenses" sheet per user

2. **SQLite = Temporary Cache**
   - Fast queries for charts and listings
   - Rebuilt from Google Sheets on every app startup
   - Not persistent across Render redeploys

3. **User Isolation**
   - Each user has their own Google Sheets
   - All operations scoped by `user_id`
   - No data leakage between users

4. **Startup Behavior**
   - App reads all users' sheets
   - Hydrates SQLite database
   - App becomes ready for requests

5. **Normal Operations**
   - Write to both SQLite (for speed) and Google Sheets (for persistence)
   - Reads come from SQLite
   - Charts generated from SQLite

6. **Client-Side Session**
   - User credentials stored in localStorage
   - Users remain logged in across redeploys
   - Logout clears localStorage and IndexedDB

---

## 🗂️ Project Structure

```
expense_tracker/
├── backend/
│   ├── __init__.py
│   ├── main.py                     # FastAPI app + all endpoints
│   ├── models.py                   # SQLModel definitions (User, Category, Expense)
│   ├── database.py                 # Database session management
│   ├── auth.py                     # Google OAuth verification
│   ├── google_sheets_service.py    # Google Sheets API wrapper
│   ├── user_mapping.py             # User → Sheet ID mapping
│   └── hydration.py                # Rebuild DB from Sheets on startup
├── frontend/
│   ├── index.html                  # Main app (protected)
│   ├── login.html                  # Google login (landing page)
│   ├── app.js                      # Frontend logic (auth + API calls)
│   ├── styles.css                  # Responsive styles
│   ├── manifest.json               # PWA manifest
│   └── service-worker.js           # Offline support
├── requirements.txt                # Python dependencies
├── Dockerfile                      # Docker build (optional)
├── Procfile                        # Render start command
├── run_local.sh                    # Local dev script
├── .env.example                    # Example environment variables
├── .gitignore                      # Ignore sensitive files
└── README.md                       # This file
```

---

## 🧪 Testing

### Test Locally

```bash
# Start the server
./run_local.sh

# In another terminal, test the health endpoint
curl http://localhost:8000/api/health

# Expected response:
# {"status": "healthy", "timestamp": "...", "google_sheets": true}
```

### Test Google Login

1. Visit `http://localhost:8000`
2. Click "Sign in with Google"
3. Sign in with a test user
4. Check the app loads

### Test Offline Mode

1. Add an expense while online
2. Open DevTools → Network tab
3. Set to "Offline" mode
4. Add another expense
5. Check it's queued in IndexedDB
6. Go back online
7. Refresh the page
8. The queued expense should sync automatically

---

## 🔐 Security Notes

- ⚠️ **Never commit** your `.env` file or service account JSON to Git
- ⚠️ Service account JSON grants full access - keep it secret
- ✅ OAuth tokens are verified server-side
- ✅ All API calls require valid `user_id`
- ✅ Users can only access their own data
- ✅ Google Sheets are private to each user's service account

---

## 📊 Default Category Taxonomy

The app seeds these categories for new users:

1. **Food**: Eat Outside, Groceries, Office Food, Snacks, Beverages
2. **Transport**: Scooty Petrol, Maintenance, Parking, Cab/Auto, Public Transport
3. **Health & Fitness**: Gym Membership, Trainer, Protein Powder, Supplements, Skincare, Doctor/Medical
4. **Education & Career**: Courses, ChatGPT/AI Tools, Books, Certifications, Workshops
5. **Home & Living**: Cooking Supplies, Utilities, Rent, Maintenance, Household Items
6. **Family & Relationships**: Parents Support, Medical for Family, Gifts, Festivals, Occasions
7. **Lifestyle**: Shopping, Entertainment, Cafes, Hobbies, Self-care
8. **Subscriptions & Tools**: Streaming, Cloud Services, Software, Productivity Apps
9. **Travel**: Transport, Stay, Food (Travel), Local Travel, Activities
10. **Miscellaneous**: One-off Expenses, Unplanned, Unknown

---

## 🐛 Troubleshooting

### Issue: "Invalid token" error on login

- **Cause**: OAuth Client ID mismatch or expired token
- **Fix**: 
  - Verify `GOOGLE_CLIENT_ID` matches the one in Google Cloud Console
  - Check authorized origins include your domain
  - Try clearing browser cookies/cache

### Issue: "Google Sheets not available"

- **Cause**: Service account credentials invalid or APIs not enabled
- **Fix**:
  - Verify `GOOGLE_APPLICATION_CREDENTIALS` path is correct
  - Check both Google Sheets API and Google Drive API are enabled
  - Verify service account JSON is valid

### Issue: "No categories available"

- **Cause**: New user, categories not seeded yet
- **Fix**:
  - Refresh the page (should auto-hydrate)
  - Check backend logs for errors
  - Manually check Google Sheets for your user

### Issue: App is slow on Render

- **Cause**: Free tier has limited resources
- **Fix**:
  - Upgrade to a paid plan
  - Or accept slower cold starts (free tier spins down after 15min of inactivity)

### Issue: Data lost after redeploy

- **Cause**: SQLite is in `/tmp` or not using Google Sheets
- **Fix**:
  - Verify `DATABASE_URL` is set correctly
  - Check backend logs confirm Google Sheets hydration runs
  - Manually verify data exists in Google Sheets

---

## 🤝 Contributing

This is a personal expense tracker, but feel free to fork and customize!

---

## 📄 License

MIT License - see `LICENSE` file for details.

---

## 🎉 Enjoy Tracking Your Expenses!

Built with ❤️ using FastAPI, Google Sheets API, and Vanilla JS.

For issues or questions, check the backend logs or inspect the browser console for errors.
