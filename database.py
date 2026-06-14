import hashlib
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from models import Base, User, BankAccount, CashTransaction, BankTransaction, Setting, Category

DATABASE_URL = "sqlite:///mobileshop.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
session_factory = sessionmaker(bind=engine)
Session = scoped_session(session_factory)

def get_hash(password: str) -> str:
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def init_db():
    Base.metadata.create_all(engine)
    
    # Schema migration: check and add missing columns to service_parts table
    from sqlalchemy import inspect, text
    inspector = inspect(engine)
    columns = [c['name'] for c in inspector.get_columns('service_parts')]
    if 'product_id' not in columns:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE service_parts ADD COLUMN product_id INTEGER REFERENCES products(id)"))
    if 'qty' not in columns:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE service_parts ADD COLUMN qty INTEGER DEFAULT 1"))

    # Schema migration: check and add category column to products table
    prod_columns = [c['name'] for c in inspector.get_columns('products')]
    if 'category' not in prod_columns:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE products ADD COLUMN category TEXT NOT NULL DEFAULT 'Phones'"))

    # Schema migration: check and add missing columns to suppliers table
    supp_columns = [c['name'] for c in inspector.get_columns('suppliers')]
    if 'bank_name' not in supp_columns:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE suppliers ADD COLUMN bank_name TEXT"))
    if 'account_number' not in supp_columns:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE suppliers ADD COLUMN account_number TEXT"))
    if 'ifsc_code' not in supp_columns:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE suppliers ADD COLUMN ifsc_code TEXT"))
    if 'upi_id' not in supp_columns:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE suppliers ADD COLUMN upi_id TEXT"))

    # Schema migration: check and add missing columns to bank_accounts table
    bank_columns = [c['name'] for c in inspector.get_columns('bank_accounts')]
    if 'account_number' not in bank_columns:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE bank_accounts ADD COLUMN account_number TEXT"))
    if 'account_type' not in bank_columns:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE bank_accounts ADD COLUMN account_type TEXT DEFAULT 'Current'"))

    # Schema migration: check and add purchase_id to payments table
    pay_columns = [c['name'] for c in inspector.get_columns('payments')]
    if 'purchase_id' not in pay_columns:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE payments ADD COLUMN purchase_id INTEGER REFERENCES purchase_master(id)"))
    if 'sales_id' not in pay_columns:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE payments ADD COLUMN sales_id INTEGER REFERENCES sales_master(id)"))

    session = Session()
    try:
        # 1. Seed admin user if it doesn't exist
        admin = session.query(User).filter_by(username='admin').first()
        if not admin:
            admin_user = User(
                username='admin',
                password_hash=get_hash('admin'),
                role='Admin'
            )
            session.add(admin_user)
            
        # 2. Seed bank accounts and opening transactions if empty
        bank_count = session.query(BankAccount).count()
        if bank_count == 0:
            icici = BankAccount(bank_name="ICICI Bank", account_name="ICICI Current A/c", balance=150000.0)
            sbi = BankAccount(bank_name="SBI Bank", account_name="SBI Savings A/c", balance=50000.0)
            session.add(icici)
            session.add(sbi)
            session.commit() # commit to generate ids
            
            # Record bank opening transactions
            tx_icici = BankTransaction(
                transaction_type='deposit',
                account_id=icici.id,
                amount=150000.0,
                source_type='direct',
                description="Opening Balance"
            )
            tx_sbi = BankTransaction(
                transaction_type='deposit',
                account_id=sbi.id,
                amount=50000.0,
                source_type='direct',
                description="Opening Balance"
            )
            session.add(tx_icici)
            session.add(tx_sbi)
            
        # 3. Seed Cash opening balance if cash transactions are empty
        cash_tx_count = session.query(CashTransaction).count()
        if cash_tx_count == 0:
            opening_cash = CashTransaction(
                transaction_type='in',
                amount=25000.0,
                source_type='direct',
                description="Opening Balance"
            )
            session.add(opening_cash)

        # 4. Seed default settings
        shop_name = session.query(Setting).filter_by(key='shop_name').first()
        if not shop_name:
            session.add(Setting(key='shop_name', value='Galaxy Mobiles & Services'))
        shop_contact = session.query(Setting).filter_by(key='shop_contact').first()
        if not shop_contact:
            session.add(Setting(key='shop_contact', value='+91 9876543210'))
        shop_address = session.query(Setting).filter_by(key='shop_address').first()
        if not shop_address:
            session.add(Setting(key='shop_address', value='123 Main Market Street, Tech City'))
        shop_gst = session.query(Setting).filter_by(key='shop_gst').first()
        if not shop_gst:
            session.add(Setting(key='shop_gst', value='27AAAAA1111A1Z1'))

        # 5. Seed default categories if empty
        cat_count = session.query(Category).count()
        if cat_count == 0:
            for name in ["Phones", "Accessories", "Spare Parts"]:
                session.add(Category(name=name))

        session.commit()
    except Exception as e:
        session.rollback()
        print(f"Error seeding DB: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully.")
