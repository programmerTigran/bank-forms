from sqlalchemy import ForeignKey, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from db import get_connection


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


engine = create_engine("postgresql+psycopg://", creator=get_connection)