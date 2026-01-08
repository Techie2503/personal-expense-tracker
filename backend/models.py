"""
Database models for Expense Tracker
Uses SQLModel (built on SQLAlchemy + Pydantic)
"""
from typing import Optional
from datetime import datetime
from sqlmodel import Field, SQLModel, create_engine, Session, select
from sqlalchemy import Column, DateTime, func


class Category1(SQLModel, table=True):
    """Primary category (C1)"""
    __tablename__ = "category1"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)
    active: bool = Field(default=True)
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )


class Category2(SQLModel, table=True):
    """Secondary category (C2) - subcategory under C1"""
    __tablename__ = "category2"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    c1_id: int = Field(foreign_key="category1.id")
    active: bool = Field(default=True)
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )


class Expense(SQLModel, table=True):
    """Expense entry"""
    __tablename__ = "expenses"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    date: datetime = Field(index=True)
    amount: float = Field(ge=0)
    c1_id: int = Field(foreign_key="category1.id", index=True)
    c2_id: int = Field(foreign_key="category2.id", index=True)
    payment_mode: str = Field(default="Cash")  # Cash, Card, UPI, etc.
    notes: Optional[str] = Field(default=None)
    person: Optional[str] = Field(default=None)  # Who made the expense
    need_vs_want: Optional[str] = Field(default=None)  # Need, Want, Neutral
    deleted: bool = Field(default=False)  # Soft delete
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
    )


# Pydantic models for API requests/responses
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

