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
    low_stock_limit = Column(Integer, default=5)

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
    purchase_id = Column(Integer, ForeignKey('purchase_master.id'), nullable=True)
    sales_id = Column(Integer, ForeignKey('sales_master.id'), nullable=True)
    remarks = Column(Text)
    
    bank_account = relationship("BankAccount")
    purchase = relationship("PurchaseMaster")
    sales = relationship("SalesMaster")

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

class FundTransfer(Base):
    __tablename__ = 'fund_transfers'
    id = Column(Integer, primary_key=True)
    date = Column(Date, default=datetime.date.today)
    from_type = Column(String, nullable=False)  # 'cash' or 'bank'
    from_account_id = Column(Integer, ForeignKey('bank_accounts.id'), nullable=True)
    to_type = Column(String, nullable=False)    # 'cash' or 'bank'
    to_account_id = Column(Integer, ForeignKey('bank_accounts.id'), nullable=True)
    amount = Column(Float, default=0.0)
    remarks = Column(Text)
    
    from_account = relationship("BankAccount", foreign_keys=[from_account_id])
    to_account = relationship("BankAccount", foreign_keys=[to_account_id])

class DirectTransaction(Base):
    __tablename__ = 'direct_transactions'
    id = Column(Integer, primary_key=True)
    date = Column(Date, default=datetime.date.today)
    transaction_type = Column(String, nullable=False) # 'deposit' or 'withdrawal'
    account_type = Column(String, nullable=False)     # 'cash' or 'bank'
    bank_id = Column(Integer, ForeignKey('bank_accounts.id'), nullable=True)
    amount = Column(Float, default=0.0)
    description = Column(Text)
    
    bank_account = relationship("BankAccount")

class MoneyTransfer(Base):
    __tablename__ = 'money_transfers'
    id = Column(Integer, primary_key=True)
    transaction_number = Column(String, unique=True, nullable=False)
    date = Column(Date, default=datetime.date.today)
    customer_name = Column(String, nullable=False)
    beneficiary_name = Column(String, nullable=False)
    transfer_type = Column(String, nullable=False) # 'UPI' or 'Bank Transfer'
    
    # UPI fields
    upi_id = Column(String, nullable=True)
    
    # Bank Transfer fields
    bank_account_number = Column(String, nullable=True)
    ifsc_code = Column(String, nullable=True)
    
    amount = Column(Float, default=0.0)
    service_charge = Column(Float, default=0.0)
    total_amount = Column(Float, default=0.0)
    deadline_date = Column(Date, nullable=False)
    remarks = Column(Text, nullable=True)
    status = Column(String, default='Pending') # 'Pending', 'Completed'
    
    payment_mode = Column(String, nullable=False) # 'Cash' or 'Bank'
    payment_bank_id = Column(Integer, ForeignKey('bank_accounts.id'), nullable=True)
    payout_mode = Column(String, nullable=False) # 'Cash' or 'Bank'
    payout_bank_id = Column(Integer, ForeignKey('bank_accounts.id'), nullable=True)
    
    payment_bank = relationship("BankAccount", foreign_keys=[payment_bank_id])
    payout_bank = relationship("BankAccount", foreign_keys=[payout_bank_id])


class SalesReturnMaster(Base):
    __tablename__ = 'sales_return_master'
    id = Column(Integer, primary_key=True)
    return_number = Column(String, unique=True, nullable=False)
    date = Column(Date, default=datetime.date.today)
    sales_id = Column(Integer, ForeignKey('sales_master.id'), nullable=True)
    customer_id = Column(Integer, ForeignKey('customers.id'), nullable=False)
    total_amount = Column(Float, default=0.0)
    refund_amount = Column(Float, default=0.0)
    balance_deducted = Column(Float, default=0.0)
    
    customer = relationship("Customer")
    sales = relationship("SalesMaster")
    items = relationship("SalesReturnItem", back_populates="sales_return", cascade="all, delete-orphan")


class SalesReturnItem(Base):
    __tablename__ = 'sales_return_items'
    id = Column(Integer, primary_key=True)
    sales_return_id = Column(Integer, ForeignKey('sales_return_master.id'), nullable=False)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    qty = Column(Integer, default=1)
    rate = Column(Float, default=0.0)
    
    sales_return = relationship("SalesReturnMaster", back_populates="items")
    product = relationship("Product")


class PurchaseReturnMaster(Base):
    __tablename__ = 'purchase_return_master'
    id = Column(Integer, primary_key=True)
    return_number = Column(String, unique=True, nullable=False)
    date = Column(Date, default=datetime.date.today)
    purchase_id = Column(Integer, ForeignKey('purchase_master.id'), nullable=True)
    supplier_id = Column(Integer, ForeignKey('suppliers.id'), nullable=False)
    total_amount = Column(Float, default=0.0)
    refund_received = Column(Float, default=0.0)
    balance_deducted = Column(Float, default=0.0)
    
    supplier = relationship("Supplier")
    purchase = relationship("PurchaseMaster")
    items = relationship("PurchaseReturnItem", back_populates="purchase_return", cascade="all, delete-orphan")


class PurchaseReturnItem(Base):
    __tablename__ = 'purchase_return_items'
    id = Column(Integer, primary_key=True)
    purchase_return_id = Column(Integer, ForeignKey('purchase_return_master.id'), nullable=False)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    qty = Column(Integer, default=1)
    rate = Column(Float, default=0.0)
    
    purchase_return = relationship("PurchaseReturnMaster", back_populates="items")
    product = relationship("Product")
