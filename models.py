import datetime
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Date, Text

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, default='Admin')  # Admin, Technician, Sales

class Customer(Base):
    __tablename__ = 'customers'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    mobile = Column(String, nullable=False)
    address = Column(Text)
    gst = Column(String, nullable=True)
    outstanding_balance = Column(Float, default=0.0)
    
    sales = relationship("SalesMaster", back_populates="customer")

class Supplier(Base):
    __tablename__ = 'suppliers'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    mobile = Column(String, nullable=False)
    address = Column(Text)
    bank_name = Column(String, nullable=True)
    account_number = Column(String, nullable=True)
    ifsc_code = Column(String, nullable=True)
    upi_id = Column(String, nullable=True)
    outstanding_balance = Column(Float, default=0.0)
    
    purchases = relationship("PurchaseMaster", back_populates="supplier")

class Product(Base):
    __tablename__ = 'products'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    category = Column(String, nullable=False, default='Phones')
    brand = Column(String, nullable=False)
    model = Column(String, nullable=False)
    imei = Column(String, unique=True, nullable=True)
    purchase_price = Column(Float, default=0.0)
    selling_price = Column(Float, default=0.0)
    stock_qty = Column(Integer, default=0)

class BankAccount(Base):
    __tablename__ = 'bank_accounts'
    id = Column(Integer, primary_key=True)
    bank_name = Column(String, nullable=False)
    account_name = Column(String, nullable=False)
    account_number = Column(String, nullable=True)
    account_type = Column(String, default='Current')
    balance = Column(Float, default=0.0)

class PurchaseMaster(Base):
    __tablename__ = 'purchase_master'
    id = Column(Integer, primary_key=True)
    invoice_number = Column(String, unique=True, nullable=False)
    date = Column(Date, default=datetime.date.today)
    supplier_id = Column(Integer, ForeignKey('suppliers.id'), nullable=False)
    total_amount = Column(Float, default=0.0)
    paid_amount = Column(Float, default=0.0)
    balance_payable = Column(Float, default=0.0)
    
    supplier = relationship("Supplier", back_populates="purchases")
    items = relationship("PurchaseItem", back_populates="purchase", cascade="all, delete-orphan")

class PurchaseItem(Base):
    __tablename__ = 'purchase_items'
    id = Column(Integer, primary_key=True)
    purchase_id = Column(Integer, ForeignKey('purchase_master.id'), nullable=False)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    qty = Column(Integer, default=1)
    rate = Column(Float, default=0.0)
    
    purchase = relationship("PurchaseMaster", back_populates="items")
    product = relationship("Product")

class SalesMaster(Base):
    __tablename__ = 'sales_master'
    id = Column(Integer, primary_key=True)
    invoice_number = Column(String, unique=True, nullable=False)
    date = Column(Date, default=datetime.date.today)
    customer_id = Column(Integer, ForeignKey('customers.id'), nullable=False)
    total_amount = Column(Float, default=0.0)
    paid_amount = Column(Float, default=0.0)
    balance_receivable = Column(Float, default=0.0)
    
    customer = relationship("Customer", back_populates="sales")
    items = relationship("SalesItem", back_populates="sales", cascade="all, delete-orphan")

class SalesItem(Base):
    __tablename__ = 'sales_items'
    id = Column(Integer, primary_key=True)
    sales_id = Column(Integer, ForeignKey('sales_master.id'), nullable=False)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    qty = Column(Integer, default=1)
    rate = Column(Float, default=0.0)
    discount = Column(Float, default=0.0)
    
    sales = relationship("SalesMaster", back_populates="items")
    product = relationship("Product")

class ServiceJob(Base):
    __tablename__ = 'service_jobs'
    id = Column(Integer, primary_key=True)
    job_number = Column(String, unique=True, nullable=False)
    customer_name = Column(String, nullable=False)
    mobile = Column(String, nullable=False)
    device_model = Column(String, nullable=False)
    imei = Column(String, nullable=False)
    complaint = Column(Text)
    technician = Column(String)
    status = Column(String, default='Received')  # Received, Under Repair, Ready, Delivered
    service_charge = Column(Float, default=0.0)
    total_amount = Column(Float, default=0.0)
    paid_amount = Column(Float, default=0.0)
    balance = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.datetime.now)
    
    parts = relationship("ServicePart", back_populates="job", cascade="all, delete-orphan")
    status_history = relationship("ServiceJobStatusHistory", back_populates="job", cascade="all, delete-orphan")

class ServiceJobStatusHistory(Base):
    __tablename__ = 'service_job_status_history'
    id = Column(Integer, primary_key=True)
    job_id = Column(Integer, ForeignKey('service_jobs.id'), nullable=False)
    status = Column(String, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.now)
    
    job = relationship("ServiceJob", back_populates="status_history")

class ServicePart(Base):
    __tablename__ = 'service_parts'
    id = Column(Integer, primary_key=True)
    job_id = Column(Integer, ForeignKey('service_jobs.id'), nullable=False)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=True)
    part_name = Column(String, nullable=False)
    qty = Column(Integer, default=1)
    cost = Column(Float, default=0.0)
    
    job = relationship("ServiceJob", back_populates="parts")
    product = relationship("Product")

class Payment(Base):
    __tablename__ = 'payments'
    id = Column(Integer, primary_key=True)
    date = Column(Date, default=datetime.date.today)
    party_type = Column(String, nullable=False)  # customer, supplier
    party_id = Column(Integer, nullable=False)  # customer_id or supplier_id
    amount = Column(Float, default=0.0)
    payment_mode = Column(String, nullable=False)  # Cash, Bank
    bank_id = Column(Integer, ForeignKey('bank_accounts.id'), nullable=True)
    remarks = Column(Text)
    
    bank_account = relationship("BankAccount")

class CashTransaction(Base):
    __tablename__ = 'cash_transactions'
    id = Column(Integer, primary_key=True)
    date = Column(Date, default=datetime.date.today)
    transaction_type = Column(String, nullable=False)  # in, out
    amount = Column(Float, default=0.0)
    source_type = Column(String, nullable=False)  # sale, purchase, service, payment, direct
    source_id = Column(Integer, nullable=True)
    description = Column(Text)

class BankTransaction(Base):
    __tablename__ = 'bank_transactions'
    id = Column(Integer, primary_key=True)
    date = Column(Date, default=datetime.date.today)
    transaction_type = Column(String, nullable=False)  # deposit, withdrawal
    account_id = Column(Integer, ForeignKey('bank_accounts.id'), nullable=False)
    amount = Column(Float, default=0.0)
    source_type = Column(String, nullable=False)  # sale, purchase, service, payment, direct
    source_id = Column(Integer, nullable=True)
    description = Column(Text)
    
    bank_account = relationship("BankAccount")

class Setting(Base):
    __tablename__ = 'settings'
    id = Column(Integer, primary_key=True)
    key = Column(String, unique=True, nullable=False)
    value = Column(String, nullable=False)

class Category(Base):
    __tablename__ = 'categories'
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
