"""
FastAPI main application
Serves both API and frontend static files
"""
import os
from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, select, func, and_
import logging

from backend.database import create_db_and_tables, get_session
from backend.models import (
    Category1, Category2, Expense,
    Category1Create, Category1Update,
    Category2Create, Category2Update,
    ExpenseCreate, ExpenseUpdate
)
from backend.seed import seed_database

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Expense Tracker API",
    description="Backend API for Expense Tracker PWA",
    version="1.0.0"
)

# CORS configuration for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this to your domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    """Initialize database on startup"""
    logger.info("Starting up application...")
    logger.info(f"Database URL: {os.getenv('DATABASE_URL', 'sqlite:///./expenses.db')}")
    create_db_and_tables()
    logger.info("Database tables created/verified")


# ============== CATEGORY ENDPOINTS ==============

@app.get("/api/categories")
def get_categories(session: Session = Depends(get_session)):
    """Get all C1 categories"""
    categories = session.exec(select(Category1).order_by(Category1.name)).all()
    return categories


@app.post("/api/categories", response_model=Category1)
def create_category(category: Category1Create, session: Session = Depends(get_session)):
    """Create new C1 category"""
    # Check if name already exists
    existing = session.exec(select(Category1).where(Category1.name == category.name)).first()
    if existing:
        raise HTTPException(status_code=400, detail="Category name already exists")
    
    db_category = Category1(name=category.name, active=True)
    session.add(db_category)
    session.commit()
    session.refresh(db_category)
    logger.info(f"Created C1 category: {db_category.name}")
    return db_category


@app.put("/api/categories/{category_id}", response_model=Category1)
def update_category(
    category_id: int,
    category_update: Category1Update,
    session: Session = Depends(get_session)
):
    """Update C1 category"""
    db_category = session.get(Category1, category_id)
    if not db_category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    if category_update.name is not None:
        db_category.name = category_update.name
    if category_update.active is not None:
        db_category.active = category_update.active
    
    session.add(db_category)
    session.commit()
    session.refresh(db_category)
    logger.info(f"Updated C1 category: {db_category.name}")
    return db_category


@app.get("/api/categories/{c1_id}/c2")
def get_c2_categories(c1_id: int, session: Session = Depends(get_session)):
    """Get all C2 subcategories for a given C1"""
    # Verify C1 exists
    c1 = session.get(Category1, c1_id)
    if not c1:
        raise HTTPException(status_code=404, detail="C1 category not found")
    
    c2_list = session.exec(
        select(Category2).where(Category2.c1_id == c1_id).order_by(Category2.name)
    ).all()
    return c2_list


@app.post("/api/categories/{c1_id}/c2", response_model=Category2)
def create_c2_category(
    c1_id: int,
    category: Category2Create,
    session: Session = Depends(get_session)
):
    """Create new C2 subcategory under C1"""
    # Verify C1 exists
    c1 = session.get(Category1, c1_id)
    if not c1:
        raise HTTPException(status_code=404, detail="C1 category not found")
    
    # Check if C2 name already exists under this C1
    existing = session.exec(
        select(Category2).where(
            and_(Category2.c1_id == c1_id, Category2.name == category.name)
        )
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="C2 name already exists under this C1")
    
    db_category = Category2(name=category.name, c1_id=c1_id, active=True)
    session.add(db_category)
    session.commit()
    session.refresh(db_category)
    logger.info(f"Created C2 category: {db_category.name} under C1: {c1.name}")
    return db_category


@app.put("/api/categories/c2/{c2_id}", response_model=Category2)
def update_c2_category(
    c2_id: int,
    category_update: Category2Update,
    session: Session = Depends(get_session)
):
    """Update C2 subcategory"""
    db_category = session.get(Category2, c2_id)
    if not db_category:
        raise HTTPException(status_code=404, detail="C2 category not found")
    
    if category_update.name is not None:
        db_category.name = category_update.name
    if category_update.active is not None:
        db_category.active = category_update.active
    
    session.add(db_category)
    session.commit()
    session.refresh(db_category)
    logger.info(f"Updated C2 category: {db_category.name}")
    return db_category


# ============== EXPENSE ENDPOINTS ==============

@app.get("/api/expenses")
def get_expenses(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=100000),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session)
):
    """
    Get expenses with optional filtering
    Excludes soft-deleted expenses
    """
    query = select(Expense).where(Expense.deleted == False)
    
    # Apply date filters if provided
    if start_date:
        try:
            start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            query = query.where(Expense.date >= start_dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid start_date format")
    
    if end_date:
        try:
            end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            query = query.where(Expense.date <= end_dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid end_date format")
    
    # Order by date descending (newest first)
    query = query.order_by(Expense.date.desc())
    
    # Apply pagination
    query = query.offset(offset).limit(limit)
    
    expenses = session.exec(query).all()
    
    # Get total count for pagination info
    count_query = select(func.count(Expense.id)).where(Expense.deleted == False)
    if start_date:
        count_query = count_query.where(Expense.date >= start_dt)
    if end_date:
        count_query = count_query.where(Expense.date <= end_dt)
    
    total = session.exec(count_query).one()
    
    return {
        "expenses": expenses,
        "total": total,
        "limit": limit,
        "offset": offset
    }


@app.post("/api/expenses", response_model=Expense)
def create_expense(expense: ExpenseCreate, session: Session = Depends(get_session)):
    """Create new expense"""
    # Verify C1 and C2 exist
    c1 = session.get(Category1, expense.c1_id)
    if not c1:
        raise HTTPException(status_code=404, detail="C1 category not found")
    
    c2 = session.get(Category2, expense.c2_id)
    if not c2:
        raise HTTPException(status_code=404, detail="C2 category not found")
    
    # Verify C2 belongs to C1
    if c2.c1_id != c1.id:
        raise HTTPException(status_code=400, detail="C2 does not belong to specified C1")
    
    db_expense = Expense(**expense.dict())
    session.add(db_expense)
    session.commit()
    session.refresh(db_expense)
    logger.info(f"Created expense: {db_expense.amount} on {db_expense.date}")
    return db_expense


@app.get("/api/expenses/top")
def get_top_expenses(
    limit: int = Query(10, ge=1, le=100),
    session: Session = Depends(get_session)
):
    """Get top N expenses by amount"""
    expenses = session.exec(
        select(Expense)
        .where(Expense.deleted == False)
        .order_by(Expense.amount.desc())
        .limit(limit)
    ).all()
    return expenses


@app.get("/api/expenses/{expense_id}", response_model=Expense)
def get_expense(expense_id: int, session: Session = Depends(get_session)):
    """Get single expense by ID"""
    expense = session.get(Expense, expense_id)
    if not expense or expense.deleted:
        raise HTTPException(status_code=404, detail="Expense not found")
    return expense


@app.put("/api/expenses/{expense_id}", response_model=Expense)
def update_expense(
    expense_id: int,
    expense_update: ExpenseUpdate,
    session: Session = Depends(get_session)
):
    """Update expense"""
    db_expense = session.get(Expense, expense_id)
    if not db_expense or db_expense.deleted:
        raise HTTPException(status_code=404, detail="Expense not found")
    
    update_data = expense_update.dict(exclude_unset=True)
    
    # Verify categories if being updated
    if "c1_id" in update_data:
        c1 = session.get(Category1, update_data["c1_id"])
        if not c1:
            raise HTTPException(status_code=404, detail="C1 category not found")
    
    if "c2_id" in update_data:
        c2 = session.get(Category2, update_data["c2_id"])
        if not c2:
            raise HTTPException(status_code=404, detail="C2 category not found")
        
        # Verify C2 belongs to C1
        c1_id = update_data.get("c1_id", db_expense.c1_id)
        if c2.c1_id != c1_id:
            raise HTTPException(status_code=400, detail="C2 does not belong to specified C1")
    
    for key, value in update_data.items():
        setattr(db_expense, key, value)
    
    db_expense.updated_at = datetime.utcnow()
    session.add(db_expense)
    session.commit()
    session.refresh(db_expense)
    logger.info(f"Updated expense ID: {expense_id}")
    return db_expense


@app.delete("/api/expenses/{expense_id}")
def delete_expense(expense_id: int, session: Session = Depends(get_session)):
    """Soft delete expense"""
    db_expense = session.get(Expense, expense_id)
    if not db_expense or db_expense.deleted:
        raise HTTPException(status_code=404, detail="Expense not found")
    
    db_expense.deleted = True
    db_expense.updated_at = datetime.utcnow()
    session.add(db_expense)
    session.commit()
    logger.info(f"Deleted expense ID: {expense_id}")
    return {"message": "Expense deleted successfully", "id": expense_id}


# ============== INSIGHTS ENDPOINTS ==============

@app.get("/api/insights/monthly")
def get_monthly_insights(session: Session = Depends(get_session)):
    """
    Get monthly aggregated totals for last 12 months
    Returns: [{month: 'YYYY-MM', total: float}, ...]
    """
    # Calculate date 12 months ago
    twelve_months_ago = datetime.utcnow() - timedelta(days=365)
    
    expenses = session.exec(
        select(Expense)
        .where(and_(Expense.deleted == False, Expense.date >= twelve_months_ago))
        .order_by(Expense.date)
    ).all()
    
    # Group by month
    monthly_totals = {}
    for expense in expenses:
        month_key = expense.date.strftime('%Y-%m')
        if month_key not in monthly_totals:
            monthly_totals[month_key] = 0
        monthly_totals[month_key] += expense.amount
    
    # Convert to list and sort
    result = [{"month": month, "total": total} for month, total in monthly_totals.items()]
    result.sort(key=lambda x: x['month'])
    
    return result


@app.get("/api/insights/c1-distribution")
def get_c1_distribution(session: Session = Depends(get_session)):
    """
    Get total spending per C1 category
    Returns: [{c1_id: int, c1_name: str, total: float}, ...]
    """
    # Join expenses with C1 categories and aggregate
    query = (
        select(
            Expense.c1_id,
            Category1.name,
            func.sum(Expense.amount).label('total')
        )
        .join(Category1, Expense.c1_id == Category1.id)
        .where(Expense.deleted == False)
        .group_by(Expense.c1_id, Category1.name)
        .order_by(func.sum(Expense.amount).desc())
    )
    
    results = session.exec(query).all()
    
    return [
        {"c1_id": row[0], "c1_name": row[1], "total": float(row[2])}
        for row in results
    ]


@app.get("/api/insights/c2-breakdown")
def get_c2_breakdown(
    c1_id: Optional[int] = Query(None),
    session: Session = Depends(get_session)
):
    """
    Get total spending per C2 category
    Optionally filter by C1
    Returns: [{c2_id: int, c2_name: str, total: float}, ...]
    """
    query = (
        select(
            Expense.c2_id,
            Category2.name,
            func.sum(Expense.amount).label('total')
        )
        .join(Category2, Expense.c2_id == Category2.id)
        .where(Expense.deleted == False)
    )
    
    if c1_id is not None:
        query = query.where(Expense.c1_id == c1_id)
    
    query = query.group_by(Expense.c2_id, Category2.name).order_by(func.sum(Expense.amount).desc())
    
    results = session.exec(query).all()
    
    return [
        {"c2_id": row[0], "c2_name": row[1], "total": float(row[2])}
        for row in results
    ]


# ============== SEED ENDPOINT ==============

@app.post("/api/seed")
def seed_endpoint(session: Session = Depends(get_session)):
    """Seed database with canonical taxonomy and sample data"""
    try:
        result = seed_database()
        return result
    except Exception as e:
        logger.error(f"Error seeding database: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error seeding database: {str(e)}")


# ============== HEALTH CHECK ==============

@app.get("/api/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


# ============== SERVE FRONTEND STATIC FILES ==============

# Mount frontend directory for static files
frontend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")

# Serve static assets
app.mount("/static", StaticFiles(directory=frontend_path), name="static")


@app.get("/manifest.json")
def serve_manifest():
    """Serve manifest.json"""
    return FileResponse(os.path.join(frontend_path, "manifest.json"))


@app.get("/service-worker.js")
def serve_service_worker():
    """Serve service worker (must be at root)"""
    return FileResponse(os.path.join(frontend_path, "service-worker.js"))


@app.get("/")
def serve_frontend():
    """Serve frontend index.html"""
    return FileResponse(os.path.join(frontend_path, "index.html"))


@app.get("/{full_path:path}")
def serve_frontend_routes(full_path: str):
    """
    Catch-all route to serve frontend for client-side routing
    If file doesn't exist, serve index.html
    """
    file_path = os.path.join(frontend_path, full_path)
    if os.path.isfile(file_path):
        return FileResponse(file_path)
    return FileResponse(os.path.join(frontend_path, "index.html"))

