import datetime
from PySide6.QtWidgets import (QWidget, QGridLayout, QVBoxLayout, QHBoxLayout, QLabel, 
                             QTableWidget, QTableWidgetItem, QHeaderView, QFrame, QLineEdit, QPushButton,
                             QDialog, QFormLayout, QMessageBox)
from PySide6.QtCore import Qt
from sqlalchemy import func
from utils.formatters import format_inr
from database import Session
from models import Product, Customer, Supplier, BankAccount, SalesMaster, ServiceJob, CashTransaction, PurchaseMaster, Payment
from utils.unit_converter import format_product_stock

class ClickableCard(QFrame):
    def __init__(self, title, border_color, parent_view, parent=None):
        super().__init__(parent)
        self.title = title
        self.parent_view = parent_view
        self.setCursor(Qt.PointingHandCursor)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.parent_view.handle_card_click(self.title)
            event.accept()
        else:
            super().mousePressEvent(event)

class DashboardView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(20)

        # 1. Search Bar at the very top of self.main_layout
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 What do you want to find? (Search name, mobile number, job number, bill number...)")
        self.search_input.setStyleSheet("QLineEdit { font-size: 14px; padding: 12px 20px; border-radius: 22px; background-color: #f4faee; border: 1.5px solid #8fd53b; color: #0f172a; } QLineEdit:focus { border: 2px solid #8fd53b; background-color: #ffffff; }")
        self.search_input.textChanged.connect(self.handle_search)
        search_layout.addWidget(self.search_input)
        self.main_layout.addLayout(search_layout)

        # 2. Container for default dashboard content (Metrics + Bank Table + Low Stock Table)
        self.default_content = QWidget()
        default_layout = QVBoxLayout(self.default_content)
        default_layout.setContentsMargins(0, 0, 0, 0)
        default_layout.setSpacing(20)

        # Grid layout for top metric cards
        self.metrics_grid = QGridLayout()
        self.metrics_grid.setSpacing(15)

        # We will initialize the metric cards
        self.cards = {}
        self.card_widgets = {}
        metric_configs = [
            ("Today's Sales", "₹0.00", "#6366f1"),
            ("Today's Service Income", "₹0.00", "#06b6d4"),
            ("Cash in Hand", "₹0.00", "#8fd53b"),
            ("Bank Balances", "₹0.00", "#3b82f6"),
            ("Customer Outstanding", "₹0.00", "#f59e0b"),
            ("Supplier Outstanding", "₹0.00", "#ef4444"),
            ("Low Stock Items", "0", "#a855f7")
        ]

        for title, default_val, border_color in metric_configs:
            is_clickable = title in ["Customer Outstanding", "Supplier Outstanding"]
            if is_clickable:
                card = ClickableCard(title, border_color, self)
                card.setProperty("class", "ClickableMetricCard")
            else:
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
            
            self.cards[title] = val_lbl
            self.card_widgets[title] = card

        # Query setting for initial layout
        from database import Setting
        session = Session()
        enable_repair = True
        try:
            val = session.query(Setting).filter_by(key='enable_repair_service').first()
            if val and val.value == 'false':
                enable_repair = False
        except Exception:
            pass
        finally:
            session.close()

        self.update_metrics_layout(enable_repair)
        default_layout.addLayout(self.metrics_grid)

        # Bottom sections (Bank Account details and Low Stock table)
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(20)

        # Bank accounts list card
        self.bank_card = QFrame()
        self.bank_card.setProperty("class", "CardFrame")
        bank_card_layout = QVBoxLayout(self.bank_card)
        bank_card_layout.setContentsMargins(15, 15, 15, 15)
        
        bank_title = QLabel("Bank & Cash Accounts Breakdown")
        bank_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #0f172a; margin-bottom: 10px;")
        bank_card_layout.addWidget(bank_title)

        self.bank_table = QTableWidget()
        self.bank_table.setColumnCount(3)
        self.bank_table.setHorizontalHeaderLabels(["Account/Bank", "Account Name", "Current Balance"])
        self.bank_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.bank_table.verticalHeader().setVisible(False)
        self.bank_table.setFixedHeight(432)
        self.bank_table.setEditTriggers(QTableWidget.NoEditTriggers)
        bank_card_layout.addWidget(self.bank_table)

        bottom_layout.addWidget(self.bank_card, 1)

        # Low stock warnings list card
        self.low_stock_card = QFrame()
        self.low_stock_card.setProperty("class", "CardFrame")
        low_stock_layout = QVBoxLayout(self.low_stock_card)
        low_stock_layout.setContentsMargins(15, 15, 15, 15)

        title_btn_layout = QHBoxLayout()
        self.low_stock_title_lbl = QLabel("Low Stock Alerts (Per-Item Limits)")
        self.low_stock_title_lbl.setStyleSheet("font-size: 15px; font-weight: bold; color: #ef4444; margin-bottom: 10px;")
        title_btn_layout.addWidget(self.low_stock_title_lbl)
        title_btn_layout.addStretch()
        
        self.check_now_btn = QPushButton("🔔 Check Now")
        self.check_now_btn.setFixedWidth(110)
        self.check_now_btn.setFixedHeight(44)
        self.check_now_btn.setStyleSheet("font-size: 11px; background-color: #3b82f6; color: white; border-radius: 4px; margin-bottom: 10px; padding: 0px 10px;")
        self.check_now_btn.clicked.connect(self.trigger_manual_low_stock_check)
        title_btn_layout.addWidget(self.check_now_btn)

        self.print_preview_btn = QPushButton("📄 Print Preview")
        self.print_preview_btn.setFixedWidth(120)
        self.print_preview_btn.setFixedHeight(44)
        self.print_preview_btn.setStyleSheet("font-size: 11px; background-color: #8fd53b; color: #0f172a; font-weight: bold; border-radius: 8px; margin-bottom: 10px; padding: 0px 10px;")
        self.print_preview_btn.clicked.connect(self.show_low_stock_print_preview)
        title_btn_layout.addWidget(self.print_preview_btn)

        self.purchase_order_btn = QPushButton("🛒 Purchase Order")
        self.purchase_order_btn.setFixedWidth(135)
        self.purchase_order_btn.setFixedHeight(44)
        self.purchase_order_btn.setStyleSheet("font-size: 11px; background-color: #f59e0b; color: white; font-weight: bold; border-radius: 8px; margin-bottom: 10px; padding: 0px 10px;")
        self.purchase_order_btn.setCursor(Qt.PointingHandCursor)
        self.purchase_order_btn.clicked.connect(self.open_purchase_order_dialog)
        title_btn_layout.addWidget(self.purchase_order_btn)
        
        low_stock_layout.addLayout(title_btn_layout)

        self.low_stock_table = QTableWidget()
        self.low_stock_table.setColumnCount(4)
        self.low_stock_table.setHorizontalHeaderLabels(["Product Name", "Brand / Model", "Current Stock", "Low Limit"])
        self.low_stock_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.low_stock_table.verticalHeader().setVisible(False)
        self.low_stock_table.setFixedHeight(432)
        self.low_stock_table.setEditTriggers(QTableWidget.NoEditTriggers)
        low_stock_layout.addWidget(self.low_stock_table)

        bottom_layout.addWidget(self.low_stock_card, 1)

        default_layout.addLayout(bottom_layout)
        default_layout.addStretch(1)
        self.main_layout.addWidget(self.default_content)

        # 3. Search Results Panel (Card Frame) - Starts Hidden
        self.search_results_card = QFrame()
        self.search_results_card.setProperty("class", "CardFrame")
        self.search_results_card.setVisible(False)
        results_layout = QVBoxLayout(self.search_results_card)
        results_layout.setContentsMargins(15, 15, 15, 15)

        results_title = QLabel("Search Results")
        results_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #0f172a; margin-bottom: 10px;")
        results_layout.addWidget(results_title)

        self.results_table = QTableWidget()
        self.results_table.setColumnCount(4)
        self.results_table.setHorizontalHeaderLabels(["Type", "Reference / Name", "Details", "Action"])
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.results_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.results_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Fixed)
        self.results_table.setColumnWidth(3, 150)
        self.results_table.verticalHeader().setVisible(False)
        self.results_table.verticalHeader().setDefaultSectionSize(50)
        self.results_table.setEditTriggers(QTableWidget.NoEditTriggers)
        results_layout.addWidget(self.results_table)

        self.main_layout.addWidget(self.search_results_card)

    def update_metrics_layout(self, enable_repair):
        # Clear layout items (but keep widgets intact)
        while self.metrics_grid.count() > 0:
            self.metrics_grid.takeAt(0)

        visible_titles = [
            "Today's Sales",
        ]
        if enable_repair:
            visible_titles.append("Today's Service Income")
            
        visible_titles.extend([
            "Cash in Hand",
            "Bank Balances",
            "Customer Outstanding",
            "Supplier Outstanding",
            "Low Stock Items"
        ])
        
        for idx, title in enumerate(visible_titles):
            card = self.card_widgets[title]
            card.setVisible(True)
            row = idx // 4
            col = idx % 4
            self.metrics_grid.addWidget(card, row, col)
            
        # Hide any card not in visible_titles
        for title, card in self.card_widgets.items():
            if title not in visible_titles:
                card.setVisible(False)

    def refresh_data(self):
        from database import Setting
        session = Session()
        try:
            enable_repair = True
            val = session.query(Setting).filter_by(key='enable_repair_service').first()
            if val and val.value == 'false':
                enable_repair = False

            self.update_metrics_layout(enable_repair)

            today = datetime.date.today()
            
            # Today's Sales
            sales_today = session.query(func.sum(SalesMaster.total_amount)).filter(SalesMaster.date == today).scalar() or 0.0
            self.cards["Today's Sales"].setText(f"₹{format_inr(sales_today)}")

            # Today's Service Income (Total amount from repair jobs logged today)
            if enable_repair:
                service_today = session.query(func.sum(ServiceJob.total_amount)).filter(func.date(ServiceJob.created_at) == today).scalar() or 0.0
                self.cards["Today's Service Income"].setText(f"₹{format_inr(service_today)}")

            # Cash in Hand calculation
            cash_in = session.query(func.sum(CashTransaction.amount)).filter(CashTransaction.transaction_type == 'in').scalar() or 0.0
            cash_out = session.query(func.sum(CashTransaction.amount)).filter(CashTransaction.transaction_type == 'out').scalar() or 0.0
            cash_in_hand = cash_in - cash_out
            self.cards["Cash in Hand"].setText(f"₹{format_inr(cash_in_hand)}")

            # Bank Balances (sum from BankAccount table)
            banks = session.query(BankAccount).all()
            total_bank_balance = sum(b.balance for b in banks)
            self.cards["Bank Balances"].setText(f"₹{format_inr(total_bank_balance)}")

            # Customer Outstanding (receivables)
            cust_outstanding = session.query(func.sum(Customer.outstanding_balance)).scalar() or 0.0
            self.cards["Customer Outstanding"].setText(f"₹{format_inr(cust_outstanding)}")

            # Supplier Outstanding (payables)
            supp_outstanding = session.query(func.sum(Supplier.outstanding_balance)).scalar() or 0.0
            self.cards["Supplier Outstanding"].setText(f"₹{format_inr(supp_outstanding)}")

            # Low Stock Items Count
            self.low_stock_title_lbl.setText("Low Stock Alerts (Per-Item Limits)")
            
            low_stock_count = session.query(Product).filter(Product.stock_qty <= Product.low_stock_limit).count()
            self.cards["Low Stock Items"].setText(str(low_stock_count))

            # Populate Bank breakdown
            self.bank_table.setRowCount(len(banks) + 1)
            row = 0
            # Cash row first
            self.bank_table.setItem(row, 0, QTableWidgetItem("Cash Ledger"))
            self.bank_table.setItem(row, 1, QTableWidgetItem("Cash-in-Hand"))
            self.bank_table.setItem(row, 2, QTableWidgetItem(f"₹{format_inr(cash_in_hand)}"))
            
            for b in banks:
                row += 1
                self.bank_table.setItem(row, 0, QTableWidgetItem(b.bank_name))
                self.bank_table.setItem(row, 1, QTableWidgetItem(b.account_name))
                self.bank_table.setItem(row, 2, QTableWidgetItem(f"₹{format_inr(b.balance)}"))

            # Populate Low Stock List
            low_stock_products = session.query(Product).filter(Product.stock_qty <= Product.low_stock_limit).all()
            self.low_stock_table.setRowCount(len(low_stock_products))
            for i, p in enumerate(low_stock_products):
                self.low_stock_table.setItem(i, 0, QTableWidgetItem(p.name))
                self.low_stock_table.setItem(i, 1, QTableWidgetItem(p.brand_model or p.brand or "-"))
                qty_item = QTableWidgetItem(format_product_stock(p, session))
                if p.stock_qty <= 0:
                    qty_item.setForeground(Qt.red)
                else:
                    qty_item.setForeground(Qt.yellow)
                self.low_stock_table.setItem(i, 2, qty_item)
                self.low_stock_table.setItem(i, 3, QTableWidgetItem(str(p.low_stock_limit)))

        except Exception as e:
            print(f"Error fetching dashboard metrics: {e}")
        finally:
            session.close()

    def handle_search(self, text):
        query_text = text.strip()
        if not query_text or len(query_text) < 2:
            self.search_results_card.setVisible(False)
            self.default_content.setVisible(True)
            self.results_table.setRowCount(0)
            return

        self.default_content.setVisible(False)
        self.search_results_card.setVisible(True)
        self.perform_global_search(query_text)

    def perform_global_search(self, query_text):
        session = Session()
        try:
            results = []
            
            # 1. Search Customers by name or mobile number
            customers = session.query(Customer).filter(
                (Customer.name.ilike(f"%{query_text}%")) |
                (Customer.mobile.ilike(f"%{query_text}%"))
            ).limit(10).all()
            for c in customers:
                results.append({
                    "type": "Customer",
                    "ref": c.name,
                    "details": f"Mobile: {c.mobile} | Outstanding: ₹{format_inr(c.outstanding_balance)}",
                    "id": c.id,
                    "obj_ref": c.mobile
                })

            # 2. Search Suppliers by name or mobile number
            suppliers = session.query(Supplier).filter(
                (Supplier.name.ilike(f"%{query_text}%")) |
                (Supplier.mobile.ilike(f"%{query_text}%"))
            ).limit(10).all()
            for s in suppliers:
                results.append({
                    "type": "Supplier",
                    "ref": s.name,
                    "details": f"Mobile: {s.mobile} | Outstanding: ₹{format_inr(s.outstanding_balance)}",
                    "id": s.id,
                    "obj_ref": s.mobile
                })

            # 3. Search Sales Invoices by invoice_number or customer details
            sales = session.query(SalesMaster).join(Customer).filter(
                (SalesMaster.invoice_number.ilike(f"%{query_text}%")) |
                (Customer.name.ilike(f"%{query_text}%")) |
                (Customer.mobile.ilike(f"%{query_text}%"))
            ).limit(10).all()
            for s in sales:
                results.append({
                    "type": "Sales Invoice",
                    "ref": s.invoice_number,
                    "details": f"Customer: {s.customer.name if s.customer else 'Deleted'} | Total: ₹{format_inr(s.total_amount)} | Date: {s.date.strftime('%Y-%m-%d')}",
                    "id": s.id,
                    "obj_ref": s.invoice_number
                })

            # 4. Search Purchase Invoices by invoice_number or supplier details
            purchases = session.query(PurchaseMaster).join(Supplier).filter(
                (PurchaseMaster.invoice_number.ilike(f"%{query_text}%")) |
                (Supplier.name.ilike(f"%{query_text}%")) |
                (Supplier.mobile.ilike(f"%{query_text}%"))
            ).limit(10).all()
            for p in purchases:
                results.append({
                    "type": "Purchase Bill",
                    "ref": p.invoice_number,
                    "details": f"Supplier: {p.supplier.name if p.supplier else 'Deleted'} | Total: ₹{format_inr(p.total_amount)} | Date: {p.date.strftime('%Y-%m-%d')}",
                    "id": p.id,
                    "obj_ref": p.invoice_number
                })

            # 5. Search Repair Job Cards by job_number, customer_name, mobile, or device_model
            jobs = session.query(ServiceJob).filter(
                (ServiceJob.job_number.ilike(f"%{query_text}%")) |
                (ServiceJob.customer_name.ilike(f"%{query_text}%")) |
                (ServiceJob.mobile.ilike(f"%{query_text}%")) |
                (ServiceJob.device_model.ilike(f"%{query_text}%")) |
                (ServiceJob.imei.ilike(f"%{query_text}%"))
            ).limit(10).all()
            for j in jobs:
                results.append({
                    "type": "Repair Job Card",
                    "ref": j.job_number,
                    "details": f"Customer: {j.customer_name} | Device: {j.device_model} | Status: {j.status}",
                    "id": j.id,
                    "obj_ref": j.job_number
                })

            # 6. Search Products by name, product_code, brand, or model
            products = session.query(Product).filter(
                (Product.name.ilike(f"%{query_text}%")) |
                (Product.product_code.ilike(f"%{query_text}%")) |
                (Product.brand.ilike(f"%{query_text}%")) |
                (Product.model.ilike(f"%{query_text}%"))
            ).limit(10).all()
            for prod in products:
                bm = f" ({prod.brand} {prod.model})".strip() if (prod.brand or prod.model) else ""
                stock_info = format_product_stock(prod, session)
                results.append({
                    "type": "Product",
                    "ref": f"{prod.name}{bm}",
                    "details": f"Code: {prod.product_code} | Stock: {stock_info} | Price: ₹{format_inr(prod.selling_price)}",
                    "id": prod.id,
                    "obj_ref": prod.product_code
                })

            # Populate table
            self.results_table.setRowCount(len(results))
            for i, r in enumerate(results):
                self.results_table.setItem(i, 0, QTableWidgetItem(r["type"]))
                self.results_table.setItem(i, 1, QTableWidgetItem(r["ref"]))
                self.results_table.setItem(i, 2, QTableWidgetItem(r["details"]))

                # View details action button
                btn_container = QWidget()
                btn_layout = QHBoxLayout(btn_container)
                btn_layout.setContentsMargins(4, 4, 4, 4)
                btn_layout.setSpacing(0)
                btn_layout.setAlignment(Qt.AlignCenter)

                view_btn = QPushButton("View")
                view_btn.setProperty("class", "btn-action-view")
                view_btn.setFixedHeight(24)
                view_btn.setFixedWidth(75)
                view_btn.clicked.connect(lambda checked, res=r: self.open_search_result(res))
                btn_layout.addWidget(view_btn)
                self.results_table.setCellWidget(i, 3, btn_container)

        except Exception as e:
            print(f"Error performing search: {e}")
        finally:
            session.close()

    def open_search_result(self, res):
        main_window = self.window()
        res_type = res["type"]
        res_id = res["id"]
        res_ref = res["obj_ref"]

        if res_type == "Sales Invoice":
            if hasattr(main_window, 'sales_view'):
                main_window.sales_view.view_invoice_details(res_id)
        elif res_type == "Purchase Bill":
            if hasattr(main_window, 'purchase_view'):
                main_window.purchase_view.view_purchase_details(res_id)
        elif res_type == "Repair Job Card":
            if hasattr(main_window, 'services_view'):
                main_window.services_view.view_job_details(res_ref)
        elif res_type == "Customer":
            self.view_customer_details(res_id)
        elif res_type == "Supplier":
            self.view_supplier_details(res_id)
        elif res_type == "Product":
            self.view_product_details(res_id)

    def view_customer_details(self, customer_id):
        session = Session()
        try:
            cust = session.query(Customer).get(customer_id)
            if not cust:
                QMessageBox.warning(self, "Error", "Customer not found.")
                return

            dialog = QDialog(self)
            dialog.setWindowTitle(f"Customer Details - {cust.name}")
            dialog.setMinimumSize(700, 520)

            dlg_layout = QVBoxLayout(dialog)
            dlg_layout.setSpacing(12)
            dlg_layout.setContentsMargins(18, 18, 18, 18)

            # Customer Profile Info Frame
            info_frame = QFrame()
            info_frame.setProperty("class", "CardFrame")
            info_layout = QFormLayout(info_frame)
            info_layout.setSpacing(8)

            lbl_name = QLabel(cust.name)
            lbl_name.setStyleSheet("font-weight: bold; font-size: 14px; color: #0f172a;")
            info_layout.addRow("Customer Name:", lbl_name)
            info_layout.addRow("Mobile Number:", QLabel(cust.mobile or "-"))
            info_layout.addRow("Address:", QLabel(cust.address or "-"))
            if cust.gst:
                info_layout.addRow("GSTIN:", QLabel(cust.gst))

            lbl_bal = QLabel(f"₹{format_inr(cust.outstanding_balance)}")
            if cust.outstanding_balance > 0:
                lbl_bal.setStyleSheet("font-weight: bold; font-size: 14px; color: #dc2626;")
            else:
                lbl_bal.setStyleSheet("font-weight: bold; font-size: 14px; color: #16a34a;")
            info_layout.addRow("Outstanding Balance:", lbl_bal)

            dlg_layout.addWidget(info_frame)

            # Recent Invoices & Repair Jobs Table
            history_title = QLabel("<b>Recent Invoices & Service History:</b>")
            history_title.setStyleSheet("font-size: 13px; color: #0f172a; margin-top: 4px;")
            dlg_layout.addWidget(history_title)

            table = QTableWidget()
            table.setColumnCount(5)
            table.setHorizontalHeaderLabels(["Date", "Type", "Ref # / Details", "Amount (₹)", "Status / Balance"])
            table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
            table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
            table.setColumnWidth(0, 95)
            table.setColumnWidth(1, 105)
            table.setColumnWidth(3, 100)
            table.setColumnWidth(4, 110)
            table.verticalHeader().setVisible(False)
            table.setSelectionBehavior(QTableWidget.SelectRows)

            sales = session.query(SalesMaster).filter_by(customer_id=cust.id).order_by(SalesMaster.id.desc()).limit(10).all()
            jobs = session.query(ServiceJob).filter_by(mobile=cust.mobile).order_by(ServiceJob.id.desc()).limit(10).all() if cust.mobile else []

            rows = []
            for s in sales:
                dt_str = s.date.strftime("%Y-%m-%d") if s.date else "-"
                bal_str = f"Bal: ₹{format_inr(s.balance_receivable)}" if s.balance_receivable > 0 else "Paid"
                rows.append((s.date or datetime.date.min, dt_str, "Sales Invoice", s.invoice_number, f"{format_inr(s.total_amount)}", bal_str))
            for j in jobs:
                j_dt = j.created_at.date() if isinstance(j.created_at, datetime.datetime) else j.created_at
                dt_str = j_dt.strftime("%Y-%m-%d") if j_dt else "-"
                bal_str = f"Bal: ₹{format_inr(j.balance)}" if j.balance > 0 else j.status
                rows.append((j_dt or datetime.date.min, dt_str, "Repair Job", f"{j.job_number} ({j.device_model})", f"{format_inr(j.total_amount)}", bal_str))

            rows.sort(key=lambda r: r[0], reverse=True)
            table.setRowCount(len(rows))
            for i, r in enumerate(rows):
                table.setItem(i, 0, QTableWidgetItem(r[1]))
                table.setItem(i, 1, QTableWidgetItem(r[2]))
                table.setItem(i, 2, QTableWidgetItem(r[3]))
                table.setItem(i, 3, QTableWidgetItem(r[4]))
                table.setItem(i, 4, QTableWidgetItem(r[5]))

            dlg_layout.addWidget(table)

            # Bottom Action Buttons
            btn_layout = QHBoxLayout()

            ledger_btn = QPushButton("📜 View Full Ledger")
            ledger_btn.setProperty("class", "btn-warning")
            def open_ledger():
                from ui.masters.ledger_dialog import LedgerBreakupDialog
                dlg_led = LedgerBreakupDialog(party_type='customer', party_id=cust.id, party_name=cust.name, parent=dialog)
                dlg_led.exec()
            ledger_btn.clicked.connect(open_ledger)
            btn_layout.addWidget(ledger_btn)

            edit_btn = QPushButton("✏️ Edit Customer")
            edit_btn.setProperty("class", "btn-secondary")
            def open_edit():
                from ui.masters.customers import CustomerDialog
                dlg_edit = CustomerDialog(customer=cust, parent=dialog)
                if dlg_edit.exec() == QDialog.Accepted:
                    dialog.accept()
                    self.perform_global_search(self.search_input.text().strip())
            edit_btn.clicked.connect(open_edit)
            btn_layout.addWidget(edit_btn)

            master_btn = QPushButton("📁 Go to Master Records")
            master_btn.setProperty("class", "btn-secondary")
            def goto_master():
                dialog.accept()
                main_win = self.window()
                if hasattr(main_win, 'switch_view'):
                    main_win.switch_view(1)
                    if hasattr(main_win, 'masters_view'):
                        main_win.masters_view.set_active_tab(2)
                    if hasattr(main_win, 'customers_view'):
                        main_win.customers_view.search_input.setText(cust.name)
            master_btn.clicked.connect(goto_master)
            btn_layout.addWidget(master_btn)

            btn_layout.addStretch()

            close_btn = QPushButton("Close")
            close_btn.clicked.connect(dialog.accept)
            btn_layout.addWidget(close_btn)

            dlg_layout.addLayout(btn_layout)
            dialog.exec()

        except Exception as e:
            print(f"Error viewing customer details: {e}")
        finally:
            session.close()

    def view_supplier_details(self, supplier_id):
        session = Session()
        try:
            supp = session.query(Supplier).get(supplier_id)
            if not supp:
                QMessageBox.warning(self, "Error", "Supplier not found.")
                return

            dialog = QDialog(self)
            dialog.setWindowTitle(f"Supplier Details - {supp.name}")
            dialog.setMinimumSize(700, 520)

            dlg_layout = QVBoxLayout(dialog)
            dlg_layout.setSpacing(12)
            dlg_layout.setContentsMargins(18, 18, 18, 18)

            # Supplier Profile Info Frame
            info_frame = QFrame()
            info_frame.setProperty("class", "CardFrame")
            info_layout = QFormLayout(info_frame)
            info_layout.setSpacing(8)

            lbl_name = QLabel(supp.name)
            lbl_name.setStyleSheet("font-weight: bold; font-size: 14px; color: #0f172a;")
            info_layout.addRow("Supplier Name:", lbl_name)
            info_layout.addRow("Mobile Number:", QLabel(supp.mobile or "-"))
            info_layout.addRow("Address:", QLabel(supp.address or "-"))
            if supp.gst:
                info_layout.addRow("GSTIN:", QLabel(supp.gst))

            lbl_bal = QLabel(f"₹{format_inr(supp.outstanding_balance)}")
            if supp.outstanding_balance > 0:
                lbl_bal.setStyleSheet("font-weight: bold; font-size: 14px; color: #dc2626;")
            else:
                lbl_bal.setStyleSheet("font-weight: bold; font-size: 14px; color: #16a34a;")
            info_layout.addRow("Outstanding Balance:", lbl_bal)

            dlg_layout.addWidget(info_frame)

            # Recent Purchase Bills Table
            history_title = QLabel("<b>Recent Purchase History:</b>")
            history_title.setStyleSheet("font-size: 13px; color: #0f172a; margin-top: 4px;")
            dlg_layout.addWidget(history_title)

            table = QTableWidget()
            table.setColumnCount(4)
            table.setHorizontalHeaderLabels(["Date", "Invoice / Bill #", "Total Amount (₹)", "Balance (₹)"])
            table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
            table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
            table.setColumnWidth(0, 110)
            table.setColumnWidth(2, 130)
            table.setColumnWidth(3, 130)
            table.verticalHeader().setVisible(False)
            table.setSelectionBehavior(QTableWidget.SelectRows)

            purchases = session.query(PurchaseMaster).filter_by(supplier_id=supp.id).order_by(PurchaseMaster.id.desc()).limit(15).all()
            table.setRowCount(len(purchases))
            for i, p in enumerate(purchases):
                dt_str = p.date.strftime("%Y-%m-%d") if p.date else "-"
                table.setItem(i, 0, QTableWidgetItem(dt_str))
                table.setItem(i, 1, QTableWidgetItem(p.invoice_number))
                table.setItem(i, 2, QTableWidgetItem(f"{format_inr(p.total_amount)}"))
                bal_str = f"{format_inr(p.balance_payable)}" if p.balance_payable > 0 else "Paid"
                table.setItem(i, 3, QTableWidgetItem(bal_str))

            dlg_layout.addWidget(table)

            # Bottom Action Buttons
            btn_layout = QHBoxLayout()

            ledger_btn = QPushButton("📜 View Full Ledger")
            ledger_btn.setProperty("class", "btn-warning")
            def open_ledger():
                from ui.masters.ledger_dialog import LedgerBreakupDialog
                dlg_led = LedgerBreakupDialog(party_type='supplier', party_id=supp.id, party_name=supp.name, parent=dialog)
                dlg_led.exec()
            ledger_btn.clicked.connect(open_ledger)
            btn_layout.addWidget(ledger_btn)

            edit_btn = QPushButton("✏️ Edit Supplier")
            edit_btn.setProperty("class", "btn-secondary")
            def open_edit():
                from ui.masters.suppliers import SupplierDialog
                dlg_edit = SupplierDialog(supplier=supp, parent=dialog)
                if dlg_edit.exec() == QDialog.Accepted:
                    dialog.accept()
                    self.perform_global_search(self.search_input.text().strip())
            edit_btn.clicked.connect(open_edit)
            btn_layout.addWidget(edit_btn)

            master_btn = QPushButton("📁 Go to Master Records")
            master_btn.setProperty("class", "btn-secondary")
            def goto_master():
                dialog.accept()
                main_win = self.window()
                if hasattr(main_win, 'switch_view'):
                    main_win.switch_view(1)
                    if hasattr(main_win, 'masters_view'):
                        main_win.masters_view.set_active_tab(3)
                    if hasattr(main_win, 'suppliers_view'):
                        main_win.suppliers_view.search_input.setText(supp.name)
            master_btn.clicked.connect(goto_master)
            btn_layout.addWidget(master_btn)

            btn_layout.addStretch()

            close_btn = QPushButton("Close")
            close_btn.clicked.connect(dialog.accept)
            btn_layout.addWidget(close_btn)

            dlg_layout.addLayout(btn_layout)
            dialog.exec()

        except Exception as e:
            print(f"Error viewing supplier details: {e}")
        finally:
            session.close()

    def view_product_details(self, product_id):
        session = Session()
        try:
            prod = session.query(Product).get(product_id)
            if not prod:
                QMessageBox.warning(self, "Error", "Product not found.")
                return

            dialog = QDialog(self)
            dialog.setWindowTitle(f"Product Details - {prod.name}")
            dialog.setMinimumSize(540, 420)

            dlg_layout = QVBoxLayout(dialog)
            dlg_layout.setSpacing(12)
            dlg_layout.setContentsMargins(18, 18, 18, 18)

            info_frame = QFrame()
            info_frame.setProperty("class", "CardFrame")
            info_layout = QFormLayout(info_frame)
            info_layout.setSpacing(8)

            lbl_name = QLabel(prod.name)
            lbl_name.setStyleSheet("font-weight: bold; font-size: 14px; color: #0f172a;")
            info_layout.addRow("Product Name:", lbl_name)
            info_layout.addRow("Product Code:", QLabel(prod.product_code or "-"))
            info_layout.addRow("Category:", QLabel(str(prod.category) if prod.category else "-"))
            info_layout.addRow("Brand / Model:", QLabel(f"{prod.brand or '-'} / {prod.model or '-'}"))
            info_layout.addRow("Unit:", QLabel(prod.unit or "Pcs"))
            info_layout.addRow("Selling Price (₹):", QLabel(f"₹{format_inr(prod.selling_price)}"))
            info_layout.addRow("Cost Price (₹):", QLabel(f"₹{format_inr(prod.cost_price)}"))

            stock_lbl = QLabel(format_product_stock(prod, session))
            if prod.stock_qty <= prod.low_stock_limit:
                stock_lbl.setStyleSheet("font-weight: bold; color: #dc2626;")
            else:
                stock_lbl.setStyleSheet("font-weight: bold; color: #16a34a;")
            info_layout.addRow("Current Stock:", stock_lbl)
            info_layout.addRow("Low Stock Limit:", QLabel(str(prod.low_stock_limit)))

            dlg_layout.addWidget(info_frame)
            dlg_layout.addStretch()

            btn_layout = QHBoxLayout()
            edit_btn = QPushButton("✏️ Edit Product")
            edit_btn.setProperty("class", "btn-secondary")
            def open_edit():
                from ui.masters.products import ProductDialog
                dlg_edit = ProductDialog(product=prod, parent=dialog)
                if dlg_edit.exec() == QDialog.Accepted:
                    dialog.accept()
                    self.perform_global_search(self.search_input.text().strip())
            edit_btn.clicked.connect(open_edit)
            btn_layout.addWidget(edit_btn)

            master_btn = QPushButton("📁 Go to Products Master")
            master_btn.setProperty("class", "btn-secondary")
            def goto_master():
                dialog.accept()
                main_win = self.window()
                if hasattr(main_win, 'switch_view'):
                    main_win.switch_view(1)
                    if hasattr(main_win, 'masters_view'):
                        main_win.masters_view.set_active_tab(0)
                    if hasattr(main_win, 'products_view'):
                        main_win.products_view.search_input.setText(prod.product_code or prod.name)
            master_btn.clicked.connect(goto_master)
            btn_layout.addWidget(master_btn)

            btn_layout.addStretch()
            close_btn = QPushButton("Close")
            close_btn.clicked.connect(dialog.accept)
            btn_layout.addWidget(close_btn)

            dlg_layout.addLayout(btn_layout)
            dialog.exec()

        except Exception as e:
            print(f"Error viewing product details: {e}")
        finally:
            session.close()

    def handle_card_click(self, title):
        main_win = self.window()
        if title == "Customer Outstanding":
            if hasattr(main_win, 'switch_view'):
                main_win.switch_view(6)  # Reports View index
                if hasattr(main_win, 'reports_view'):
                    main_win.reports_view.tabs.setCurrentIndex(3)  # Customer Receivables tab
        elif title == "Supplier Outstanding":
            if hasattr(main_win, 'switch_view'):
                main_win.switch_view(6)  # Reports View index
                if hasattr(main_win, 'reports_view'):
                    main_win.reports_view.tabs.setCurrentIndex(4)  # Supplier Payables tab

    def trigger_manual_low_stock_check(self):
        main_win = self.window()
        if hasattr(main_win, 'check_low_stock_alert'):
            main_win.check_low_stock_alert(manual=True)

    def open_purchase_order_dialog(self):
        from ui.inventory.purchase_order import PurchaseOrderDialog
        dlg = PurchaseOrderDialog(self)
        dlg.exec()
        self.refresh_data()

    def show_low_stock_print_preview(self):
        import os
        from database import Session, Setting
        from models import Product
        from utils.pdf_generator import generate_low_stock_pdf
        from PySide6.QtWidgets import QMessageBox
        
        session = Session()
        try:
            # 1. Fetch Shop details
            s_name = session.query(Setting).filter_by(key='shop_name').first()
            s_contact = session.query(Setting).filter_by(key='shop_contact').first()
            s_address = session.query(Setting).filter_by(key='shop_address').first()
            s_gst = session.query(Setting).filter_by(key='shop_gst').first()
            
            shop_name = s_name.value if s_name else "SUN COMPUTERS,"
            shop_contact = s_contact.value if s_contact else "N/A"
            shop_address = s_address.value if s_address else "N/A"
            shop_gst = s_gst.value if s_gst else "N/A"
            
            # 2. Fetch Low Stock items
            low_stock_products = session.query(Product).filter(Product.stock_qty <= Product.low_stock_limit).all()
            if not low_stock_products:
                QMessageBox.information(self, "No Low Stock", "There are currently no products with low stock to print!")
                return
                
            # Prepare data
            items_data = []
            for p in low_stock_products:
                p_code = f"[{p.product_code}] " if p.product_code else ""
                items_data.append({
                    "name": f"{p_code}{p.name}",
                    "brand_model": f"{p.brand} / {p.model}",
                    "current_stock": p.stock_qty,
                    "low_limit": p.low_stock_limit
                })
                
            report_data = {
                "shop_name": shop_name,
                "shop_contact": shop_contact,
                "shop_address": shop_address,
                "shop_gst": shop_gst,
                "date": datetime.date.today().strftime("%Y-%m-%d"),
                "items": items_data
            }
            
            os.makedirs("statements", exist_ok=True)
            path = os.path.abspath("statements/low_stock_report.pdf")
            generate_low_stock_pdf(report_data, path)
            
            QMessageBox.information(self, "Success", f"Low Stock Report PDF generated at:\n{path}")
            try:
                os.startfile(path)
            except Exception as e:
                print(f"Could not auto-open PDF: {e}")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate Low Stock Report: {e}")
        finally:
            session.close()
