import datetime
import json
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Date, Text, Boolean

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    role = Column(String, default='Standard User')  # Administrator, Standard User
    is_active = Column(Boolean, default=True)
    last_login = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.now)
    permissions = Column(Text, nullable=True)  # JSON string storing module permissions

    def get_permissions(self):
        if not self.permissions:
            return {}
        try:
            return json.loads(self.permissions)
        except Exception:
            return {}

    def set_permissions(self, perm_dict):
        self.permissions = json.dumps(perm_dict)

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
    gst = Column(String, nullable=True)
    
    purchases = relationship("PurchaseMaster", back_populates="supplier")

class Product(Base):
    __tablename__ = 'products'
    id = Column(Integer, primary_key=True)
    product_code = Column(String, unique=True, nullable=True)
    name = Column(String, nullable=False)
    category = Column(String, nullable=True, default='General')
    brand = Column(String, nullable=True, default='')  # Stores Brand / Model
    model = Column(String, nullable=True, default='')
    imei = Column(String, unique=True, nullable=True)
    purchase_price = Column(Float, default=0.0)
    selling_price = Column(Float, default=0.0)
    stock_qty = Column(Integer, default=0)
    low_stock_limit = Column(Integer, default=5)
    unit = Column(String, nullable=True, default='Pcs')

    @property
    def cost_price(self):
        return self.purchase_price or 0.0

    @property
    def brand_model(self):
        if self.brand and self.model and self.brand != self.model:
            return f"{self.brand} {self.model}".strip()
        return (self.brand or self.model or "").strip()

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
    gst_enabled = Column(Boolean, default=False)
    gst_type = Column(String, default="CGST+SGST")
    taxable_amount = Column(Float, default=0.0)
    total_cgst = Column(Float, default=0.0)
    total_sgst = Column(Float, default=0.0)
    total_igst = Column(Float, default=0.0)
    total_gst = Column(Float, default=0.0)
    
    supplier = relationship("Supplier", back_populates="purchases")
    items = relationship("PurchaseItem", back_populates="purchase", cascade="all, delete-orphan")

class PurchaseItem(Base):
    __tablename__ = 'purchase_items'
    id = Column(Integer, primary_key=True)
    purchase_id = Column(Integer, ForeignKey('purchase_master.id'), nullable=False)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    qty = Column(Integer, default=1)
    rate = Column(Float, default=0.0)
    unit = Column(String, nullable=True, default='Pcs')
    gst_rate = Column(Float, default=0.0)
    cgst_amount = Column(Float, default=0.0)
    sgst_amount = Column(Float, default=0.0)
    igst_amount = Column(Float, default=0.0)
    tax_amount = Column(Float, default=0.0)
    taxable_value = Column(Float, default=0.0)
    
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
    gst_enabled = Column(Boolean, default=False)
    gst_type = Column(String, default="CGST+SGST")
    taxable_amount = Column(Float, default=0.0)
    total_cgst = Column(Float, default=0.0)
    total_sgst = Column(Float, default=0.0)
    total_igst = Column(Float, default=0.0)
    total_gst = Column(Float, default=0.0)
    
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
    unit = Column(String, nullable=True, default='Pcs')
    gst_rate = Column(Float, default=0.0)
    cgst_amount = Column(Float, default=0.0)
    sgst_amount = Column(Float, default=0.0)
    igst_amount = Column(Float, default=0.0)
    tax_amount = Column(Float, default=0.0)
    taxable_value = Column(Float, default=0.0)
    
    sales = relationship("SalesMaster", back_populates="items")
    product = relationship("Product")

class ServiceJob(Base):
    __tablename__ = 'service_jobs'
    id = Column(Integer, primary_key=True)
    job_number = Column(String, unique=True, nullable=False)
    customer_name = Column(String, nullable=False)
    mobile = Column(String, nullable=False)
    device_model = Column(String, nullable=False)
    imei = Column(String, nullable=True)
    complaint = Column(Text)
    technician = Column(String)
    status = Column(String, default='Received')  # Received, Under Repair, Ready, Delivered
    service_charge = Column(Float, default=0.0)
    advance_payment = Column(Float, default=0.0)
    total_amount = Column(Float, default=0.0)
    paid_amount = Column(Float, default=0.0)
    balance = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.datetime.now)
    
    parts = relationship("ServicePart", back_populates="job", cascade="all, delete-orphan")
    status_history = relationship("ServiceJobStatusHistory", back_populates="job", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="job", cascade="all, delete-orphan")

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
    job_id = Column(Integer, ForeignKey('service_jobs.id'), nullable=True)
    remarks = Column(Text)
    
    bank_account = relationship("BankAccount")
    purchase = relationship("PurchaseMaster")
    sales = relationship("SalesMaster")
    job = relationship("ServiceJob", back_populates="payments")

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
    description = Column(String, nullable=True)

class Brand(Base):
    __tablename__ = 'brands'
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)

class Unit(Base):
    __tablename__ = 'units'
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(String, nullable=True)

class ProductModel(Base):
    __tablename__ = 'models'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    brand_id = Column(Integer, ForeignKey('brands.id'), nullable=True)
    brand_name = Column(String, nullable=True)

    brand = relationship("Brand")

# Alias for backward compatibility and convenience
Model = ProductModel

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
    unit = Column(String, nullable=True, default='Pcs')
    gst_rate = Column(Float, default=0.0)
    cgst_amount = Column(Float, default=0.0)
    sgst_amount = Column(Float, default=0.0)
    igst_amount = Column(Float, default=0.0)
    tax_amount = Column(Float, default=0.0)
    taxable_value = Column(Float, default=0.0)
    
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
    unit = Column(String, nullable=True, default='Pcs')
    gst_rate = Column(Float, default=0.0)
    cgst_amount = Column(Float, default=0.0)
    sgst_amount = Column(Float, default=0.0)
    igst_amount = Column(Float, default=0.0)
    tax_amount = Column(Float, default=0.0)
    taxable_value = Column(Float, default=0.0)
    
    purchase_return = relationship("PurchaseReturnMaster", back_populates="items")
    product = relationship("Product")


class ExpenseCategory(Base):
    __tablename__ = 'expense_categories'
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.now)

    expenses = relationship("Expense", back_populates="category")


class Expense(Base):
    __tablename__ = 'expenses'
    id = Column(Integer, primary_key=True)
    voucher_number = Column(String, unique=True, nullable=False)
    date = Column(Date, default=datetime.date.today)
    category_id = Column(Integer, ForeignKey('expense_categories.id'), nullable=False)
    amount = Column(Float, default=0.0)
    payment_mode = Column(String, default='Cash')  # 'Cash', 'Bank'
    bank_id = Column(Integer, ForeignKey('bank_accounts.id'), nullable=True)
    payee = Column(String, nullable=True)          # Paid To / Vendor
    reference_no = Column(String, nullable=True)   # Invoice / Receipt / Txn #
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.now)

    category = relationship("ExpenseCategory", back_populates="expenses")
    bank_account = relationship("BankAccount")


class Staff(Base):
    __tablename__ = 'staff'
    id = Column(Integer, primary_key=True)
    staff_code = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    mobile = Column(String, nullable=False)
    email = Column(String, nullable=True)
    designation = Column(String, default='Salesperson')  # Technician, Salesperson, Cashier, Manager, Helper
    salary_type = Column(String, default='Monthly')      # Monthly, Daily, Weekly
    base_salary = Column(Float, default=0.0)
    joining_date = Column(Date, default=datetime.date.today)
    address = Column(Text, nullable=True)
    id_proof_type = Column(String, nullable=True)        # Aadhaar, Voter ID, PAN, Driving License
    id_proof_number = Column(String, nullable=True)
    status = Column(String, default='Active')            # Active, Inactive, Resigned
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.now)

    attendances = relationship("StaffAttendance", back_populates="staff", cascade="all, delete-orphan")
    salary_payments = relationship("StaffSalaryPayment", back_populates="staff", cascade="all, delete-orphan")


class StaffAttendance(Base):
    __tablename__ = 'staff_attendance'
    id = Column(Integer, primary_key=True)
    staff_id = Column(Integer, ForeignKey('staff.id'), nullable=False)
    date = Column(Date, default=datetime.date.today)
    status = Column(String, default='Present')           # Present, Absent, Half Day, Leave
    in_time = Column(String, nullable=True)              # e.g. 09:30 AM
    out_time = Column(String, nullable=True)             # e.g. 08:30 PM
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.now)

    staff = relationship("Staff", back_populates="attendances")


class StaffSalaryPayment(Base):
    __tablename__ = 'staff_salary_payments'
    id = Column(Integer, primary_key=True)
    payment_number = Column(String, unique=True, nullable=False)
    staff_id = Column(Integer, ForeignKey('staff.id'), nullable=False)
    date = Column(Date, default=datetime.date.today)
    payment_type = Column(String, default='Salary')      # Salary, Advance, Bonus, Incentive
    for_month = Column(String, nullable=False)           # e.g. 2026-11
    amount = Column(Float, default=0.0)                 # Gross Amount
    deductions = Column(Float, default=0.0)             # Advance / Other Deductions
    net_paid = Column(Float, default=0.0)               # Net Amount Paid
    payment_mode = Column(String, default='Cash')       # Cash, Bank
    bank_id = Column(Integer, ForeignKey('bank_accounts.id'), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.now)

    staff = relationship("Staff", back_populates="salary_payments")
    bank_account = relationship("BankAccount")

class ExistingStockMaster(Base):
    __tablename__ = 'existing_stock_master'
    id = Column(Integer, primary_key=True)
    entry_number = Column(String, unique=True, nullable=False)
    date = Column(Date, default=datetime.date.today)
    notes = Column(Text, nullable=True)
    total_items = Column(Integer, default=0)
    total_qty = Column(Integer, default=0)
    total_value = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.datetime.now)

    items = relationship("ExistingStockItem", back_populates="master", cascade="all, delete-orphan")


class ExistingStockItem(Base):
    __tablename__ = 'existing_stock_items'
    id = Column(Integer, primary_key=True)
    master_id = Column(Integer, ForeignKey('existing_stock_master.id'), nullable=False)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    qty = Column(Integer, default=1)
    rate = Column(Float, default=0.0)
    selling_price = Column(Float, default=0.0)
    unit = Column(String, nullable=True, default='Pcs')
    total_amount = Column(Float, default=0.0)

    master = relationship("ExistingStockMaster", back_populates="items")
    product = relationship("Product")



class PurchaseOrderMaster(Base):
    __tablename__ = 'purchase_order_master'
    id = Column(Integer, primary_key=True)
    po_number = Column(String, unique=True, nullable=False, index=True)
    date = Column(Date, default=datetime.date.today)
    expected_date = Column(Date, nullable=True)
    supplier_id = Column(Integer, ForeignKey('suppliers.id'), nullable=True)
    supplier_name = Column(String, nullable=True)
    supplier_mobile = Column(String, nullable=True)
    supplier_address = Column(Text, nullable=True)
    supplier_gst = Column(String, nullable=True)
    total_items = Column(Integer, default=0)
    total_qty = Column(Integer, default=0)
    total_amount = Column(Float, default=0.0)
    status = Column(String, default="Pending")  # Pending, Ordered, Approved, Completed, Cancelled
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.now)

    supplier = relationship("Supplier")
    items = relationship("PurchaseOrderItem", back_populates="purchase_order", cascade="all, delete-orphan")


class PurchaseOrderItem(Base):
    __tablename__ = 'purchase_order_items'
    id = Column(Integer, primary_key=True)
    po_id = Column(Integer, ForeignKey('purchase_order_master.id'), nullable=False)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=True)
    product_code = Column(String, nullable=True)
    item_name = Column(String, nullable=False)
    brand_model = Column(String, nullable=True)
    unit = Column(String, nullable=True, default='Pcs')
    current_stock = Column(Integer, default=0)
    low_limit = Column(Integer, default=0)
    qty = Column(Integer, default=1)
    rate = Column(Float, default=0.0)
    total_amount = Column(Float, default=0.0)

    purchase_order = relationship("PurchaseOrderMaster", back_populates="items")
    product = relationship("Product")
