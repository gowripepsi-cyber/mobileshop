import datetime
from PySide6.QtWidgets import QWidget, QGridLayout, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget, QTableWidgetItem, QHeaderView, QFrame
from PySide6.QtCore import Qt
from sqlalchemy import func
from database import Session
from models import Product, Customer, Supplier, BankAccount, SalesMaster, ServiceJob, CashTransaction

class DashboardView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(20)

        # 1. Grid layout for top metric cards
        self.metrics_grid = QGridLayout()
        self.metrics_grid.setSpacing(15)

        # We will initialize the metric cards
        self.cards = {}
        metric_configs = [
            ("Today's Sales", "₹0.00", 0, 0, "#6366f1"),
            ("Today's Service Income", "₹0.00", 0, 1, "#06b6d4"),
            ("Cash in Hand", "₹0.00", 0, 2, "#10b981"),
            ("Bank Balances", "₹0.00", 0, 3, "#3b82f6"),
            ("Customer Outstanding", "₹0.00", 1, 0, "#f59e0b"),
            ("Supplier Outstanding", "₹0.00", 1, 1, "#ef4444"),
            ("Low Stock Items", "0", 1, 2, "#a855f7")
        ]

        for title, default_val, row, col, border_color in metric_configs:
            card = QFrame()
            card.setProperty("class", "MetricCard")
            card.setStyleSheet(f"border-left: 4px solid {border_color};")
            
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(15, 12, 15, 12)
            
            title_lbl = QLabel(title)
            title_lbl.setProperty("class", "MetricTitle")
            
            val_lbl = QLabel(default_val)
            val_lbl.setProperty("class", "MetricValue")
            val_lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
            
            card_layout.addWidget(title_lbl)
            card_layout.addWidget(val_lbl)
            
            self.metrics_grid.addWidget(card, row, col)
            self.cards[title] = val_lbl

        self.main_layout.addLayout(self.metrics_grid)

        # 2. Bottom sections (Bank Account details and Low Stock table)
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(20)

        # Bank accounts list card
        self.bank_card = QFrame()
        self.bank_card.setProperty("class", "CardFrame")
        bank_card_layout = QVBoxLayout(self.bank_card)
        bank_card_layout.setContentsMargins(15, 15, 15, 15)
        
        bank_title = QLabel("Bank & Cash Accounts Breakdown")
        bank_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #ffffff; margin-bottom: 10px;")
        bank_card_layout.addWidget(bank_title)

        self.bank_table = QTableWidget()
        self.bank_table.setColumnCount(3)
        self.bank_table.setHorizontalHeaderLabels(["Account/Bank", "Account Name", "Current Balance"])
        self.bank_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.bank_table.verticalHeader().setVisible(False)
        self.bank_table.setFixedHeight(180)
        self.bank_table.setEditTriggers(QTableWidget.NoEditTriggers)
        bank_card_layout.addWidget(self.bank_table)

        bottom_layout.addWidget(self.bank_card, 1)

        # Low stock warnings list card
        self.low_stock_card = QFrame()
        self.low_stock_card.setProperty("class", "CardFrame")
        low_stock_layout = QVBoxLayout(self.low_stock_card)
        low_stock_layout.setContentsMargins(15, 15, 15, 15)

        low_stock_title = QLabel("Low Stock Alerts (Qty <= 5)")
        low_stock_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #ef4444; margin-bottom: 10px;")
        low_stock_layout.addWidget(low_stock_title)

        self.low_stock_table = QTableWidget()
        self.low_stock_table.setColumnCount(3)
        self.low_stock_table.setHorizontalHeaderLabels(["Product Name", "Brand / Model", "Current Stock"])
        self.low_stock_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.low_stock_table.verticalHeader().setVisible(False)
        self.low_stock_table.setFixedHeight(180)
        self.low_stock_table.setEditTriggers(QTableWidget.NoEditTriggers)
        low_stock_layout.addWidget(self.low_stock_table)

        bottom_layout.addWidget(self.low_stock_card, 1)

        self.main_layout.addLayout(bottom_layout)

    def refresh_data(self):
        session = Session()
        try:
            today = datetime.date.today()
            
            # Today's Sales
            sales_today = session.query(func.sum(SalesMaster.total_amount)).filter(SalesMaster.date == today).scalar() or 0.0
            self.cards["Today's Sales"].setText(f"₹{sales_today:,.2f}")

            # Today's Service Income (Total amount from repair jobs logged today)
            # Service jobs might record total amount
            service_today = session.query(func.sum(ServiceJob.total_amount)).filter(func.date(ServiceJob.created_at) == today).scalar() or 0.0
            self.cards["Today's Service Income"].setText(f"₹{service_today:,.2f}")

            # Cash in Hand calculation
            cash_in = session.query(func.sum(CashTransaction.amount)).filter(CashTransaction.transaction_type == 'in').scalar() or 0.0
            cash_out = session.query(func.sum(CashTransaction.amount)).filter(CashTransaction.transaction_type == 'out').scalar() or 0.0
            cash_in_hand = cash_in - cash_out
            self.cards["Cash in Hand"].setText(f"₹{cash_in_hand:,.2f}")

            # Bank Balances (sum from BankAccount table)
            banks = session.query(BankAccount).all()
            total_bank_balance = sum(b.balance for b in banks)
            self.cards["Bank Balances"].setText(f"₹{total_bank_balance:,.2f}")

            # Customer Outstanding (receivables)
            cust_outstanding = session.query(func.sum(Customer.outstanding_balance)).scalar() or 0.0
            self.cards["Customer Outstanding"].setText(f"₹{cust_outstanding:,.2f}")

            # Supplier Outstanding (payables)
            supp_outstanding = session.query(func.sum(Supplier.outstanding_balance)).scalar() or 0.0
            self.cards["Supplier Outstanding"].setText(f"₹{supp_outstanding:,.2f}")

            # Low Stock Items Count
            low_stock_qty_limit = 5
            low_stock_count = session.query(Product).filter(Product.stock_qty <= low_stock_qty_limit).count()
            self.cards["Low Stock Items"].setText(str(low_stock_count))

            # Populate Bank breakdown
            self.bank_table.setRowCount(len(banks) + 1)
            row = 0
            # Cash row first
            self.bank_table.setItem(row, 0, QTableWidgetItem("Cash Ledger"))
            self.bank_table.setItem(row, 1, QTableWidgetItem("Cash-in-Hand"))
            self.bank_table.setItem(row, 2, QTableWidgetItem(f"₹{cash_in_hand:,.2f}"))
            
            for b in banks:
                row += 1
                self.bank_table.setItem(row, 0, QTableWidgetItem(b.bank_name))
                self.bank_table.setItem(row, 1, QTableWidgetItem(b.account_name))
                self.bank_table.setItem(row, 2, QTableWidgetItem(f"₹{b.balance:,.2f}"))

            # Populate Low Stock List
            low_stock_products = session.query(Product).filter(Product.stock_qty <= low_stock_qty_limit).all()
            self.low_stock_table.setRowCount(len(low_stock_products))
            for i, p in enumerate(low_stock_products):
                self.low_stock_table.setItem(i, 0, QTableWidgetItem(p.name))
                self.low_stock_table.setItem(i, 1, QTableWidgetItem(f"{p.brand} / {p.model}"))
                qty_item = QTableWidgetItem(str(p.stock_qty))
                if p.stock_qty == 0:
                    qty_item.setForeground(Qt.red)
                else:
                    qty_item.setForeground(Qt.yellow)
                self.low_stock_table.setItem(i, 2, qty_item)

        except Exception as e:
            print(f"Error fetching dashboard metrics: {e}")
        finally:
            session.close()
