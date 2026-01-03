from sqlalchemy import (
    Column,
    String,
    Integer,
    Date,
    DateTime,
    ForeignKey,
    Enum,
)
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import relationship

from .db import Base


class PlanTierEnum(str):
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class AcquisitionChannelEnum(str):
    ORGANIC = "organic"
    PAID = "paid"
    REFERRAL = "referral"


class Users(Base):
    __tablename__ = "users"

    user_id = Column(String, primary_key=True, index=True)
    company_id = Column(String, ForeignKey("companies.company_id"), index=True)
    country = Column(String, index=True)
    plan_tier = Column(String, index=True)  # values from PlanTierEnum
    signup_date = Column(Date, index=True)
    acquisition_channel = Column(String, index=True)  # values from AcquisitionChannelEnum

    company = relationship("Companies", back_populates="users")
    events = relationship("Events", back_populates="user")


class Companies(Base):
    __tablename__ = "companies"

    company_id = Column(String, primary_key=True, index=True)
    company_name = Column(String, index=True)
    employee_count = Column(Integer)

    users = relationship("Users", back_populates="company")


class Events(Base):
    __tablename__ = "events"

    event_id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.user_id"), index=True)
    event_name = Column(String, index=True)  # signup, login, view_dashboard, export_report, invite_teammate, upgrade_plan
    event_time = Column(DateTime, index=True)
    event_metadata = Column("metadata", JSON, nullable=True)

    user = relationship("Users", back_populates="events")
