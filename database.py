import hashlib
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from models import Base, User, BankAccount, CashTransaction, BankTransaction, Setting, Category, FundTransfer, DirectTransaction, MoneyTransfer, SalesReturnMaster, SalesReturnItem, PurchaseReturnMaster, PurchaseReturnItem, Product, Brand, ProductModel, Unit

DATABASE_URL = "sqlite:///inventory.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
session_factory = sessionmaker(bind=engine)
Session = scoped_session(session_factory)

def get_hash(password: str) -> str:
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def get_category_code(session, category_name: str) -> str:
    category = session.query(Category).filter(Category.name.ilike(category_name.strip())).first() if category_name else None
    if category:
        return str(category.id % 10)
    return "1"

def generate_next_product_code(session, category_name: str) -> str:
    category = session.query(Category).filter(Category.name.ilike(category_name.strip())).first() if category_name else None
    category_id = category.id if category else 1
    cat_code = str(category_id % 10) if category_id else "1"
    
    prefix = cat_code
    products = session.query(Product).filter(
        Product.product_code.like(f"{prefix}%")
    ).all()
    
    existing_nums = set()
    for p in products:
        if p.product_code and len(p.product_code) == 4 and p.product_code.startswith(prefix):
            try:
                num = int(p.product_code[1:])
                existing_nums.add(num)
            except ValueError:
                pass
                
    next_num = 1
    while next_num in existing_nums or session.query(Product).filter_by(product_code=f"{prefix}{next_num:03d}").first() is not None:
        next_num += 1
        
    return f"{prefix}{next_num:03d}"

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
    if 'low_stock_limit' not in prod_columns:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE products ADD COLUMN low_stock_limit INTEGER DEFAULT 5"))
    if 'product_code' not in prod_columns:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE products ADD COLUMN product_code TEXT"))
    if 'unit' not in prod_columns:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE products ADD COLUMN unit TEXT DEFAULT 'Pcs'"))

    # Schema migration: check and add unit column to items tables
    pur_item_cols = [c['name'] for c in inspector.get_columns('purchase_items')]
    if 'unit' not in pur_item_cols:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE purchase_items ADD COLUMN unit TEXT DEFAULT 'Pcs'"))

    sales_item_cols = [c['name'] for c in inspector.get_columns('sales_items')]
    if 'unit' not in sales_item_cols:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE sales_items ADD COLUMN unit TEXT DEFAULT 'Pcs'"))

    pur_ret_item_cols = [c['name'] for c in inspector.get_columns('purchase_return_items')]
    if 'unit' not in pur_ret_item_cols:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE purchase_return_items ADD COLUMN unit TEXT DEFAULT 'Pcs'"))

    sales_ret_item_cols = [c['name'] for c in inspector.get_columns('sales_return_items')]
    if 'unit' not in sales_ret_item_cols:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE sales_return_items ADD COLUMN unit TEXT DEFAULT 'Pcs'"))

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

    # Schema migration: check and add columns to users table
    user_columns = [c['name'] for c in inspector.get_columns('users')]
    if 'full_name' not in user_columns:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE users ADD COLUMN full_name TEXT"))
    if 'is_active' not in user_columns:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE users ADD COLUMN is_active INTEGER DEFAULT 1"))
    if 'last_login' not in user_columns:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE users ADD COLUMN last_login DATETIME"))
    if 'created_at' not in user_columns:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE users ADD COLUMN created_at DATETIME"))
    if 'permissions' not in user_columns:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE users ADD COLUMN permissions TEXT"))

    # Schema migration: check and add missing GST columns to suppliers
    if 'gst' not in supp_columns:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE suppliers ADD COLUMN gst TEXT"))

    # Schema migration: check and add GST columns to purchase_master
    pur_master_cols = [c['name'] for c in inspector.get_columns('purchase_master')]
    if 'gst_enabled' not in pur_master_cols:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE purchase_master ADD COLUMN gst_enabled INTEGER DEFAULT 0"))
            conn.execute(text("ALTER TABLE purchase_master ADD COLUMN gst_type TEXT DEFAULT 'CGST+SGST'"))
            conn.execute(text("ALTER TABLE purchase_master ADD COLUMN taxable_amount REAL DEFAULT 0.0"))
            conn.execute(text("ALTER TABLE purchase_master ADD COLUMN total_cgst REAL DEFAULT 0.0"))
            conn.execute(text("ALTER TABLE purchase_master ADD COLUMN total_sgst REAL DEFAULT 0.0"))
            conn.execute(text("ALTER TABLE purchase_master ADD COLUMN total_igst REAL DEFAULT 0.0"))
            conn.execute(text("ALTER TABLE purchase_master ADD COLUMN total_gst REAL DEFAULT 0.0"))

    # Schema migration: check and add GST columns to sales_master
    sales_master_cols = [c['name'] for c in inspector.get_columns('sales_master')]
    if 'gst_enabled' not in sales_master_cols:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE sales_master ADD COLUMN gst_enabled INTEGER DEFAULT 0"))
            conn.execute(text("ALTER TABLE sales_master ADD COLUMN gst_type TEXT DEFAULT 'CGST+SGST'"))
            conn.execute(text("ALTER TABLE sales_master ADD COLUMN taxable_amount REAL DEFAULT 0.0"))
            conn.execute(text("ALTER TABLE sales_master ADD COLUMN total_cgst REAL DEFAULT 0.0"))
            conn.execute(text("ALTER TABLE sales_master ADD COLUMN total_sgst REAL DEFAULT 0.0"))
            conn.execute(text("ALTER TABLE sales_master ADD COLUMN total_igst REAL DEFAULT 0.0"))
            conn.execute(text("ALTER TABLE sales_master ADD COLUMN total_gst REAL DEFAULT 0.0"))

    # Schema migration: check and add GST columns to line items
    for tbl in ('purchase_items', 'sales_items', 'purchase_return_items', 'sales_return_items'):
        cols = [c['name'] for c in inspector.get_columns(tbl)]
        if 'gst_rate' not in cols:
            with engine.begin() as conn:
                conn.execute(text(f"ALTER TABLE {tbl} ADD COLUMN gst_rate REAL DEFAULT 0.0"))
                conn.execute(text(f"ALTER TABLE {tbl} ADD COLUMN cgst_amount REAL DEFAULT 0.0"))
                conn.execute(text(f"ALTER TABLE {tbl} ADD COLUMN sgst_amount REAL DEFAULT 0.0"))
                conn.execute(text(f"ALTER TABLE {tbl} ADD COLUMN igst_amount REAL DEFAULT 0.0"))
                conn.execute(text(f"ALTER TABLE {tbl} ADD COLUMN tax_amount REAL DEFAULT 0.0"))
                conn.execute(text(f"ALTER TABLE {tbl} ADD COLUMN taxable_value REAL DEFAULT 0.0"))

    session = Session()
    try:
        # Update existing users with role 'Admin' to 'Administrator'
        with engine.begin() as conn:
            conn.execute(text("UPDATE users SET role = 'Administrator' WHERE role = 'Admin'"))

        # 1. Seed admin user if it doesn't exist
        admin = session.query(User).filter_by(username='admin').first()
        if not admin:
            admin_user = User(
                username='admin',
                password_hash=get_hash('admin'),
                full_name='System Administrator',
                role='Administrator',
                is_active=True
            )
            session.add(admin_user)
        else:
            if not admin.full_name:
                admin.full_name = 'System Administrator'
            if admin.role != 'Administrator':
                admin.role = 'Administrator'
            admin.is_active = True
            
        # 2. Seed bank accounts and opening transactions if empty
        bank_count = session.query(BankAccount).count()
        if bank_count == 0:
            icici = BankAccount(bank_name="ICICI Bank", account_name="ICICI Current A/c", balance=0.0)
            sbi = BankAccount(bank_name="SBI Bank", account_name="SBI Savings A/c", balance=0.0)
            session.add(icici)
            session.add(sbi)
            session.commit() # commit to generate ids
            
            # Record bank opening transactions
            tx_icici = BankTransaction(
                transaction_type='deposit',
                account_id=icici.id,
                amount=0.0,
                source_type='direct',
                description="Opening Balance"
            )
            tx_sbi = BankTransaction(
                transaction_type='deposit',
                account_id=sbi.id,
                amount=0.0,
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
                amount=0.0,
                source_type='direct',
                description="Opening Balance"
            )
            session.add(opening_cash)

        # 4. Seed default settings
        shop_name = session.query(Setting).filter_by(key='shop_name').first()
        if not shop_name:
            session.add(Setting(key='shop_name', value='SUN COMPUTERS,'))
        shop_contact = session.query(Setting).filter_by(key='shop_contact').first()
        if not shop_contact:
            session.add(Setting(key='shop_contact', value='8122913041, 8667729988'))
        shop_address = session.query(Setting).filter_by(key='shop_address').first()
        if not shop_address:
            session.add(Setting(key='shop_address', value='PARIBALAN COMPLEX. MANAMELKUDI. 614620'))
        shop_gst = session.query(Setting).filter_by(key='shop_gst').first()
        if not shop_gst:
            session.add(Setting(key='shop_gst', value='27AAAAA1111A1Z1'))
        low_stock_limit = session.query(Setting).filter_by(key='low_stock_limit').first()
        if not low_stock_limit:
            session.add(Setting(key='low_stock_limit', value='5'))
        enable_repair = session.query(Setting).filter_by(key='enable_repair_service').first()
        if not enable_repair:
            session.add(Setting(key='enable_repair_service', value='true'))
        enable_money = session.query(Setting).filter_by(key='enable_money_transfer').first()
        if not enable_money:
            session.add(Setting(key='enable_money_transfer', value='true'))
        enable_imei = session.query(Setting).filter_by(key='enable_imei_tracking').first()
        if not enable_imei:
            session.add(Setting(key='enable_imei_tracking', value='true'))

        enable_gst = session.query(Setting).filter_by(key='enable_gst').first()
        if not enable_gst:
            session.add(Setting(key='enable_gst', value='false'))

        # 5. Seed default categories if empty
        cat_count = session.query(Category).count()
        if cat_count == 0:
            for name in ["General Inventory", "Electronics", "Supplies"]:
                session.add(Category(name=name))
            session.commit()

        # 6. Seed default/existing brands if empty
        brand_count = session.query(Brand).count()
        if brand_count == 0:
            existing_brands = {b[0].strip() for b in session.query(Product.brand).distinct() if b[0] and b[0].strip()}
            default_brands = ["Apple", "Samsung", "Xiaomi", "Vivo", "Oppo", "Realme", "OnePlus"]
            all_brands = sorted(list(existing_brands.union(default_brands)))
            for b_name in all_brands:
                session.add(Brand(name=b_name))
            session.commit()

        # 7. Seed default/existing models if empty
        model_count = session.query(ProductModel).count()
        if model_count == 0:
            brand_map = {b.name.lower(): b for b in session.query(Brand).all()}
            existing_models = session.query(Product.model, Product.brand).distinct().all()
            added_model_names = set()
            for m_tuple in existing_models:
                m_name = m_tuple[0].strip() if m_tuple[0] else ""
                b_name = m_tuple[1].strip() if m_tuple[1] else ""
                if m_name and m_name.lower() not in added_model_names:
                    brand_obj = brand_map.get(b_name.lower())
                    session.add(ProductModel(
                        name=m_name,
                        brand_id=brand_obj.id if brand_obj else None,
                        brand_name=brand_obj.name if brand_obj else (b_name or None)
                    ))
                    added_model_names.add(m_name.lower())
            session.commit()

        # 8. Backfill existing products without product_code
        prods_to_backfill = session.query(Product).filter((Product.product_code == None) | (Product.product_code == "")).all()
        for p in prods_to_backfill:
            p.product_code = generate_next_product_code(session, p.category)
            session.commit()

        # 9. Seed default units if empty
        unit_count = session.query(Unit).count()
        if unit_count == 0:
            default_units = [
                ("Pcs", "Pieces"),
                ("Box", "Box"),
                ("Kg", "Kilograms"),
                ("Grams", "Grams"),
                ("Ltr", "Litres"),
                ("Mtr", "Meters"),
                ("Nos", "Numbers"),
                ("Pack", "Pack"),
                ("Set", "Set")
            ]
            for u_name, u_desc in default_units:
                session.add(Unit(name=u_name, description=u_desc))
            session.commit()

        session.commit()
    except Exception as e:
        session.rollback()
        print(f"Error seeding DB: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully.")
