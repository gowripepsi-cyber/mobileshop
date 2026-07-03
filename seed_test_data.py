from database import Session, generate_next_product_code
from models import Product, Supplier, Category

def seed():
    session = Session()
    try:
        # 1. Seed Categories if they don't exist
        categories = ["Phones", "Accessories", "Electronics", "General Inventory", "Supplies"]
        for cat_name in categories:
            existing = session.query(Category).filter_by(name=cat_name).first()
            if not existing:
                session.add(Category(name=cat_name))
        session.commit()

        # 2. Seed Suppliers if they don't exist
        suppliers = [
            {"name": "Apple India Pvt Ltd", "mobile": "9876543210", "address": "Mumbai, India", "outstanding_balance": 0.0},
            {"name": "Samsung Distributors", "mobile": "9876543211", "address": "Delhi, India", "outstanding_balance": 0.0},
            {"name": "Supreme Mobile Accessories", "mobile": "9876543212", "address": "Chennai, India", "outstanding_balance": 0.0}
        ]
        for sup_data in suppliers:
            existing = session.query(Supplier).filter_by(name=sup_data["name"]).first()
            if not existing:
                session.add(Supplier(**sup_data))
        session.commit()

        # 3. Seed Products
        products = [
            {
                "name": "iPhone 15 Pro Max 256GB",
                "category": "Phones",
                "brand": "Apple",
                "model": "iPhone 15 Pro Max",
                "purchase_price": 135000.0,
                "selling_price": 159900.0,
                "stock_qty": 0,
                "low_stock_limit": 5
            },
            {
                "name": "Samsung Galaxy S24 Ultra 512GB",
                "category": "Phones",
                "brand": "Samsung",
                "model": "Galaxy S24 Ultra",
                "purchase_price": 120000.0,
                "selling_price": 139900.0,
                "stock_qty": 0,
                "low_stock_limit": 5
            },
            {
                "name": "AirPods Pro Gen 2",
                "category": "Accessories",
                "brand": "Apple",
                "model": "AirPods Pro 2",
                "purchase_price": 20000.0,
                "selling_price": 24900.0,
                "stock_qty": 0,
                "low_stock_limit": 10
            },
            {
                "name": "OnePlus 12 256GB",
                "category": "Phones",
                "brand": "OnePlus",
                "model": "OnePlus 12",
                "purchase_price": 55000.0,
                "selling_price": 64999.0,
                "stock_qty": 0,
                "low_stock_limit": 5
            },
            {
                "name": "Spigen Liquid Air Case iPhone 15 Pro",
                "category": "Accessories",
                "brand": "Spigen",
                "model": "Liquid Air",
                "purchase_price": 800.0,
                "selling_price": 1499.0,
                "stock_qty": 0,
                "low_stock_limit": 15
            },
            {
                "name": "Anker PowerPort III 20W",
                "category": "Accessories",
                "brand": "Anker",
                "model": "PowerPort III",
                "purchase_price": 900.0,
                "selling_price": 1699.0,
                "stock_qty": 0,
                "low_stock_limit": 20
            }
        ]

        for prod_data in products:
            existing = session.query(Product).filter_by(name=prod_data["name"]).first()
            if not existing:
                p = Product(**prod_data)
                # Generate product code based on category
                p.product_code = generate_next_product_code(session, p.category)
                session.add(p)
        session.commit()
        print("Successfully seeded test categories, suppliers, and products!")
    except Exception as e:
        session.rollback()
        print(f"Error seeding data: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    seed()
