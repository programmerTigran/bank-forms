"""
models.py
SQLAlchemy models (companies, customers, document_templates) and the engine.
Used by form_store.py, which reads the form recipes through the ORM.
"""

# ============================================================
# 1. IMPORTS
# ============================================================

from sqlalchemy import ForeignKey, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB

from db import new_connection

# ============================================================
# 2. MODELS
# ============================================================

class Base(DeclarativeBase):
    pass

class Company(Base):
    __tablename__ = "companies"
    company_id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    logo: Mapped[str | None]
    sort_order: Mapped[int]
    customers: Mapped[list["Customer"]] = relationship(
        back_populates="company", order_by="Customer.customer_id"
    )

class Customer(Base):
    __tablename__ = "customers"
    customer_id: Mapped[int] = mapped_column(primary_key=True)
    first_name: Mapped[str]
    surname: Mapped[str]
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.company_id"))
    company: Mapped["Company | None"] = relationship(back_populates="customers")

class DocumentTemplate(Base):
    __tablename__ = "document_templates"
    name: Mapped[str] = mapped_column(primary_key=True)
    version: Mapped[int] = mapped_column(primary_key=True)
    definition: Mapped[dict] = mapped_column(JSONB)

# ============================================================
# 3. ENGINE
# ============================================================

# SQLAlchemy keeps its own pool, so it gets plain connections.
engine = create_engine("postgresql+psycopg://", creator=new_connection, pool_pre_ping=True)
