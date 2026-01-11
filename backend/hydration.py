"""
Data Hydration Service
Rebuilds local DB from Google Sheets on app startup
"""
from datetime import datetime
from sqlmodel import Session, select
from backend.models import User, Category1, Category2, Expense
from backend.google_sheets_service import google_sheets_service
from backend.user_mapping import user_sheet_mapping
import logging

logger = logging.getLogger(__name__)


def hydrate_user_data(session: Session, user_id: str):
    """
    Hydrate local DB with user's data from Google Sheets
    Called on app startup and when user logs in
    """
    logger.info(f"Hydrating data for user {user_id}")
    
    # Get user's sheet IDs
    user = session.get(User, user_id)
    if not user:
        logger.error(f"User {user_id} not found in DB")
        return
    
    categories_sheet_id = user.categories_sheet_id
    expenses_sheet_id = user.expenses_sheet_id
    
    # Skip if using local mode
    if categories_sheet_id == "local":
        logger.info("Local mode - skipping Google Sheets hydration")
        return
    
    # Clear existing data for this user (local DB is cache)
    session.exec(select(Category1).where(Category1.user_id == user_id)).all()
    session.exec(select(Category2).where(Category2.user_id == user_id)).all()
    session.exec(select(Expense).where(Expense.user_id == user_id)).all()
    
    # Delete from DB
    session.query(Category1).filter(Category1.user_id == user_id).delete()
    session.query(Category2).filter(Category2.user_id == user_id).delete()
    session.query(Expense).filter(Expense.user_id == user_id).delete()
    session.commit()
    
    logger.info(f"Cleared existing cache for user {user_id}")
    
    # Load categories from Sheets
    try:
        categories_data = google_sheets_service.load_categories(categories_sheet_id)
        logger.info(f"Loaded {len(categories_data)} rows from categories sheet")
        
        # Debug: show first row
        if categories_data:
            logger.info(f"First row: {categories_data[0]}")
        
        # Build C1 map
        c1_map = {}  # c1_name -> Category1 object
        
        for row in categories_data:
            c1_name = row.get('c1_name', '')
            c2_name = row.get('c2_name', '')
            # Parse is_active (handle string TRUE/FALSE from Sheets)
            is_active_str = str(row.get('is_active', 'TRUE')).upper()
            is_active = is_active_str == 'TRUE'
            
            if not c1_name or not c2_name:
                continue
            
            # Create or get C1
            if c1_name not in c1_map:
                c1 = Category1(
                    user_id=user_id,
                    name=c1_name,
                    active=True  # C1 is active if any C2 is active
                )
                session.add(c1)
                session.flush()  # Get ID
                c1_map[c1_name] = c1
            else:
                c1 = c1_map[c1_name]
            
            # Create C2
            c2 = Category2(
                user_id=user_id,
                name=c2_name,
                c1_id=c1.id,
                c1_name=c1_name,
                active=is_active
            )
            session.add(c2)
        
        session.commit()
        logger.info(f"Hydrated {len(c1_map)} C1 and {len(categories_data)} C2 categories")
        
    except Exception as e:
        logger.error(f"Error hydrating categories: {e}")
        session.rollback()
    
    # Load expenses from Sheets
    try:
        expenses_data = google_sheets_service.load_expenses(expenses_sheet_id)
        
        # Get category mappings for ID lookup
        c1_lookup = {}
        c2_lookup = {}
        
        for c1 in session.exec(select(Category1).where(Category1.user_id == user_id)).all():
            c1_lookup[c1.name] = c1
        
        for c2 in session.exec(select(Category2).where(Category2.user_id == user_id)).all():
            c2_lookup[f"{c2.c1_name}/{c2.name}"] = c2
        
        for row in expenses_data:
            try:
                c1_name = row.get('c1_name', '')
                c2_name = row.get('c2_name', '')
                
                if not c1_name or not c2_name:
                    continue
                
                c1 = c1_lookup.get(c1_name)
                c2 = c2_lookup.get(f"{c1_name}/{c2_name}")
                
                if not c1 or not c2:
                    logger.warning(f"Category not found for expense: {c1_name}/{c2_name}")
                    continue
                
                # Parse date
                date_str = row.get('date', '')
                try:
                    expense_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                except:
                    expense_date = datetime.utcnow()
                
                # Parse deleted status (handle string TRUE/FALSE from Sheets)
                deleted_str = str(row.get('deleted', 'FALSE')).upper()
                is_deleted = deleted_str == 'TRUE'
                
                expense = Expense(
                    user_id=user_id,
                    date=expense_date,
                    amount=float(row.get('amount', 0)),
                    c1_id=c1.id,
                    c2_id=c2.id,
                    c1_name=c1_name,
                    c2_name=c2_name,
                    payment_mode=row.get('payment_mode', 'Cash'),
                    notes=row.get('notes'),
                    person=row.get('person'),
                    need_vs_want=row.get('need_vs_want'),
                    deleted=is_deleted
                )
                session.add(expense)
                
            except Exception as e:
                logger.error(f"Error processing expense row: {e}")
                continue
        
        session.commit()
        logger.info(f"Hydrated {len(expenses_data)} expenses")
        
    except Exception as e:
        logger.error(f"Error hydrating expenses: {e}")
        session.rollback()
    
    logger.info(f"Hydration complete for user {user_id}")


def hydrate_all_users(session: Session):
    """
    Hydrate data for all users on app startup
    Called when server starts/restarts
    """
    logger.info("Starting full hydration for all users")
    
    users = session.exec(select(User)).all()
    
    for user in users:
        try:
            hydrate_user_data(session, user.user_id)
        except Exception as e:
            logger.error(f"Error hydrating user {user.user_id}: {e}")
    
    logger.info(f"Completed hydration for {len(users)} users")
