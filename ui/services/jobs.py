import datetime
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox, 
                             QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, 
                             QFrame, QFormLayout, QDialog, QTextEdit, QDoubleSpinBox, QSpacerItem, QSizePolicy,
                             QApplication, QScrollArea, QSpinBox)
from PySide6.QtCore import Qt
from database import Session
from models import ServiceJob, ServicePart, Customer, CashTransaction, BankTransaction, BankAccount, Product

class JobCardDialog(QDialog):
    def __init__(self, job=None, parent=None):
        super().__init__(parent)
        self.job = job
        self.setWindowTitle("Edit Repair Job" if job else "New Repair Job Card")
        self.setFixedSize(450, 480)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        self.job_num_input = QLineEdit()
        self.job_num_input.setPlaceholderText("e.g. JOB-1001")
        
        self.cust_name_input = QLineEdit()
        self.cust_mobile_input = QLineEdit()
        self.cust_mobile_input.setPlaceholderText("Search customer mobile or type new")
        self.cust_mobile_input.textChanged.connect(self.lookup_customer_by_mobile)

        self.device_model_input = QLineEdit()
        self.imei_input = QLineEdit()
        
        self.complaint_input = QTextEdit()
        self.complaint_input.setFixedHeight(80)
        
        self.technician_input = QLineEdit()
        
        self.status_combo = QComboBox()
        self.status_combo.addItems(["Received", "Under Repair", "Ready", "Delivered"])

        form_layout.addRow("Job Number *:", self.job_num_input)
        form_layout.addRow("Customer Mobile *:", self.cust_mobile_input)
        form_layout.addRow("Customer Name *:", self.cust_name_input)
        form_layout.addRow("Device Model *:", self.device_model_input)
        form_layout.addRow("Device IMEI/Serial *:", self.imei_input)
        form_layout.addRow("Complaint details:", self.complaint_input)
        form_layout.addRow("Assigned Technician:", self.technician_input)
        form_layout.addRow("Job Status:", self.status_combo)

        layout.addLayout(form_layout)

        # Buttons
        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("Save Card")
        self.save_btn.clicked.connect(self.handle_save)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setProperty("class", "btn-secondary")
        self.cancel_btn.clicked.connect(self.reject)

        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)

        if self.job:
            self.job_num_input.setText(self.job.job_number)
            self.job_num_input.setEnabled(False)
            self.cust_mobile_input.setText(self.job.mobile)
            self.cust_name_input.setText(self.job.customer_name)
            self.device_model_input.setText(self.job.device_model)
            self.imei_input.setText(self.job.imei)
            self.complaint_input.setPlainText(self.job.complaint or "")
            self.technician_input.setText(self.job.technician or "")
            self.status_combo.setCurrentText(self.job.status)
        else:
            # Suggest Job Number
            session = Session()
            last_job = session.query(ServiceJob).order_by(ServiceJob.id.desc()).first()
            if last_job:
                self.job_num_input.setText(f"JOB-{last_job.id + 1001}")
            else:
                self.job_num_input.setText("JOB-1001")
            session.close()

    def lookup_customer_by_mobile(self, text):
        if len(text.strip()) >= 10:
            session = Session()
            cust = session.query(Customer).filter_by(mobile=text.strip()).first()
            if cust:
                self.cust_name_input.setText(cust.name)
            session.close()

    def handle_save(self):
        job_num = self.job_num_input.text().strip()
        mobile = self.cust_mobile_input.text().strip()
        name = self.cust_name_input.text().strip()
        model = self.device_model_input.text().strip()
        imei = self.imei_input.text().strip()
        complaint = self.complaint_input.toPlainText().strip()
        tech = self.technician_input.text().strip()
        status = self.status_combo.currentText()

        if not job_num or not mobile or not name or not model or not imei:
            QMessageBox.warning(self, "Validation Error", "Please fill in all mandatory fields (*)")
            return

        session = Session()
        try:
            # 1. Handle Customer Account Creation / Association
            cust = session.query(Customer).filter_by(mobile=mobile).first()
            if not cust:
                new_cust = Customer(name=name, mobile=mobile, address="Logged via Service Center")
                session.add(new_cust)
                session.commit()

            if self.job:
                # Update
                db_job = session.query(ServiceJob).get(self.job.id)
                db_job.mobile = mobile
                db_job.customer_name = name
                db_job.device_model = model
                db_job.imei = imei
                db_job.complaint = complaint
                db_job.technician = tech
                db_job.status = status
            else:
                # Add
                # Check uniqueness
                dup = session.query(ServiceJob).filter_by(job_number=job_num).first()
                if dup:
                    QMessageBox.warning(self, "Duplicate Job Number", f"Job Number {job_num} already exists.")
                    session.close()
                    return

                new_job = ServiceJob(
                    job_number=job_num, customer_name=name, mobile=mobile,
                    device_model=model, imei=imei, complaint=complaint,
                    technician=tech, status=status
                )
                session.add(new_job)

            session.commit()
            self.accept()
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", f"Failed to save job card: {e}")
        finally:
            session.close()


class BillingDialog(QDialog):
    def __init__(self, job, parent=None):
        super().__init__(parent)
        self.job = job
        self.parts_list = []  # list of dicts: {"name": str, "cost": float}
        self.setWindowTitle(f"Billing for Job: {job.job_number}")
        # Make the dialog top-level frameless and show fullscreen
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.showFullScreen()
        self.init_ui()

    def init_ui(self):
        # Central main layout of the dialog
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(25, 25, 25, 25)
        main_layout.setSpacing(15)

        # 1. Custom Header Bar (Always Visible at the Top)
        header_bar = QHBoxLayout()
        header_bar.setContentsMargins(0, 0, 0, 5)
        
        header_title = QLabel(f"<b>BILLING & ESTIMATE</b>")
        header_title.setStyleSheet("font-size: 20px; font-weight: bold; color: #ffffff;")
        header_bar.addWidget(header_title)
        
        header_sub = QLabel(f"| &nbsp;&nbsp;Job Card: <b>{self.job.job_number}</b> &nbsp;&nbsp;|&nbsp;&nbsp; Status: <b>{self.job.status}</b>")
        header_sub.setStyleSheet("font-size: 13px; color: #94a3b8;")
        header_bar.addWidget(header_sub)
        
        header_bar.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
        
        # Exit/Close Button in the header
        exit_btn = QPushButton("✕ Close")
        exit_btn.setProperty("class", "btn-secondary")
        exit_btn.setStyleSheet("font-size: 13px; padding: 6px 15px;")
        exit_btn.clicked.connect(self.reject)
        header_bar.addWidget(exit_btn)
        
        main_layout.addLayout(header_bar)

        # 2. Scroll Area for Responsive Middle Content
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet("QScrollArea { background-color: transparent; border: none; }")
        if scroll_area.viewport():
            scroll_area.viewport().setStyleSheet("background-color: transparent;")
        
        # Scroll Content Widget
        scroll_content = QWidget()
        scroll_content.setStyleSheet("background-color: transparent;")
        
        # Split Layout inside the Scroll Content
        content_layout = QHBoxLayout(scroll_content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(20)

        # LEFT COLUMN: Service Info & Spare Parts
        left_card = QFrame()
        left_card.setProperty("class", "CardFrame")
        left_layout = QVBoxLayout(left_card)
        left_layout.setContentsMargins(15, 15, 15, 15)
        left_layout.setSpacing(12)

        left_title = QLabel("Job Details & Spare Parts Entry")
        left_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #6366f1; border-bottom: 1px solid #28284e; padding-bottom: 6px;")
        left_layout.addWidget(left_title)

        # Job Details grid/layout
        details_layout = QHBoxLayout()
        details_layout.setSpacing(15)
        
        cust_info = QLabel(
            f"<b>Customer:</b> {self.job.customer_name}<br/>"
            f"<b>Mobile:</b> {self.job.mobile}"
        )
        cust_info.setStyleSheet("color: #e2e8f0; font-size: 12px; line-height: 1.3;")
        cust_info.setWordWrap(True)
        
        device_info = QLabel(
            f"<b>Device:</b> {self.job.device_model}<br/>"
            f"<b>IMEI:</b> {self.job.imei or '-'}"
        )
        device_info.setStyleSheet("color: #e2e8f0; font-size: 12px; line-height: 1.3;")
        device_info.setWordWrap(True)
        
        tech_info = QLabel(
            f"<b>Tech:</b> {self.job.technician or '-'}<br/>"
            f"<b>Complaint:</b> {self.job.complaint or '-'}"
        )
        tech_info.setStyleSheet("color: #e2e8f0; font-size: 12px; line-height: 1.3;")
        tech_info.setWordWrap(True)

        details_layout.addWidget(cust_info, 1)
        details_layout.addWidget(device_info, 1)
        details_layout.addWidget(tech_info, 1)
        left_layout.addLayout(details_layout)

        # Service Charge Form
        form_layout = QFormLayout()
        form_layout.setSpacing(8)
        
        self.service_charge_input = QDoubleSpinBox()
        self.service_charge_input.setRange(0, 999999)
        self.service_charge_input.setValue(self.job.service_charge)
        self.service_charge_input.setStyleSheet("font-size: 13px; font-weight: bold; padding: 5px;")
        self.service_charge_input.valueChanged.connect(self.recalculate_totals)
        form_layout.addRow("Service Labor Charge (₹) *:", self.service_charge_input)
        left_layout.addLayout(form_layout)

        # Spare Parts Entry Section
        parts_header = QLabel("Spare Parts Used")
        parts_header.setStyleSheet("font-size: 13px; font-weight: bold; color: #ffffff; margin-top: 5px;")
        left_layout.addWidget(parts_header)

        add_part_layout = QVBoxLayout()
        add_part_layout.setSpacing(8)
        
        # Row 1: Product selection and Custom input
        row1_layout = QHBoxLayout()
        self.part_product_combo = QComboBox()
        self.part_product_combo.setStyleSheet("padding: 6px;")
        self.part_product_combo.currentIndexChanged.connect(self.handle_product_selection_change)
        
        self.part_custom_name_input = QLineEdit()
        self.part_custom_name_input.setPlaceholderText("Custom Part Name")
        self.part_custom_name_input.setStyleSheet("padding: 6px;")
        
        row1_layout.addWidget(self.part_product_combo, 3)
        row1_layout.addWidget(self.part_custom_name_input, 2)
        add_part_layout.addLayout(row1_layout)
        
        # Row 2: Stock label, Qty input, Cost input, Add button
        row2_layout = QHBoxLayout()
        
        self.part_stock_lbl = QLabel("Stock: N/A")
        self.part_stock_lbl.setStyleSheet("font-size: 12px; color: #94a3b8; font-weight: bold;")
        
        self.part_qty_input = QSpinBox()
        self.part_qty_input.setRange(1, 9999)
        self.part_qty_input.setValue(1)
        self.part_qty_input.setStyleSheet("padding: 6px;")
        
        self.part_cost_input = QDoubleSpinBox()
        self.part_cost_input.setRange(0, 999999)
        self.part_cost_input.setStyleSheet("padding: 6px;")
        self.part_cost_input.setPrefix("₹ ")
        
        self.add_part_btn = QPushButton("Add Part")
        self.add_part_btn.setStyleSheet("padding: 6px 15px;")
        self.add_part_btn.clicked.connect(self.add_part)
        
        row2_layout.addWidget(self.part_stock_lbl, 2)
        row2_layout.addWidget(QLabel("Qty:"), 0)
        row2_layout.addWidget(self.part_qty_input, 1)
        row2_layout.addWidget(QLabel("Rate:"), 0)
        row2_layout.addWidget(self.part_cost_input, 2)
        row2_layout.addWidget(self.add_part_btn, 1)
        add_part_layout.addLayout(row2_layout)
        
        left_layout.addLayout(add_part_layout)

        # Spare Parts Table with minimum height to prevent collapse and allow scroll
        self.parts_table = QTableWidget()
        self.parts_table.setColumnCount(5)
        self.parts_table.setHorizontalHeaderLabels(["Part Name", "Qty", "Rate (₹)", "Total (₹)", "Action"])
        self.parts_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.parts_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.parts_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.parts_table.verticalHeader().setVisible(False)
        self.parts_table.setMinimumHeight(180)
        self.parts_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        left_layout.addWidget(self.parts_table)

        content_layout.addWidget(left_card, 3)

        # RIGHT COLUMN: Payment Summary (Fixed/Max width for visual balance)
        right_card = QFrame()
        right_card.setProperty("class", "CardFrame")
        right_card.setFixedWidth(380)
        right_layout = QVBoxLayout(right_card)
        right_layout.setContentsMargins(15, 15, 15, 15)
        right_layout.setSpacing(15)

        right_title = QLabel("Settlement & Invoice Summary")
        right_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #10b981; border-bottom: 1px solid #28284e; padding-bottom: 6px;")
        right_layout.addWidget(right_title)

        totals_form = QFormLayout()
        totals_form.setSpacing(8)
        
        self.parts_cost_lbl = QLabel("₹0.00")
        self.parts_cost_lbl.setStyleSheet("font-size: 14px; font-weight: bold; color: #ffffff;")
        totals_form.addRow("Spare Parts Total Cost:", self.parts_cost_lbl)
        
        right_layout.addLayout(totals_form)

        # Net Total Card
        total_card = QFrame()
        total_card.setStyleSheet("background-color: #1e1e38; border: 1px solid #6366f1; border-radius: 8px; padding: 10px;")
        total_card_layout = QVBoxLayout(total_card)
        total_card_layout.setSpacing(2)
        
        total_title = QLabel("NET TOTAL AMOUNT DUE")
        total_title.setStyleSheet("font-size: 10px; font-weight: bold; color: #94a3b8; text-transform: uppercase;")
        
        self.total_lbl = QLabel("₹0.00")
        self.total_lbl.setStyleSheet("font-size: 24px; font-weight: bold; color: #10b981;")
        
        total_card_layout.addWidget(total_title)
        total_card_layout.addWidget(self.total_lbl)
        right_layout.addWidget(total_card)

        # Payment Input Form
        payment_form = QFormLayout()
        payment_form.setSpacing(10)

        self.pay_mode_combo = QComboBox()
        self.pay_mode_combo.addItems(["Cash", "Bank"])
        self.pay_mode_combo.setStyleSheet("padding: 6px;")
        self.pay_mode_combo.currentTextChanged.connect(self.toggle_bank)

        self.bank_combo = QComboBox()
        self.bank_combo.setEnabled(False)
        self.bank_combo.setStyleSheet("padding: 6px;")

        self.paid_input = QDoubleSpinBox()
        self.paid_input.setRange(0, 999999)
        self.paid_input.setValue(self.job.paid_amount)
        self.paid_input.setStyleSheet("font-size: 14px; font-weight: bold; padding: 6px;")
        self.paid_input.setPrefix("₹ ")
        self.paid_input.valueChanged.connect(self.recalculate_totals)

        payment_form.addRow("Payment Mode:", self.pay_mode_combo)
        payment_form.addRow("Select Bank A/c:", self.bank_combo)
        payment_form.addRow("Amount Paid Now (₹) *:", self.paid_input)
        right_layout.addLayout(payment_form)

        # Balance Receivable Card
        balance_card = QFrame()
        balance_card.setStyleSheet("background-color: #1e1e38; border: 1px solid #28284e; border-radius: 8px; padding: 10px;")
        balance_card_layout = QVBoxLayout(balance_card)
        balance_card_layout.setSpacing(2)
        
        balance_title = QLabel("BALANCE RECEIVABLE (OUTSTANDING)")
        balance_title.setStyleSheet("font-size: 10px; font-weight: bold; color: #94a3b8; text-transform: uppercase;")
        
        self.balance_lbl = QLabel("₹0.00")
        self.balance_lbl.setStyleSheet("font-size: 20px; font-weight: bold; color: #ef4444;")
        
        balance_card_layout.addWidget(balance_title)
        balance_card_layout.addWidget(self.balance_lbl)
        right_layout.addWidget(balance_card)

        content_layout.addWidget(right_card, 2)

        scroll_area.setWidget(scroll_content)
        main_layout.addWidget(scroll_area, 1)

        # 3. Bottom Action Footer Bar (Always Visible and Reachable)
        footer_bar = QHBoxLayout()
        footer_bar.setContentsMargins(0, 10, 0, 0)
        footer_bar.setSpacing(15)
        
        footer_bar.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
        
        self.cancel_btn = QPushButton("Cancel / Go Back")
        self.cancel_btn.setProperty("class", "btn-secondary")
        self.cancel_btn.setStyleSheet("font-size: 13px; padding: 10px 24px; min-width: 130px;")
        self.cancel_btn.clicked.connect(self.reject)
        
        self.save_btn = QPushButton("Save & Close Bill")
        self.save_btn.setProperty("class", "btn-success")
        self.save_btn.setStyleSheet("font-size: 14px; padding: 10px 30px; font-weight: bold; min-width: 180px;")
        self.save_btn.clicked.connect(self.handle_billing_save)

        footer_bar.addWidget(self.cancel_btn)
        footer_bar.addWidget(self.save_btn)
        main_layout.addLayout(footer_bar)

        # Load bank accounts
        session = Session()
        banks = session.query(BankAccount).all()
        for b in banks:
            self.bank_combo.addItem(f"{b.bank_name} ({b.account_name})", b.id)

        # Load existing parts if any
        self.original_parts_qty = {}
        existing_parts = session.query(ServicePart).filter_by(job_id=self.job.id).all()

        # Load products for spare parts: filter by category 'Spare Parts' or if they are already in the existing parts of this job
        self.products_cache = {}
        self.part_product_combo.addItem("-- Custom / Non-Inventory Part --", None)
        existing_prod_ids = [ep.product_id for ep in existing_parts if ep.product_id]
        products = session.query(Product).filter(
            (Product.category == 'Spare Parts') |
            (Product.id.in_(existing_prod_ids))
        ).all()
        
        for p in products:
            self.products_cache[p.id] = p
            display_txt = f"{p.name} ({p.brand} - {p.model})"
            if p.imei:
                display_txt += f" [IMEI: {p.imei}]"
            self.part_product_combo.addItem(display_txt, p.id)
        
        for ep in existing_parts:
            self.parts_list.append({
                "product_id": ep.product_id,
                "name": ep.part_name,
                "qty": ep.qty,
                "cost": ep.cost
            })
            if ep.product_id:
                self.original_parts_qty[ep.product_id] = self.original_parts_qty.get(ep.product_id, 0) + ep.qty
        session.close()

        self.update_parts_table()

    def toggle_bank(self, mode):
        self.bank_combo.setEnabled(mode == "Bank")

    def handle_product_selection_change(self):
        prod_id = self.part_product_combo.currentData()
        if prod_id and prod_id in self.products_cache:
            prod = self.products_cache[prod_id]
            self.part_custom_name_input.setText(prod.name)
            self.part_custom_name_input.setEnabled(False)
            
            # Virtual stock = stock + original_qty - currently_used_in_parts_list
            original_qty = self.original_parts_qty.get(prod_id, 0)
            used_in_list = sum(p["qty"] for p in self.parts_list if p["product_id"] == prod_id)
            available_stock = prod.stock_qty + original_qty - used_in_list
            
            self.part_stock_lbl.setText(f"Stock: {available_stock}")
            self.part_cost_input.setValue(prod.selling_price)
            self.part_qty_input.setRange(1, max(1, available_stock))
            if available_stock <= 0:
                self.add_part_btn.setEnabled(False)
            else:
                self.add_part_btn.setEnabled(True)
        else:
            self.part_custom_name_input.clear()
            self.part_custom_name_input.setEnabled(True)
            self.part_stock_lbl.setText("Stock: N/A")
            self.part_cost_input.setValue(0.0)
            self.part_qty_input.setRange(1, 9999)
            self.add_part_btn.setEnabled(True)

    def add_part(self):
        try:
            prod_id = self.part_product_combo.currentData()
            qty = self.part_qty_input.value()
            cost = self.part_cost_input.value()
            
            if prod_id:
                prod = self.products_cache[prod_id]
                name = prod.name
                # Validate stock
                original_qty = self.original_parts_qty.get(prod_id, 0)
                used_in_list = sum(p["qty"] for p in self.parts_list if p["product_id"] == prod_id)
                available_stock = prod.stock_qty + original_qty - used_in_list
                if qty > available_stock:
                    QMessageBox.warning(self, "Insufficient Stock", 
                                        f"Cannot add {qty} units of '{name}'. Only {available_stock} units available.")
                    return
            else:
                name = self.part_custom_name_input.text().strip()
                if not name:
                    QMessageBox.warning(self, "Validation Error", "Please enter a Custom Spare Part Name.")
                    return

            # Check if product/name is already in the list
            for p in self.parts_list:
                if prod_id and p["product_id"] == prod_id:
                    p["qty"] += qty
                    p["cost"] = cost # update with latest cost
                    self.update_parts_table()
                    return
                elif not prod_id and not p["product_id"] and p["name"] == name:
                    p["qty"] += qty
                    p["cost"] = cost
                    self.update_parts_table()
                    return

            self.parts_list.append({
                "product_id": prod_id,
                "name": name,
                "qty": qty,
                "cost": cost
            })
            
            # Reset inputs
            self.part_product_combo.setCurrentIndex(0)
            self.part_custom_name_input.clear()
            self.part_qty_input.setValue(1)
            self.part_cost_input.setValue(0.0)
            
            self.update_parts_table()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to add part: {e}")

    def delete_part(self, idx):
        try:
            self.parts_list.pop(idx)
            self.update_parts_table()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to delete part: {e}")

    def update_parts_table(self):
        try:
            self.parts_table.setRowCount(len(self.parts_list))
            for i, p in enumerate(self.parts_list):
                self.parts_table.setItem(i, 0, QTableWidgetItem(p["name"]))
                self.parts_table.setItem(i, 1, QTableWidgetItem(str(p["qty"])))
                self.parts_table.setItem(i, 2, QTableWidgetItem(f"{p['cost']:.2f}"))
                total_val = p["cost"] * p["qty"]
                self.parts_table.setItem(i, 3, QTableWidgetItem(f"{total_val:.2f}"))
                
                del_btn = QPushButton("Remove")
                del_btn.setProperty("class", "btn-danger")
                del_btn.clicked.connect(lambda checked, idx=i: self.delete_part(idx))
                self.parts_table.setCellWidget(i, 4, del_btn)

            self.recalculate_totals()
            self.handle_product_selection_change()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to update parts table: {e}")

    def recalculate_totals(self):
        parts_total = sum(p["cost"] * p["qty"] for p in self.parts_list)
        self.parts_cost_lbl.setText(f"₹{parts_total:,.2f}")

        service_charge = self.service_charge_input.value()
        net_total = parts_total + service_charge
        self.total_lbl.setText(f"₹{net_total:,.2f}")

        paid = self.paid_input.value()
        balance = net_total - paid
        if balance < 0:
            balance = 0.0
        self.balance_lbl.setText(f"₹{balance:,.2f}")

    def handle_billing_save(self):
        parts_total = sum(p["cost"] * p["qty"] for p in self.parts_list)
        service_charge = self.service_charge_input.value()
        net_total = parts_total + service_charge
        paid = self.paid_input.value()
        balance = net_total - paid
        if balance < 0:
            balance = 0.0

        pay_mode = self.pay_mode_combo.currentText()
        bank_id = self.bank_combo.currentData() if pay_mode == "Bank" else None

        session = Session()
        try:
            # 1. Update job details
            job = session.query(ServiceJob).get(self.job.id)
            
            # Determine if new payment occurred
            payment_diff = paid - job.paid_amount

            job.service_charge = service_charge
            job.total_amount = net_total
            job.paid_amount = paid
            job.balance = balance
            # Mark status as Ready or Delivered automatically when fully paid/settled
            if balance == 0:
                job.status = "Delivered"

            # 2. Restore stock for original parts
            original_parts = session.query(ServicePart).filter_by(job_id=job.id).all()
            for op in original_parts:
                if op.product_id:
                    prod = session.query(Product).get(op.product_id)
                    if prod:
                        prod.stock_qty += op.qty

            # Reset and rewrite parts list
            session.query(ServicePart).filter_by(job_id=job.id).delete()
            for p in self.parts_list:
                part = ServicePart(
                    job_id=job.id,
                    product_id=p["product_id"],
                    part_name=p["name"],
                    qty=p["qty"],
                    cost=p["cost"]
                )
                session.add(part)
                
                # Deduct stock
                if p["product_id"]:
                    prod = session.query(Product).get(p["product_id"])
                    if prod:
                        prod.stock_qty -= p["qty"]
                        if prod.stock_qty < 0:
                            raise ValueError(f"Insufficient stock for {prod.name}")

            # 3. Log payment differences in Ledger
            if payment_diff > 0:
                desc = f"Payment for repair job card {job.job_number}"
                if pay_mode == "Cash":
                    tx = CashTransaction(
                        transaction_type='in', amount=payment_diff,
                        source_type='service', source_id=job.id, description=desc
                    )
                    session.add(tx)
                else:
                    tx = BankTransaction(
                        transaction_type='deposit', account_id=bank_id,
                        amount=payment_diff, source_type='service',
                        source_id=job.id, description=desc
                    )
                    session.add(tx)
                    
                    # Update bank accounts balance
                    bank = session.query(BankAccount).get(bank_id)
                    bank.balance += payment_diff

            # 4. If there's outstanding balance, sync to Customer profile
            cust = session.query(Customer).filter_by(mobile=job.mobile).first()
            if cust:
                # Outstanding balance is recalculated based on net transactions or set manually
                # For simplicity, we add the remaining balance receivable to customer profile outstanding
                if balance > 0:
                    cust.outstanding_balance += balance

            session.commit()
            QMessageBox.information(self, "Success", "Repair invoice details and billing saved.")
            self.accept()
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", f"Failed to save billing: {e}")
        finally:
            session.close()


class ServicesView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Top bar
        top_bar = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search job cards by Job #, Customer, Mobile, or Model...")
        self.search_input.textChanged.connect(self.refresh_data)
        top_bar.addWidget(self.search_input, 4)

        self.add_btn = QPushButton("New Job Card")
        self.add_btn.clicked.connect(self.add_job)
        top_bar.addWidget(self.add_btn, 1)

        self.bill_btn = QPushButton("Billing & Estimate")
        self.bill_btn.setProperty("class", "btn-success")
        self.bill_btn.clicked.connect(self.bill_job)
        top_bar.addWidget(self.bill_btn, 1)

        self.edit_btn = QPushButton("Edit Info")
        self.edit_btn.setProperty("class", "btn-secondary")
        self.edit_btn.clicked.connect(self.edit_job)
        top_bar.addWidget(self.edit_btn, 1)

        layout.addLayout(top_bar)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "Job Number", "Customer Name", "Mobile", "Device Model", 
            "Status", "Service Charge", "Total Bill", "Balance Due"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.doubleClicked.connect(self.edit_job)
        layout.addWidget(self.table)

    def refresh_data(self):
        search_txt = self.search_input.text().strip()
        session = Session()
        try:
            query = session.query(ServiceJob)
            if search_txt:
                query = query.filter(
                    ServiceJob.job_number.like(f"%{search_txt}%") |
                    ServiceJob.customer_name.like(f"%{search_txt}%") |
                    ServiceJob.mobile.like(f"%{search_txt}%") |
                    ServiceJob.device_model.like(f"%{search_txt}%") |
                    ServiceJob.status.like(f"%{search_txt}%")
                )
            jobs = query.order_by(ServiceJob.created_at.desc()).all()

            self.table.setRowCount(len(jobs))
            for i, j in enumerate(jobs):
                self.table.setItem(i, 0, QTableWidgetItem(j.job_number))
                self.table.setItem(i, 1, QTableWidgetItem(j.customer_name))
                self.table.setItem(i, 2, QTableWidgetItem(j.mobile))
                self.table.setItem(i, 3, QTableWidgetItem(j.device_model))
                
                status_item = QTableWidgetItem(j.status)
                # Color status tags
                if j.status == "Received":
                    status_item.setForeground(Qt.cyan)
                elif j.status == "Under Repair":
                    status_item.setForeground(Qt.yellow)
                elif j.status == "Ready":
                    status_item.setForeground(Qt.green)
                elif j.status == "Delivered":
                    status_item.setForeground(Qt.gray)
                self.table.setItem(i, 4, status_item)

                self.table.setItem(i, 5, QTableWidgetItem(f"₹{j.service_charge:,.2f}"))
                self.table.setItem(i, 6, QTableWidgetItem(f"₹{j.total_amount:,.2f}"))
                
                bal_item = QTableWidgetItem(f"₹{j.balance:,.2f}")
                if j.balance > 0:
                    bal_item.setForeground(Qt.red)
                self.table.setItem(i, 7, bal_item)

        except Exception as e:
            print(f"Error loading service jobs: {e}")
        finally:
            session.close()

    def get_selected_job_number(self):
        selected = self.table.selectedItems()
        if not selected:
            return None
        return self.table.item(selected[0].row(), 0).text()

    def add_job(self):
        dlg = JobCardDialog(parent=self)
        if dlg.exec() == QDialog.Accepted:
            self.refresh_data()

    def edit_job(self):
        job_num = self.get_selected_job_number()
        if job_num is None:
            QMessageBox.information(self, "No Selection", "Please select a job card to edit.")
            return

        session = Session()
        try:
            job = session.query(ServiceJob).filter_by(job_number=job_num).first()
            if job:
                dlg = JobCardDialog(job=job, parent=self)
                if dlg.exec() == QDialog.Accepted:
                    self.refresh_data()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not load job details: {e}")
        finally:
            session.close()

    def bill_job(self):
        job_num = self.get_selected_job_number()
        if job_num is None:
            QMessageBox.information(self, "No Selection", "Please select a job card for billing.")
            return

        session = Session()
        try:
            job = session.query(ServiceJob).filter_by(job_number=job_num).first()
            if job:
                dlg = BillingDialog(job=job, parent=self)
                if dlg.exec() == QDialog.Accepted:
                    self.refresh_data()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not load billing window: {e}")
        finally:
            session.close()
