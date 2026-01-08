# 🚀 QUICK START GUIDE

## Three Commands to Run Locally

After navigating to the project directory:

### 1. Make the script executable (one-time)
```bash
chmod +x run_local.sh
```

### 2. Run the application
```bash
./run_local.sh
```

This will:
- Create a virtual environment
- Install all Python dependencies
- Set up the database
- Start the server on port 8000

### 3. Open in your browser
```
http://localhost:8000
```

### 4. (Optional) Seed the database with sample data
Open a new terminal and run:
```bash
curl -X POST http://localhost:8000/api/seed
```

## ✅ That's it! Your app is running.

---

## 📱 Render Deploy Checklist

Copy-paste this into your Render setup:

### Service Configuration
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
- **Runtime**: Python 3

### Disk Configuration
1. **Add Disk**
   - Name: `expense-data`
   - Mount Path: `/data`
   - Size: 1 GB

### Environment Variables
| Key | Value |
|-----|-------|
| `DATABASE_URL` | `sqlite:////data/expenses.db` |

### Post-Deploy
```bash
# Seed production database
curl -X POST https://your-app.onrender.com/api/seed
```

---

## 🎯 Test Offline Mode

1. Open http://localhost:8000
2. Open DevTools (F12)
3. Go to Network tab → Check "Offline"
4. Add an expense → Should save locally
5. Uncheck "Offline"
6. Go to Settings → Click "Sync Now"
7. Expense syncs to server!

---

## 📂 Project Structure

```
expense_tracker/
├── backend/               # FastAPI backend
│   ├── main.py           # API routes + static serving
│   ├── models.py         # Database models
│   ├── database.py       # DB connection
│   └── seed.py           # Seed script
├── frontend/             # PWA frontend
│   ├── index.html        # Single-page app
│   ├── app.js            # Main JavaScript
│   ├── styles.css        # Responsive CSS
│   ├── manifest.json     # PWA manifest
│   └── service-worker.js # Offline support
├── requirements.txt      # Python deps
├── Dockerfile           # Docker config
├── Procfile             # Render start cmd
├── run_local.sh         # Local run script
└── README.md            # Full documentation
```

---

## 🔗 Important URLs

When running locally:
- **App**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Seed Endpoint**: http://localhost:8000/api/seed
- **Health Check**: http://localhost:8000/api/health

---

## 🆘 Quick Troubleshooting

**Port 8000 already in use?**
```bash
# Find process using port 8000
lsof -i :8000
# Kill it
kill -9 <PID>
```

**Module not found error?**
```bash
# Make sure virtual environment is activated
source venv/bin/activate
# Reinstall dependencies
pip install -r requirements.txt
```

**Database errors?**
```bash
# Delete old database and restart
rm expenses.db
./run_local.sh
```

---

**Need more help? See the full README.md**

