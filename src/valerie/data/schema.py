"""SQLAlchemy schema for supplier data."""

from datetime import datetime
from sqlalchemy import (
    Column,
    String,
    Float,
    Integer,
    DateTime,
    ForeignKey,
    Index,
    Text,
)
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


class Supplier(Base):
    """Supplier entity."""

    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), unique=True, nullable=False, index=True)
    site = Column(String(255))
    total_orders = Column(Integer, default=0)
    total_amount = Column(Float, default=0.0)
    avg_order_value = Column(Float, default=0.0)
    first_order_date = Column(DateTime)
    last_order_date = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    items = relationship("SupplierItem", back_populates="supplier", lazy="dynamic")
    categories = relationship(
        "SupplierCategory", back_populates="supplier", lazy="dynamic"
    )

    def __repr__(self) -> str:
        return f"<Supplier(name='{self.name}', total_amount={self.total_amount})>"


class Category(Base):
    """Product category with 3-level hierarchy."""

    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(500), unique=True, nullable=False, index=True)
    level1 = Column(String(100), index=True)  # Controlled/Non-Controlled
    level2 = Column(String(200), index=True)  # Material/Service + Subcategory
    level3 = Column(String(200), index=True)  # Specific item type
    item_count = Column(Integer, default=0)
    total_amount = Column(Float, default=0.0)

    __table_args__ = (Index("ix_category_levels", "level1", "level2", "level3"),)

    def __repr__(self) -> str:
        return f"<Category(name='{self.name}')>"


class SupplierItem(Base):
    """Items/products provided by a supplier."""

    __tablename__ = "supplier_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    supplier_id = Column(
        Integer, ForeignKey("suppliers.id"), nullable=False, index=True
    )
    item_code = Column(String(100), index=True)
    description = Column(Text)
    supplier_item_code = Column(String(100))
    category_id = Column(Integer, ForeignKey("categories.id"), index=True)
    uom = Column(String(20), default="EA")
    avg_price = Column(Float, default=0.0)
    min_price = Column(Float, default=0.0)
    max_price = Column(Float, default=0.0)
    total_ordered_qty = Column(Float, default=0.0)
    total_ordered_amount = Column(Float, default=0.0)
    order_count = Column(Integer, default=0)
    last_order_date = Column(DateTime)

    supplier = relationship("Supplier", back_populates="items")
    category = relationship("Category")

    __table_args__ = (
        Index("ix_supplier_item", "supplier_id", "item_code"),
        Index("ix_item_description", "description"),
    )

    def __repr__(self) -> str:
        return f"<SupplierItem(code='{self.item_code}', supplier_id={self.supplier_id})>"


class SupplierCategory(Base):
    """Junction table: suppliers and their categories with aggregates."""

    __tablename__ = "supplier_categories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    item_count = Column(Integer, default=0)
    total_amount = Column(Float, default=0.0)

    supplier = relationship("Supplier", back_populates="categories")
    category = relationship("Category")

    __table_args__ = (
        Index("ix_supplier_category", "supplier_id", "category_id", unique=True),
    )

    def __repr__(self) -> str:
        return f"<SupplierCategory(supplier_id={self.supplier_id}, category_id={self.category_id})>"


class LegalEntity(Base):
    """Legal entities (companies) that purchase from suppliers."""

    __tablename__ = "legal_entities"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), unique=True, nullable=False)
    total_orders = Column(Integer, default=0)
    total_amount = Column(Float, default=0.0)

    def __repr__(self) -> str:
        return f"<LegalEntity(name='{self.name}')>"
