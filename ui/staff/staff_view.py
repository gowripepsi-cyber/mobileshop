import os
import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QFrame, QFormLayout, QDialog, QTextEdit, QDoubleSpinBox, QDateEdit,
    QTabWidget, QSpacerItem, QSizePolicy, QFileDialog, QDialogButtonBox,
    QTimeEdit
)
from PySide6.QtCore import Qt, QDate, QTime
from PySide6.QtGui import QColor, QFont

from database import (
    Session, Setting, BankAccount, CashTransaction, BankTransaction,
    Staff, StaffAttendance, StaffSalaryPayment,
    generate_next_staff_code, generate_next_salary_payment_number
)
from utils.translator import tr


class StaffDialog(QDialog):
    """Dialog to Add or Edit a Staff Member."""
    def __init__(self, parent=None, staff_id=None):
        super().__init__(parent)
        self.staff_id = staff_id
        self.setWindowTitle("Add Staff Member" if not staff_id else "Edit Staff Details")
        self.setMinimumWidth(500)
        self.setModal(True)
        self.init_ui()
        self.load_data()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel("Add New Staff Profile" if not self.staff_id else "Edit Staff Profile")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #0f172a;")
        layout.addWidget(title)

        form_layout = QFormLayout()
        form_layout.setSpacing(10)

        # Staff Code
        self.code_input = QLineEdit()
        self.code_input.setReadOnly(True)
        self.code_input.setStyleSheet("background-color: #f1f5f9; color: #475569; font-weight: bold;")
        form_layout.addRow("Staff Code:", self.code_input)

        # Full Name
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Full Name of Employee *")
        form_layout.addRow("Full Name *:", self.name_input)

        # Mobile
        self.mobile_input = QLineEdit()
        self.mobile_input.setPlaceholderText("Mobile Number (10 digits) *")
        self.mobile_input.setMaxLength(15)
        form_layout.addRow("Mobile Number *:", self.mobile_input)

        # Email
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("Optional email address")
        form_layout.addRow("Email Address:", self.email_input)

        # Designation
        self.designation_combo = QComboBox()
        self.designation_combo.setEditable(True)
        self.designation_combo.addItems([
            "Technician", "Salesperson", "Cashier", "Store Manager", "Helper", "Accountant"
        ])
        form_layout.addRow("Designation *:", self.designation_combo)

        # Salary Type
        self.salary_type_combo = QComboBox()
        self.salary_type_combo.addItems(["Monthly", "Daily", "Weekly"])
        form_layout.addRow("Salary Type *:", self.salary_type_combo)

        # Base Salary
        self.salary_input = QDoubleSpinBox()
        self.salary_input.setRange(0.0, 999999.0)
        self.salary_input.setDecimals(2)
        self.salary_input.setPrefix("₹ ")
        self.salary_input.setStyleSheet("font-size: 13px; font-weight: bold;")
        form_layout.addRow("Base Salary (₹):", self.salary_input)

        # Joining Date
        self.join_date_input = QDateEdit()
        self.join_date_input.setCalendarPopup(True)
        self.join_date_input.setDate(QDate.currentDate())
        form_layout.addRow("Joining Date:", self.join_date_input)

        # ID Proof Type & Number
        id_layout = QHBoxLayout()
        self.id_type_combo = QComboBox()
        self.id_type_combo.addItems(["Aadhaar Card", "Voter ID", "PAN Card", "Driving License", "Other"])
        self.id_num_input = QLineEdit()
        self.id_num_input.setPlaceholderText("ID Proof Number")
        id_layout.addWidget(self.id_type_combo, 1)
        id_layout.addWidget(self.id_num_input, 2)
        form_layout.addRow("ID Proof:", id_layout)

        # Status
        self.status_combo = QComboBox()
        self.status_combo.addItems(["Active", "Inactive", "Resigned"])
        form_layout.addRow("Status:", self.status_combo)

        # Address
        self.address_input = QTextEdit()
        self.address_input.setPlaceholderText("Residential address...")
        self.address_input.setMaximumHeight(60)
        form_layout.addRow("Address:", self.address_input)

        # Notes
        self.notes_input = QTextEdit()
        self.notes_input.setPlaceholderText("Notes / Emergency contact...")
        self.notes_input.setMaximumHeight(50)
        form_layout.addRow("Notes:", self.notes_input)

        layout.addLayout(form_layout)

        # Buttons
        btn_box = QDialogButtonBox()
        self.save_btn = QPushButton(tr("Save Staff"))
        self.save_btn.setProperty("class", "btn-success")
        self.cancel_btn = QPushButton(tr("Cancel"))
        self.cancel_btn.setProperty("class", "btn-secondary")
        btn_box.addButton(self.save_btn, QDialogButtonBox.AcceptRole)
        btn_box.addButton(self.cancel_btn, QDialogButtonBox.RejectRole)
        self.save_btn.clicked.connect(self.save_staff)
        self.cancel_btn.clicked.connect(self.reject)
        layout.addWidget(btn_box)

    def load_data(self):
        session = Session()
        try:
            if not self.staff_id:
                code = generate_next_staff_code(session)
                self.code_input.setText(code)
            else:
                s = session.query(Staff).get(self.staff_id)
                if s:
                    self.code_input.setText(s.staff_code)
                    self.name_input.setText(s.name)
                    self.mobile_input.setText(s.mobile)
                    self.email_input.setText(s.email or "")
                    self.designation_combo.setCurrentText(s.designation or "Salesperson")
                    self.salary_type_combo.setCurrentText(s.salary_type or "Monthly")
                    self.salary_input.setValue(s.base_salary or 0.0)
                    if s.joining_date:
                        self.join_date_input.setDate(QDate(s.joining_date.year, s.joining_date.month, s.joining_date.day))
                    self.id_type_combo.setCurrentText(s.id_proof_type or "Aadhaar Card")
                    self.id_num_input.setText(s.id_proof_number or "")
                    self.status_combo.setCurrentText(s.status or "Active")
                    self.address_input.setPlainText(s.address or "")
                    self.notes_input.setPlainText(s.notes or "")
        finally:
            session.close()

    def save_staff(self):
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Validation", "Staff name is required.")
            return

        mobile = self.mobile_input.text().strip()
        if not mobile:
            QMessageBox.warning(self, "Validation", "Mobile number is required.")
            return

        q_date = self.join_date_input.date()
        j_date = datetime.date(q_date.year(), q_date.month(), q_date.day())

        session = Session()
        try:
            if not self.staff_id:
                code = self.code_input.text().strip() or generate_next_staff_code(session)
                # Check uniqueness
                exist = session.query(Staff).filter_by(staff_code=code).first()
                if exist:
                    code = generate_next_staff_code(session)

                st = Staff(
                    staff_code=code,
                    name=name,
                    mobile=mobile,
                    email=self.email_input.text().strip(),
                    designation=self.designation_combo.currentText().strip(),
                    salary_type=self.salary_type_combo.currentText(),
                    base_salary=self.salary_input.value(),
                    joining_date=j_date,
                    id_proof_type=self.id_type_combo.currentText(),
                    id_proof_number=self.id_num_input.text().strip(),
                    status=self.status_combo.currentText(),
                    address=self.address_input.toPlainText().strip(),
                    notes=self.notes_input.toPlainText().strip()
                )
                session.add(st)
            else:
                st = session.query(Staff).get(self.staff_id)
                if not st:
                    return
                st.name = name
                st.mobile = mobile
                st.email = self.email_input.text().strip()
                st.designation = self.designation_combo.currentText().strip()
                st.salary_type = self.salary_type_combo.currentText()
                st.base_salary = self.salary_input.value()
                st.joining_date = j_date
                st.id_proof_type = self.id_type_combo.currentText()
                st.id_proof_number = self.id_num_input.text().strip()
                st.status = self.status_combo.currentText()
                st.address = self.address_input.toPlainText().strip()
                st.notes = self.notes_input.toPlainText().strip()

            session.commit()
            self.accept()
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", f"Failed to save staff profile: {e}")
        finally:
            session.close()


class SalaryPaymentDialog(QDialog):
    """Dialog to Pay Salary or Advance to a Staff Member."""
    def __init__(self, parent=None, staff_id=None):
        super().__init__(parent)
        self.preselect_staff_id = staff_id
        self.setWindowTitle("Pay Salary / Advance")
        self.setMinimumWidth(480)
        self.setModal(True)
        self.init_ui()
        self.load_data()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel("Staff Salary / Advance Payout")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #0f172a;")
        layout.addWidget(title)

        form_layout = QFormLayout()
        form_layout.setSpacing(11)

        # Payment #
        self.pay_num_input = QLineEdit()
        self.pay_num_input.setReadOnly(True)
        self.pay_num_input.setStyleSheet("background-color: #f1f5f9; color: #475569; font-weight: bold;")
        form_layout.addRow("Payment #:", self.pay_num_input)

        # Date
        self.date_input = QDateEdit()
        self.date_input.setCalendarPopup(True)
        self.date_input.setDate(QDate.currentDate())
        form_layout.addRow("Date *:", self.date_input)

        # Staff Selection
        self.staff_combo = QComboBox()
        self.staff_combo.currentIndexChanged.connect(self.on_staff_changed)
        form_layout.addRow("Staff Member *:", self.staff_combo)

        # Payment Type
        self.type_combo = QComboBox()
        self.type_combo.addItems(["Salary", "Advance", "Bonus", "Incentive"])
        self.type_combo.currentIndexChanged.connect(self.on_type_changed)
        form_layout.addRow("Payment Type *:", self.type_combo)

        # For Month
        today = datetime.date.today()
        self.month_combo = QComboBox()
        for offset in range(-6, 3):
            # approximate months
            yr = today.year + (today.month + offset - 1) // 12
            mo = (today.month + offset - 1) % 12 + 1
            m_str = f"{yr}-{mo:02d}"
            self.month_combo.addItem(m_str, m_str)
        self.month_combo.setCurrentText(f"{today.year}-{today.month:02d}")
        form_layout.addRow("For Month *:", self.month_combo)

        # Gross Amount
        self.gross_input = QDoubleSpinBox()
        self.gross_input.setRange(0.0, 999999.0)
        self.gross_input.setDecimals(2)
        self.gross_input.setPrefix("₹ ")
        self.gross_input.setStyleSheet("font-size: 13px; font-weight: bold;")
        self.gross_input.valueChanged.connect(self.recalc_net)
        form_layout.addRow("Gross Amount (₹) *:", self.gross_input)

        # Deductions (Advance adjustment, etc.)
        self.deductions_input = QDoubleSpinBox()
        self.deductions_input.setRange(0.0, 999999.0)
        self.deductions_input.setDecimals(2)
        self.deductions_input.setPrefix("₹ ")
        self.deductions_input.valueChanged.connect(self.recalc_net)
        form_layout.addRow("Deductions (₹):", self.deductions_input)

        # Net Paid
        self.net_lbl = QLabel("₹ 0.00")
        self.net_lbl.setStyleSheet("font-size: 15px; font-weight: 800; color: #10b981;")
        form_layout.addRow("Net Paid (₹):", self.net_lbl)

        # Payment Mode
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Cash Drawer", "Bank Account"])
        self.mode_combo.currentIndexChanged.connect(self.on_mode_changed)
        form_layout.addRow("Paid Via *:", self.mode_combo)

        # Bank Account
        self.bank_combo = QComboBox()
        self.bank_combo.setEnabled(False)
        form_layout.addRow("Bank Account:", self.bank_combo)

        # Notes
        self.notes_input = QTextEdit()
        self.notes_input.setPlaceholderText("Payment notes, deduction details...")
        self.notes_input.setMaximumHeight(60)
        form_layout.addRow("Notes:", self.notes_input)

        layout.addLayout(form_layout)

        # Buttons
        btn_box = QDialogButtonBox()
        self.save_btn = QPushButton(tr("Process Payout"))
        self.save_btn.setProperty("class", "btn-success")
        self.cancel_btn = QPushButton(tr("Cancel"))
        self.cancel_btn.setProperty("class", "btn-secondary")
        btn_box.addButton(self.save_btn, QDialogButtonBox.AcceptRole)
        btn_box.addButton(self.cancel_btn, QDialogButtonBox.RejectRole)
        self.save_btn.clicked.connect(self.save_payout)
        self.cancel_btn.clicked.connect(self.reject)
        layout.addWidget(btn_box)

    def on_mode_changed(self, idx):
        is_bank = (idx == 1)
        self.bank_combo.setEnabled(is_bank)
        if not is_bank:
            self.bank_combo.setCurrentIndex(-1)
        elif self.bank_combo.count() > 0 and self.bank_combo.currentIndex() == -1:
            self.bank_combo.setCurrentIndex(0)

    def on_type_changed(self, idx):
        session = Session()
        try:
            ptype = self.type_combo.currentText()
            pnum = generate_next_salary_payment_number(session, ptype)
            self.pay_num_input.setText(pnum)
            if ptype == "Advance":
                self.deductions_input.setValue(0.0)
                self.deductions_input.setEnabled(False)
            else:
                self.deductions_input.setEnabled(True)
        finally:
            session.close()

    def on_staff_changed(self, idx):
        staff_id = self.staff_combo.currentData()
        if not staff_id:
            return
        session = Session()
        try:
            st = session.query(Staff).get(staff_id)
            if st and self.type_combo.currentText() == "Salary":
                self.gross_input.setValue(st.base_salary or 0.0)
        finally:
            session.close()

    def recalc_net(self):
        gross = self.gross_input.value()
        ded = self.deductions_input.value()
        net = max(0.0, gross - ded)
        self.net_lbl.setText(f"₹ {net:,.2f}")

    def load_data(self):
        # Load Banks
        session = Session()
        try:
            banks = session.query(BankAccount).order_by(BankAccount.bank_name).all()
            for b in banks:
                self.bank_combo.addItem(f"{b.bank_name} ({b.account_number})", b.id)

            # Load Staff
            staff_list = session.query(Staff).filter_by(status='Active').order_by(Staff.name).all()
            sel_idx = 0
            for idx, s in enumerate(staff_list):
                self.staff_combo.addItem(f"{s.name} ({s.staff_code} - {s.designation})", s.id)
                if self.preselect_staff_id and s.id == self.preselect_staff_id:
                    sel_idx = idx

            if self.staff_combo.count() > 0:
                self.staff_combo.setCurrentIndex(sel_idx)

            ptype = self.type_combo.currentText()
            pnum = generate_next_salary_payment_number(session, ptype)
            self.pay_num_input.setText(pnum)

            # Pre-fill base salary
            cur_st_id = self.staff_combo.currentData()
            if cur_st_id:
                cur_st = session.query(Staff).get(cur_st_id)
                if cur_st:
                    self.gross_input.setValue(cur_st.base_salary or 0.0)

            self.recalc_net()
        finally:
            session.close()

    def save_payout(self):
        staff_id = self.staff_combo.currentData()
        if not staff_id:
            QMessageBox.warning(self, "Validation", "Please select a staff member.")
            return

        gross = self.gross_input.value()
        ded = self.deductions_input.value()
        net = max(0.0, gross - ded)
        if net <= 0 and gross <= 0:
            QMessageBox.warning(self, "Validation", "Amount must be greater than zero.")
            return

        is_bank = (self.mode_combo.currentIndex() == 1)
        bank_id = self.bank_combo.currentData() if is_bank else None
        if is_bank and not bank_id:
            QMessageBox.warning(self, "Validation", "Please select a bank account.")
            return

        q_date = self.date_input.date()
        p_date = datetime.date(q_date.year(), q_date.month(), q_date.day())
        ptype = self.type_combo.currentText()
        m_val = self.month_combo.currentText()
        notes = self.notes_input.toPlainText().strip()
        staff_name = self.staff_combo.currentText().split(" (")[0]

        session = Session()
        try:
            pnum = self.pay_num_input.text().strip() or generate_next_salary_payment_number(session, ptype)
            sal = StaffSalaryPayment(
                payment_number=pnum,
                staff_id=staff_id,
                date=p_date,
                payment_type=ptype,
                for_month=m_val,
                amount=gross,
                deductions=ded,
                net_paid=net,
                payment_mode='Bank' if is_bank else 'Cash',
                bank_id=bank_id,
                notes=notes
            )
            session.add(sal)
            session.flush()

            # Record Cash / Bank Transaction
            txn_desc = f"Staff {ptype} [{staff_name}] ({m_val}) (Ref: {pnum})"
            if is_bank:
                session.add(BankTransaction(
                    date=p_date,
                    transaction_type='withdrawal',
                    account_id=bank_id,
                    amount=net,
                    source_type='salary',
                    source_id=sal.id,
                    description=txn_desc
                ))
            else:
                session.add(CashTransaction(
                    date=p_date,
                    transaction_type='out',
                    amount=net,
                    source_type='salary',
                    source_id=sal.id,
                    description=txn_desc
                ))

            session.commit()
            self.accept()
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", f"Failed to record payout: {e}")
        finally:
            session.close()


class StaffLedgerDialog(QDialog):
    """Shows complete payout & advance history for a specific staff member."""
    def __init__(self, staff_id, parent=None):
        super().__init__(parent)
        self.staff_id = staff_id
        self.setMinimumWidth(700)
        self.setMinimumHeight(450)
        self.setModal(True)
        self.init_ui()
        self.load_history()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)

        self.title_lbl = QLabel("Staff Payment History")
        self.title_lbl.setStyleSheet("font-size: 16px; font-weight: bold; color: #0f172a;")
        layout.addWidget(self.title_lbl)

        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "Payment #", "Date", "Type", "For Month", "Gross (₹)", "Deductions (₹)", "Net Paid (₹)", "Mode"
        ])
        hdr = self.table.horizontalHeader()
        hdr.setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table)

        # Summary footer
        self.summary_lbl = QLabel("")
        self.summary_lbl.setStyleSheet("font-size: 13px; font-weight: bold; color: #334155;")
        layout.addWidget(self.summary_lbl)

        btn_close = QPushButton("Close")
        btn_close.setProperty("class", "btn-secondary")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close, alignment=Qt.AlignRight)

    def load_history(self):
        session = Session()
        try:
            st = session.query(Staff).get(self.staff_id)
            if not st:
                return
            self.setWindowTitle(f"Payment History - {st.name} ({st.staff_code})")
            self.title_lbl.setText(f"Salary & Advance Ledger: {st.name} ({st.staff_code})")

            payments = session.query(StaffSalaryPayment).filter_by(staff_id=self.staff_id).order_by(StaffSalaryPayment.date.desc()).all()
            self.table.setRowCount(len(payments))

            total_sal = 0.0
            total_adv = 0.0
            total_net = 0.0

            for i, p in enumerate(payments):
                self.table.setItem(i, 0, QTableWidgetItem(p.payment_number))
                self.table.setItem(i, 1, QTableWidgetItem(p.date.strftime("%Y-%m-%d") if p.date else "-"))
                self.table.setItem(i, 2, QTableWidgetItem(p.payment_type))
                self.table.setItem(i, 3, QTableWidgetItem(p.for_month or "-"))
                self.table.setItem(i, 4, QTableWidgetItem(f"{p.amount:,.2f}"))
                self.table.setItem(i, 5, QTableWidgetItem(f"{p.deductions:,.2f}"))
                self.table.setItem(i, 6, QTableWidgetItem(f"{p.net_paid:,.2f}"))
                self.table.setItem(i, 7, QTableWidgetItem(p.payment_mode))

                if p.payment_type == "Salary":
                    total_sal += p.amount
                elif p.payment_type == "Advance":
                    total_adv += p.amount
                total_net += p.net_paid

            self.summary_lbl.setText(
                f"Total Salary Earned: ₹{total_sal:,.2f}  |  Total Advances: ₹{total_adv:,.2f}  |  Total Net Paid: ₹{total_net:,.2f}"
            )
        finally:
            session.close()


class StaffView(QWidget):
    """Staff Management View (Directory, Daily Attendance, Salary Payouts)."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        self.load_data()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(12)

        # Tab Widget
        self.tabs = QTabWidget()
        self.tabs.setObjectName("custom_tabs")

        # 1. Staff Directory Tab
        self.directory_tab = QWidget()
        self.setup_directory_tab()
        self.tabs.addTab(self.directory_tab, f"👥 {tr('Staff Directory')}")

        # 2. Daily Attendance Tab
        self.attendance_tab = QWidget()
        self.setup_attendance_tab()
        self.tabs.addTab(self.attendance_tab, f"📅 {tr('Daily Attendance')}")

        # 3. Salary & Advances Tab
        self.salary_tab = QWidget()
        self.setup_salary_tab()
        self.tabs.addTab(self.salary_tab, f"💰 {tr('Salary & Advances')}")

        main_layout.addWidget(self.tabs)

    # -------------------------------------------------------------
    # TAB 1: STAFF DIRECTORY
    # -------------------------------------------------------------
    def setup_directory_tab(self):
        layout = QVBoxLayout(self.directory_tab)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # KPI Summary Cards
        kpi_layout = QHBoxLayout()
        kpi_layout.setSpacing(15)

        self.card_total_staff = self._create_kpi_card("TOTAL STAFF", "0", "#6366f1")
        self.card_active_staff = self._create_kpi_card("ACTIVE EMPLOYEES", "0", "#10b981")
        self.card_tech_count = self._create_kpi_card("TECHNICIANS", "0", "#f59e0b")
        self.card_monthly_payroll = self._create_kpi_card("EST. MONTHLY PAYROLL", "₹0.00", "#ef4444")

        kpi_layout.addWidget(self.card_total_staff)
        kpi_layout.addWidget(self.card_active_staff)
        kpi_layout.addWidget(self.card_tech_count)
        kpi_layout.addWidget(self.card_monthly_payroll)
        layout.addLayout(kpi_layout)

        # Toolbar
        bar_frame = QFrame()
        bar_frame.setProperty("class", "CardFrame")
        bar_layout = QHBoxLayout(bar_frame)
        bar_layout.setContentsMargins(12, 10, 12, 10)
        bar_layout.setSpacing(10)

        bar_layout.addWidget(QLabel("Designation:"))
        self.filter_staff_desig = QComboBox()
        self.filter_staff_desig.addItems(["All", "Technician", "Salesperson", "Cashier", "Store Manager", "Helper", "Accountant"])
        self.filter_staff_desig.currentIndexChanged.connect(self.load_staff_table)
        bar_layout.addWidget(self.filter_staff_desig)

        bar_layout.addWidget(QLabel("Status:"))
        self.filter_staff_status = QComboBox()
        self.filter_staff_status.addItems(["All", "Active", "Inactive", "Resigned"])
        self.filter_staff_status.setCurrentText("Active")
        self.filter_staff_status.currentIndexChanged.connect(self.load_staff_table)
        bar_layout.addWidget(self.filter_staff_status)

        self.search_staff_input = QLineEdit()
        self.search_staff_input.setPlaceholderText("Search Staff Name, Mobile, Code...")
        self.search_staff_input.textChanged.connect(self.load_staff_table)
        bar_layout.addWidget(self.search_staff_input)

        bar_layout.addStretch()

        self.btn_add_staff = QPushButton("➕ Add New Staff")
        self.btn_add_staff.setProperty("class", "btn-primary")
        self.btn_add_staff.setFixedHeight(34)
        self.btn_add_staff.clicked.connect(self.open_add_staff_dialog)
        bar_layout.addWidget(self.btn_add_staff)

        layout.addWidget(bar_frame)

        # Staff Table
        self.staff_table = QTableWidget()
        self.staff_table.setColumnCount(9)
        self.staff_table.setHorizontalHeaderLabels([
            "Staff Code", "Full Name", "Designation", "Mobile", "Salary Type",
            "Base Salary (₹)", "Joining Date", "Status", "Action"
        ])
        header = self.staff_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.setSectionResizeMode(1, QHeaderView.Stretch)  # Name stretches
        self.staff_table.setColumnWidth(0, 85)   # Code
        self.staff_table.setColumnWidth(2, 110)  # Desig
        self.staff_table.setColumnWidth(3, 100)  # Mobile
        self.staff_table.setColumnWidth(4, 85)   # Type
        self.staff_table.setColumnWidth(5, 95)   # Salary
        self.staff_table.setColumnWidth(6, 90)   # Join date
        self.staff_table.setColumnWidth(7, 85)   # Status
        header.setSectionResizeMode(8, QHeaderView.Fixed)
        self.staff_table.setColumnWidth(8, 170)  # Actions
        self.staff_table.verticalHeader().setVisible(False)
        self.staff_table.verticalHeader().setDefaultSectionSize(48)
        layout.addWidget(self.staff_table)

    def _create_kpi_card(self, title, default_val, border_color):
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: #ffffff;
                border: 1px solid #e2e8f0;
                border-left: 5px solid {border_color};
                border-radius: 16px;
                padding: 12px 16px;
            }}
        """)
        c_layout = QVBoxLayout(card)
        c_layout.setContentsMargins(0, 0, 0, 0)
        c_layout.setSpacing(4)

        lbl_title = QLabel(title)
        lbl_title.setStyleSheet("font-size: 11px; font-weight: 700; color: #64748b; letter-spacing: 0.5px;")
        lbl_val = QLabel(default_val)
        lbl_val.setStyleSheet("font-size: 20px; font-weight: 800; color: #0f172a;")
        c_layout.addWidget(lbl_title)
        c_layout.addWidget(lbl_val)

        card.lbl_val = lbl_val
        return card

    def open_add_staff_dialog(self):
        dlg = StaffDialog(self)
        if dlg.exec() == QDialog.Accepted:
            self.load_data()

    def open_edit_staff_dialog(self, staff_id):
        dlg = StaffDialog(self, staff_id=staff_id)
        if dlg.exec() == QDialog.Accepted:
            self.load_data()

    def open_staff_ledger(self, staff_id):
        dlg = StaffLedgerDialog(staff_id, self)
        dlg.exec()

    def delete_staff(self, staff_id):
        confirm = QMessageBox.question(
            self, "Confirm Delete",
            "Are you sure you want to delete this staff record?\nAll attendance and salary history for this staff member will be removed.",
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm == QMessageBox.Yes:
            session = Session()
            try:
                session.query(Staff).filter_by(id=staff_id).delete()
                session.commit()
                self.load_data()
            except Exception as e:
                session.rollback()
                QMessageBox.critical(self, "Error", f"Failed to delete staff: {e}")
            finally:
                session.close()

    # -------------------------------------------------------------
    # TAB 2: DAILY ATTENDANCE
    # -------------------------------------------------------------
    def setup_attendance_tab(self):
        layout = QVBoxLayout(self.attendance_tab)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # Date control bar
        ctrl_frame = QFrame()
        ctrl_frame.setProperty("class", "CardFrame")
        c_layout = QHBoxLayout(ctrl_frame)
        c_layout.setContentsMargins(12, 10, 12, 10)
        c_layout.setSpacing(8)

        self.btn_prev_day = QPushButton("◀ Prev Day")
        self.btn_prev_day.setProperty("class", "btn-secondary")
        self.btn_prev_day.clicked.connect(self.prev_attendance_day)
        c_layout.addWidget(self.btn_prev_day)

        self.att_date_picker = QDateEdit()
        self.att_date_picker.setCalendarPopup(True)
        self.att_date_picker.setDate(QDate.currentDate())
        self.att_date_picker.dateChanged.connect(self.load_attendance_for_date)
        c_layout.addWidget(self.att_date_picker)

        self.btn_next_day = QPushButton("Next Day ▶")
        self.btn_next_day.setProperty("class", "btn-secondary")
        self.btn_next_day.clicked.connect(self.next_attendance_day)
        c_layout.addWidget(self.btn_next_day)

        self.btn_today_att = QPushButton("Today")
        self.btn_today_att.setProperty("class", "btn-secondary")
        self.btn_today_att.clicked.connect(lambda: self.att_date_picker.setDate(QDate.currentDate()))
        c_layout.addWidget(self.btn_today_att)

        c_layout.addStretch()

        self.btn_mark_all_present = QPushButton(f"✓ {tr('Mark All Present')}")
        self.btn_mark_all_present.setProperty("class", "btn-secondary")
        self.btn_mark_all_present.setFixedHeight(34)
        self.btn_mark_all_present.clicked.connect(self.mark_all_present)
        c_layout.addWidget(self.btn_mark_all_present)

        self.btn_save_attendance = QPushButton(f"💾 {tr('Save Attendance')}")
        self.btn_save_attendance.setProperty("class", "btn-success")
        self.btn_save_attendance.setFixedHeight(34)
        self.btn_save_attendance.clicked.connect(self.save_attendance)
        c_layout.addWidget(self.btn_save_attendance)

        layout.addWidget(ctrl_frame)

        # KPI attendance badges
        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(15)
        self.card_att_total = self._create_kpi_card("STAFF ON DUTY", "0", "#6366f1")
        self.card_att_present = self._create_kpi_card("PRESENT TODAY", "0", "#10b981")
        self.card_att_absent = self._create_kpi_card("ABSENT TODAY", "0", "#ef4444")
        self.card_att_leave = self._create_kpi_card("HALF DAY / LEAVE", "0", "#f59e0b")

        kpi_row.addWidget(self.card_att_total)
        kpi_row.addWidget(self.card_att_present)
        kpi_row.addWidget(self.card_att_absent)
        kpi_row.addWidget(self.card_att_leave)
        layout.addLayout(kpi_row)

        # Attendance Table
        self.att_table = QTableWidget()
        self.att_table.setColumnCount(7)
        self.att_table.setHorizontalHeaderLabels([
            "Staff Code", "Full Name", "Designation", "Status", "In Time", "Out Time", "Notes / Remarks"
        ])
        att_hdr = self.att_table.horizontalHeader()
        att_hdr.setSectionResizeMode(QHeaderView.Interactive)
        att_hdr.setSectionResizeMode(1, QHeaderView.Stretch)  # Name stretches
        att_hdr.setSectionResizeMode(6, QHeaderView.Stretch)  # Notes stretches
        self.att_table.setColumnWidth(0, 85)   # Code
        self.att_table.setColumnWidth(2, 120)  # Desig
        self.att_table.setColumnWidth(3, 130)  # Status combo
        self.att_table.setColumnWidth(4, 95)   # In time
        self.att_table.setColumnWidth(5, 95)   # Out time
        self.att_table.verticalHeader().setVisible(False)
        self.att_table.verticalHeader().setDefaultSectionSize(46)
        layout.addWidget(self.att_table)

    def prev_attendance_day(self):
        cur = self.att_date_picker.date()
        self.att_date_picker.setDate(cur.addDays(-1))

    def next_attendance_day(self):
        cur = self.att_date_picker.date()
        self.att_date_picker.setDate(cur.addDays(1))

    def mark_all_present(self):
        for r in range(self.att_table.rowCount()):
            combo = self.att_table.cellWidget(r, 3)
            if combo:
                combo.setCurrentText("Present")
        self.update_attendance_kpis()

    def update_attendance_kpis(self):
        total = self.att_table.rowCount()
        present = 0
        absent = 0
        leave = 0
        for r in range(total):
            combo = self.att_table.cellWidget(r, 3)
            if combo:
                st = combo.currentText()
                if st == "Present":
                    present += 1
                elif st == "Absent":
                    absent += 1
                else:
                    leave += 1
        self.card_att_total.lbl_val.setText(str(total))
        self.card_att_present.lbl_val.setText(str(present))
        self.card_att_absent.lbl_val.setText(str(absent))
        self.card_att_leave.lbl_val.setText(str(leave))

    def load_attendance_for_date(self):
        q_date = self.att_date_picker.date()
        sel_date = datetime.date(q_date.year(), q_date.month(), q_date.day())

        session = Session()
        try:
            # Active staff members
            active_staff = session.query(Staff).filter_by(status='Active').order_by(Staff.name).all()

            # Existing attendance for selected date
            existing_att = session.query(StaffAttendance).filter_by(date=sel_date).all()
            att_map = {a.staff_id: a for a in existing_att}

            self.att_table.setRowCount(len(active_staff))
            self.att_row_staff_ids = []

            for i, st in enumerate(active_staff):
                self.att_row_staff_ids.append(st.id)

                self.att_table.setItem(i, 0, QTableWidgetItem(st.staff_code))
                self.att_table.setItem(i, 1, QTableWidgetItem(st.name))
                self.att_table.setItem(i, 2, QTableWidgetItem(st.designation or "-"))

                att_rec = att_map.get(st.id)

                # Status combo
                st_combo = QComboBox()
                st_combo.addItems(["Present", "Absent", "Half Day", "Leave"])
                if att_rec:
                    st_combo.setCurrentText(att_rec.status or "Present")
                else:
                    st_combo.setCurrentText("Present")
                st_combo.currentIndexChanged.connect(self.update_attendance_kpis)
                self.att_table.setCellWidget(i, 3, st_combo)

                # In Time
                in_edit = QLineEdit()
                in_edit.setText(att_rec.in_time if (att_rec and att_rec.in_time) else "09:30 AM")
                in_edit.setAlignment(Qt.AlignCenter)
                self.att_table.setCellWidget(i, 4, in_edit)

                # Out Time
                out_edit = QLineEdit()
                out_edit.setText(att_rec.out_time if (att_rec and att_rec.out_time) else "08:30 PM")
                out_edit.setAlignment(Qt.AlignCenter)
                self.att_table.setCellWidget(i, 5, out_edit)

                # Remarks
                rem_edit = QLineEdit()
                rem_edit.setText(att_rec.notes if (att_rec and att_rec.notes) else "")
                rem_edit.setPlaceholderText("Notes...")
                self.att_table.setCellWidget(i, 6, rem_edit)

            self.update_attendance_kpis()
        finally:
            session.close()

    def save_attendance(self):
        q_date = self.att_date_picker.date()
        sel_date = datetime.date(q_date.year(), q_date.month(), q_date.day())

        session = Session()
        try:
            for r in range(self.att_table.rowCount()):
                st_id = self.att_row_staff_ids[r]
                st_combo = self.att_table.cellWidget(r, 3)
                in_edit = self.att_table.cellWidget(r, 4)
                out_edit = self.att_table.cellWidget(r, 5)
                rem_edit = self.att_table.cellWidget(r, 6)

                st_val = st_combo.currentText() if st_combo else "Present"
                in_val = in_edit.text().strip() if in_edit else ""
                out_val = out_edit.text().strip() if out_edit else ""
                rem_val = rem_edit.text().strip() if rem_edit else ""

                # Check existing
                att = session.query(StaffAttendance).filter_by(staff_id=st_id, date=sel_date).first()
                if not att:
                    att = StaffAttendance(
                        staff_id=st_id,
                        date=sel_date,
                        status=st_val,
                        in_time=in_val,
                        out_time=out_val,
                        notes=rem_val
                    )
                    session.add(att)
                else:
                    att.status = st_val
                    att.in_time = in_val
                    att.out_time = out_val
                    att.notes = rem_val

            session.commit()
            QMessageBox.information(self, "Attendance Saved", f"Attendance for {sel_date.strftime('%d-%b-%Y')} saved successfully.")
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", f"Failed to save attendance: {e}")
        finally:
            session.close()

    # -------------------------------------------------------------
    # TAB 3: SALARY & ADVANCES
    # -------------------------------------------------------------
    def setup_salary_tab(self):
        layout = QVBoxLayout(self.salary_tab)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # KPI Summary Cards
        kpi_layout = QHBoxLayout()
        kpi_layout.setSpacing(15)

        self.card_sal_paid_month = self._create_kpi_card("SALARY PAID (THIS MONTH)", "₹0.00", "#10b981")
        self.card_adv_given_month = self._create_kpi_card("ADVANCES GIVEN (THIS MONTH)", "₹0.00", "#f59e0b")
        self.card_tot_payout_month = self._create_kpi_card("TOTAL PAYOUT (THIS MONTH)", "₹0.00", "#6366f1")

        kpi_layout.addWidget(self.card_sal_paid_month)
        kpi_layout.addWidget(self.card_adv_given_month)
        kpi_layout.addWidget(self.card_tot_payout_month)
        layout.addLayout(kpi_layout)

        # Filter & Action Toolbar
        bar_frame = QFrame()
        bar_frame.setProperty("class", "CardFrame")
        bar_layout = QHBoxLayout(bar_frame)
        bar_layout.setContentsMargins(12, 10, 12, 10)
        bar_layout.setSpacing(10)

        bar_layout.addWidget(QLabel("Staff:"))
        self.filter_sal_staff = QComboBox()
        self.filter_sal_staff.addItem("All Staff Members", None)
        self.filter_sal_staff.currentIndexChanged.connect(self.load_salary_table)
        bar_layout.addWidget(self.filter_sal_staff)

        bar_layout.addWidget(QLabel("Type:"))
        self.filter_sal_type = QComboBox()
        self.filter_sal_type.addItems(["All Types", "Salary", "Advance", "Bonus", "Incentive"])
        self.filter_sal_type.currentIndexChanged.connect(self.load_salary_table)
        bar_layout.addWidget(self.filter_sal_type)

        bar_layout.addStretch()

        self.btn_pay_salary = QPushButton(f"➕ {tr('Pay Salary / Advance')}")
        self.btn_pay_salary.setProperty("class", "btn-success")
        self.btn_pay_salary.setFixedHeight(34)
        self.btn_pay_salary.clicked.connect(self.open_pay_salary_dialog)
        bar_layout.addWidget(self.btn_pay_salary)

        layout.addWidget(bar_frame)

        # Salary Records Table
        self.sal_table = QTableWidget()
        self.sal_table.setColumnCount(11)
        self.sal_table.setHorizontalHeaderLabels([
            "Payment #", "Date", "Staff Name", "Type", "For Month",
            "Gross (₹)", "Deductions (₹)", "Net Paid (₹)", "Mode", "Bank", "Action"
        ])
        s_hdr = self.sal_table.horizontalHeader()
        s_hdr.setSectionResizeMode(QHeaderView.Interactive)
        s_hdr.setSectionResizeMode(2, QHeaderView.Stretch)  # Staff Name stretches
        self.sal_table.setColumnWidth(0, 90)   # Payment #
        self.sal_table.setColumnWidth(1, 85)   # Date
        self.sal_table.setColumnWidth(3, 80)   # Type
        self.sal_table.setColumnWidth(4, 85)   # Month
        self.sal_table.setColumnWidth(5, 85)   # Gross
        self.sal_table.setColumnWidth(6, 85)   # Ded
        self.sal_table.setColumnWidth(7, 95)   # Net
        self.sal_table.setColumnWidth(8, 65)   # Mode
        self.sal_table.setColumnWidth(9, 100)  # Bank
        s_hdr.setSectionResizeMode(10, QHeaderView.Fixed)
        self.sal_table.setColumnWidth(10, 130) # Action
        self.sal_table.verticalHeader().setVisible(False)
        self.sal_table.verticalHeader().setDefaultSectionSize(48)
        layout.addWidget(self.sal_table)

    def open_pay_salary_dialog(self, staff_id=None):
        dlg = SalaryPaymentDialog(self, staff_id=staff_id)
        if dlg.exec() == QDialog.Accepted:
            self.load_data()

    def delete_salary_record(self, payment_id):
        confirm = QMessageBox.question(
            self, "Confirm Delete",
            "Are you sure you want to delete this payment record?\nAssociated Cash/Bank ledger entries will be reversed.",
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm == QMessageBox.Yes:
            session = Session()
            try:
                session.query(CashTransaction).filter_by(source_type='salary', source_id=payment_id).delete()
                session.query(BankTransaction).filter_by(source_type='salary', source_id=payment_id).delete()
                session.query(StaffSalaryPayment).filter_by(id=payment_id).delete()
                session.commit()
                self.load_data()
            except Exception as e:
                session.rollback()
                QMessageBox.critical(self, "Error", f"Failed to delete payment record: {e}")
            finally:
                session.close()

    # -------------------------------------------------------------
    # DATA LOADING
    # -------------------------------------------------------------
    def load_data(self):
        self.load_staff_table()
        self.load_attendance_for_date()
        self.populate_salary_staff_filter()
        self.load_salary_table()

    def refresh_data(self):
        self.load_data()

    def load_staff_table(self):
        session = Session()
        try:
            query = session.query(Staff)

            desig = self.filter_staff_desig.currentText()
            if desig != "All":
                query = query.filter_by(designation=desig)

            status = self.filter_staff_status.currentText()
            if status != "All":
                query = query.filter_by(status=status)

            search = self.search_staff_input.text().strip().lower()
            if search:
                query = query.filter(
                    (Staff.name.ilike(f"%{search}%")) |
                    (Staff.mobile.ilike(f"%{search}%")) |
                    (Staff.staff_code.ilike(f"%{search}%"))
                )

            staff_members = query.order_by(Staff.staff_code).all()

            # KPI calculations
            all_staff = session.query(Staff).all()
            tot_count = len(all_staff)
            act_count = sum(1 for s in all_staff if s.status == 'Active')
            tech_count = sum(1 for s in all_staff if s.status == 'Active' and (s.designation or '').lower() == 'technician')
            tot_payroll = sum((s.base_salary or 0.0) for s in all_staff if s.status == 'Active' and s.salary_type == 'Monthly')

            self.card_total_staff.lbl_val.setText(str(tot_count))
            self.card_active_staff.lbl_val.setText(str(act_count))
            self.card_tech_count.lbl_val.setText(str(tech_count))
            self.card_monthly_payroll.lbl_val.setText(f"₹{tot_payroll:,.2f}")

            # Populate Table
            self.staff_table.setRowCount(len(staff_members))
            for i, st in enumerate(staff_members):
                self.staff_table.setItem(i, 0, QTableWidgetItem(st.staff_code))
                self.staff_table.setItem(i, 1, QTableWidgetItem(st.name))
                self.staff_table.setItem(i, 2, QTableWidgetItem(st.designation or "-"))
                self.staff_table.setItem(i, 3, QTableWidgetItem(st.mobile))
                self.staff_table.setItem(i, 4, QTableWidgetItem(st.salary_type or "Monthly"))

                sal_item = QTableWidgetItem(f"₹{(st.base_salary or 0.0):,.2f}")
                sal_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.staff_table.setItem(i, 5, sal_item)

                j_date = st.joining_date.strftime("%Y-%m-%d") if st.joining_date else "-"
                self.staff_table.setItem(i, 6, QTableWidgetItem(j_date))

                # Status item
                st_item = QTableWidgetItem(st.status or "Active")
                st_item.setTextAlignment(Qt.AlignCenter)
                self.staff_table.setItem(i, 7, st_item)

                # Actions
                btn_widget = QWidget()
                btn_layout = QHBoxLayout(btn_widget)
                btn_layout.setContentsMargins(4, 2, 4, 2)
                btn_layout.setSpacing(4)

                btn_edit = QPushButton("Edit")
                btn_edit.setProperty("class", "btn-action-view")
                btn_edit.setFixedHeight(26)
                btn_edit.clicked.connect(lambda _, sid=st.id: self.open_edit_staff_dialog(sid))

                btn_ledger = QPushButton("Pay History")
                btn_ledger.setProperty("class", "btn-secondary")
                btn_ledger.setFixedHeight(26)
                btn_ledger.clicked.connect(lambda _, sid=st.id: self.open_staff_ledger(sid))

                btn_del = QPushButton("Delete")
                btn_del.setProperty("class", "btn-action-delete")
                btn_del.setFixedHeight(26)
                btn_del.clicked.connect(lambda _, sid=st.id: self.delete_staff(sid))

                btn_layout.addWidget(btn_edit)
                btn_layout.addWidget(btn_ledger)
                btn_layout.addWidget(btn_del)
                self.staff_table.setCellWidget(i, 8, btn_widget)

        finally:
            session.close()

    def populate_salary_staff_filter(self):
        cur_data = self.filter_sal_staff.currentData()
        self.filter_sal_staff.blockSignals(True)
        self.filter_sal_staff.clear()
        self.filter_sal_staff.addItem("All Staff Members", None)
        session = Session()
        try:
            staff_list = session.query(Staff).order_by(Staff.name).all()
            for s in staff_list:
                self.filter_sal_staff.addItem(f"{s.name} ({s.staff_code})", s.id)
            if cur_data:
                idx = self.filter_sal_staff.findData(cur_data)
                if idx >= 0:
                    self.filter_sal_staff.setCurrentIndex(idx)
        finally:
            session.close()
        self.filter_sal_staff.blockSignals(False)

    def load_salary_table(self):
        session = Session()
        try:
            query = session.query(StaffSalaryPayment)

            st_id = self.filter_sal_staff.currentData()
            if st_id:
                query = query.filter_by(staff_id=st_id)

            ptype = self.filter_sal_type.currentText()
            if ptype != "All Types":
                query = query.filter_by(payment_type=ptype)

            records = query.order_by(StaffSalaryPayment.date.desc(), StaffSalaryPayment.id.desc()).all()

            # KPI calculations for this month
            today = datetime.date.today()
            first_day = today.replace(day=1)
            month_records = session.query(StaffSalaryPayment).filter(
                StaffSalaryPayment.date >= first_day, StaffSalaryPayment.date <= today
            ).all()

            sal_paid_month = sum(r.net_paid for r in month_records if r.payment_type == 'Salary')
            adv_given_month = sum(r.net_paid for r in month_records if r.payment_type == 'Advance')
            tot_payout_month = sum(r.net_paid for r in month_records)

            self.card_sal_paid_month.lbl_val.setText(f"₹{sal_paid_month:,.2f}")
            self.card_adv_given_month.lbl_val.setText(f"₹{adv_given_month:,.2f}")
            self.card_tot_payout_month.lbl_val.setText(f"₹{tot_payout_month:,.2f}")

            # Populate Table
            self.sal_table.setRowCount(len(records))
            for i, p in enumerate(records):
                self.sal_table.setItem(i, 0, QTableWidgetItem(p.payment_number))
                self.sal_table.setItem(i, 1, QTableWidgetItem(p.date.strftime("%Y-%m-%d") if p.date else "-"))

                s_name = p.staff.name if p.staff else "Unknown Staff"
                self.sal_table.setItem(i, 2, QTableWidgetItem(s_name))
                self.sal_table.setItem(i, 3, QTableWidgetItem(p.payment_type))
                self.sal_table.setItem(i, 4, QTableWidgetItem(p.for_month or "-"))

                gross_item = QTableWidgetItem(f"{p.amount:,.2f}")
                gross_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.sal_table.setItem(i, 5, gross_item)

                ded_item = QTableWidgetItem(f"{p.deductions:,.2f}")
                ded_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.sal_table.setItem(i, 6, ded_item)

                net_item = QTableWidgetItem(f"{p.net_paid:,.2f}")
                net_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.sal_table.setItem(i, 7, net_item)

                self.sal_table.setItem(i, 8, QTableWidgetItem(p.payment_mode))

                b_name = p.bank_account.bank_name if p.bank_account else "-"
                self.sal_table.setItem(i, 9, QTableWidgetItem(b_name))

                # Actions
                btn_widget = QWidget()
                btn_layout = QHBoxLayout(btn_widget)
                btn_layout.setContentsMargins(4, 2, 4, 2)
                btn_layout.setSpacing(4)

                btn_slip = QPushButton("Slip")
                btn_slip.setProperty("class", "btn-action-view")
                btn_slip.setFixedHeight(26)
                btn_slip.clicked.connect(lambda _, pid=p.id: self.print_pay_slip(pid))

                btn_del = QPushButton("Delete")
                btn_del.setProperty("class", "btn-action-delete")
                btn_del.setFixedHeight(26)
                btn_del.clicked.connect(lambda _, pid=p.id: self.delete_salary_record(pid))

                btn_layout.addWidget(btn_slip)
                btn_layout.addWidget(btn_del)
                self.sal_table.setCellWidget(i, 10, btn_widget)

        finally:
            session.close()

    def print_pay_slip(self, payment_id):
        session = Session()
        try:
            p = session.query(StaffSalaryPayment).get(payment_id)
            if not p:
                return

            shop_setting = session.query(Setting).filter_by(key='shop_name').first()
            shop_name = shop_setting.value if shop_setting else "SUN COMPUTERS"

            st_name = p.staff.name if p.staff else "Employee"
            st_code = p.staff.staff_code if p.staff else "-"
            st_desig = p.staff.designation if p.staff else "-"

            file_path, _ = QFileDialog.getSaveFileName(
                self, "Save Pay Slip PDF", f"PaySlip_{p.payment_number}.pdf", "PDF Files (*.pdf)"
            )
            if not file_path:
                return

            from reportlab.lib.pagesizes import letter
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib import colors
            from utils.pdf_generator import FONT_REGULAR, FONT_BOLD

            doc = SimpleDocTemplate(file_path, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=30, bottomMargin=30)
            elements = []
            styles = getSampleStyleSheet()

            # Shop Title
            title_style = ParagraphStyle('ShopTitle', parent=styles['Heading1'], fontName=FONT_BOLD, fontSize=18, leading=22, alignment=1, textColor=colors.HexColor("#0f172a"))
            elements.append(Paragraph(shop_name, title_style))

            sub_style = ParagraphStyle('SubTitle', parent=styles['Normal'], fontName=FONT_REGULAR, fontSize=11, leading=14, alignment=1, textColor=colors.HexColor("#64748b"))
            elements.append(Paragraph(f"STAFF SALARY / PAYOUT VOUCHER", sub_style))
            elements.append(Spacer(1, 15))

            # Info block
            info_data = [
                ["Voucher Number:", p.payment_number, "Payment Date:", p.date.strftime("%d-%b-%Y") if p.date else "-"],
                ["Staff Name:", st_name, "Staff Code:", st_code],
                ["Designation:", st_desig, "For Month:", p.for_month or "-"],
                ["Payment Type:", p.payment_type, "Payment Mode:", p.payment_mode]
            ]
            t_info = Table(info_data, colWidths=[110, 160, 100, 160])
            t_info.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), FONT_REGULAR),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('FONTNAME', (0, 0), (0, -1), FONT_BOLD),
                ('FONTNAME', (2, 0), (2, -1), FONT_BOLD),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ]))
            elements.append(t_info)
            elements.append(Spacer(1, 20))

            # Financial breakdown table
            fin_data = [
                ["Description", "Amount (INR)"],
                [f"Gross Amount ({p.payment_type})", f"{p.amount:,.2f}"],
                ["Less: Deductions / Advance Adjustments", f"{p.deductions:,.2f}"],
                ["NET PAYABLE / DISBURSED", f"{p.net_paid:,.2f}"]
            ]
            t_fin = Table(fin_data, colWidths=[350, 180])
            t_fin.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1e293b")),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('FONTNAME', (0, 0), (-1, 0), FONT_BOLD),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor("#f1f5f9")),
                ('FONTNAME', (0, -1), (-1, -1), FONT_BOLD),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
            ]))
            elements.append(t_fin)
            elements.append(Spacer(1, 40))

            # Signature block
            sig_data = [
                ["______________________", "______________________"],
                ["Employer / Authorized Signature", "Employee Signature"]
            ]
            t_sig = Table(sig_data, colWidths=[265, 265])
            t_sig.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 1), (-1, 1), FONT_BOLD),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
            ]))
            elements.append(t_sig)

            doc.build(elements)
            QMessageBox.information(self, "Success", f"Pay Slip generated:\n{file_path}")
            try:
                os.startfile(file_path)
            except Exception:
                pass
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate pay slip: {e}")
        finally:
            session.close()

