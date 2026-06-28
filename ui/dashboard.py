import datetime
from PySide6.QtWidgets import (QWidget, QGridLayout, QVBoxLayout, QHBoxLayout, QLabel, 
                             QTableWidget, QTableWidgetItem, QHeaderView, QFrame, QLineEdit, QPushButton)
from PySide6.QtCore import Qt
from sqlalchemy import func
from database import Session
from models import Product, Customer, Supplier, BankAccount, SalesMaster, ServiceJob, CashTransaction, PurchaseMaster

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
        self.search_input.setPlaceholderText("🔍 Search name, mobile number, job number, bill number...")
        self.search_input.setStyleSheet("font-size: 14px; padding: 10px 15px; border-radius: 8px;")
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
            ("Cash in Hand", "₹0.00", "#10b981"),
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
        bank_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #ffffff; margin-bottom: 10px;")
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
        self.print_preview_btn.setStyleSheet("font-size: 11px; background-color: #10b981; color: white; border-radius: 4px; margin-bottom: 10px; padding: 0px 10px;")
        self.print_preview_btn.clicked.connect(self.show_low_stock_print_preview)
        title_btn_layout.addWidget(self.print_preview_btn)
        
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
        results_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #6366f1; margin-bottom: 10px;")
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
            self.cards["Today's Sales"].setText(f"₹{sales_today:,.2f}")

            # Today's Service Income (Total amount from repair jobs logged today)
            if enable_repair:
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
            self.low_stock_title_lbl.setText("Low Stock Alerts (Per-Item Limits)")
            
            low_stock_count = session.query(Product).filter(Product.stock_qty <= Product.low_stock_limit).count()
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
            low_stock_products = session.query(Product).filter(Product.stock_qty <= Product.low_stock_limit).all()
            self.low_stock_table.setRowCount(len(low_stock_products))
            for i, p in enumerate(low_stock_products):
                p_code = f"[{p.product_code}] " if p.product_code else ""
                self.low_stock_table.setItem(i, 0, QTableWidgetItem(f"{p_code}{p.name}"))
                self.low_stock_table.setItem(i, 1, QTableWidgetItem(f"{p.brand} / {p.model}"))
                qty_item = QTableWidgetItem(str(p.stock_qty))
                if p.stock_qty == 0:
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
                    "details": f"Mobile: {c.mobile} | Outstanding: ₹{c.outstanding_balance:,.2f}",
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
                    "details": f"Mobile: {s.mobile} | Outstanding: ₹{s.outstanding_balance:,.2f}",
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
                    "details": f"Customer: {s.customer.name if s.customer else 'Deleted'} | Total: ₹{s.total_amount:,.2f} | Date: {s.date.strftime('%Y-%m-%d')}",
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
                    "details": f"Supplier: {p.supplier.name if p.supplier else 'Deleted'} | Total: ₹{p.total_amount:,.2f} | Date: {p.date.strftime('%Y-%m-%d')}",
                    "id": p.id,
                    "obj_ref": p.invoice_number
                })

            # 5. Search Repair Job Cards by job_number, customer_name, mobile, or device_model
            jobs = session.query(ServiceJob).filter(
                (ServiceJob.job_number.ilike(f"%{query_text}%")) |
                (ServiceJob.customer_name.ilike(f"%{query_text}%")) |
                (ServiceJob.mobile.ilike(f"%{query_text}%")) |
                (ServiceJob.device_model.ilike(f"%{query_text}%"))
            ).limit(10).all()
            for j in jobs:
                results.append({
                    "type": "Repair Job Card",
                    "ref": j.job_number,
                    "details": f"Customer: {j.customer_name} | Device: {j.device_model} | Status: {j.status}",
                    "id": j.id,
                    "obj_ref": j.job_number
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
            if hasattr(main_window, 'customers_view'):
                main_window.switch_view(1)
                if hasattr(main_window, 'masters_view'):
                    main_window.masters_view.set_active_tab(1)
                main_window.customers_view.search_input.setText(res_ref)
        elif res_type == "Supplier":
            if hasattr(main_window, 'suppliers_view'):
                main_window.switch_view(1)
                if hasattr(main_window, 'masters_view'):
                    main_window.masters_view.set_active_tab(2)
                main_window.suppliers_view.search_input.setText(res_ref)

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
