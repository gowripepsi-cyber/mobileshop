import datetime
import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox, 
                             QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, 
                             QFrame, QFormLayout, QDialog, QTextEdit, QDoubleSpinBox, QSpacerItem, QSizePolicy,
                             QApplication, QScrollArea, QSpinBox, QDialogButtonBox, QGridLayout)
from PySide6.QtCore import Qt, QObject, QEvent, QTimer, QRegularExpression
from PySide6.QtGui import QColor, QFont, QRegularExpressionValidator
from PySide6.QtWidgets import QCompleter
from sqlalchemy import case
from utils.formatters import format_inr
from database import Session, Setting
from models import ServiceJob, ServicePart, Customer, CashTransaction, BankTransaction, BankAccount, Product, Payment, Staff
from utils.pdf_generator import generate_service_pdf
from utils.ui_helpers import enable_quick_add_auto_select

class CustomerNameClickFilter(QObject):
    def __init__(self, combo, is_new=True):
        super().__init__(combo)
        self.combo = combo
        self.is_new = is_new
        self._user_typed = False

    def eventFilter(self, obj, event):
        if event.type() in (QEvent.MouseButtonPress, QEvent.FocusIn):
            txt = self.combo.currentText().strip()
            if txt == "-- Select or Type Customer --" or (self.is_new and not self._user_typed):
                if self.combo.lineEdit():
                    self.combo.lineEdit().clear()
                self.combo.setEditText("")
                self.combo.setCurrentIndex(-1)
                if self.combo.lineEdit():
                    QTimer.singleShot(0, lambda: self.combo.lineEdit().setCursorPosition(0))
        elif event.type() == QEvent.KeyPress:
            self._user_typed = True
        return super().eventFilter(obj, event)


class JobCardDialog(QDialog):
    def __init__(self, job=None, parent=None):
        super().__init__(parent)
        self.job = job
        self.setWindowTitle("Edit Repair Job" if job else "New Repair Job Card")
        
        # Check settings for IMEI visibility
        from database import Setting
        session = Session()
        self.show_imei = True
        try:
            val = session.query(Setting).filter_by(key='enable_imei_tracking').first()
            if val and val.value == 'false':
                self.show_imei = False
        except Exception:
            pass
        finally:
            session.close()

        if self.job:
            h = 560 if self.show_imei else 530
        else:
            h = 515 if self.show_imei else 485
        self.setFixedSize(480, h)
            
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        self.job_num_input = QLineEdit()
        self.job_num_input.setPlaceholderText("6-digit ID (e.g. 000001)")
        self.job_num_input.setMaxLength(6)
        regex = QRegularExpression(r"^[0-9]{0,6}$")
        self.job_num_input.setValidator(QRegularExpressionValidator(regex, self))
        
        self.cust_name_combo = QComboBox()
        self.cust_name_combo.setEditable(True)
        self.cust_name_combo.setInsertPolicy(QComboBox.NoInsert)
        self.cust_name_combo.currentTextChanged.connect(self.check_customer_match)
        if self.cust_name_combo.lineEdit():
            self.cust_name_combo.lineEdit().setPlaceholderText("Select or type customer name")
            self.cust_name_combo.lineEdit().setClearButtonEnabled(True)
        self.cust_name_combo.currentIndexChanged.connect(self.on_customer_selected)

        # Install click-to-clear filter on customer name input
        self.cust_click_filter = CustomerNameClickFilter(self.cust_name_combo, is_new=(self.job is None))
        if self.cust_name_combo.lineEdit():
            self.cust_name_combo.lineEdit().installEventFilter(self.cust_click_filter)
        self.cust_name_combo.installEventFilter(self.cust_click_filter)

        cust_layout = QHBoxLayout()
        cust_layout.setContentsMargins(0, 0, 0, 0)
        cust_layout.setSpacing(6)
        cust_layout.addWidget(self.cust_name_combo, 1)

        self.add_cust_btn = QPushButton("+")
        self.add_cust_btn.setToolTip("Add new customer")
        self.add_cust_btn.setProperty("class", "btn-quick-add")
        self.add_cust_btn.setFixedWidth(40)
        self.add_cust_btn.setStyleSheet("padding: 0px; font-size: 18px; font-weight: bold; text-align: center;")
        self.add_cust_btn.setCursor(Qt.PointingHandCursor)
        self.add_cust_btn.clicked.connect(self.handle_add_customer_click)
        self.add_cust_btn.hide()
        cust_layout.addWidget(self.add_cust_btn)

        self.cust_mobile_input = QLineEdit()
        self.cust_mobile_input.setPlaceholderText("Search customer mobile or type new")
        self.cust_mobile_input.textChanged.connect(self.lookup_customer_by_mobile)

        self.device_model_input = QLineEdit()
        self.device_model_input.setPlaceholderText("Enter device detail (e.g. Model, Specs)")
        self.imei_input = QLineEdit()
        self.imei_input.setPlaceholderText("Enter device ID / Serial / IMEI (optional)")
        
        self.complaint_input = QTextEdit()
        self.complaint_input.setFixedHeight(80)
        
        # Mechanic / Service Attender (Optional dropdown & search from Staff table)
        self.technician_combo = QComboBox()
        self.technician_combo.setEditable(True)
        self.technician_combo.setInsertPolicy(QComboBox.NoInsert)
        if self.technician_combo.lineEdit():
            self.technician_combo.lineEdit().setPlaceholderText("Select or type mechanic / attender (optional)")
            self.technician_combo.lineEdit().setClearButtonEnabled(True)

        # Backward compatibility alias
        self.technician_input = self.technician_combo.lineEdit()
        
        # Only show Job Status dropdown when editing an existing job card (new jobs are always 'Received' by default)
        if self.job:
            self.status_combo = QComboBox()
            self.status_combo.addItems(["Received", "Under Repair", "Ready", "Delivered"])
        else:
            self.status_combo = None

        form_layout.addRow("Job Number *:", self.job_num_input)
        form_layout.addRow("Customer Name *:", cust_layout)
        form_layout.addRow("Customer Mobile *:", self.cust_mobile_input)
        form_layout.addRow("Device Detail *:", self.device_model_input)
        form_layout.addRow("Device ID:", self.imei_input)
        form_layout.addRow("Complaint details:", self.complaint_input)
        form_layout.addRow("Mechanic / Attender:", self.technician_combo)
        if self.status_combo:
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

        self.load_customers()
        self.load_technicians(selected_tech=self.job.technician if self.job else None)

        if self.job:
            self.job_num_input.setText(self.job.job_number)
            self.job_num_input.setEnabled(False)
            self.cust_mobile_input.setText(self.job.mobile)
            self.cust_name_combo.setCurrentText(self.job.customer_name)
            self.device_model_input.setText(self.job.device_model)
            self.imei_input.setText(self.job.imei)
            self.complaint_input.setPlainText(self.job.complaint or "")
            if self.status_combo:
                self.status_combo.setCurrentText(self.job.status or "Received")
        else:
            # Suggest next 6-digit serial number (pure numbers, no alphabets)
            session = Session()
            try:
                jobs = session.query(ServiceJob.job_number).all()
                max_num = 0
                for (j_num,) in jobs:
                    if j_num and j_num.strip().isdigit():
                        max_num = max(max_num, int(j_num.strip()))
                next_val = max_num + 1
                self.job_num_input.setText(f"{next_val:06d}")
            except Exception:
                self.job_num_input.setText("000001")
            finally:
                session.close()

    def load_customers(self, select_customer_name=None):
        session = Session()
        try:
            self.cust_name_combo.blockSignals(True)
            self.cust_name_combo.clear()
            customers = session.query(Customer).order_by(Customer.name.asc()).all()
            for c in customers:
                self.cust_name_combo.addItem(c.name, {"mobile": c.mobile})
            
            # Setup completer for fast autocomplete
            completer = QCompleter(self.cust_name_combo.model(), self.cust_name_combo)
            completer.setFilterMode(Qt.MatchContains)
            completer.setCaseSensitivity(Qt.CaseInsensitive)
            completer.setCompletionMode(QCompleter.PopupCompletion)
            self.cust_name_combo.setCompleter(completer)

            if select_customer_name:
                self.cust_name_combo.setCurrentText(select_customer_name)
                if hasattr(self, 'cust_click_filter'):
                    self.cust_click_filter._user_typed = True
            else:
                self.cust_name_combo.setCurrentIndex(-1)
                if self.cust_name_combo.lineEdit():
                    self.cust_name_combo.lineEdit().clear()
                    self.cust_name_combo.lineEdit().setPlaceholderText("Select or type customer name")
                if hasattr(self, 'cust_click_filter'):
                    self.cust_click_filter._user_typed = False
            self.cust_name_combo.blockSignals(False)
            self.check_customer_match()
        except Exception:
            pass
        finally:
            session.close()

    def check_customer_match(self):
        text = self.cust_name_combo.currentText().strip()
        if not text or text == "-- Select or Type Customer --":
            self.add_cust_btn.hide()
            return
        
        matched = False
        for i in range(self.cust_name_combo.count()):
            item_text = self.cust_name_combo.itemText(i).strip()
            if item_text and item_text != "-- Select or Type Customer --" and item_text.lower() == text.lower():
                matched = True
                break
        
        if not matched:
            self.add_cust_btn.show()
        else:
            self.add_cust_btn.hide()

    def on_customer_selected(self, index):
        data = self.cust_name_combo.currentData()
        if data and isinstance(data, dict) and data.get("mobile"):
            self.cust_mobile_input.setText(data["mobile"])
        if hasattr(self, 'cust_click_filter') and index >= 0:
            self.cust_click_filter._user_typed = True

    def handle_add_customer_click(self):
        from ui.masters.customers import CustomerDialog
        typed_text = self.cust_name_combo.currentText().strip()
        if typed_text == "-- Select or Type Customer --":
            typed_text = ""
        dlg = CustomerDialog(initial_name=typed_text, parent=self)
        if dlg.exec() == QDialog.Accepted and hasattr(dlg, 'saved_customer_name'):
            session = Session()
            try:
                saved_cust = session.query(Customer).filter_by(name=dlg.saved_customer_name).first()
                saved_mobile = saved_cust.mobile if saved_cust else ""
            except Exception:
                saved_mobile = ""
            finally:
                session.close()
            self.load_customers(select_customer_name=dlg.saved_customer_name)
            if saved_mobile:
                self.cust_mobile_input.setText(saved_mobile)

    def lookup_customer_by_mobile(self, text):
        if len(text.strip()) >= 10:
            session = Session()
            cust = session.query(Customer).filter_by(mobile=text.strip()).first()
            if cust:
                self.cust_name_combo.setCurrentText(cust.name)
                if hasattr(self, 'cust_click_filter'):
                    self.cust_click_filter._user_typed = True
            session.close()

    def load_technicians(self, selected_tech=None):
        session = Session()
        try:
            self.technician_combo.blockSignals(True)
            self.technician_combo.clear()
            self.technician_combo.addItem("-- Select Mechanic / Service Attender (Optional) --", "")

            # Prioritize Technicians, but list all Active staff alphabetically
            active_staff = session.query(Staff).filter_by(status='Active').order_by(
                Staff.designation.ilike('%technician%').desc(),
                Staff.name.asc()
            ).all()

            names_for_comp = []
            for s in active_staff:
                label = f"{s.name} ({s.designation})" if s.designation else s.name
                self.technician_combo.addItem(label, s.name)
                names_for_comp.append(label)
                if s.name not in names_for_comp:
                    names_for_comp.append(s.name)

            comp = QCompleter(names_for_comp, self.technician_combo)
            comp.setFilterMode(Qt.MatchContains)
            comp.setCaseSensitivity(Qt.CaseInsensitive)
            comp.setCompletionMode(QCompleter.PopupCompletion)
            self.technician_combo.setCompleter(comp)

            if selected_tech:
                matched = -1
                for i in range(self.technician_combo.count()):
                    if self.technician_combo.itemData(i) == selected_tech or self.technician_combo.itemText(i) == selected_tech:
                        matched = i
                        break
                if matched >= 0:
                    self.technician_combo.setCurrentIndex(matched)
                else:
                    self.technician_combo.setEditText(selected_tech)
            else:
                self.technician_combo.setCurrentIndex(0)
            self.technician_combo.blockSignals(False)
        except Exception as e:
            print(f"Error loading staff/technicians: {e}")
        finally:
            session.close()

    def get_selected_technician(self):
        text = self.technician_combo.currentText().strip()
        idx = self.technician_combo.currentIndex()

        if not text or text == "-- Select Mechanic / Service Attender (Optional) --":
            return ""

        # If currentText matches the selected combo item's text, return its associated data (staff name)
        if idx >= 0 and self.technician_combo.itemText(idx).strip() == text:
            data = self.technician_combo.itemData(idx)
            if data and isinstance(data, str) and data.strip():
                return data.strip()
            return text

        # If text matches any other item in the combo, return its data
        for i in range(self.technician_combo.count()):
            item_txt = self.technician_combo.itemText(i).strip()
            item_data = self.technician_combo.itemData(i)
            if item_txt.lower() == text.lower() or (item_data and item_data.strip().lower() == text.lower()):
                if item_data and isinstance(item_data, str) and item_data.strip():
                    return item_data.strip()

        # If user typed "Name (Role)", extract just the name
        if "(" in text and text.endswith(")"):
            return text.rsplit("(", 1)[0].strip()

        return text


    def handle_save(self):
        job_num = self.job_num_input.text().strip()
        mobile = self.cust_mobile_input.text().strip()
        name = self.cust_name_combo.currentText().strip()
        if name == "-- Select or Type Customer --":
            name = ""
        model = self.device_model_input.text().strip()
        imei = self.imei_input.text().strip()
        complaint = self.complaint_input.toPlainText().strip()
        tech = self.get_selected_technician()
        status = self.status_combo.currentText() if self.status_combo else (self.job.status if self.job else "Received")

        is_invalid = not job_num or not mobile or not name or not model
        if is_invalid:
            QMessageBox.warning(self, "Validation Error", "Please fill in all mandatory fields (*)\n(Customer Name, Mobile, and Device Detail are required)")
            return

        # Ensure Job ID is purely numeric (no alphabets or special characters)
        if not job_num.isdigit():
            QMessageBox.warning(self, "Validation Error", "Job ID must contain only numbers (no alphabets).")
            return

        # Auto-pad to 6 digits if fewer digits entered
        if len(job_num) < 6:
            job_num = job_num.zfill(6)
            self.job_num_input.setText(job_num)
        elif len(job_num) > 6:
            QMessageBox.warning(self, "Validation Error", "Job ID must be exactly 6 digits.")
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
        self.job_id = job.id
        self.job_number = job.job_number
        self.job_status = job.status
        self.job_paid_amount = float(job.paid_amount or 0.0)
        self.job_created_date = job.created_at.strftime("%Y-%m-%d") if getattr(job, 'created_at', None) else ""
        self.parts_list = []  # list of dicts: {"name": str, "cost": float}
        self.total_paid_so_far = 0.0
        self.setWindowTitle(f"Billing for Job: {self.job_number}")
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
        header_title.setStyleSheet("font-size: 20px; font-weight: bold; color: #0f172a;")
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

        # 2. Middle Section: Fixed Left Column & Self-Scrolling Right Column
        content_layout = QHBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(20)
        main_layout.addLayout(content_layout, 1)

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
            f"<b>Device Detail:</b> {self.job.device_model}<br/>"
            f"<b>Device ID:</b> {self.job.imei or '-'}"
        )
        device_info.setStyleSheet("color: #e2e8f0; font-size: 12px; line-height: 1.3;")
        device_info.setWordWrap(True)
        
        tech_info = QLabel(
            f"<b>Mechanic / Attender:</b> {self.job.technician or '-'}<br/>"
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
        parts_header.setStyleSheet("font-size: 13px; font-weight: bold; color: #0f172a; margin-top: 5px;")
        left_layout.addWidget(parts_header)

        add_part_layout = QVBoxLayout()
        add_part_layout.setSpacing(8)
        
        # Row 1: Product selection and Custom input
        row1_layout = QHBoxLayout()
        self.part_product_combo = QComboBox()
        self.part_product_combo.currentIndexChanged.connect(self.handle_product_selection_change)
        
        self.part_custom_name_input = QLineEdit()
        self.part_custom_name_input.setPlaceholderText("Custom Part Name")
        
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
        
        self.part_cost_input = QDoubleSpinBox()
        self.part_cost_input.setRange(0, 999999)
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
        self.parts_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Fixed)
        self.parts_table.setColumnWidth(4, 110)
        self.parts_table.verticalHeader().setVisible(False)
        self.parts_table.setMinimumHeight(180)
        self.parts_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        left_layout.addWidget(self.parts_table)

        content_layout.addWidget(left_card, 3)

        # RIGHT COLUMN: Settlement & Invoice Summary (Dedicated Scrollable Card)
        right_card = QFrame()
        right_card.setProperty("class", "CardFrame")
        right_card.setFixedWidth(465)
        right_layout = QVBoxLayout(right_card)
        right_layout.setContentsMargins(15, 12, 10, 12)
        right_layout.setSpacing(10)

        # Pinned Header for Settlement Block
        right_title = QLabel("Settlement & Invoice Summary")
        right_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #8fd53b; border-bottom: 1px solid #28284e; padding-bottom: 6px;")
        right_layout.addWidget(right_title)

        # Internal Scroll Area for ONLY the Settlement & Summary contents
        right_scroll = QScrollArea()
        right_scroll.setWidgetResizable(True)
        right_scroll.setFrameShape(QFrame.NoFrame)
        right_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        right_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        right_scroll.setStyleSheet("""
            QScrollArea { background-color: transparent; border: none; }
            QScrollArea > QWidget > QWidget { background-color: transparent; }
            QScrollBar:vertical {
                border: none;
                background-color: #f1f5f9;
                width: 8px;
                margin: 0px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background-color: #cbd5e1;
                min-height: 25px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #94a3b8;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                border: none;
                background: none;
                height: 0px;
            }
        """)
        if right_scroll.viewport():
            right_scroll.viewport().setStyleSheet("background-color: transparent;")

        right_scroll_content = QWidget()
        right_scroll_content.setStyleSheet("background-color: transparent;")
        right_content_layout = QVBoxLayout(right_scroll_content)
        right_content_layout.setContentsMargins(0, 4, 12, 4)
        right_content_layout.setSpacing(10)

        totals_form = QFormLayout()
        totals_form.setSpacing(4)
        
        self.parts_cost_lbl = QLabel("₹0.00")
        self.parts_cost_lbl.setStyleSheet("font-size: 13px; font-weight: bold; color: #0f172a;")
        totals_form.addRow("Spare Parts Total Cost:", self.parts_cost_lbl)
        right_content_layout.addLayout(totals_form)

        # Net Total Card
        total_card = QFrame()
        total_card.setStyleSheet("background-color: #fbfdf9; border: 2px solid #8fd53b; border-radius: 10px; padding: 6px;")
        total_card_layout = QVBoxLayout(total_card)
        total_card_layout.setContentsMargins(8, 6, 8, 6)
        total_card_layout.setSpacing(1)
        
        total_title = QLabel("NET TOTAL AMOUNT DUE")
        total_title.setStyleSheet("font-size: 10px; font-weight: bold; color: #64748b; text-transform: uppercase;")
        
        self.total_lbl = QLabel("₹0.00")
        self.total_lbl.setStyleSheet("font-size: 22px; font-weight: bold; color: #8fd53b;")
        
        total_card_layout.addWidget(total_title)
        total_card_layout.addWidget(self.total_lbl)
        right_content_layout.addWidget(total_card)

        # Balances Row (Already Paid + Remaining Balance)
        bal_row = QHBoxLayout()
        bal_row.setSpacing(8)
        
        # Already Paid Box
        paid_card = QFrame()
        paid_card.setStyleSheet("background-color: #f0fdf4; border: 1.5px solid #86efac; border-left: 5px solid #16a34a; border-radius: 10px; padding: 6px 10px;")
        paid_card_layout = QVBoxLayout(paid_card)
        paid_card_layout.setContentsMargins(4, 4, 4, 4)
        paid_card_layout.setSpacing(2)
        paid_title = QLabel("PAID SO FAR")
        paid_title.setStyleSheet("font-size: 9px; font-weight: bold; color: #15803d; text-transform: uppercase;")
        self.already_paid_lbl = QLabel("₹0.00")
        self.already_paid_lbl.setStyleSheet("font-size: 16px; font-weight: bold; color: #16a34a;")
        paid_card_layout.addWidget(paid_title)
        paid_card_layout.addWidget(self.already_paid_lbl)
        bal_row.addWidget(paid_card, 1)

        # Remaining Balance Box
        self.balance_card = QFrame()
        self.balance_card.setStyleSheet("background-color: #fef2f2; border: 1.5px solid #fecaca; border-left: 5px solid #ef4444; border-radius: 10px; padding: 6px 10px;")
        balance_card_layout = QVBoxLayout(self.balance_card)
        balance_card_layout.setContentsMargins(4, 4, 4, 4)
        balance_card_layout.setSpacing(2)
        self.balance_title = QLabel("BALANCE DUE")
        self.balance_title.setStyleSheet("font-size: 9px; font-weight: bold; color: #dc2626; text-transform: uppercase;")
        self.balance_lbl = QLabel("₹0.00")
        self.balance_lbl.setStyleSheet("font-size: 16px; font-weight: 800; color: #ef4444;")
        balance_card_layout.addWidget(self.balance_title)
        balance_card_layout.addWidget(self.balance_lbl)
        bal_row.addWidget(self.balance_card, 1)

        right_content_layout.addLayout(bal_row)

        # 1. Record New Payment Sub-Card (Positioned directly under Balances for easy entry)
        new_pay_box = QFrame()
        new_pay_box.setStyleSheet("background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px; padding: 8px;")
        new_pay_layout = QVBoxLayout(new_pay_box)
        new_pay_layout.setContentsMargins(8, 8, 8, 8)
        new_pay_layout.setSpacing(6)

        new_pay_title = QLabel("Record New Payment / Installment")
        new_pay_title.setStyleSheet("font-size: 12px; font-weight: bold; color: #1e293b;")
        new_pay_layout.addWidget(new_pay_title)

        pay_form = QFormLayout()
        pay_form.setSpacing(6)

        # Amount Paying Now with Quick Balance button
        pay_amt_layout = QHBoxLayout()
        self.paying_now_input = QDoubleSpinBox()
        self.paying_now_input.setRange(0.0, 999999.0)
        self.paying_now_input.setValue(0.0)
        self.paying_now_input.setDecimals(2)
        self.paying_now_input.setPrefix("₹ ")
        self.paying_now_input.setStyleSheet("font-size: 13px; font-weight: bold;")
        self.paying_now_input.valueChanged.connect(self.recalculate_totals)
        pay_amt_layout.addWidget(self.paying_now_input, 2)

        self.btn_pay_full = QPushButton("Pay Balance")
        self.btn_pay_full.setProperty("class", "btn-secondary")
        self.btn_pay_full.setCursor(Qt.PointingHandCursor)
        self.btn_pay_full.setStyleSheet("font-size: 11px; padding: 4px 8px;")
        self.btn_pay_full.setToolTip("Auto-fill with remaining balance")
        self.btn_pay_full.clicked.connect(self.fill_full_balance)
        pay_amt_layout.addWidget(self.btn_pay_full, 1)

        pay_form.addRow("Amount Paying Now *:", pay_amt_layout)

        self.pay_mode_combo = QComboBox()
        self.pay_mode_combo.addItems(["Cash", "Bank"])
        self.pay_mode_combo.currentTextChanged.connect(self.toggle_bank)
        pay_form.addRow("Payment Mode:", self.pay_mode_combo)

        self.bank_combo = QComboBox()
        self.bank_combo.setEnabled(False)
        pay_form.addRow("Select Bank A/c:", self.bank_combo)

        self.pay_remarks_input = QLineEdit()
        self.pay_remarks_input.setPlaceholderText("e.g. Advance, 2nd installment, GPay")
        pay_form.addRow("Payment Note:", self.pay_remarks_input)

        new_pay_layout.addLayout(pay_form)

        # Projected balance preview
        self.projected_balance_lbl = QLabel("")
        self.projected_balance_lbl.setStyleSheet("font-size: 11px; font-weight: bold; color: #475569;")
        new_pay_layout.addWidget(self.projected_balance_lbl)

        # Quick record payment button
        self.btn_record_now = QPushButton("Add Payment Now")
        self.btn_record_now.setProperty("class", "btn-action-view")
        self.btn_record_now.setCursor(Qt.PointingHandCursor)
        self.btn_record_now.setStyleSheet("font-size: 12px; font-weight: bold; padding: 6px 12px;")
        self.btn_record_now.clicked.connect(self.record_payment_immediate)
        new_pay_layout.addWidget(self.btn_record_now)

        right_content_layout.addWidget(new_pay_box)

        # 2. Payment History Section (Positioned at the Bottom)
        hist_header = QLabel("Payment History (Installments)")
        hist_header.setStyleSheet("font-size: 12px; font-weight: bold; color: #0f172a; margin-top: 6px;")
        right_content_layout.addWidget(hist_header)

        self.payments_table = QTableWidget()
        self.payments_table.setColumnCount(4)
        self.payments_table.setHorizontalHeaderLabels(["Date", "Mode", "Amount (₹)", "Remarks"])
        self.payments_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.payments_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.payments_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.payments_table.verticalHeader().setVisible(False)
        self.payments_table.setFixedHeight(110)
        self.payments_table.setStyleSheet("QTableWidget { font-size: 11px; border: 1px solid #e2e8f0; border-radius: 6px; }")
        right_content_layout.addWidget(self.payments_table)

        right_scroll.setWidget(right_scroll_content)
        right_layout.addWidget(right_scroll, 1)

        content_layout.addWidget(right_card, 0)

        # Status Update Panel with Radio Buttons
        from PySide6.QtWidgets import QRadioButton, QButtonGroup
        self.status_group = QButtonGroup(self)
        
        status_panel = QFrame()
        status_panel.setStyleSheet("background-color: #1b1b32; border: 1px solid #28284e; border-radius: 8px; padding: 12px;")
        status_layout = QHBoxLayout(status_panel)
        status_layout.setContentsMargins(20, 8, 20, 8)
        status_layout.setSpacing(25)
        
        status_lbl = QLabel("Update Job Status:")
        status_lbl.setStyleSheet("font-weight: bold; color: #94a3b8; font-size: 13px;")
        status_layout.addWidget(status_lbl)
        
        self.radio_received = QRadioButton("Received")
        self.radio_under_repair = QRadioButton("Under Repair")
        self.radio_ready = QRadioButton("Ready")
        self.radio_delivered = QRadioButton("Delivered")
        
        radio_style = "QRadioButton { color: #e2e8f0; font-size: 13px; font-weight: bold; } QRadioButton::indicator { width: 16px; height: 16px; }"
        for r in [self.radio_received, self.radio_under_repair, self.radio_ready, self.radio_delivered]:
            r.setStyleSheet(radio_style)
            self.status_group.addButton(r)
            status_layout.addWidget(r)
            
        status_layout.addStretch()
        main_layout.addWidget(status_panel)

        # Set default selection based on current job status
        curr_status = self.job.status
        if curr_status == "Received":
            self.radio_received.setChecked(True)
        elif curr_status == "Under Repair":
            self.radio_under_repair.setChecked(True)
        elif curr_status == "Ready":
            self.radio_ready.setChecked(True)
        elif curr_status == "Delivered":
            self.radio_delivered.setChecked(True)
        else:
            self.radio_received.setChecked(True)

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
            (Product.category.in_(['Spare Parts', 'Spares', 'spares', 'spare parts'])) |
            (Product.id.in_(existing_prod_ids))
        ).all()
        
        for p in products:
            self.products_cache[p.id] = p
            bm = getattr(p, 'brand_model', None) or getattr(p, 'brand', '') or ''
            display_txt = f"{p.name} ({bm}) [Stock: {p.stock_qty}]" if bm else f"{p.name} [Stock: {p.stock_qty}]"
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
        self.load_payments_history()
        self.recalculate_totals()

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
                
                # Remove button (centered wrapper container)
                btn_container = QWidget()
                btn_layout = QHBoxLayout(btn_container)
                btn_layout.setContentsMargins(4, 4, 4, 4)
                btn_layout.setSpacing(0)
                btn_layout.setAlignment(Qt.AlignCenter)

                del_btn = QPushButton("🗑️")
                del_btn.setToolTip("Remove Part")
                del_btn.setCursor(Qt.PointingHandCursor)
                del_btn.setProperty("class", "btn-action-icon-delete")
                del_btn.clicked.connect(lambda checked, idx=i: self.delete_part(idx))
                btn_layout.addWidget(del_btn)
                self.parts_table.setCellWidget(i, 4, btn_container)

            self.recalculate_totals()
            self.handle_product_selection_change()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to update parts table: {e}")

    def load_payments_history(self):
        session = Session()
        try:
            from sqlalchemy import func
            payments = session.query(Payment).filter_by(job_id=self.job_id).order_by(Payment.id.asc()).all()
            self.payments_table.setRowCount(len(payments))
            total_paid = 0.0
            for i, p in enumerate(payments):
                self.payments_table.setItem(i, 0, QTableWidgetItem(p.date.strftime("%Y-%m-%d")))
                self.payments_table.setItem(i, 1, QTableWidgetItem(p.payment_mode))
                amt_item = QTableWidgetItem(f"₹{format_inr(p.amount)}")
                amt_item.setForeground(Qt.darkGreen)
                self.payments_table.setItem(i, 2, amt_item)
                self.payments_table.setItem(i, 3, QTableWidgetItem(p.remarks or "-"))
                total_paid += p.amount

            # If no Payment rows yet but job_paid_amount > 0, fallback display
            if not payments and getattr(self, 'job_paid_amount', 0.0) > 0:
                total_paid = self.job_paid_amount
                self.payments_table.setRowCount(1)
                self.payments_table.setItem(0, 0, QTableWidgetItem(getattr(self, 'job_created_date', '')))
                self.payments_table.setItem(0, 1, QTableWidgetItem("Cash"))
                amt_item = QTableWidgetItem(f"₹{format_inr(total_paid)}")
                amt_item.setForeground(Qt.darkGreen)
                self.payments_table.setItem(0, 2, amt_item)
                self.payments_table.setItem(0, 3, QTableWidgetItem("Initial Payment / Advance"))

            self.total_paid_so_far = total_paid
            self.already_paid_lbl.setText(f"₹{format_inr(total_paid)}")
        except Exception as e:
            print(f"Error loading payments history: {e}")
        finally:
            session.close()

    def fill_full_balance(self):
        parts_total = sum(p["cost"] * p["qty"] for p in self.parts_list)
        service_charge = self.service_charge_input.value()
        net_total = parts_total + service_charge
        already_paid = getattr(self, 'total_paid_so_far', 0.0)
        rem = max(0.0, net_total - already_paid)
        self.paying_now_input.setValue(rem)

    def recalculate_totals(self):
        parts_total = sum(p["cost"] * p["qty"] for p in self.parts_list)
        self.parts_cost_lbl.setText(f"₹{format_inr(parts_total)}")

        service_charge = self.service_charge_input.value()
        net_total = parts_total + service_charge
        self.total_lbl.setText(f"₹{format_inr(net_total)}")

        already_paid = getattr(self, 'total_paid_so_far', 0.0)
        self.already_paid_lbl.setText(f"₹{format_inr(already_paid)}")

        paying_now = self.paying_now_input.value()
        projected_paid = already_paid + paying_now
        remaining_balance = net_total - projected_paid
        if remaining_balance < 0:
            remaining_balance = 0.0

        self.balance_lbl.setText(f"₹{format_inr(remaining_balance)}")

        # Balance badge styling
        if remaining_balance == 0 and net_total > 0:
            self.balance_title.setText("BALANCE DUE (FULLY SETTLED)")
            self.balance_title.setStyleSheet("font-size: 9px; font-weight: bold; color: #16a34a; text-transform: uppercase; border: none; background: transparent;")
            self.balance_lbl.setStyleSheet("font-size: 16px; font-weight: 800; color: #16a34a; border: none; background: transparent;")
            self.balance_card.setStyleSheet("background-color: #f0fdf4; border: 1.5px solid #86efac; border-left: 5px solid #22c55e; border-radius: 10px; padding: 6px 10px;")
        else:
            self.balance_title.setText("BALANCE DUE (OUTSTANDING)")
            self.balance_title.setStyleSheet("font-size: 9px; font-weight: bold; color: #dc2626; text-transform: uppercase; border: none; background: transparent;")
            self.balance_lbl.setStyleSheet("font-size: 16px; font-weight: 800; color: #ef4444; border: none; background: transparent;")
            self.balance_card.setStyleSheet("background-color: #fef2f2; border: 1.5px solid #fecaca; border-left: 5px solid #ef4444; border-radius: 10px; padding: 6px 10px;")

        if paying_now > 0:
            self.projected_balance_lbl.setText(f"After paying ₹{format_inr(paying_now)} now: Balance will be ₹{format_inr(remaining_balance)}")
            self.projected_balance_lbl.setStyleSheet("font-size: 11px; font-weight: bold; color: #15803d;")
        else:
            self.projected_balance_lbl.setText(f"No payment currently entered. Balance: ₹{format_inr(remaining_balance)}")
            self.projected_balance_lbl.setStyleSheet("font-size: 11px; font-weight: bold; color: #64748b;")

    def record_payment_immediate(self):
        paying_now = self.paying_now_input.value()
        if paying_now <= 0:
            QMessageBox.warning(self, "Validation Error", "Please enter an amount greater than zero.")
            return

        parts_total = sum(p["cost"] * p["qty"] for p in self.parts_list)
        service_charge = self.service_charge_input.value()
        net_total = parts_total + service_charge
        current_rem = max(0.0, net_total - self.total_paid_so_far)
        if paying_now > current_rem + 0.01:
            QMessageBox.warning(self, "Validation Error", f"Payment amount (₹{format_inr(paying_now)}) cannot exceed pending balance (₹{format_inr(current_rem)}).")
            return

        pay_mode = self.pay_mode_combo.currentText()
        bank_id = self.bank_combo.currentData() if pay_mode == "Bank" else None
        remarks = self.pay_remarks_input.text().strip() or None

        session = Session()
        try:
            from sqlalchemy import func
            job = session.query(ServiceJob).get(self.job.id)
            cust = session.query(Customer).filter_by(mobile=job.mobile).first()
            cust_id = cust.id if cust else 1

            p = Payment(
                date=datetime.date.today(),
                party_type='customer',
                party_id=cust_id,
                amount=paying_now,
                payment_mode=pay_mode,
                bank_id=bank_id,
                job_id=job.id,
                remarks=remarks or f"Installment payment for job card {job.job_number}"
            )
            session.add(p)
            session.flush()

            desc = f"Payment for repair job card {job.job_number}"
            if remarks:
                desc += f" ({remarks})"

            if pay_mode == "Cash":
                tx = CashTransaction(
                    date=datetime.date.today(),
                    transaction_type='in', amount=paying_now,
                    source_type='service', source_id=job.id, description=desc
                )
                session.add(tx)
            else:
                tx = BankTransaction(
                    date=datetime.date.today(),
                    transaction_type='deposit', account_id=bank_id,
                    amount=paying_now, source_type='service',
                    source_id=job.id, description=desc
                )
                session.add(tx)
                bank = session.query(BankAccount).get(bank_id)
                if bank:
                    bank.balance += paying_now

            # Recompute total paid and balance
            all_payments = session.query(func.sum(Payment.amount)).filter_by(job_id=job.id).scalar() or 0.0
            job.paid_amount = all_payments
            job.total_amount = net_total
            new_balance = max(0.0, net_total - all_payments)
            job.balance = new_balance

            if cust and cust.outstanding_balance >= paying_now:
                cust.outstanding_balance -= paying_now

            session.commit()
            session.close()

            self.paying_now_input.setValue(0.0)
            self.pay_remarks_input.clear()
            self.load_payments_history()
            self.recalculate_totals()
            QMessageBox.information(self, "Success", f"Payment installment of ₹{format_inr(paying_now)} recorded successfully.\nRemaining Balance: ₹{format_inr(new_balance)}")
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", f"Failed to record payment: {e}")
        finally:
            session.close()

    def handle_billing_save(self):
        parts_total = sum(p["cost"] * p["qty"] for p in self.parts_list)
        service_charge = self.service_charge_input.value()
        net_total = parts_total + service_charge

        paying_now = self.paying_now_input.value()
        current_rem = max(0.0, net_total - self.total_paid_so_far)
        if paying_now > current_rem + 0.01:
            QMessageBox.warning(self, "Validation Error", f"Payment amount (₹{format_inr(paying_now)}) cannot exceed pending balance (₹{format_inr(current_rem)}).")
            return

        pay_mode = self.pay_mode_combo.currentText()
        bank_id = self.bank_combo.currentData() if pay_mode == "Bank" else None
        remarks = self.pay_remarks_input.text().strip() or None

        session = Session()
        try:
            from sqlalchemy import func
            # 1. Update job details
            job = session.query(ServiceJob).get(self.job.id)
            cust = session.query(Customer).filter_by(mobile=job.mobile).first()
            cust_id = cust.id if cust else 1

            # 2. Record new payment if entered
            if paying_now > 0:
                p = Payment(
                    date=datetime.date.today(),
                    party_type='customer',
                    party_id=cust_id,
                    amount=paying_now,
                    payment_mode=pay_mode,
                    bank_id=bank_id,
                    job_id=job.id,
                    remarks=remarks or f"Payment for repair job card {job.job_number}"
                )
                session.add(p)
                session.flush()

                desc = f"Payment for repair job card {job.job_number}"
                if remarks:
                    desc += f" ({remarks})"

                if pay_mode == "Cash":
                    tx = CashTransaction(
                        date=datetime.date.today(),
                        transaction_type='in', amount=paying_now,
                        source_type='service', source_id=job.id, description=desc
                    )
                    session.add(tx)
                else:
                    tx = BankTransaction(
                        date=datetime.date.today(),
                        transaction_type='deposit', account_id=bank_id,
                        amount=paying_now, source_type='service',
                        source_id=job.id, description=desc
                    )
                    session.add(tx)
                    bank = session.query(BankAccount).get(bank_id)
                    if bank:
                        bank.balance += paying_now

                if cust and cust.outstanding_balance >= paying_now:
                    cust.outstanding_balance -= paying_now

            # 3. Restore stock for original parts and rewrite parts
            original_parts = session.query(ServicePart).filter_by(job_id=job.id).all()
            for op in original_parts:
                if op.product_id:
                    prod = session.query(Product).get(op.product_id)
                    if prod:
                        prod.stock_qty += op.qty

            job.parts.clear()
            for p_item in self.parts_list:
                part = ServicePart(
                    job_id=job.id,
                    product_id=p_item["product_id"],
                    part_name=p_item["name"],
                    qty=p_item["qty"],
                    cost=p_item["cost"]
                )
                session.add(part)

                # Deduct stock
                if p_item["product_id"]:
                    prod = session.query(Product).get(p_item["product_id"])
                    if prod:
                        prod.stock_qty -= p_item["qty"]
                        if prod.stock_qty < 0:
                            raise ValueError(f"Insufficient stock for {prod.name}")

            # 4. Update status based on selected radio button
            selected_status = "Received"
            if self.radio_received.isChecked():
                selected_status = "Received"
            elif self.radio_under_repair.isChecked():
                selected_status = "Under Repair"
            elif self.radio_ready.isChecked():
                selected_status = "Ready"
            elif self.radio_delivered.isChecked():
                selected_status = "Delivered"

            status_changed = (job.status != selected_status)
            job.status = selected_status

            if status_changed:
                from models import ServiceJobStatusHistory
                history_entry = ServiceJobStatusHistory(
                    job_id=job.id,
                    status=selected_status,
                    updated_at=datetime.datetime.now()
                )
                session.add(history_entry)

            # 5. Compute exact totals and balances
            job.service_charge = service_charge
            job.total_amount = net_total
            all_payments_sum = session.query(func.sum(Payment.amount)).filter_by(job_id=job.id).scalar() or 0.0
            job.paid_amount = all_payments_sum
            final_bal = max(0.0, net_total - all_payments_sum)
            job.balance = final_bal

            final_total = float(net_total)
            final_paid = float(all_payments_sum)

            session.commit()
            session.close()
            msg = f"Repair invoice details saved.\nTotal: ₹{format_inr(final_total)}\nTotal Paid: ₹{format_inr(final_paid)}\nBalance Remaining: ₹{format_inr(final_bal)}"
            QMessageBox.information(self, "Success", msg)
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
        top_bar.setSpacing(10)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search job cards by Job #, Customer, Mobile, or Device...")
        self.search_input.textChanged.connect(self.refresh_data)
        top_bar.addWidget(self.search_input, 3)

        # Status Filter
        self.status_filter = QComboBox()
        self.status_filter.addItems([
            "All Statuses", 
            "Received", 
            "Under Repair", 
            "Ready", 
            "Delivered",
            "Has Balance (Unpaid)"
        ])
        self.status_filter.currentIndexChanged.connect(self.refresh_data)
        top_bar.addWidget(self.status_filter, 1)

        # Sort Filter Option (Date, Days, Status, Total, Balance)
        self.sort_filter = QComboBox()
        self.sort_filter.addItems([
            "Sort: Date (Newest First)",
            "Sort: Date (Oldest First)",
            "Sort: Days (Most Overdue First)",
            "Sort: Days (Fewest Days First)",
            "Sort: Status (Active First)",
            "Sort: Total (Highest First)",
            "Sort: Total (Lowest First)",
            "Sort: Balance (Highest Due First)",
            "Sort: Balance (Lowest Due First)",
        ])
        self.sort_filter.currentIndexChanged.connect(self.refresh_data)
        top_bar.addWidget(self.sort_filter, 1.4)

        self.add_btn = QPushButton("+ New Job Card")
        self.add_btn.setCursor(Qt.PointingHandCursor)
        self.add_btn.clicked.connect(self.add_job)
        top_bar.addWidget(self.add_btn, 1)

        layout.addLayout(top_bar)

        # Table with 11 columns (includes new "Days" column)
        self.table = QTableWidget()
        self.table.setColumnCount(11)
        self.table.setHorizontalHeaderLabels([
            "Job #", "Date", "Days", "Customer", "Mobile", "Device Detail", 
            "Status", "Labor (₹)", "Total (₹)", "Balance (₹)", "Actions"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        
        # Days column: fixed width with centered text
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Fixed)
        self.table.setColumnWidth(2, 90)

        # Mobile column
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)

        # Status column
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.Fixed)
        self.table.setColumnWidth(6, 110)
        
        # Reduce width of Labor, Total, and Balance columns
        self.table.horizontalHeader().setSectionResizeMode(7, QHeaderView.Fixed)
        self.table.setColumnWidth(7, 85)
        self.table.horizontalHeader().setSectionResizeMode(8, QHeaderView.Fixed)
        self.table.setColumnWidth(8, 95)
        self.table.horizontalHeader().setSectionResizeMode(9, QHeaderView.Fixed)
        self.table.setColumnWidth(9, 95)
        
        # Actions column with compact logo buttons
        self.table.horizontalHeader().setSectionResizeMode(10, QHeaderView.Fixed)
        self.table.setColumnWidth(10, 180)
        
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(54)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.doubleClicked.connect(self.edit_job)
        
        # Allow clicking column headers to sort quickly
        self.table.horizontalHeader().setSectionsClickable(True)
        self.table.horizontalHeader().sectionClicked.connect(self.handle_header_click)
        
        layout.addWidget(self.table)

        # Lazy loading state
        self.jobs_offset = 0
        self.has_more_jobs = True
        self.table.verticalScrollBar().valueChanged.connect(self.handle_jobs_scroll)

    def handle_header_click(self, col):
        current = self.sort_filter.currentText() if hasattr(self, 'sort_filter') else ""
        if col == 1:  # Date
            if "Date (Newest" in current:
                self.sort_filter.setCurrentText("Sort: Date (Oldest First)")
            else:
                self.sort_filter.setCurrentText("Sort: Date (Newest First)")
        elif col == 2:  # Days
            if "Days (Most Overdue" in current:
                self.sort_filter.setCurrentText("Sort: Days (Fewest Days First)")
            else:
                self.sort_filter.setCurrentText("Sort: Days (Most Overdue First)")
        elif col == 6:  # Status
            self.sort_filter.setCurrentText("Sort: Status (Active First)")
        elif col == 8:  # Total
            if "Total (Highest" in current:
                self.sort_filter.setCurrentText("Sort: Total (Lowest First)")
            else:
                self.sort_filter.setCurrentText("Sort: Total (Highest First)")
        elif col == 9:  # Balance
            if "Balance (Highest" in current:
                self.sort_filter.setCurrentText("Sort: Balance (Lowest Due First)")
            else:
                self.sort_filter.setCurrentText("Sort: Balance (Highest Due First)")

    def handle_jobs_scroll(self, value):
        scrollbar = self.table.verticalScrollBar()
        if value == scrollbar.maximum() and scrollbar.maximum() > 0:
            if self.has_more_jobs:
                self.jobs_offset += 25
                self.refresh_data(reset=False)

    def refresh_data(self, reset=True):
        if not isinstance(reset, bool):
            reset = True

        if reset:
            self.jobs_offset = 0
            self.has_more_jobs = True
            self.table.setRowCount(0)

        search_txt = self.search_input.text().strip()
        selected_status = self.status_filter.currentText() if hasattr(self, 'status_filter') else "All Statuses"
        sort_choice = self.sort_filter.currentText() if hasattr(self, 'sort_filter') else "Sort: Date (Newest First)"

        session = Session()
        try:
            query = session.query(ServiceJob)
            if search_txt:
                query = query.filter(
                    ServiceJob.job_number.like(f"%{search_txt}%") |
                    ServiceJob.customer_name.like(f"%{search_txt}%") |
                    ServiceJob.mobile.like(f"%{search_txt}%") |
                    ServiceJob.device_model.like(f"%{search_txt}%") |
                    ServiceJob.imei.like(f"%{search_txt}%") |
                    ServiceJob.status.like(f"%{search_txt}%")
                )
            if selected_status == "Has Balance (Unpaid)":
                query = query.filter(ServiceJob.balance > 0)
            elif selected_status != "All Statuses":
                query = query.filter(ServiceJob.status == selected_status)
            
            # Status custom order: Received (1) -> Under Repair (2) -> Ready (3) -> Delivered (4)
            status_order = case(
                (ServiceJob.status == 'Received', 1),
                (ServiceJob.status == 'Under Repair', 2),
                (ServiceJob.status == 'Ready', 3),
                (ServiceJob.status == 'Delivered', 4),
                else_=5
            )

            # Apply user-selected sort
            if "Date (Oldest First)" in sort_choice:
                order_by = [ServiceJob.created_at.asc()]
            elif "Days (Most Overdue First)" in sort_choice or "Days (Highest First)" in sort_choice:
                # Most days waiting = oldest created date first
                order_by = [ServiceJob.created_at.asc()]
            elif "Days (Fewest Days First)" in sort_choice or "Days (Lowest First)" in sort_choice:
                # Fewest days waiting = newest created date first
                order_by = [ServiceJob.created_at.desc()]
            elif "Status" in sort_choice:
                order_by = [status_order, ServiceJob.created_at.desc()]
            elif "Total (Highest First)" in sort_choice:
                order_by = [ServiceJob.total_amount.desc(), ServiceJob.created_at.desc()]
            elif "Total (Lowest First)" in sort_choice:
                order_by = [ServiceJob.total_amount.asc(), ServiceJob.created_at.desc()]
            elif "Balance (Highest Due First)" in sort_choice:
                order_by = [ServiceJob.balance.desc(), ServiceJob.created_at.desc()]
            elif "Balance (Lowest Due First)" in sort_choice:
                order_by = [ServiceJob.balance.asc(), ServiceJob.created_at.desc()]
            else:  # Default: Date (Newest First)
                order_by = [ServiceJob.created_at.desc()]

            jobs = query.order_by(*order_by).offset(self.jobs_offset).limit(25).all()

            if len(jobs) < 25:
                self.has_more_jobs = False

            start_row = self.table.rowCount()
            self.table.setRowCount(start_row + len(jobs))
            today = datetime.date.today()

            for offset_idx, j in enumerate(jobs):
                i = start_row + offset_idx
                # Col 0: Job # (Centered 6-digit numeric ID)
                job_item = QTableWidgetItem(j.job_number)
                job_item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(i, 0, job_item)

                # Col 1: Created Date
                if j.created_at:
                    date_str = j.created_at.strftime("%Y-%m-%d %H:%M") if hasattr(j.created_at, 'strftime') else str(j.created_at)
                    jdt = j.created_at.date() if hasattr(j.created_at, 'date') else j.created_at
                    diff_days = max(0, (today - jdt).days)
                else:
                    date_str = ""
                    diff_days = 0
                date_item = QTableWidgetItem(date_str)
                date_item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(i, 1, date_item)

                # Col 2: Days (how many days after received device)
                if diff_days == 0:
                    days_text = "0 d (Today)"
                elif diff_days == 1:
                    days_text = "1 Day"
                else:
                    days_text = f"{diff_days} Days"

                days_item = QTableWidgetItem(days_text)
                days_item.setTextAlignment(Qt.AlignCenter)

                # Alert styling for days waiting in shop
                if j.status == "Delivered":
                    days_item.setForeground(Qt.gray)
                elif diff_days >= 7:
                    days_item.setForeground(QColor("#dc2626"))  # Red for 7+ days (high delay)
                    font = days_item.font()
                    font.setBold(True)
                    days_item.setFont(font)
                elif diff_days >= 3:
                    days_item.setForeground(QColor("#d97706"))  # Amber for 3-6 days
                    font = days_item.font()
                    font.setBold(True)
                    days_item.setFont(font)
                else:
                    days_item.setForeground(QColor("#16a34a"))  # Green for 0-2 days
                self.table.setItem(i, 2, days_item)

                # Col 3: Customer
                self.table.setItem(i, 3, QTableWidgetItem(j.customer_name or ""))
                # Col 4: Mobile
                self.table.setItem(i, 4, QTableWidgetItem(j.mobile or ""))
                # Col 5: Device Detail
                self.table.setItem(i, 5, QTableWidgetItem(j.device_model or ""))
                
                # Col 6: Status
                status_item = QTableWidgetItem(j.status or "")
                status_item.setTextAlignment(Qt.AlignCenter)
                if j.status == "Received":
                    status_item.setForeground(Qt.cyan)
                elif j.status == "Under Repair":
                    status_item.setForeground(Qt.yellow)
                elif j.status == "Ready":
                    status_item.setForeground(Qt.green)
                elif j.status == "Delivered":
                    status_item.setForeground(Qt.gray)
                self.table.setItem(i, 6, status_item)

                # Col 7: Labor
                labor_item = QTableWidgetItem(f"₹{format_inr(j.service_charge)}")
                labor_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.table.setItem(i, 7, labor_item)

                # Col 8: Total
                tot_item = QTableWidgetItem(f"₹{format_inr(j.total_amount)}")
                tot_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.table.setItem(i, 8, tot_item)
                
                # Col 9: Balance
                bal_item = QTableWidgetItem(f"₹{format_inr(j.balance)}")
                bal_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                if j.balance > 0:
                    bal_item.setForeground(Qt.red)
                    font = bal_item.font()
                    font.setBold(True)
                    bal_item.setFont(font)
                self.table.setItem(i, 9, bal_item)

                # Col 10: Action Buttons (Logos)
                actions_widget = QWidget()
                actions_layout = QHBoxLayout(actions_widget)
                actions_layout.setContentsMargins(4, 2, 4, 2)
                actions_layout.setSpacing(6)
                actions_layout.setAlignment(Qt.AlignCenter)
                
                view_btn = QPushButton("👁")
                view_btn.setToolTip("View Job Card Details")
                view_btn.setCursor(Qt.PointingHandCursor)
                view_btn.setProperty("class", "btn-action-icon-view")
                view_btn.clicked.connect(lambda checked, jnum=j.job_number: self.view_job_details(jnum))
                actions_layout.addWidget(view_btn)
                
                bill_btn = QPushButton("🧾")
                bill_btn.setToolTip("Generate Bill / Invoice")
                bill_btn.setCursor(Qt.PointingHandCursor)
                bill_btn.setProperty("class", "btn-action-icon-success")
                bill_btn.clicked.connect(lambda checked, jnum=j.job_number: self.bill_job(job_number=jnum))
                actions_layout.addWidget(bill_btn)
                
                edit_btn = QPushButton("✏️")
                edit_btn.setToolTip("Edit Job Card")
                edit_btn.setCursor(Qt.PointingHandCursor)
                edit_btn.setProperty("class", "btn-action-icon-edit")
                edit_btn.clicked.connect(lambda checked, jnum=j.job_number: self.edit_job(job_number=jnum))
                actions_layout.addWidget(edit_btn)
                
                del_btn = QPushButton("🗑️")
                del_btn.setToolTip("Delete Job Card")
                del_btn.setCursor(Qt.PointingHandCursor)
                del_btn.setProperty("class", "btn-action-icon-delete")
                del_btn.clicked.connect(lambda checked, jnum=j.job_number: self.delete_job_invoice(jnum))
                actions_layout.addWidget(del_btn)
                
                self.table.setCellWidget(i, 10, actions_widget)

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

    def edit_job(self, *args, job_number=None):
        if not job_number:
            job_num = self.get_selected_job_number()
        else:
            job_num = job_number

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

    def bill_job(self, job_number=None):
        if not job_number:
            job_num = self.get_selected_job_number()
        else:
            job_num = job_number

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

    def view_job_details(self, job_number):
        session = Session()
        try:
            job = session.query(ServiceJob).filter_by(job_number=job_number).first()
            if not job:
                QMessageBox.warning(self, "Error", "Job card not found.")
                return

            # Retrieve Settings details for Company Header
            s_name = (session.query(Setting).filter_by(key='shop_name').first() or Setting(value='I TECH MOBILES,')).value
            s_contact = (session.query(Setting).filter_by(key='shop_contact').first() or Setting(value='')).value
            s_address = (session.query(Setting).filter_by(key='shop_address').first() or Setting(value='')).value
            s_gst = (session.query(Setting).filter_by(key='shop_gst').first() or Setting(value='')).value

            dialog = QDialog(self)
            dialog.setWindowTitle(f"Job Card Details / Service Invoice - {job.job_number}")
            dialog.setMinimumSize(700, 600)
            dialog.resize(760, 740)
            dialog.setStyleSheet("QDialog { background-color: #f1f5f9; }")
            
            main_dlg_layout = QVBoxLayout(dialog)
            main_dlg_layout.setContentsMargins(12, 12, 12, 12)
            main_dlg_layout.setSpacing(10)

            # Scroll Area for responsive desktop & mobile viewing
            scroll_area = QScrollArea()
            scroll_area.setWidgetResizable(True)
            scroll_area.setFrameShape(QFrame.NoFrame)
            scroll_area.setStyleSheet("QScrollArea { background: transparent; border: none; }")
            
            scroll_content = QWidget()
            scroll_layout = QVBoxLayout(scroll_content)
            scroll_layout.setContentsMargins(0, 0, 0, 0)
            scroll_layout.setSpacing(0)

            # Invoice Paper Sheet (White container)
            paper_sheet = QFrame()
            paper_sheet.setObjectName("invoice_paper_sheet")
            paper_sheet.setStyleSheet("""
                QFrame#invoice_paper_sheet {
                    background-color: #ffffff;
                    border: 1px solid #cbd5e1;
                    border-radius: 8px;
                }
            """)
            paper_layout = QVBoxLayout(paper_sheet)
            paper_layout.setContentsMargins(28, 24, 28, 24)
            paper_layout.setSpacing(14)
            
            # 1. Company Header (Left) & Invoice Title/Date (Right)
            top_header_layout = QHBoxLayout()
            top_header_layout.setContentsMargins(0, 0, 0, 0)
            top_header_layout.setSpacing(20)

            # Left: Company Details
            comp_box = QVBoxLayout()
            comp_box.setSpacing(3)
            comp_title = QLabel(f"<b>{s_name}</b>")
            comp_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #4338ca;")
            comp_box.addWidget(comp_title)

            if s_address:
                comp_addr = QLabel(s_address)
                comp_addr.setStyleSheet("font-size: 11px; color: #475569;")
                comp_box.addWidget(comp_addr)
            if s_contact:
                comp_cnt = QLabel(f"Contact: {s_contact}")
                comp_cnt.setStyleSheet("font-size: 11px; color: #475569;")
                comp_box.addWidget(comp_cnt)
            if s_gst:
                comp_gst = QLabel(f"GSTIN: {s_gst}")
                comp_gst.setStyleSheet("font-size: 11px; color: #475569;")
                comp_box.addWidget(comp_gst)

            top_header_layout.addLayout(comp_box, 1)

            # Right: Invoice Title & Meta
            meta_box = QVBoxLayout()
            meta_box.setSpacing(4)
            meta_box.setAlignment(Qt.AlignRight | Qt.AlignTop)

            inv_title = QLabel("SERVICE INVOICE")
            inv_title.setStyleSheet("font-size: 20px; font-weight: 800; color: #1e1b4b; letter-spacing: 0.5px;")
            inv_title.setAlignment(Qt.AlignRight)
            meta_box.addWidget(inv_title)

            job_num_lbl = QLabel(f"Job Number: <b>{job.job_number}</b>")
            job_num_lbl.setStyleSheet("font-size: 12px; color: #1e293b;")
            job_num_lbl.setAlignment(Qt.AlignRight)
            meta_box.addWidget(job_num_lbl)

            created_date_str = job.created_at.strftime("%Y-%m-%d %H:%M") if job.created_at else "-"
            date_lbl = QLabel(f"Date: {created_date_str}")
            date_lbl.setStyleSheet("font-size: 11px; color: #64748b;")
            date_lbl.setAlignment(Qt.AlignRight)
            meta_box.addWidget(date_lbl)

            top_header_layout.addLayout(meta_box, 1)
            paper_layout.addLayout(top_header_layout)

            # 2. Customer Details Section (Top-Left, no Device Details on top-right)
            cust_section = QVBoxLayout()
            cust_section.setSpacing(4)
            cust_section.setContentsMargins(0, 8, 0, 8)

            cust_head = QLabel("<b>CUSTOMER DETAILS:</b>")
            cust_head.setStyleSheet("font-size: 12px; font-weight: bold; color: #1e1b4b;")
            cust_section.addWidget(cust_head)

            cust_name_lbl = QLabel(f"Name: {job.customer_name or '-'}")
            cust_name_lbl.setStyleSheet("font-size: 12px; color: #334155;")
            cust_section.addWidget(cust_name_lbl)

            cust_mob_lbl = QLabel(f"Mobile: {job.mobile or '-'}")
            cust_mob_lbl.setStyleSheet("font-size: 12px; color: #334155;")
            cust_section.addWidget(cust_mob_lbl)

            paper_layout.addLayout(cust_section)

            # Divider line below Customer Details
            div_line1 = QFrame()
            div_line1.setFrameShape(QFrame.HLine)
            div_line1.setStyleSheet("border: none; border-top: 1px solid #cbd5e1; margin-bottom: 6px;")
            paper_layout.addWidget(div_line1)
            
            # 3. Service / Part Description Table (Displayed prominently first)
            items_table = QTableWidget()
            items_table.setColumnCount(4)
            items_table.setHorizontalHeaderLabels(["Service / Part Description", "Qty", "Rate (₹)", "Total (₹)"])
            items_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
            items_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
            items_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
            items_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
            items_table.verticalHeader().setVisible(False)
            items_table.setStyleSheet("""
                QTableWidget {
                    border: 1px solid #e2e8f0;
                    background-color: #ffffff;
                    gridline-color: #f1f5f9;
                }
                QHeaderView::section {
                    background-color: #1e1b4b;
                    color: #ffffff;
                    font-weight: bold;
                    font-size: 11px;
                    padding: 7px 10px;
                    border: none;
                }
            """)
            
            # Row items list
            items = []
            # Service Labor
            items.append(("Service Labor & Diagnostic Charges", 1, job.service_charge, job.service_charge))
            # Spare Parts
            parts = session.query(ServicePart).filter_by(job_id=job.id).all()
            for part in parts:
                items.append((part.part_name, part.qty, part.cost, part.qty * part.cost))
                
            items_table.setRowCount(len(items))
            for i, (desc, qty, rate, subtotal) in enumerate(items):
                items_table.setItem(i, 0, QTableWidgetItem(desc))
                q_item = QTableWidgetItem(str(qty))
                q_item.setTextAlignment(Qt.AlignCenter)
                items_table.setItem(i, 1, q_item)
                r_item = QTableWidgetItem(f"₹{format_inr(rate)}")
                r_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                items_table.setItem(i, 2, r_item)
                t_item = QTableWidgetItem(f"₹{format_inr(subtotal)}")
                t_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                t_font = t_item.font()
                t_font.setBold(True)
                t_item.setFont(t_font)
                items_table.setItem(i, 3, t_item)
                
            items_table.setFixedHeight(min(180, 36 * len(items) + 38))
            paper_layout.addWidget(items_table)

            # 4. Center-aligned Device, Technician & Complaint Information Block
            # Positioned immediately BELOW the Service / Part Description table
            info_block = QFrame()
            info_block.setObjectName("repair_info_block")
            info_block.setStyleSheet("""
                QFrame#repair_info_block {
                    background-color: #f8fafc;
                    border: 1px solid #cbd5e1;
                    border-radius: 8px;
                }
                QFrame#repair_info_block QLabel {
                    border: none;
                    background: transparent;
                }
            """)
            info_block_layout = QVBoxLayout(info_block)
            info_block_layout.setContentsMargins(18, 14, 18, 14)
            info_block_layout.setSpacing(10)

            block_title = QLabel("DEVICE & REPAIR SPECIFICATIONS")
            block_title.setStyleSheet("font-size: 12px; font-weight: bold; color: #1e1b4b; border-bottom: 1px solid #e2e8f0; padding-bottom: 6px;")
            info_block_layout.addWidget(block_title)

            details_grid = QGridLayout()
            details_grid.setHorizontalSpacing(40)
            details_grid.setVerticalSpacing(8)

            # Col 0: Device Details
            sec1_head = QLabel("DEVICE DETAILS")
            sec1_head.setStyleSheet("font-size: 11px; font-weight: bold; color: #4338ca; text-transform: uppercase;")
            details_grid.addWidget(sec1_head, 0, 0)

            lbl_m = QLabel(f"<span style='color: #64748b;'>Device Model / Detail:</span> <b>{job.device_model or '-'}</b>")
            lbl_m.setStyleSheet("font-size: 12px; color: #1e293b;")
            details_grid.addWidget(lbl_m, 1, 0)

            lbl_i = QLabel(f"<span style='color: #64748b;'>Device ID / IMEI / Serial:</span> <b>{job.imei or '-'}</b>")
            lbl_i.setStyleSheet("font-size: 12px; color: #1e293b;")
            details_grid.addWidget(lbl_i, 2, 0)

            # Col 1: Technician Details & Status
            sec2_head = QLabel("TECHNICIAN & REPAIR STATUS")
            sec2_head.setStyleSheet("font-size: 11px; font-weight: bold; color: #4338ca; text-transform: uppercase;")
            details_grid.addWidget(sec2_head, 0, 1)

            lbl_t = QLabel(f"<span style='color: #64748b;'>Assigned Technician:</span> <b>{job.technician or '-'}</b>")
            lbl_t.setStyleSheet("font-size: 12px; color: #1e293b;")
            details_grid.addWidget(lbl_t, 1, 1)

            lbl_s = QLabel(f"<span style='color: #64748b;'>Job Status:</span> <b>{job.status or '-'}</b>")
            lbl_s.setStyleSheet("font-size: 12px; color: #1e293b;")
            details_grid.addWidget(lbl_s, 2, 1)

            info_block_layout.addLayout(details_grid)

            # Divider line inside card
            c_div = QFrame()
            c_div.setFrameShape(QFrame.HLine)
            c_div.setStyleSheet("border: none; border-top: 1px solid #e2e8f0; margin-top: 4px; margin-bottom: 4px;")
            info_block_layout.addWidget(c_div)

            # Complaint Details (full width, wrapping long text cleanly)
            sec3_head = QLabel("COMPLAINT & ISSUE DETAILS")
            sec3_head.setStyleSheet("font-size: 11px; font-weight: bold; color: #4338ca; text-transform: uppercase;")
            info_block_layout.addWidget(sec3_head)

            lbl_c = QLabel(job.complaint or "-")
            lbl_c.setWordWrap(True)
            lbl_c.setStyleSheet("font-size: 12px; color: #334155; line-height: 1.4;")
            info_block_layout.addWidget(lbl_c)

            paper_layout.addWidget(info_block)
            
            # 5. Right-Aligned Summary & Totals Block
            totals_container = QHBoxLayout()
            totals_container.addStretch()

            totals_box = QGridLayout()
            totals_box.setHorizontalSpacing(24)
            totals_box.setVerticalSpacing(6)

            tot_lbl1 = QLabel("Grand Total:")
            tot_lbl1.setStyleSheet("font-size: 12px; font-weight: bold; color: #1e1b4b;")
            tot_val1 = QLabel(f"₹{format_inr(job.total_amount)}")
            tot_val1.setStyleSheet("font-size: 12px; font-weight: bold; color: #1e1b4b;")
            tot_val1.setAlignment(Qt.AlignRight)
            totals_box.addWidget(tot_lbl1, 0, 0)
            totals_box.addWidget(tot_val1, 0, 1)

            tot_lbl2 = QLabel("Amount Paid:")
            tot_lbl2.setStyleSheet("font-size: 12px; font-weight: bold; color: #1e1b4b;")
            tot_val2 = QLabel(f"₹{format_inr(job.paid_amount)}")
            tot_val2.setStyleSheet("font-size: 12px; font-weight: bold; color: #16a34a;")
            tot_val2.setAlignment(Qt.AlignRight)
            totals_box.addWidget(tot_lbl2, 1, 0)
            totals_box.addWidget(tot_val2, 1, 1)

            tot_lbl3 = QLabel("Balance Due:")
            tot_lbl3.setStyleSheet("font-size: 13px; font-weight: bold; color: #1e1b4b; border-bottom: 2px solid #6366f1; padding-bottom: 3px;")
            tot_val3 = QLabel(f"₹{format_inr(job.balance)}")
            tot_val3.setStyleSheet("font-size: 13px; font-weight: bold; color: #dc2626; border-bottom: 2px solid #6366f1; padding-bottom: 3px;")
            tot_val3.setAlignment(Qt.AlignRight)
            totals_box.addWidget(tot_lbl3, 2, 0)
            totals_box.addWidget(tot_val3, 2, 1)

            totals_container.addLayout(totals_box)
            paper_layout.addLayout(totals_container)

            # 6. Payment History Installments
            job_payments = session.query(Payment).filter_by(job_id=job.id).order_by(Payment.id.asc()).all()
            if job_payments:
                hist_lbl = QLabel("<b>Payment History (Installments):</b>")
                hist_lbl.setStyleSheet("font-size: 12px; font-weight: bold; color: #0f172a; margin-top: 6px;")
                paper_layout.addWidget(hist_lbl)

                pay_table = QTableWidget()
                pay_table.setColumnCount(4)
                pay_table.setHorizontalHeaderLabels(["Date", "Payment Mode", "Amount (₹)", "Remarks / Note"])
                pay_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
                pay_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
                pay_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
                pay_table.verticalHeader().setVisible(False)
                pay_table.setRowCount(len(job_payments))
                for idx, jp in enumerate(job_payments):
                    pay_table.setItem(idx, 0, QTableWidgetItem(jp.date.strftime("%Y-%m-%d")))
                    pay_table.setItem(idx, 1, QTableWidgetItem(jp.payment_mode))
                    amt_item = QTableWidgetItem(f"₹{format_inr(jp.amount)}")
                    amt_item.setForeground(Qt.darkGreen)
                    pay_table.setItem(idx, 2, amt_item)
                    pay_table.setItem(idx, 3, QTableWidgetItem(jp.remarks or "-"))
                pay_table.setFixedHeight(min(120, 32 * len(job_payments) + 32))
                paper_layout.addWidget(pay_table)

            # 7. Terms & Conditions and Thank You note
            terms_lbl = QLabel("<b>Terms & Conditions:</b><br/>1. 30 days warranty on spare parts replaced (does not cover physical/liquid damage).<br/>2. Please collect device within 15 days of repair completion.")
            terms_lbl.setStyleSheet("font-size: 10px; color: #64748b; line-height: 1.4; margin-top: 10px;")
            paper_layout.addWidget(terms_lbl)

            thank_lbl = QLabel("<b>Thank you! Visit again.</b>")
            thank_lbl.setStyleSheet("font-size: 12px; font-weight: bold; color: #6366f1; margin-top: 6px;")
            thank_lbl.setAlignment(Qt.AlignCenter)
            paper_layout.addWidget(thank_lbl)
            
            scroll_layout.addWidget(paper_sheet)
            scroll_area.setWidget(scroll_content)
            main_dlg_layout.addWidget(scroll_area, 1)

            # Pinned Bottom Buttons (Print & Close) - Always visible
            btn_layout = QHBoxLayout()
            btn_layout.setContentsMargins(10, 6, 10, 2)
            btn_layout.addStretch()
            
            print_btn = QPushButton("Print Invoice")
            print_btn.setProperty("class", "btn-success")
            print_btn.setStyleSheet("font-weight: bold; padding: 8px 24px; font-size: 13px; background-color: #16a34a; color: white; border-radius: 6px;")
            print_btn.clicked.connect(lambda: self.print_job_invoice(job_number))
            btn_layout.addWidget(print_btn)
            
            close_btn = QPushButton("Close")
            close_btn.setProperty("class", "btn-secondary")
            close_btn.setStyleSheet("padding: 8px 20px; font-size: 13px; background-color: #64748b; color: white; border-radius: 6px;")
            close_btn.clicked.connect(dialog.accept)
            btn_layout.addWidget(close_btn)
            
            main_dlg_layout.addLayout(btn_layout)
            
            dialog.exec()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load job details: {e}")
        finally:
            session.close()

    def print_job_invoice(self, job_number):
        session = Session()
        try:
            job = session.query(ServiceJob).filter_by(job_number=job_number).first()
            if not job:
                QMessageBox.warning(self, "Error", "Job card not found.")
                return
                
            # Retrieve Settings details
            s_name = session.query(Setting).filter_by(key='shop_name').first().value
            s_contact = session.query(Setting).filter_by(key='shop_contact').first().value
            s_address = session.query(Setting).filter_by(key='shop_address').first().value
            s_gst = session.query(Setting).filter_by(key='shop_gst').first().value

            # Prepare items list (spare parts)
            pdf_parts = []
            for item in job.parts:
                pdf_parts.append({
                    "name": item.part_name,
                    "qty": item.qty,
                    "cost": item.cost,
                    "total": item.qty * item.cost
                })

            # Payment installments for PDF
            pdf_payments = []
            job_payments = session.query(Payment).filter_by(job_id=job.id).order_by(Payment.id.asc()).all()
            for jp in job_payments:
                pdf_payments.append({
                    "date": jp.date.strftime("%Y-%m-%d"),
                    "mode": jp.payment_mode,
                    "amount": jp.amount,
                    "remarks": jp.remarks or "-"
                })

            # Prepare Service PDF data
            pdf_data = {
                "shop_name": s_name,
                "shop_contact": s_contact,
                "shop_address": s_address,
                "shop_gst": s_gst,
                "job_number": job.job_number,
                "date": job.created_at.strftime("%Y-%m-%d %H:%M"),
                "customer_name": job.customer_name,
                "customer_mobile": job.mobile,
                "device_model": job.device_model,
                "imei": job.imei,
                "complaint": job.complaint,
                "status": job.status,
                "technician": job.technician,
                "service_charge": job.service_charge,
                "parts": pdf_parts,
                "payments": pdf_payments,
                "total_amount": job.total_amount,
                "paid_amount": job.paid_amount,
                "balance": job.balance
            }

            os.makedirs("invoices", exist_ok=True)
            path = os.path.abspath(f"invoices/{job.job_number}.pdf")
            generate_service_pdf(pdf_data, path)
            
            QMessageBox.information(self, "Success", f"Service Invoice PDF generated at:\n{path}")
            
            # Auto-open
            try:
                os.startfile(path)
            except Exception as e:
                print(f"Could not auto-open PDF: {e}")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to print/generate PDF: {e}")
        finally:
            session.close()

    def delete_job_invoice(self, job_number):
        confirm = QMessageBox.question(
            self, "Confirm Delete", 
            "Are you sure you want to delete this job card?\nAll inventory stock, customer outstanding, and ledger payments will be reverted.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if confirm != QMessageBox.Yes:
            return
            
        session = Session()
        try:
            job = session.query(ServiceJob).filter_by(job_number=job_number).first()
            if not job:
                QMessageBox.warning(self, "Error", "Job card not found.")
                session.close()
                return
                
            # Revert inventory stock of spare parts used (add back stock)
            for part in job.parts:
                if part.product_id:
                    prod = session.query(Product).get(part.product_id)
                    if prod:
                        prod.stock_qty += part.qty
                    
            # Revert customer outstanding balance
            cust = session.query(Customer).filter_by(mobile=job.mobile).first()
            if cust:
                cust.outstanding_balance -= job.balance
                
            # Revert/delete ledger entries (CashTransaction/BankTransaction)
            cash_txs = session.query(CashTransaction).filter_by(source_type='service', source_id=job.id).all()
            for tx in cash_txs:
                session.delete(tx)
                
            bank_txs = session.query(BankTransaction).filter_by(source_type='service', source_id=job.id).all()
            for tx in bank_txs:
                # Revert bank account balance (deduct funds received from service)
                bank = session.query(BankAccount).get(tx.account_id)
                if bank:
                    bank.balance -= tx.amount
                session.delete(tx)
                
            # Delete Job Card (cascading deletes parts)
            session.delete(job)
            
            session.commit()
            QMessageBox.information(self, "Success", "Job card deleted and related records reverted successfully.")
            self.refresh_data()
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", f"Failed to delete job card: {e}")
        finally:
            session.close()
