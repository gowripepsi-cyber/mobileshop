import os
import unittest
import datetime
from database import Session, init_db
from models import Product, Customer, Supplier, BankAccount, PurchaseMaster, PurchaseItem, SalesMaster, SalesItem, Payment, CashTransaction, BankTransaction, ServiceJob, ServicePart

class TestMobileShopDB(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Initialize DB (uses mobileshop.db)
        init_db()

    def setUp(self):
        self.session = Session()

    def tearDown(self):
        self.session.close()

    def test_01_product_creation(self):
        # Clear existing test products if any
        self.session.query(Product).filter_by(name="Test Phone").delete()
        self.session.commit()

        # Add new test product
        p = Product(name="Test Phone", brand="BrandX", model="ModelY", imei="TEST-IMEI-101", purchase_price=10000.0, selling_price=13000.0, stock_qty=0)
        self.session.add(p)
        self.session.commit()

        db_p = self.session.query(Product).filter_by(imei="TEST-IMEI-101").first()
        self.assertIsNotNone(db_p)
        self.assertEqual(db_p.stock_qty, 0)
        self.assertEqual(db_p.selling_price, 13000.0)

    def test_02_purchase_and_stock_increase(self):
        # Find product
        prod = self.session.query(Product).filter_by(imei="TEST-IMEI-101").first()
        self.assertIsNotNone(prod)

        # Setup Supplier
        supp = self.session.query(Supplier).filter_by(name="Test Supplier").first()
        if not supp:
            supp = Supplier(name="Test Supplier", mobile="9999999999", address="Test Addr", outstanding_balance=0.0)
            self.session.add(supp)
            self.session.commit()

        # Save Purchase entry (Qty 10 @ 10000. Total = 100000. Paid = 40000. Outstanding = 60000)
        invoice_no = f"TEST-PUR-{datetime.datetime.now().microsecond}"
        total = 100000.0
        paid = 40000.0
        balance = 60000.0

        # Purchase Master
        purchase = PurchaseMaster(
            invoice_number=invoice_no,
            date=datetime.date.today(),
            supplier_id=supp.id,
            total_amount=total,
            paid_amount=paid,
            balance_payable=balance
        )
        self.session.add(purchase)
        self.session.commit()

        # Purchase Item
        p_item = PurchaseItem(purchase_id=purchase.id, product_id=prod.id, qty=10, rate=10000.0)
        self.session.add(p_item)

        # Update stock qty
        prod.stock_qty += 10
        # Update supplier outstanding
        supp.outstanding_balance += balance

        # Cash transaction log
        tx = CashTransaction(
            transaction_type='out',
            amount=paid,
            source_type='purchase',
            source_id=purchase.id,
            description=f"Paid {paid} for invoice {invoice_no}"
        )
        self.session.add(tx)

        self.session.commit()

        # Assertions
        updated_prod = self.session.query(Product).filter_by(imei="TEST-IMEI-101").first()
        self.assertEqual(updated_prod.stock_qty, 10)

        updated_supp = self.session.query(Supplier).filter_by(name="Test Supplier").first()
        self.assertEqual(updated_supp.outstanding_balance, 60000.0)

    def test_03_sales_and_stock_decrease(self):
        # Find product
        prod = self.session.query(Product).filter_by(imei="TEST-IMEI-101").first()
        self.assertIsNotNone(prod)
        self.assertEqual(prod.stock_qty, 10)

        # Setup Customer
        cust = self.session.query(Customer).filter_by(name="Test Customer").first()
        if not cust:
            cust = Customer(name="Test Customer", mobile="8888888888", address="Test Addr", outstanding_balance=0.0)
            self.session.add(cust)
            self.session.commit()

        # Sale 3 items. Unit Rate = 13000, Discount = 1000 per item. Total = (13000 * 3) - 3000 = 36000.
        # Paid = 20000. Balance Receivable = 16000.
        invoice_no = f"TEST-SAL-{datetime.datetime.now().microsecond}"
        total = 36000.0
        paid = 20000.0
        balance = 16000.0

        sale = SalesMaster(
            invoice_number=invoice_no,
            date=datetime.date.today(),
            customer_id=cust.id,
            total_amount=total,
            paid_amount=paid,
            balance_receivable=balance
        )
        self.session.add(sale)
        self.session.commit()

        s_item = SalesItem(sales_id=sale.id, product_id=prod.id, qty=3, rate=13000.0, discount=3000.0)
        self.session.add(s_item)

        # Update stock
        prod.stock_qty -= 3
        # Update customer outstanding
        cust.outstanding_balance += balance

        # Cash transaction log
        tx = CashTransaction(
            transaction_type='in',
            amount=paid,
            source_type='sale',
            source_id=sale.id,
            description=f"Received {paid} for invoice {invoice_no}"
        )
        self.session.add(tx)

        self.session.commit()

        # Assertions
        updated_prod = self.session.query(Product).filter_by(imei="TEST-IMEI-101").first()
        self.assertEqual(updated_prod.stock_qty, 7)

        updated_cust = self.session.query(Customer).filter_by(name="Test Customer").first()
        self.assertEqual(updated_cust.outstanding_balance, 16000.0)

    def test_04_payment_outstanding_reduction(self):
        cust = self.session.query(Customer).filter_by(name="Test Customer").first()
        self.assertIsNotNone(cust)
        current_bal = cust.outstanding_balance

        # Customer pays ₹5000 of outstanding
        payment_amt = 5000.0
        cust.outstanding_balance -= payment_amt

        pay_rec = Payment(
            date=datetime.date.today(),
            party_type='customer',
            party_id=cust.id,
            amount=payment_amt,
            payment_mode='Cash'
        )
        self.session.add(pay_rec)

        tx = CashTransaction(
            transaction_type='in',
            amount=payment_amt,
            source_type='payment',
            description="Customer Collection"
        )
        self.session.add(tx)

        self.session.commit()

        # Assertions
        updated_cust = self.session.query(Customer).filter_by(name="Test Customer").first()
        self.assertEqual(updated_cust.outstanding_balance, current_bal - 5000.0)

    def test_05_shop_name_settings(self):
        from models import Setting
        s_name = self.session.query(Setting).filter_by(key='shop_name').first()
        self.assertIsNotNone(s_name)
        old_val = s_name.value
        
        # Test modifying the setting
        s_name.value = "Test Apex Mobiles"
        self.session.commit()
        
        db_setting = self.session.query(Setting).filter_by(key='shop_name').first()
        self.assertEqual(db_setting.value, "Test Apex Mobiles")
        
        # Restore setting to old value
        s_name.value = old_val
        self.session.commit()

    def test_06_service_parts_inventory(self):
        # 1. Create a dummy product for spare part
        self.session.query(Product).filter_by(name="Test Spare Part Screen").delete()
        self.session.commit()
        
        prod = Product(
            name="Test Spare Part Screen", 
            brand="BrandX", 
            model="ModelY", 
            purchase_price=1500.0, 
            selling_price=2500.0, 
            stock_qty=5
        )
        self.session.add(prod)
        self.session.commit()
        
        # 2. Create a dummy Service Job
        job_no = f"TEST-JOB-{datetime.datetime.now().microsecond}"
        job = ServiceJob(
            job_number=job_no,
            customer_name="Test Service Customer",
            mobile="9876543210",
            device_model="ModelY",
            imei="TEST-IMEI-999"
        )
        self.session.add(job)
        self.session.commit()
        
        # 3. Add ServicePart linked to product (qty=2, cost=2500.0)
        part = ServicePart(
            job_id=job.id,
            product_id=prod.id,
            part_name=prod.name,
            qty=2,
            cost=2500.0
        )
        self.session.add(part)
        prod.stock_qty -= 2
        self.session.commit()
        
        # Verify initial state
        updated_prod = self.session.query(Product).get(prod.id)
        self.assertEqual(updated_prod.stock_qty, 3)
        
        # 4. Modify billing (restore old stock, save new stock)
        # Simulate restoring original stock (simulating UI rollback before save)
        original_parts = self.session.query(ServicePart).filter_by(job_id=job.id).all()
        for op in original_parts:
            if op.product_id:
                p = self.session.query(Product).get(op.product_id)
                p.stock_qty += op.qty
        
        # Delete original parts
        self.session.query(ServicePart).filter_by(job_id=job.id).delete()
        
        # Add new part list (qty=1 instead of 2)
        new_part = ServicePart(
            job_id=job.id,
            product_id=prod.id,
            part_name=prod.name,
            qty=1,
            cost=2500.0
        )
        self.session.add(new_part)
        prod.stock_qty -= 1
        self.session.commit()
        
        # Verify modified state
        updated_prod2 = self.session.query(Product).get(prod.id)
        self.assertEqual(updated_prod2.stock_qty, 4)
        
        # 5. Clean up job parts (simulating clearing parts)
        original_parts2 = self.session.query(ServicePart).filter_by(job_id=job.id).all()
        for op in original_parts2:
            if op.product_id:
                p = self.session.query(Product).get(op.product_id)
                p.stock_qty += op.qty
        self.session.query(ServicePart).filter_by(job_id=job.id).delete()
        self.session.commit()
        
        # Verify final returned state
        updated_prod3 = self.session.query(Product).get(prod.id)
        self.assertEqual(updated_prod3.stock_qty, 5)

    def test_07_bank_account_fields(self):
        # Clean up if test bank exists
        self.session.query(BankAccount).filter_by(account_name="Test Bank Account").delete()
        self.session.commit()

        # Add new bank account with new fields
        bank = BankAccount(
            bank_name="Test Bank",
            account_name="Test Bank Account",
            account_number="1234567890",
            account_type="Saving",
            balance=1000.0
        )
        self.session.add(bank)
        self.session.commit()

        db_bank = self.session.query(BankAccount).filter_by(account_name="Test Bank Account").first()
        self.assertIsNotNone(db_bank)
        self.assertEqual(db_bank.account_number, "1234567890")
        self.assertEqual(db_bank.account_type, "Saving")
        self.assertEqual(db_bank.balance, 1000.0)

        # Clean up
        self.session.delete(db_bank)
        self.session.commit()

if __name__ == '__main__':
    unittest.main()
