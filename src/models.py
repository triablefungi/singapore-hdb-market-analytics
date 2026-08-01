from datetime import date
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, Integer, Numeric, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class HDBResale(Base):
    __tablename__ = "hdb_resale"

    source_row_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    town: Mapped[str] = mapped_column(String(32), index=True)
    flat_type: Mapped[str] = mapped_column(String(32), index=True)
    block: Mapped[str] = mapped_column(String(16))
    street_name: Mapped[str] = mapped_column(String(64))
    storey_range: Mapped[str] = mapped_column(String(16))
    floor_area_sqm: Mapped[Decimal] = mapped_column(Numeric(6, 1))
    flat_model: Mapped[str] = mapped_column(String(64))
    lease_commence_date: Mapped[int] = mapped_column(Integer)
    remaining_lease: Mapped[str] = mapped_column(String(32))
    resale_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    transaction_month: Mapped[date] = mapped_column(Date, index=True)
    address: Mapped[str] = mapped_column(String(96), index=True)
    remaining_lease_months: Mapped[int] = mapped_column(Integer)
    storey_lower: Mapped[int] = mapped_column(Integer)
    storey_upper: Mapped[int] = mapped_column(Integer)
    storey_midpoint: Mapped[Decimal] = mapped_column(Numeric(4, 1))
    price_per_sqm: Mapped[Decimal] = mapped_column(Numeric(10, 2))

    __table_args__ = (
        CheckConstraint(
            "floor_area_sqm > 0",
            name="ck_hdb_resale_floor_area_positive",
        ),
        CheckConstraint(
            "resale_price > 0",
            name="ck_hdb_resale_price_positive",
        ),
        CheckConstraint(
            "remaining_lease_months BETWEEN 0 AND 1188",
            name="ck_hdb_resale_lease_months",
        ),
        CheckConstraint(
            "storey_lower <= storey_upper",
            name="ck_hdb_resale_storey_order",
        ),
    )


class HDBRental(Base):
    __tablename__ = "hdb_rental"

    source_row_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    town: Mapped[str] = mapped_column(String(32), index=True)
    block: Mapped[str] = mapped_column(String(16))
    street_name: Mapped[str] = mapped_column(String(64))
    flat_type: Mapped[str] = mapped_column(String(32), index=True)
    monthly_rent: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    approval_month: Mapped[date] = mapped_column(Date, index=True)
    address: Mapped[str] = mapped_column(String(96), index=True)

    __table_args__ = (
        CheckConstraint(
            "monthly_rent > 0",
            name="ck_hdb_rental_rent_positive",
        ),
    )


class MRTExit(Base):
    __tablename__ = "mrt_exits"

    source_row_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    station_name: Mapped[str] = mapped_column(String(64), index=True)
    exit_code: Mapped[str] = mapped_column(String(16))
    longitude: Mapped[Decimal] = mapped_column(Numeric(12, 9))
    latitude: Mapped[Decimal] = mapped_column(Numeric(10, 9))

    __table_args__ = (
        CheckConstraint(
            "longitude BETWEEN 103 AND 105",
            name="ck_mrt_exit_longitude",
        ),
        CheckConstraint(
            "latitude BETWEEN 1 AND 2",
            name="ck_mrt_exit_latitude",
        ),
    )