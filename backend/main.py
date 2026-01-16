"""
FastAPI main application - Multi-User with Google Sheets
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file FIRST
load_dotenv()

from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import FastAPI, Depends, HTTPException, Query, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, select, func, and_
import logging

from backend.database import create_db_and_tables, get_session
from backend.models import (
    User, Category1, Category2, Expense,
    UserResponse, LoginRequest,
    Category1Create, Category1Update,
    Category2Create, Category2Update,
    ExpenseCreate, ExpenseUpdate
)
from backend.auth import verify_google_token
from backend.google_sheets_service import google_sheets_service
from backend.user_mapping import user_sheet_mapping
from backend.hydration import hydrate_user_data, hydrate_all_users

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Get Google Client ID for frontend
GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID', '')

# Create FastAPI app
app = FastAPI(
    title="Expense Tracker API - Multi-User",
    description="Multi-user expense tracker with Google Sheets backend",
    version="2.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    """Initialize database and hydrate from Google Sheets"""
    logger.info("Starting up application...")
    logger.info(f"Database URL: {os.getenv('DATABASE_URL', 'sqlite:///./expenses.db')}")
    
    # Create tables
    create_db_and_tables()
    logger.info("Database tables created/verified")
    
    # Hydrate all users from Google Sheets
    logger.info("Starting data hydration from Google Sheets...")
    try:
        from backend.database import engine
        with Session(engine) as session:
            hydrate_all_users(session)
        logger.info("Data hydration completed successfully")
    except Exception as e:
        logger.error(f"Error during hydration: {e}")


# ============== AUTHENTICATION ENDPOINTS ==============

@app.post("/api/auth/google", response_model=UserResponse)
def google_login(login_req: LoginRequest, session: Session = Depends(get_session)):
    """
    Google OAuth login endpoint
    Verifies ID token, creates/updates user, initializes sheets if new user
    """
    # Debug logging
    logger.info(f"Login request received - has user_info: {hasattr(login_req, 'user_info')}, access_token: {bool(login_req.access_token)}")
    
    # Check if user_info is provided directly (OAuth flow with access token)
    if hasattr(login_req, 'user_info') and getattr(login_req, 'user_info', None):
        user_info = getattr(login_req, 'user_info')
        user_data = {
            'user_id': str(user_info.get('id', '')),
            'email': user_info.get('email', ''),
            'name': user_info.get('name', ''),
            'picture': user_info.get('picture', '')
        }
        logger.info(f"Using OAuth flow for user: {user_data['email']}")
    else:
        # Verify ID token (fallback)
        logger.info("Using ID token verification")
        user_data = verify_google_token(login_req.id_token)
        
        if not user_data:
            raise HTTPException(status_code=401, detail="Invalid token")
    
    user_id = user_data['user_id']
    email = user_data['email']
    name = user_data['name']
    picture = user_data.get('picture', '')
    access_token = login_req.access_token
    
    logger.info(f"Processing login for {email} - access_token present: {bool(access_token)}")
    
    # Check if user exists
    user = session.get(User, user_id)
    
    if user:
        # Existing user - update last login and token
        user.last_login = datetime.utcnow()
        if access_token:
            user.oauth_access_token = access_token
        session.add(user)
        session.commit()
        logger.info(f"User logged in: {email}")
    else:
        # New user - create sheets and user record
        logger.info(f"New user detected: {email}")
        
        # Get or create Google Sheets (with OAuth if token provided)
        sheet_ids = google_sheets_service.get_or_create_user_sheets(
            user_id, 
            email,
            oauth_access_token=access_token
        )
        
        # Create user record
        user = User(
            user_id=user_id,
            email=email,
            name=name,
            picture=picture,
            categories_sheet_id=sheet_ids['categories_sheet_id'],
            expenses_sheet_id=sheet_ids['expenses_sheet_id'],
            oauth_access_token=access_token
        )
        session.add(user)
        session.commit()
        
        # Store mapping
        user_sheet_mapping.set_user_sheets(
            user_id,
            sheet_ids['categories_sheet_id'],
            sheet_ids['expenses_sheet_id']
        )
        
        # Hydrate data from sheets (will load seeded categories)
        hydrate_user_data(session, user_id)
        
        logger.info(f"New user created and initialized: {email}")
    
    return UserResponse(
        user_id=user.user_id,
        email=user.email,
        name=user.name,
        picture=user.picture
    )


@app.get("/api/auth/me", response_model=UserResponse)
def get_current_user(user_id: str = Query(...), session: Session = Depends(get_session)):
    """
    Get current user info
    Frontend passes user_id from localStorage
    """
    user = session.get(User, user_id)
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return UserResponse(
        user_id=user.user_id,
        email=user.email,
        name=user.name,
        picture=user.picture
    )


@app.post("/api/auth/logout")
def logout():
    """
    Logout endpoint (client-side clears localStorage)
    """
    return {"message": "Logged out successfully"}


@app.post("/api/sync/hydrate")
def sync_hydrate(
    user_id: str = Depends(get_user_id_from_query),
    session: Session = Depends(get_session)
):
    """
    Manually trigger hydration from Google Sheets for the current user
    Useful after server restarts (e.g. Render free tier redeploys)
    """
    try:
        # Verify user exists
        user = session.get(User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        logger.info(f"Manual hydration requested for user: {user.email}")
        
        # Trigger hydration
        hydrate_user_data(session, user_id)
        
        logger.info(f"Manual hydration completed for user: {user.email}")
        
        return {
            "message": "Data refreshed successfully from Google Sheets",
            "user_id": user_id
        }
    except Exception as e:
        logger.error(f"Error during manual hydration for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Hydration failed: {str(e)}")


# ============== HELPER: Get User from Request ==============

def get_user_id_from_query(user_id: str = Query(...)) -> str:
    """
    Extract user_id from query parameter
    Used as dependency for all protected endpoints
    """
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID required")
    return user_id


# ============== CATEGORY ENDPOINTS ==============

@app.get("/api/categories")
def get_categories(
    user_id: str = Depends(get_user_id_from_query),
    session: Session = Depends(get_session)
):
    """Get all C1 categories for user"""
    categories = session.exec(
        select(Category1)
        .where(Category1.user_id == user_id)
        .order_by(Category1.name)
    ).all()
    return categories


@app.post("/api/categories", response_model=Category1)
def create_category(
    category: Category1Create,
    user_id: str = Depends(get_user_id_from_query),
    session: Session = Depends(get_session)
):
    """Create new C1 category"""
    # Check if name already exists for this user
    existing = session.exec(
        select(Category1).where(
            and_(Category1.user_id == user_id, Category1.name == category.name)
        )
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Category name already exists")
    
    db_category = Category1(user_id=user_id, name=category.name, active=True)
    session.add(db_category)
    session.commit()
    session.refresh(db_category)
    
    logger.info(f"Created C1 category: {db_category.name} for user {user_id}")
    
    # Sync to Google Sheets
    try:
        user = session.get(User, user_id)
        if user and user.categories_sheet_id != "local":
            # Note: C1 alone can't be added to sheets (needs C2)
            # We'll add a placeholder C2 or just log
            logger.info(f"C1 created but needs C2 to sync to Sheets")
    except Exception as e:
        logger.error(f"Error syncing C1 to sheets: {e}")
    
    return db_category


@app.get("/api/categories/{c1_id}/c2")
def get_c2_categories(
    c1_id: int,
    user_id: str = Depends(get_user_id_from_query),
    session: Session = Depends(get_session)
):
    """Get all C2 subcategories for a given C1"""
    # Verify C1 belongs to user
    c1 = session.get(Category1, c1_id)
    if not c1 or c1.user_id != user_id:
        raise HTTPException(status_code=404, detail="C1 category not found")
    
    c2_list = session.exec(
        select(Category2)
        .where(and_(Category2.c1_id == c1_id, Category2.user_id == user_id))
        .order_by(Category2.name)
    ).all()
    return c2_list


@app.post("/api/categories/{c1_id}/c2", response_model=Category2)
def create_c2_category(
    c1_id: int,
    category: Category2Create,
    user_id: str = Depends(get_user_id_from_query),
    session: Session = Depends(get_session)
):
    """Create new C2 subcategory under C1"""
    # Verify C1 belongs to user
    c1 = session.get(Category1, c1_id)
    if not c1 or c1.user_id != user_id:
        raise HTTPException(status_code=404, detail="C1 category not found")
    
    # Check for duplicate C2 under this C1
    existing = session.exec(
        select(Category2).where(
            Category2.user_id == user_id,
            Category2.c1_id == c1_id,
            Category2.name == category.name
        )
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Category '{category.name}' already exists under '{c1.name}'")
    
    db_category = Category2(
        user_id=user_id,
        name=category.name,
        c1_id=c1_id,
        c1_name=c1.name,
        active=True
    )
    session.add(db_category)
    session.commit()
    session.refresh(db_category)
    
    logger.info(f"Created C2 category: {db_category.name} for user {user_id}")
    
    # Sync to Google Sheets
    try:
        user = session.get(User, user_id)
        if user and user.categories_sheet_id != "local":
            # Append new category to Google Sheets
            google_sheets_service.append_category(
                user.categories_sheet_id,
                {
                    "c1_name": c1.name,
                    "c2_name": db_category.name,
                    "is_active": "true"
                }
            )
            logger.info(f"Synced new C2 to Google Sheets: {c1.name}/{db_category.name}")
    except Exception as e:
        logger.error(f"Error syncing C2 to sheets: {e}")
    
    return db_category


@app.put("/api/categories/c2/{c2_id}", response_model=Category2)
def update_c2_category(
    c2_id: int,
    category_update: Category2Update,
    user_id: str = Depends(get_user_id_from_query),
    session: Session = Depends(get_session)
):
    """Update C2 subcategory"""
    db_category = session.get(Category2, c2_id)
    if not db_category or db_category.user_id != user_id:
        raise HTTPException(status_code=404, detail="C2 category not found")
    
    if category_update.name is not None:
        db_category.name = category_update.name
    if category_update.active is not None:
        db_category.active = category_update.active
        
        # Sync to Google Sheets
        user = session.get(User, user_id)
        if user:
            try:
                google_sheets_service.update_category_status(
                    user.categories_sheet_id,
                    db_category.c1_name,
                    db_category.name,
                    db_category.active
                )
            except Exception as e:
                logger.error(f"Failed to sync category to Sheets: {e}")
    
    session.add(db_category)
    session.commit()
    session.refresh(db_category)
    
    logger.info(f"Updated C2 category: {db_category.name} for user {user_id}")
    return db_category


# ============== EXPENSE ENDPOINTS ==============

@app.get("/api/expenses")
def get_expenses(
    user_id: str = Depends(get_user_id_from_query),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=100000),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session)
):
    """Get expenses for user with optional filtering"""
    query = select(Expense).where(
        and_(Expense.user_id == user_id, Expense.deleted == False)
    )
    
    # Apply date filters
    if start_date:
        try:
            start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            query = query.where(Expense.date >= start_dt)
        except ValueError:
            pass
    
    if end_date:
        try:
            end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            query = query.where(Expense.date <= end_dt)
        except ValueError:
            pass
    
    query = query.order_by(Expense.date.desc()).offset(offset).limit(limit)
    
    expenses = session.exec(query).all()
    
    # Get total count
    count_query = select(func.count(Expense.id)).where(
        and_(Expense.user_id == user_id, Expense.deleted == False)
    )
    total = session.exec(count_query).one()
    
    return {
        "expenses": expenses,
        "total": total,
        "limit": limit,
        "offset": offset
    }


@app.post("/api/expenses", response_model=Expense)
def create_expense(
    expense: ExpenseCreate,
    user_id: str = Depends(get_user_id_from_query),
    session: Session = Depends(get_session)
):
    """Create new expense"""
    # Verify categories belong to user
    c1 = session.get(Category1, expense.c1_id)
    if not c1 or c1.user_id != user_id:
        raise HTTPException(status_code=404, detail="C1 category not found")
    
    c2 = session.get(Category2, expense.c2_id)
    if not c2 or c2.user_id != user_id:
        raise HTTPException(status_code=404, detail="C2 category not found")
    
    if c2.c1_id != c1.id:
        raise HTTPException(status_code=400, detail="C2 does not belong to C1")
    
    db_expense = Expense(
        user_id=user_id,
        date=expense.date,
        amount=expense.amount,
        c1_id=c1.id,
        c2_id=c2.id,
        c1_name=c1.name,
        c2_name=c2.name,
        payment_mode=expense.payment_mode,
        notes=expense.notes,
        person=expense.person,
        need_vs_want=expense.need_vs_want,
        deleted=False
    )
    session.add(db_expense)
    session.commit()
    session.refresh(db_expense)
    
    # Sync to Google Sheets
    user = session.get(User, user_id)
    if user:
        try:
            google_sheets_service.append_expense(
                user.expenses_sheet_id,
                {
                    'date': db_expense.date.isoformat(),
                    'amount': db_expense.amount,
                    'c1_name': db_expense.c1_name,
                    'c2_name': db_expense.c2_name,
                    'payment_mode': db_expense.payment_mode,
                    'notes': db_expense.notes or '',
                    'person': db_expense.person or '',
                    'need_vs_want': db_expense.need_vs_want or '',
                    'created_at': db_expense.created_at.isoformat()
                }
            )
        except Exception as e:
            logger.error(f"Failed to sync expense to Sheets: {e}")
    
    logger.info(f"Created expense for user {user_id}: {db_expense.amount}")
    return db_expense


@app.get("/api/expenses/top")
def get_top_expenses(
    user_id: str = Depends(get_user_id_from_query),
    limit: int = Query(10, ge=1, le=100),
    session: Session = Depends(get_session)
):
    """Get top N expenses by amount for user"""
    expenses = session.exec(
        select(Expense)
        .where(and_(Expense.user_id == user_id, Expense.deleted == False))
        .order_by(Expense.amount.desc())
        .limit(limit)
    ).all()
    return expenses


@app.delete("/api/expenses/{expense_id}")
def delete_expense(
    expense_id: int,
    user_id: str = Depends(get_user_id_from_query),
    session: Session = Depends(get_session)
):
    """Soft delete expense"""
    db_expense = session.get(Expense, expense_id)
    if not db_expense or db_expense.user_id != user_id or db_expense.deleted:
        raise HTTPException(status_code=404, detail="Expense not found")
    
    # Mark as deleted in DB
    db_expense.deleted = True
    db_expense.updated_at = datetime.utcnow()
    session.add(db_expense)
    session.commit()
    
    logger.info(f"Deleted expense ID: {expense_id} for user {user_id}")
    
    # Sync to Google Sheets
    try:
        user = session.get(User, user_id)
        if user and user.expenses_sheet_id != "local":
            # Mark as deleted in Sheets (find by date+amount+c2)
            google_sheets_service.mark_expense_deleted(
                user.expenses_sheet_id,
                db_expense.date.strftime("%Y-%m-%dT%H:%M") if db_expense.date else "",
                db_expense.amount,
                db_expense.c2_name,
                db_expense.created_at.isoformat()
            )
            logger.info(f"Synced expense deletion to Google Sheets")
    except Exception as e:
        logger.error(f"Error syncing expense deletion to sheets: {e}")
    
    return {"message": "Expense deleted successfully", "id": expense_id}


# ============== INSIGHTS ENDPOINTS ==============

@app.get("/api/insights/monthly")
def get_monthly_insights(
    user_id: str = Depends(get_user_id_from_query),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    session: Session = Depends(get_session)
):
    """Get monthly aggregated totals for user"""
    query = select(Expense).where(
        and_(Expense.user_id == user_id, Expense.deleted == False)
    )
    
    if start_date:
        try:
            start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            query = query.where(Expense.date >= start_dt)
        except ValueError:
            pass
    else:
        twelve_months_ago = datetime.utcnow() - timedelta(days=365)
        query = query.where(Expense.date >= twelve_months_ago)
    
    if end_date:
        try:
            end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            query = query.where(Expense.date <= end_dt)
        except ValueError:
            pass
    
    expenses = session.exec(query.order_by(Expense.date)).all()
    
    monthly_totals = {}
    for expense in expenses:
        month_key = expense.date.strftime('%Y-%m')
        if month_key not in monthly_totals:
            monthly_totals[month_key] = 0
        monthly_totals[month_key] += expense.amount
    
    result = [{"month": month, "total": total} for month, total in monthly_totals.items()]
    result.sort(key=lambda x: x['month'])
    
    return result


@app.get("/api/insights/c1-distribution")
def get_c1_distribution(
    user_id: str = Depends(get_user_id_from_query),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    session: Session = Depends(get_session)
):
    """Get total spending per C1 category for user"""
    query = (
        select(
            Expense.c1_id,
            Category1.name,
            func.sum(Expense.amount).label('total')
        )
        .join(Category1, Expense.c1_id == Category1.id)
        .where(and_(Expense.user_id == user_id, Expense.deleted == False))
    )
    
    if start_date:
        try:
            start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            query = query.where(Expense.date >= start_dt)
        except ValueError:
            pass
    
    if end_date:
        try:
            end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            query = query.where(Expense.date <= end_dt)
        except ValueError:
            pass
    
    query = query.group_by(Expense.c1_id, Category1.name).order_by(func.sum(Expense.amount).desc())
    
    results = session.exec(query).all()
    
    return [
        {"c1_id": row[0], "c1_name": row[1], "total": float(row[2])}
        for row in results
    ]


@app.get("/api/insights/c2-breakdown")
def get_c2_breakdown(
    user_id: str = Depends(get_user_id_from_query),
    c1_id: Optional[int] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    session: Session = Depends(get_session)
):
    """Get total spending per C2 category for user"""
    query = (
        select(
            Expense.c2_id,
            Category2.name,
            func.sum(Expense.amount).label('total')
        )
        .join(Category2, Expense.c2_id == Category2.id)
        .where(and_(Expense.user_id == user_id, Expense.deleted == False))
    )
    
    if c1_id is not None:
        query = query.where(Expense.c1_id == c1_id)
    
    if start_date:
        try:
            start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            query = query.where(Expense.date >= start_dt)
        except ValueError:
            pass
    
    if end_date:
        try:
            end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            query = query.where(Expense.date <= end_dt)
        except ValueError:
            pass
    
    query = query.group_by(Expense.c2_id, Category2.name).order_by(func.sum(Expense.amount).desc())
    
    results = session.exec(query).all()
    
    return [
        {"c2_id": row[0], "c2_name": row[1], "total": float(row[2])}
        for row in results
    ]


# ============== HEALTH CHECK ==============

@app.get("/api/health")
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "google_sheets": google_sheets_service.is_available()
    }


# ============== SERVE FRONTEND ==============

frontend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")

# Serve static assets
app.mount("/static", StaticFiles(directory=frontend_path), name="static")


@app.get("/manifest.json")
def serve_manifest():
    """Serve manifest.json"""
    return FileResponse(os.path.join(frontend_path, "manifest.json"))


@app.get("/service-worker.js")
def serve_service_worker():
    """Serve service worker"""
    return FileResponse(os.path.join(frontend_path, "service-worker.js"))


@app.get("/")
def serve_login():
    """Serve login page (landing page)"""
    # Replace placeholder with actual Google Client ID
    with open(os.path.join(frontend_path, "login.html"), 'r') as f:
        html = f.read()
    html = html.replace('{{GOOGLE_CLIENT_ID}}', GOOGLE_CLIENT_ID)
    return HTMLResponse(content=html)


@app.get("/app")
def serve_app():
    """Serve main app (protected - frontend checks auth)"""
    return FileResponse(os.path.join(frontend_path, "index.html"))
