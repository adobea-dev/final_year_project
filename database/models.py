from sqlalchemy import Column, String, Float, Boolean, Integer, Date, Text, ForeignKey
from config.database import Base

class AccountManager(Base):
    __tablename__ = "account_managers"
    accountmanagerid = Column(String, primary_key=True)
    country = Column(String, nullable=False)
    accountmanager = Column(String, nullable=False)
    sourceid = Column(String, nullable=False)

class Dealer(Base):
    __tablename__ = "dealers"
    dealer_id = Column(String, primary_key=True)
    dealership_name = Column(String, nullable=False)
    country = Column(String, nullable=False)
    accountmanager = Column(String)
    type = Column(String)
    accountmanagerid = Column(String)
    sourceid = Column(String)
    longitude = Column(Float)
    latitude = Column(Float)
    df_category = Column(String)
    dealer_class = Column(String)
    has_listings = Column(Boolean, default=False)

class Listing(Base):
    __tablename__ = "listings"
    listing_id = Column(String, primary_key=True)
    country = Column(String, nullable=False)
    dealer_id = Column(String, ForeignKey("dealers.dealer_id"), nullable=False)
    date_posted = Column(Date)
    title = Column(Text)
    seller_type = Column(String)
    price = Column(Float)
    car_make = Column(String)
    car_model = Column(String)
    car_variant = Column(String)
    condition = Column(String)
    year_manufactured = Column(Integer)
    transmission = Column(String)
    engine_capacity = Column(String)
    body_type = Column(String)
    location = Column(String)
    warranty = Column(String)
    mileage = Column(String)
    colour_type = Column(String)
    colour = Column(String)
    description = Column(Text)

class Lead(Base):
    __tablename__ = "leads"
    lead_id = Column(String, primary_key=True)
    country = Column(String, nullable=False)
    lead_date = Column(Date)
    lead_source = Column(String)
    lead_channel = Column(String)
    dealer_id = Column(String, ForeignKey("dealers.dealer_id"), nullable=False)
    dealer_name = Column(String)
    linked_loanid = Column(String)

class Application(Base):
    __tablename__ = "applications"
    loanid = Column(String, primary_key=True)
    country = Column(String, nullable=False)
    lead_date = Column(Date)
    source = Column(String)
    dealer_id = Column(String, ForeignKey("dealers.dealer_id"), nullable=False)
    dealer_name = Column(String)
    product_status = Column(String)

class Sale(Base):
    __tablename__ = "sales"
    transaction_id = Column(String, primary_key=True)
    country = Column(String, nullable=False)
    fulfillment_date = Column(Date)
    gmv_in_dollars = Column(Float)
    product_classification = Column(String)
    lead_source = Column(String)
    loan_id = Column(String)
    financing_bank = Column(String)
    dealer_source_name = Column(String)
    dealer_id = Column(String, ForeignKey("dealers.dealer_id"), nullable=False)

class DealerActivityMetrics(Base):
    __tablename__ = "dealer_activity_metrics"
    dealer_id = Column(String, ForeignKey("dealers.dealer_id"), primary_key=True)
    period_start_date = Column(Date, primary_key=True)
    period_end_date = Column(Date, primary_key=True)
    country = Column(String, nullable=False)
    active_listings = Column(Integer, default=0)
    leads_count = Column(Integer, default=0)
    applications_count = Column(Integer, default=0)
    sales_count = Column(Integer, default=0)
    gmv_total = Column(Float, default=0.0)

#database design file