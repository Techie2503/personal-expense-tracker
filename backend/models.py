"""
Database models for Expense Tracker (Multi-User with Google Sheets)
Uses SQLModel (built on SQLAlchemy + Pydantic)
Local DB is a TEMPORARY cache - Google Sheets is source of truth
"""
from typing import Optional
from datetime import datetime
from sqlmodel import Field, SQLModel, create_engine, Session, select
from sqlalchemy import Column, DateTime, func


class User(SQLModel, table=True):
    """User account linked to Google"""
    __tablename__ = "users"
    
    user_id: str = Field(primary_key=True)  # Google sub (user ID)
    email: str = Field(index=True, unique=True)
    name: str
    picture: Optional[str] = None
    categories_sheet_id: str
    expenses_sheet_id: str
    income_categories_sheet_id: Optional[str] = None  # Income categories sheet
    cashflows_sheet_id: Optional[str] = None  # Cashflows (inflows) sheet
    oauth_access_token: Optional[str] = None  # For creating sheets in user's Drive
    oauth_refresh_token: Optional[str] = None  # For refreshing access
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )
    last_login: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
    )


class Category1(SQLModel, table=True):
    """Primary category (C1) - per user"""
    __tablename__ = "category1"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str = Field(foreign_key="users.user_id", index=True)
    name: str = Field(index=True)
    active: bool = Field(default=True)
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )


class Category2(SQLModel, table=True):
    """Secondary category (C2) - subcategory under C1"""
    __tablename__ = "category2"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str = Field(foreign_key="users.user_id", index=True)
    name: str = Field(index=True)
    c1_id: int = Field(foreign_key="category1.id")
    c1_name: str = Field(index=True)  # Denormalized for Sheets compatibility
    active: bool = Field(default=True)
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )


class Expense(SQLModel, table=True):
    """Expense entry - per user"""
    __tablename__ = "expenses"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str = Field(foreign_key="users.user_id", index=True)
    date: datetime = Field(index=True)
    amount: float = Field(ge=0)
    c1_id: int = Field(foreign_key="category1.id", index=True)
    c2_id: int = Field(foreign_key="category2.id", index=True)
    c1_name: str  # Denormalized for Sheets compatibility
    c2_name: str  # Denormalized for Sheets compatibility
    payment_mode: str = Field(default="Cash")
    notes: Optional[str] = Field(default=None)
    person: Optional[str] = Field(default=None)
    need_vs_want: Optional[str] = Field(default=None)
    deleted: bool = Field(default=False)
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
    )


class IncomeCategory(SQLModel, table=True):
    """Income category (C2 only - no C1 hierarchy)"""
    __tablename__ = "income_categories"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str = Field(foreign_key="users.user_id", index=True)
    name: str = Field(index=True)  # c2_name in sheets
    active: bool = Field(default=True)
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )


class Inflow(SQLModel, table=True):
    """Cash inflow (income) entry - per user"""
    __tablename__ = "inflows"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str = Field(foreign_key="users.user_id", index=True)
    sheet_id: str = Field(index=True)  # UUID from Google Sheets
    date: datetime = Field(index=True)
    amount: float = Field(ge=0)
    category_id: int = Field(foreign_key="income_categories.id", index=True)
    category_name: str  # c2_name - denormalized for Sheets compatibility
    notes: Optional[str] = Field(default=None)
    deleted: bool = Field(default=False)
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
    )


# Pydantic models for API requests/responses
class UserResponse(SQLModel):
    user_id: str
    email: str
    name: str
    picture: Optional[str] = None


class LoginRequest(SQLModel):
    id_token: str = ""  # Google ID token (optional if user_info provided)
    access_token: Optional[str] = None  # OAuth access token for Drive access
    user_info: Optional[dict] = None  # User info from OAuth (id, email, name, picture)


class Category1Create(SQLModel):
    name: str


class Category1Update(SQLModel):
    name: Optional[str] = None
    active: Optional[bool] = None


class Category2Create(SQLModel):
    name: str


class Category2Update(SQLModel):
    name: Optional[str] = None
    active: Optional[bool] = None


class ExpenseCreate(SQLModel):
    date: datetime
    amount: float = Field(ge=0)
    c1_id: int
    c2_id: int
    payment_mode: str = "Cash"
    notes: Optional[str] = None
    person: Optional[str] = None
    need_vs_want: Optional[str] = None


class ExpenseUpdate(SQLModel):
    date: Optional[datetime] = None
    amount: Optional[float] = Field(default=None, ge=0)
    c1_id: Optional[int] = None
    c2_id: Optional[int] = None
    payment_mode: Optional[str] = None
    notes: Optional[str] = None
    person: Optional[str] = None
    need_vs_want: Optional[str] = None


class IncomeCategoryCreate(SQLModel):
    name: str


class IncomeCategoryUpdate(SQLModel):
    name: Optional[str] = None
    active: Optional[bool] = None


class InflowCreate(SQLModel):
    date: datetime
    amount: float = Field(ge=0)
    category_id: int
    notes: Optional[str] = None


class InflowUpdate(SQLModel):
    date: Optional[datetime] = None
    amount: Optional[float] = Field(default=None, ge=0)
    category_id: Optional[int] = None
    notes: Optional[str] = None

