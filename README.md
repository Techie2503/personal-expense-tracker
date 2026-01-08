# 💰 Expense Tracker PWA

A complete, offline-first Progressive Web App (PWA) for tracking expenses with automatic sync, charts, and category management. Built with FastAPI backend and vanilla JavaScript frontend.

## ✨ Features

- 📱 **PWA** - Installable on mobile devices
- 🔄 **Offline-first** - Works without internet, syncs when online
- 📊 **Charts & Insights** - Monthly trends, category distribution, top expenses
- 🏷️ **Category Management** - Two-level category system (C1 → C2)
- 💾 **IndexedDB** - Local queue for offline expense entry
- 🎨 **Responsive UI** - Mobile-first design
- 🚀 **Fast** - Single-page app with <10 second expense entry
- 🌐 **Single Service** - Backend serves both API and frontend

## 🛠️ Tech Stack

- **Backend**: FastAPI (Python 3.10+)
- **Database**: SQLite with SQLModel
- **Frontend**: HTML, CSS, Vanilla JavaScript
- **Charts**: Chart.js
- **Offline**: IndexedDB + Service Worker
- **Deployment**: Render-ready with persistent disk support

## 📦 Installation & Local Setup

### Prerequisites

- Python 3.10 or higher
- pip
- Modern web browser

### Quick Start (3 Commands)

1. **Clone and navigate:**
   ```bash
   cd /path/to/expense_tracker
   ```

2. **Run the setup script:**
   ```bash
   chmod +x run_local.sh
   ./run_local.sh
   ```

3. **Open your browser:**
   ```
   http://localhost:8000
   ```

The script will:
- Create a virtual environment
- Install all dependencies
- Set up the database
- Start the server with auto-reload

### Manual Setup (Alternative)

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set database URL (optional, defaults to sqlite:///./expenses.db)
export DATABASE_URL="sqlite:///./expenses.db"

# Run the server
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

## 🌱 Seeding the Database

The app includes a canonical taxonomy with 10 C1 categories and their subcategories.

### Option 1: Via API Endpoint
```bash
curl -X POST http://localhost:8000/api/seed
```

### Option 2: Via Web UI
1. Open http://localhost:8000
2. Navigate to the browser console
3. The database will auto-create tables on startup
4. Click the seed endpoint or use the curl command above

### Option 3: Via Python Script
```bash
source venv/bin/activate
python -c "from backend.database import create_db_and_tables; from backend.seed import seed_database; create_db_and_tables(); seed_database()"
```

The seed will create:
- 10 C1 categories (Food, Transport, Health & Fitness, etc.)
- 45+ C2 subcategories
- 50 sample expenses for the last 3 months

## 📱 Using the App

### Add Expense (Main Screen)
1. Date is pre-filled with current time
2. Enter amount
3. Select C1 category → C2 subcategory auto-populates
4. Choose payment mode (Cash/Card/UPI/Net Banking)
5. Optional: Add person, need vs want, notes
6. Click "Save" - Takes <10 seconds total!

**Offline Mode**: If offline, expense is saved to IndexedDB and queued for sync.

### View Expenses
- Browse all expenses with pagination
- Filter by date range
- Delete expenses (soft delete)

### Insights & Charts
- **Monthly Trend**: Line chart of last 12 months
- **C1 Distribution**: Pie chart of spending by category
- **C2 Breakdown**: Bar chart of subcategories (filterable)
- **Top 10 Expenses**: Table of highest expenses

### Manage Categories
- Add new C1 categories
- Add C2 subcategories under any C1
- Enable/disable categories (doesn't delete, just hides)

### Settings
- View sync queue status
- Manual sync button
- Install PWA button
- App information

## 🔄 Offline & Sync Behavior

### How Offline Works
1. **Network Available**: Expenses POST directly to API
2. **Network Unavailable**: Expenses saved to IndexedDB queue
3. **Network Restored**: Auto-sync triggers, pushes queue to server
4. **Service Worker**: Caches app shell for instant offline loading

### Testing Offline Mode
1. Open app in browser
2. Open DevTools → Network tab
3. Check "Offline" checkbox
4. Add an expense - see "Saved offline" message
5. Go to Settings → See queue count
6. Uncheck "Offline"
7. Click "Sync Now" or wait for auto-sync
8. Expense appears in server database

### Background Sync
The service worker implements:
- Cache-first strategy for static files
- Network-first strategy for API calls
- Background sync API (where supported)
- Fallback periodic sync on page load

## 🚀 Deploy to Render

### Step-by-Step Deployment

#### 1. Prepare Repository
```bash
# Initialize git (if not already done)
git init
git add .
git commit -m "Initial commit: Expense Tracker PWA"

# Push to GitHub
git remote add origin https://github.com/yourusername/expense-tracker.git
git push -u origin main
```

#### 2. Create Web Service on Render
1. Go to [Render Dashboard](https://dashboard.render.com/)
2. Click **"New +"** → **"Web Service"**
3. Connect your GitHub repository
4. Configure the service:

**Basic Settings:**
- **Name**: `expense-tracker` (or your choice)
- **Region**: Choose closest to your users
- **Branch**: `main`
- **Root Directory**: Leave empty
- **Runtime**: `Python 3`

**Build & Deploy:**
- **Build Command**: 
  ```
  pip install -r requirements.txt
  ```
- **Start Command**: 
  ```
  uvicorn backend.main:app --host 0.0.0.0 --port $PORT
  ```

#### 3. Add Persistent Disk
**IMPORTANT**: SQLite needs persistent storage!

1. In your Web Service dashboard, go to **"Disks"** tab
2. Click **"Add Disk"**
3. Configure:
   - **Name**: `expense-data`
   - **Mount Path**: `/data`
   - **Size**: 1 GB (or more if needed)
4. Click **"Save"**

#### 4. Set Environment Variables
Go to **"Environment"** tab and add:

| Key | Value |
|-----|-------|
| `DATABASE_URL` | `sqlite:////data/expenses.db` |
| `PORT` | (Auto-set by Render, no need to add) |

**Note**: Use **4 forward slashes** (`////`) for absolute path!

#### 5. Deploy
1. Click **"Create Web Service"**
2. Wait for build & deploy (2-3 minutes)
3. Once deployed, click the service URL (e.g., `https://expense-tracker.onrender.com`)

#### 6. Seed Production Database
```bash
curl -X POST https://your-app.onrender.com/api/seed
```

Or open the URL in browser and access: `/api/seed`

#### 7. Test PWA Installation
1. Open the deployed URL on mobile
2. Browser will prompt "Add to Home Screen"
3. Install and test offline functionality!

### Important Render Notes

- **Free Tier**: Spins down after 15 min of inactivity. First request may be slow.
- **Persistent Disk**: Required for SQLite. Data persists across deploys.
- **Database Path**: Must use `/data/expenses.db` with 4 slashes in DATABASE_URL
- **Health Checks**: Render auto-checks `/api/health` endpoint
- **Logs**: View real-time logs in Render dashboard

### Upgrading Render Plan (Optional)
For production use:
- Upgrade to paid plan ($7/mo) for always-on service
- Increase disk size if needed
- Add custom domain
- Enable auto-deploy on git push

## 🏗️ Project Structure

```
expense_tracker/
├── backend/
│   ├── __init__.py
│   ├── main.py          # FastAPI app, routes, static file serving
│   ├── models.py        # SQLModel database models
│   ├── database.py      # Database connection & session
│   └── seed.py          # Seed script with taxonomy
├── frontend/
│   ├── index.html       # Single-page app HTML
│   ├── styles.css       # Responsive mobile-first CSS
│   ├── app.js           # Main JavaScript (IndexedDB, API, UI)
│   ├── manifest.json    # PWA manifest
│   └── service-worker.js # Service worker for offline support
├── requirements.txt     # Python dependencies
├── Dockerfile          # Docker configuration
├── Procfile            # Render/Heroku start command
├── .gitignore          # Git ignore file
├── LICENSE             # MIT License
├── run_local.sh        # Local setup & run script
└── README.md           # This file
```

## 🔧 Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite:///./expenses.db` | Database connection string |
| `PORT` | `8000` | Server port (auto-set by Render) |

### Database URLs

**Local Development:**
```
sqlite:///./expenses.db        # Relative path in project root
```

**Docker:**
```
sqlite:///./expenses.db        # Inside container
```

**Render Production:**
```
sqlite:////data/expenses.db    # Absolute path to mounted disk
```

## 📊 API Documentation

Once running, visit:
- **Interactive Docs**: http://localhost:8000/docs
- **Alternative Docs**: http://localhost:8000/redoc

### Key Endpoints

#### Categories
- `GET /api/categories` - List all C1 categories
- `POST /api/categories` - Create C1 category
- `PUT /api/categories/{id}` - Update C1 category
- `GET /api/categories/{c1_id}/c2` - List C2 for C1
- `POST /api/categories/{c1_id}/c2` - Create C2 under C1
- `PUT /api/categories/c2/{id}` - Update C2 category

#### Expenses
- `GET /api/expenses` - List expenses (supports filters: start_date, end_date, limit, offset)
- `POST /api/expenses` - Create expense
- `GET /api/expenses/{id}` - Get single expense
- `PUT /api/expenses/{id}` - Update expense
- `DELETE /api/expenses/{id}` - Delete expense (soft delete)
- `GET /api/expenses/top?limit=10` - Top N expenses

#### Insights
- `GET /api/insights/monthly` - Monthly totals (last 12 months)
- `GET /api/insights/c1-distribution` - Total per C1 category
- `GET /api/insights/c2-breakdown?c1_id=X` - Total per C2 (optional C1 filter)

#### Utility
- `POST /api/seed` - Seed database with taxonomy
- `GET /api/health` - Health check

## 🧪 Testing

### Test Offline Functionality

1. **Setup:**
   ```bash
   ./run_local.sh
   # Open http://localhost:8000
   ```

2. **Go Offline:**
   - Chrome DevTools → Network → Check "Offline"
   - Add an expense
   - Should see "📥 Saved offline. Will sync when online."

3. **Check Queue:**
   - Navigate to Settings screen
   - Should show "X expense(s) waiting to sync"

4. **Go Online:**
   - Uncheck "Offline" in DevTools
   - Click "Sync Now" button
   - Should see "✅ Synced X expense(s)!"

5. **Verify:**
   - Navigate to Expenses list
   - Offline expense should appear

### Test PWA Installation

**Desktop (Chrome):**
1. Open app → Look for install icon in address bar
2. Click → Install
3. App opens in standalone window

**Mobile (iOS Safari):**
1. Open app → Tap Share button
2. Tap "Add to Home Screen"
3. App appears on home screen

**Mobile (Android Chrome):**
1. Open app → Tap "Add to Home Screen" prompt
2. Or Menu → "Install app"
3. App appears in app drawer

## 🐛 Troubleshooting

### Issue: CORS Errors
**Symptom**: API calls fail with CORS errors in browser console.

**Solution**: 
- Check backend CORS settings in `backend/main.py`
- For production, restrict `allow_origins` to your domain
- Currently set to `["*"]` for development

### Issue: Database Not Found
**Symptom**: `no such table` errors.

**Solution**:
```bash
# Delete old database
rm expenses.db

# Restart server (tables auto-create)
./run_local.sh

# Seed database
curl -X POST http://localhost:8000/api/seed
```

### Issue: Render Deploy Fails
**Symptom**: Build or start command fails on Render.

**Common Fixes**:
1. Check Python version (must be 3.10+)
2. Verify `requirements.txt` is in root
3. Check start command: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
4. View logs in Render dashboard

### Issue: Data Not Persisting on Render
**Symptom**: Data disappears after redeploy.

**Solution**:
1. Ensure persistent disk is attached
2. Mount path is `/data`
3. `DATABASE_URL=sqlite:////data/expenses.db` (4 slashes!)
4. Disk survives across deploys

### Issue: PWA Not Installing
**Symptom**: No "Add to Home Screen" option.

**Checks**:
1. Must be served over HTTPS (Render provides this)
2. Manifest.json must be valid
3. Service worker must register successfully
4. Check browser console for errors
5. Some browsers require user interaction first

### Issue: Offline Sync Not Working
**Symptom**: Queued expenses don't sync.

**Debug Steps**:
1. Open DevTools → Application → IndexedDB → ExpenseTrackerDB
2. Check `queuedExpenses` store for items
3. Open DevTools → Application → Service Workers
4. Verify service worker is active
5. Check Network tab for failed requests
6. Use "Sync Now" button in Settings for manual trigger

### Issue: Charts Not Displaying
**Symptom**: Blank chart areas.

**Solution**:
1. Check browser console for JavaScript errors
2. Verify Chart.js CDN is loading (check Network tab)
3. Ensure API endpoints return data
4. Try refreshing the page

## 📱 Browser Support

| Browser | Version | PWA Install | Offline Sync |
|---------|---------|-------------|--------------|
| Chrome | 80+ | ✅ | ✅ |
| Edge | 80+ | ✅ | ✅ |
| Firefox | 90+ | ✅ | ⚠️ Partial |
| Safari (iOS) | 14+ | ✅ | ⚠️ Fallback |
| Safari (macOS) | 14+ | ✅ | ⚠️ Fallback |

**Note**: Background Sync API has limited support. Fallback periodic sync implemented for all browsers.

## 🔐 Security Considerations

For production use:
1. **CORS**: Restrict `allow_origins` to your domain
2. **HTTPS**: Always use HTTPS (Render provides free SSL)
3. **Input Validation**: All inputs validated on backend
4. **SQL Injection**: Protected by SQLModel/SQLAlchemy
5. **Authentication**: Not implemented (add if needed for multi-user)

## 🚀 Performance

- **First Load**: ~500ms (cached after first visit)
- **Offline Load**: <100ms (service worker cache)
- **Add Expense**: <10 seconds user time
- **API Response**: <50ms (local SQLite)
- **Chart Load**: ~200ms (client-side rendering)

## 📈 Future Enhancements

Potential improvements:
- [ ] Multi-user support with authentication
- [ ] Recurring expenses
- [ ] Budget tracking & alerts
- [ ] Export to CSV/PDF
- [ ] Receipt photo upload
- [ ] Currency conversion
- [ ] Split expenses between people
- [ ] Push notifications
- [ ] Dark mode
- [ ] Advanced filters & search

## 🤝 Contributing

This is a complete, runnable reference implementation. To modify:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test locally with `./run_local.sh`
5. Submit a pull request

## 📄 License

MIT License - See [LICENSE](LICENSE) file for details.

## 💡 Tips & Best Practices

### Development
- Use `--reload` flag for auto-restart on code changes
- Check browser console for JavaScript errors
- Use DevTools → Application tab to inspect IndexedDB and Service Worker
- Test offline mode frequently during development

### Production
- Monitor Render logs for errors
- Set up uptime monitoring (e.g., UptimeRobot)
- Regular database backups (download from Render disk)
- Consider upgrading to paid plan for better performance

### Data Management
- **Backup**: Download `/data/expenses.db` from Render disk
- **Restore**: Upload db file to `/data` mount point
- **Migration**: If changing schema, create migration script
- **Export**: Use API endpoints to export data as JSON

## 📞 Support

For issues or questions:
1. Check this README first
2. Check browser console for errors
3. Review Render logs
4. Test locally to isolate issue
5. Check API docs at `/docs` endpoint

## 🎉 Quick Start Checklist

- [ ] Clone repository
- [ ] Run `chmod +x run_local.sh`
- [ ] Run `./run_local.sh`
- [ ] Open http://localhost:8000
- [ ] Seed database: `curl -X POST http://localhost:8000/api/seed`
- [ ] Add a test expense
- [ ] Test offline mode
- [ ] Deploy to Render
- [ ] Set up persistent disk
- [ ] Set DATABASE_URL env var
- [ ] Seed production database
- [ ] Test PWA install on mobile

---

**Built with ❤️ for offline-first expense tracking**

*Version 1.0.0 - January 2026*

# personal-expense-tracker
