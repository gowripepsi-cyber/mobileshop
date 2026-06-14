import os
import unittest
import datetime
from database import Session, init_db
from models import Product, Customer, Supplier, BankAccount, PurchaseMaster, PurchaseItem, SalesMaster, SalesItem, Payment, CashTransaction, BankTransaction, ServiceJob, ServicePart, MoneyTransfer

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

    def test_08_fund_transfer(self):
        from models import FundTransfer
        
        # 1. Setup Test Bank Accounts
        self.session.query(BankAccount).filter(BankAccount.account_name.in_(["FT Source", "FT Dest"])).delete()
        self.session.commit()

        src_bank = BankAccount(bank_name="Source Bank", account_name="FT Source", balance=10000.0)
        dest_bank = BankAccount(bank_name="Dest Bank", account_name="FT Dest", balance=5000.0)
        self.session.add(src_bank)
        self.session.add(dest_bank)
        self.session.commit()

        # 2. Simulate transfer of ₹3000 from FT Source to FT Dest
        amount = 3000.0
        transfer = FundTransfer(
            date=datetime.date.today(),
            from_type='bank',
            from_account_id=src_bank.id,
            to_type='bank',
            to_account_id=dest_bank.id,
            amount=amount,
            remarks="Unit Test Transfer"
        )
        self.session.add(transfer)
        self.session.commit()

        # Update balances
        src_bank.balance -= amount
        dest_bank.balance += amount

        # Log transactions
        tx_out = BankTransaction(
            date=datetime.date.today(), transaction_type='withdrawal', account_id=src_bank.id,
            amount=amount, source_type='transfer', source_id=transfer.id, description="Transfer out"
        )
        tx_in = BankTransaction(
            date=datetime.date.today(), transaction_type='deposit', account_id=dest_bank.id,
            amount=amount, source_type='transfer', source_id=transfer.id, description="Transfer in"
        )
        self.session.add(tx_out)
        self.session.add(tx_in)
        self.session.commit()

        # Verify balances
        self.assertEqual(src_bank.balance, 7000.0)
        self.assertEqual(dest_bank.balance, 8000.0)

        # 3. Simulate reversion (deleting the transfer)
        # Revert balances
        src_bank.balance += amount
        dest_bank.balance -= amount

        # Delete transactions and transfer
        self.session.query(BankTransaction).filter_by(source_type='transfer', source_id=transfer.id).delete()
        self.session.delete(transfer)
        self.session.commit()

        # Verify reverted balances
        self.assertEqual(src_bank.balance, 10000.0)
        self.assertEqual(dest_bank.balance, 5000.0)

        # Clean up banks
        self.session.delete(src_bank)
        self.session.delete(dest_bank)
        self.session.commit()

    def test_09_direct_transaction(self):
        from models import DirectTransaction
        
        # 1. Setup Test Bank Account
        self.session.query(BankAccount).filter_by(account_name="FT Direct").delete()
        self.session.commit()

        bank = BankAccount(bank_name="Direct Bank", account_name="FT Direct", balance=5000.0)
        self.session.add(bank)
        self.session.commit()

        # 2. Deposit 2000
        dep_amount = 2000.0
        dt_dep = DirectTransaction(
            date=datetime.date.today(),
            transaction_type='deposit',
            account_type='bank',
            bank_id=bank.id,
            amount=dep_amount,
            description="Test Inflow"
        )
        self.session.add(dt_dep)
        self.session.commit()
        bank.balance += dep_amount

        # Log deposit transaction
        tx_dep = BankTransaction(
            date=datetime.date.today(), transaction_type='deposit', account_id=bank.id,
            amount=dep_amount, source_type='direct', source_id=dt_dep.id, description="Direct deposit"
        )
        self.session.add(tx_dep)
        self.session.commit()

        self.assertEqual(bank.balance, 7000.0)

        # 3. Withdraw 1000
        wdr_amount = 1000.0
        dt_wdr = DirectTransaction(
            date=datetime.date.today(),
            transaction_type='withdrawal',
            account_type='bank',
            bank_id=bank.id,
            amount=wdr_amount,
            description="Test Outflow"
        )
        self.session.add(dt_wdr)
        self.session.commit()
        bank.balance -= wdr_amount

        # Log withdrawal transaction
        tx_wdr = BankTransaction(
            date=datetime.date.today(), transaction_type='withdrawal', account_id=bank.id,
            amount=wdr_amount, source_type='direct', source_id=dt_wdr.id, description="Direct withdrawal"
        )
        self.session.add(tx_wdr)
        self.session.commit()

        self.assertEqual(bank.balance, 6000.0)

        # 4. Revert withdrawal
        bank.balance += wdr_amount
        self.session.query(BankTransaction).filter_by(source_type='direct', source_id=dt_wdr.id).delete()
        self.session.delete(dt_wdr)
        self.session.commit()

        # Revert deposit
        bank.balance -= dep_amount
        self.session.query(BankTransaction).filter_by(source_type='direct', source_id=dt_dep.id).delete()
        self.session.delete(dt_dep)
        self.session.commit()

        # Verify reverted balance
        self.assertEqual(bank.balance, 5000.0)

        # Clean up
        self.session.delete(bank)
        self.session.commit()

    def test_10_money_transfer(self):
        # 1. Setup Test Bank Accounts
        self.session.query(BankAccount).filter(BankAccount.account_name.in_(["MT Pay Bank", "MT Payout Bank"])).delete()
        self.session.commit()

        pay_bank = BankAccount(bank_name="Test Pay Bank", account_name="MT Pay Bank", balance=10000.0)
        payout_bank = BankAccount(bank_name="Test Payout Bank", account_name="MT Payout Bank", balance=15000.0)
        self.session.add(pay_bank)
        self.session.add(payout_bank)
        self.session.commit()

        # 2. Setup transaction details
        last_mt = self.session.query(MoneyTransfer).order_by(MoneyTransfer.id.desc()).first()
        tx_no = f"MT-{last_mt.id + 10001}" if last_mt else "MT-10001"
        amount = 5000.0
        charge = 150.0
        total_amount = amount + charge

        # 3. Create Money Transfer (using Bank as payment mode, and Bank as payout mode)
        mt = MoneyTransfer(
            transaction_number=tx_no,
            date=datetime.date.today(),
            customer_name="Test Sender",
            beneficiary_name="Test Beneficiary",
            transfer_type="UPI",
            upi_id="test@upi",
            amount=amount,
            service_charge=charge,
            total_amount=total_amount,
            deadline_date=datetime.date.today() + datetime.timedelta(days=1),
            remarks="Unit test transfer",
            status='Pending',
            payment_mode='Bank',
            payment_bank_id=pay_bank.id,
            payout_mode='Bank',
            payout_bank_id=payout_bank.id
        )
        self.session.add(mt)
        self.session.flush()

        # Log Inflow Ledger
        desc_in = f"Inflow for Money Transfer {tx_no} from customer Test Sender"
        tx_in = BankTransaction(
            date=datetime.date.today(), transaction_type='deposit', account_id=pay_bank.id,
            amount=total_amount, source_type='direct', source_id=mt.id, description=desc_in
        )
        self.session.add(tx_in)
        pay_bank.balance += total_amount

        # Log Outflow Ledger
        desc_out = f"Outflow for Money Transfer {tx_no} to beneficiary Test Beneficiary"
        tx_out = BankTransaction(
            date=datetime.date.today(), transaction_type='withdrawal', account_id=payout_bank.id,
            amount=amount, source_type='direct', source_id=mt.id, description=desc_out
        )
        self.session.add(tx_out)
        payout_bank.balance -= amount
        
        self.session.commit()

        # 4. Verify balances updated
        self.assertEqual(pay_bank.balance, 10000.0 + total_amount)
        self.assertEqual(payout_bank.balance, 15000.0 - amount)

        # Verify transaction entries
        db_in_tx = self.session.query(BankTransaction).filter_by(source_type='direct', source_id=mt.id, transaction_type='deposit').first()
        self.assertIsNotNone(db_in_tx)
        self.assertEqual(db_in_tx.amount, total_amount)

        db_out_tx = self.session.query(BankTransaction).filter_by(source_type='direct', source_id=mt.id, transaction_type='withdrawal').first()
        self.assertIsNotNone(db_out_tx)
        self.assertEqual(db_out_tx.amount, amount)

        # 5. Toggle status and verify
        self.assertEqual(mt.status, 'Pending')
        mt.status = 'Completed'
        self.session.commit()
        self.assertEqual(mt.status, 'Completed')

        # 6. Reversion and delete (mimic delete_transfer in ui/money_transfer.py)
        # Revert payment inflow
        pay_bank.balance -= mt.total_amount
        # Revert payout outflow
        payout_bank.balance += mt.amount

        # Delete related transactions
        self.session.query(BankTransaction).filter_by(source_type='direct', source_id=mt.id).delete()
        # Delete transfer record
        self.session.delete(mt)
        self.session.commit()

        # Verify reverted balances
        self.assertEqual(pay_bank.balance, 10000.0)
        self.assertEqual(payout_bank.balance, 15000.0)

        # Clean up bank accounts
        self.session.delete(pay_bank)
        self.session.delete(payout_bank)
        self.session.commit()

if __name__ == '__main__':
    unittest.main()


