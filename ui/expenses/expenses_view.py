import os
import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QFrame, QFormLayout, QDialog, QTextEdit, QDoubleSpinBox, QDateEdit,
    QTabWidget, QSpacerItem, QSizePolicy, QFileDialog, QDialogButtonBox,
    QGridLayout
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QColor, QFont

from database import (
    Session, Setting, BankAccount, CashTransaction, BankTransaction,
    ExpenseCategory, Expense, generate_next_expense_voucher
)
from utils.translator import tr


class ExpenseDialog(QDialog):
    """Dialog to Add or Edit an Expense."""
    def __init__(self, parent=None, expense_id=None):
        super().__init__(parent)
        self.expense_id = expense_id
        self.setWindowTitle("Record Expense" if not expense_id else "Edit Expense")
        self.setMinimumWidth(480)
        self.setModal(True)
        self.init_ui()
        self.load_data()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel("Record New Expense" if not self.expense_id else "Edit Expense Record")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #0f172a;")
        layout.addWidget(title)

        form_layout = QFormLayout()
        form_layout.setSpacing(12)

        # Voucher #
        self.voucher_input = QLineEdit()
        self.voucher_input.setReadOnly(True)
        self.voucher_input.setStyleSheet("background-color: #f1f5f9; color: #475569; font-weight: bold;")
        form_layout.addRow("Voucher #:", self.voucher_input)

        # Date
        self.date_input = QDateEdit()
        self.date_input.setCalendarPopup(True)
        self.date_input.setDate(QDate.currentDate())
        form_layout.addRow("Date *:", self.date_input)

        # Category with quick "+ New" button
        cat_layout = QHBoxLayout()
        self.category_combo = QComboBox()
        self.add_cat_btn = QPushButton("+ New")
        self.add_cat_btn.setFixedWidth(65)
        self.add_cat_btn.setProperty("class", "btn-secondary")
        self.add_cat_btn.clicked.connect(self.quick_add_category)
        cat_layout.addWidget(self.category_combo, 1)
        cat_layout.addWidget(self.add_cat_btn)
        form_layout.addRow("Category *:", cat_layout)

        # Amount
        self.amount_input = QDoubleSpinBox()
        self.amount_input.setRange(0.01, 9999999.00)
        self.amount_input.setDecimals(2)
        self.amount_input.setPrefix("₹ ")
        self.amount_input.setStyleSheet("font-size: 14px; font-weight: bold; color: #0f172a;")
        form_layout.addRow("Amount (₹) *:", self.amount_input)

        # Payment Mode
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Cash Drawer", "Bank Account"])
        self.mode_combo.currentIndexChanged.connect(self.on_mode_changed)
        form_layout.addRow("Paid Via *:", self.mode_combo)

        # Bank Account
        self.bank_combo = QComboBox()
        self.bank_combo.setEnabled(False)
        form_layout.addRow("Bank Account:", self.bank_combo)

        # Paid To / Payee
        self.payee_input = QLineEdit()
        self.payee_input.setPlaceholderText("e.g. EB Office, Landlord, Sathya Stores")
        form_layout.addRow("Paid To (Payee):", self.payee_input)

        # Reference / Bill #
        self.ref_input = QLineEdit()
        self.ref_input.setPlaceholderText("e.g. Bill #, Receipt #, Txn Ref")
        form_layout.addRow("Ref / Bill #:", self.ref_input)

        # Description
        self.desc_input = QTextEdit()
        self.desc_input.setPlaceholderText("Remarks or additional notes...")
        self.desc_input.setMaximumHeight(70)
        form_layout.addRow("Description:", self.desc_input)

        layout.addLayout(form_layout)

        # Buttons
        btn_box = QDialogButtonBox()
        self.save_btn = QPushButton(tr("Save Expense"))
        self.save_btn.setProperty("class", "btn-success")
        self.cancel_btn = QPushButton(tr("Cancel"))
        self.cancel_btn.setProperty("class", "btn-secondary")
        btn_box.addButton(self.save_btn, QDialogButtonBox.AcceptRole)
        btn_box.addButton(self.cancel_btn, QDialogButtonBox.RejectRole)
        self.save_btn.clicked.connect(self.save_expense)
        self.cancel_btn.clicked.connect(self.reject)
        layout.addWidget(btn_box)

    def on_mode_changed(self, idx):
        is_bank = (idx == 1)
        self.bank_combo.setEnabled(is_bank)
        if not is_bank:
            self.bank_combo.setCurrentIndex(-1)
        elif self.bank_combo.count() > 0 and self.bank_combo.currentIndex() == -1:
            self.bank_combo.setCurrentIndex(0)

    def quick_add_category(self):
        from PySide6.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(self, "New Category", "Enter Expense Category Name:")
        if ok and name.strip():
            session = Session()
            try:
                exist = session.query(ExpenseCategory).filter(ExpenseCategory.name.ilike(name.strip())).first()
                if exist:
                    QMessageBox.warning(self, "Exists", "Category already exists.")
                    return
                cat = ExpenseCategory(name=name.strip())
                session.add(cat)
                session.commit()
                self.load_categories(select_id=cat.id)
            except Exception as e:
                session.rollback()
                QMessageBox.critical(self, "Error", f"Failed to add category: {e}")
            finally:
                session.close()

    def load_categories(self, select_id=None):
        self.category_combo.clear()
        session = Session()
        try:
            cats = session.query(ExpenseCategory).filter_by(is_active=True).order_by(ExpenseCategory.name).all()
            sel_idx = 0
            for idx, c in enumerate(cats):
                self.category_combo.addItem(c.name, c.id)
                if select_id and c.id == select_id:
                    sel_idx = idx
            if self.category_combo.count() > 0:
                self.category_combo.setCurrentIndex(sel_idx)
        finally:
            session.close()

    def load_banks(self, select_id=None):
        self.bank_combo.clear()
        session = Session()
        try:
            banks = session.query(BankAccount).order_by(BankAccount.bank_name).all()
            sel_idx = 0
            for idx, b in enumerate(banks):
                self.bank_combo.addItem(f"{b.bank_name} ({b.account_number})", b.id)
                if select_id and b.id == select_id:
                    sel_idx = idx
            if self.bank_combo.count() > 0:
                self.bank_combo.setCurrentIndex(sel_idx)
        finally:
            session.close()

    def load_data(self):
        self.load_categories()
        self.load_banks()
        session = Session()
        try:
            if not self.expense_id:
                # Generate new voucher
                v_num = generate_next_expense_voucher(session)
                self.voucher_input.setText(v_num)
            else:
                exp = session.query(Expense).get(self.expense_id)
                if exp:
                    self.voucher_input.setText(exp.voucher_number)
                    if exp.date:
                        self.date_input.setDate(QDate(exp.date.year, exp.date.month, exp.date.day))
                    # Category
                    cat_idx = self.category_combo.findData(exp.category_id)
                    if cat_idx >= 0:
                        self.category_combo.setCurrentIndex(cat_idx)
                    self.amount_input.setValue(exp.amount)
                    # Mode
                    if exp.payment_mode == 'Bank':
                        self.mode_combo.setCurrentIndex(1)
                        b_idx = self.bank_combo.findData(exp.bank_id)
                        if b_idx >= 0:
                            self.bank_combo.setCurrentIndex(b_idx)
                    else:
                        self.mode_combo.setCurrentIndex(0)
                    self.payee_input.setText(exp.payee or "")
                    self.ref_input.setText(exp.reference_no or "")
                    self.desc_input.setPlainText(exp.description or "")
        finally:
            session.close()

    def save_expense(self):
        cat_id = self.category_combo.currentData()
        if not cat_id:
            QMessageBox.warning(self, "Validation", "Please select an expense category.")
            return

        amount = self.amount_input.value()
        if amount <= 0:
            QMessageBox.warning(self, "Validation", "Amount must be greater than zero.")
            return

        is_bank = (self.mode_combo.currentIndex() == 1)
        bank_id = self.bank_combo.currentData() if is_bank else None
        if is_bank and not bank_id:
            QMessageBox.warning(self, "Validation", "Please select a bank account.")
            return

        qdate = self.date_input.date()
        exp_date = datetime.date(qdate.year(), qdate.month(), qdate.day())
        payee = self.payee_input.text().strip()
        ref_no = self.ref_input.text().strip()
        desc = self.desc_input.toPlainText().strip()
        cat_name = self.category_combo.currentText()

        session = Session()
        try:
            if not self.expense_id:
                # Create Expense
                v_num = self.voucher_input.text().strip() or generate_next_expense_voucher(session)
                exp = Expense(
                    voucher_number=v_num,
                    date=exp_date,
                    category_id=cat_id,
                    amount=amount,
                    payment_mode='Bank' if is_bank else 'Cash',
                    bank_id=bank_id,
                    payee=payee,
                    reference_no=ref_no,
                    description=desc
                )
                session.add(exp)
                session.flush()

                # Record Cash / Bank Transaction
                txn_desc = f"Expense [{cat_name}] {f'- {payee}' if payee else ''} (Voucher: {v_num})"
                if is_bank:
                    session.add(BankTransaction(
                        date=exp_date,
                        transaction_type='withdrawal',
                        account_id=bank_id,
                        amount=amount,
                        source_type='expense',
                        source_id=exp.id,
                        description=txn_desc
                    ))
                else:
                    session.add(CashTransaction(
                        date=exp_date,
                        transaction_type='out',
                        amount=amount,
                        source_type='expense',
                        source_id=exp.id,
                        description=txn_desc
                    ))
            else:
                # Update Expense
                exp = session.query(Expense).get(self.expense_id)
                if not exp:
                    return
                exp.date = exp_date
                exp.category_id = cat_id
                exp.amount = amount
                exp.payment_mode = 'Bank' if is_bank else 'Cash'
                exp.bank_id = bank_id
                exp.payee = payee
                exp.reference_no = ref_no
                exp.description = desc

                # Recreate transaction
                session.query(CashTransaction).filter_by(source_type='expense', source_id=exp.id).delete()
                session.query(BankTransaction).filter_by(source_type='expense', source_id=exp.id).delete()

                txn_desc = f"Expense [{cat_name}] {f'- {payee}' if payee else ''} (Voucher: {exp.voucher_number})"
                if is_bank:
                    session.add(BankTransaction(
                        date=exp_date,
                        transaction_type='withdrawal',
                        account_id=bank_id,
                        amount=amount,
                        source_type='expense',
                        source_id=exp.id,
                        description=txn_desc
                    ))
                else:
                    session.add(CashTransaction(
                        date=exp_date,
                        transaction_type='out',
                        amount=amount,
                        source_type='expense',
                        source_id=exp.id,
                        description=txn_desc
                    ))

            session.commit()
            self.accept()
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", f"Failed to save expense: {e}")
        finally:
            session.close()


class ExpensesView(QWidget):
    """Expenses Management View."""
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

        # 1. Register Tab
        self.register_tab = QWidget()
        self.setup_register_tab()
        self.tabs.addTab(self.register_tab, f"📝 {tr('Daily Expenses')}")

        # 2. Categories Tab
        self.categories_tab = QWidget()
        self.setup_categories_tab()
        self.tabs.addTab(self.categories_tab, f"🏷️ {tr('Expense Categories')}")

        # 3. Analytics Tab
        self.analytics_tab = QWidget()
        self.setup_analytics_tab()
        self.tabs.addTab(self.analytics_tab, f"📊 {tr('Expense Analytics')}")

        main_layout.addWidget(self.tabs)

    # -------------------------------------------------------------
    # TAB 1: DAILY EXPENSES & REGISTER
    # -------------------------------------------------------------
    def setup_register_tab(self):
        layout = QVBoxLayout(self.register_tab)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # KPI Summary Cards (Dashboard style)
        kpi_layout = QHBoxLayout()
        kpi_layout.setSpacing(15)

        self.card_today = self._create_kpi_card("TODAY'S EXPENSES", "₹0.00", "#ef4444")
        self.card_month = self._create_kpi_card("THIS MONTH'S EXPENSES", "₹0.00", "#f59e0b")
        self.card_cash = self._create_kpi_card("CASH EXPENSES (THIS MONTH)", "₹0.00", "#10b981")
        self.card_bank = self._create_kpi_card("BANK EXPENSES (THIS MONTH)", "₹0.00", "#6366f1")

        kpi_layout.addWidget(self.card_today)
        kpi_layout.addWidget(self.card_month)
        kpi_layout.addWidget(self.card_cash)
        kpi_layout.addWidget(self.card_bank)
        layout.addLayout(kpi_layout)

        # Filter & Action Toolbar
        filter_frame = QFrame()
        filter_frame.setProperty("class", "CardFrame")
        filter_layout = QHBoxLayout(filter_frame)
        filter_layout.setContentsMargins(12, 10, 12, 10)
        filter_layout.setSpacing(10)

        # Date Filter
        filter_layout.addWidget(QLabel("Date Range:"))
        self.filter_date_range = QComboBox()
        self.filter_date_range.addItems([
            "All Time", "Today", "Yesterday", "This Week", "This Month", "Last Month", "This Year", "Custom Range"
        ])
        self.filter_date_range.setCurrentText("This Month")
        self.filter_date_range.currentIndexChanged.connect(self.on_date_filter_changed)
        filter_layout.addWidget(self.filter_date_range)

        # Custom dates
        self.custom_dates_widget = QWidget()
        custom_layout = QHBoxLayout(self.custom_dates_widget)
        custom_layout.setContentsMargins(0, 0, 0, 0)
        custom_layout.setSpacing(6)
        self.filter_start_date = QDateEdit()
        self.filter_start_date.setCalendarPopup(True)
        self.filter_start_date.setDate(QDate.currentDate().addDays(-30))
        self.filter_end_date = QDateEdit()
        self.filter_end_date.setCalendarPopup(True)
        self.filter_end_date.setDate(QDate.currentDate())
        custom_layout.addWidget(QLabel("From:"))
        custom_layout.addWidget(self.filter_start_date)
        custom_layout.addWidget(QLabel("To:"))
        custom_layout.addWidget(self.filter_end_date)
        self.custom_dates_widget.setVisible(False)
        filter_layout.addWidget(self.custom_dates_widget)

        # Category Filter
        filter_layout.addWidget(QLabel("Category:"))
        self.filter_category = QComboBox()
        self.filter_category.addItem("All Categories", None)
        self.filter_category.currentIndexChanged.connect(self.apply_filters)
        filter_layout.addWidget(self.filter_category)

        # Mode Filter
        filter_layout.addWidget(QLabel("Mode:"))
        self.filter_mode = QComboBox()
        self.filter_mode.addItems(["All Modes", "Cash", "Bank"])
        self.filter_mode.currentIndexChanged.connect(self.apply_filters)
        filter_layout.addWidget(self.filter_mode)

        # Search Bar
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search Payee, Voucher #, Notes...")
        self.search_input.textChanged.connect(self.apply_filters)
        filter_layout.addWidget(self.search_input)

        filter_layout.addStretch()

        # Action Buttons
        self.btn_new_expense = QPushButton(f"➕ {tr('Record Expense')}")
        self.btn_new_expense.setProperty("class", "btn-primary")
        self.btn_new_expense.setFixedHeight(34)
        self.btn_new_expense.clicked.connect(self.open_new_expense_dialog)
        filter_layout.addWidget(self.btn_new_expense)

        self.btn_export_pdf = QPushButton("PDF Report")
        self.btn_export_pdf.setProperty("class", "btn-action-view")
        self.btn_export_pdf.setFixedHeight(34)
        self.btn_export_pdf.clicked.connect(self.export_pdf)
        filter_layout.addWidget(self.btn_export_pdf)

        self.btn_export_excel = QPushButton("Excel Export")
        self.btn_export_excel.setProperty("class", "btn-action-view")
        self.btn_export_excel.setFixedHeight(34)
        self.btn_export_excel.clicked.connect(self.export_excel)
        filter_layout.addWidget(self.btn_export_excel)

        layout.addWidget(filter_frame)

        # Expense Log Table
        self.table = QTableWidget()
        self.table.setColumnCount(10)
        self.table.setHorizontalHeaderLabels([
            "Voucher #", "Date", "Category", "Paid To", "Mode",
            "Bank", "Amount (₹)", "Ref / Bill #", "Description", "Action"
        ])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.setSectionResizeMode(8, QHeaderView.Stretch)  # Description stretches
        self.table.setColumnWidth(0, 85)   # Voucher
        self.table.setColumnWidth(1, 85)   # Date
        self.table.setColumnWidth(2, 120)  # Category
        self.table.setColumnWidth(3, 110)  # Paid To
        self.table.setColumnWidth(4, 60)   # Mode
        self.table.setColumnWidth(5, 110)  # Bank
        self.table.setColumnWidth(6, 85)   # Amount
        self.table.setColumnWidth(7, 85)   # Ref
        header.setSectionResizeMode(9, QHeaderView.Fixed)
        self.table.setColumnWidth(9, 120)  # Action buttons
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(48)
        layout.addWidget(self.table)

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

    def on_date_filter_changed(self):
        is_custom = (self.filter_date_range.currentText() == "Custom Range")
        self.custom_dates_widget.setVisible(is_custom)
        self.apply_filters()

    def open_new_expense_dialog(self):
        dlg = ExpenseDialog(self)
        if dlg.exec() == QDialog.Accepted:
            self.load_data()

    def open_edit_expense_dialog(self, expense_id):
        dlg = ExpenseDialog(self, expense_id=expense_id)
        if dlg.exec() == QDialog.Accepted:
            self.load_data()

    def delete_expense(self, expense_id):
        confirm = QMessageBox.question(
            self, "Confirm Delete",
            "Are you sure you want to delete this expense record?\nAssociated Cash/Bank ledger entries will also be reversed.",
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm == QMessageBox.Yes:
            session = Session()
            try:
                # Reverse Cash & Bank transactions
                session.query(CashTransaction).filter_by(source_type='expense', source_id=expense_id).delete()
                session.query(BankTransaction).filter_by(source_type='expense', source_id=expense_id).delete()
                # Delete Expense
                session.query(Expense).filter_by(id=expense_id).delete()
                session.commit()
                self.load_data()
            except Exception as e:
                session.rollback()
                QMessageBox.critical(self, "Error", f"Failed to delete expense: {e}")
            finally:
                session.close()

    # -------------------------------------------------------------
    # TAB 2: EXPENSE CATEGORIES MASTER
    # -------------------------------------------------------------
    def setup_categories_tab(self):
        layout = QHBoxLayout(self.categories_tab)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(20)

        # Left Card: Add/Edit Category Form
        form_frame = QFrame()
        form_frame.setProperty("class", "CardFrame")
        form_frame.setFixedWidth(360)
        f_layout = QVBoxLayout(form_frame)
        f_layout.setContentsMargins(15, 15, 15, 15)
        f_layout.setSpacing(12)

        self.cat_form_title = QLabel("Add Expense Category")
        self.cat_form_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #0f172a;")
        f_layout.addWidget(self.cat_form_title)

        c_form = QFormLayout()
        c_form.setSpacing(10)

        self.cat_name_input = QLineEdit()
        self.cat_name_input.setPlaceholderText("e.g. Office Supplies, Generator Fuel")
        c_form.addRow("Category Name *:", self.cat_name_input)

        self.cat_desc_input = QTextEdit()
        self.cat_desc_input.setPlaceholderText("Brief description of this expense head...")
        self.cat_desc_input.setMaximumHeight(80)
        c_form.addRow("Description:", self.cat_desc_input)

        f_layout.addLayout(c_form)

        btn_layout = QHBoxLayout()
        self.btn_save_cat = QPushButton("Save Category")
        self.btn_save_cat.setProperty("class", "btn-success")
        self.btn_save_cat.setFixedHeight(36)
        self.btn_save_cat.clicked.connect(self.save_category)
        btn_layout.addWidget(self.btn_save_cat)

        self.btn_clear_cat = QPushButton("Clear")
        self.btn_clear_cat.setProperty("class", "btn-secondary")
        self.btn_clear_cat.setFixedHeight(36)
        self.btn_clear_cat.clicked.connect(self.clear_category_form)
        btn_layout.addWidget(self.btn_clear_cat)

        f_layout.addLayout(btn_layout)
        f_layout.addStretch()

        self.editing_cat_id = None
        layout.addWidget(form_frame)

        # Right Card: Table
        table_frame = QFrame()
        table_frame.setProperty("class", "CardFrame")
        t_layout = QVBoxLayout(table_frame)
        t_layout.setContentsMargins(15, 15, 15, 15)

        t_title = QLabel("Expense Categories Master")
        t_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #0f172a; margin-bottom: 8px;")
        t_layout.addWidget(t_title)

        self.cat_table = QTableWidget()
        self.cat_table.setColumnCount(6)
        self.cat_table.setHorizontalHeaderLabels([
            "ID", "Category Name", "Description", "Expenses Count", "Total Spent (₹)", "Action"
        ])
        c_hdr = self.cat_table.horizontalHeader()
        c_hdr.setSectionResizeMode(QHeaderView.Interactive)
        c_hdr.setSectionResizeMode(1, QHeaderView.Stretch)
        self.cat_table.setColumnWidth(0, 50)
        self.cat_table.setColumnWidth(2, 180)
        self.cat_table.setColumnWidth(3, 110)
        self.cat_table.setColumnWidth(4, 110)
        c_hdr.setSectionResizeMode(5, QHeaderView.Fixed)
        self.cat_table.setColumnWidth(5, 120)
        self.cat_table.verticalHeader().setVisible(False)
        self.cat_table.verticalHeader().setDefaultSectionSize(44)
        t_layout.addWidget(self.cat_table)

        layout.addWidget(table_frame, 1)

    def save_category(self):
        name = self.cat_name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Validation", "Category name is required.")
            return

        desc = self.cat_desc_input.toPlainText().strip()
        session = Session()
        try:
            if not self.editing_cat_id:
                # Check uniqueness
                exist = session.query(ExpenseCategory).filter(ExpenseCategory.name.ilike(name)).first()
                if exist:
                    QMessageBox.warning(self, "Exists", "Category with this name already exists.")
                    return
                cat = ExpenseCategory(name=name, description=desc)
                session.add(cat)
            else:
                cat = session.query(ExpenseCategory).get(self.editing_cat_id)
                if cat:
                    cat.name = name
                    cat.description = desc
            session.commit()
            self.clear_category_form()
            self.load_categories()
            self.populate_category_filter()
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", f"Failed to save category: {e}")
        finally:
            session.close()

    def edit_category(self, cat_id):
        session = Session()
        try:
            cat = session.query(ExpenseCategory).get(cat_id)
            if cat:
                self.editing_cat_id = cat.id
                self.cat_name_input.setText(cat.name)
                self.cat_desc_input.setPlainText(cat.description or "")
                self.cat_form_title.setText(f"Edit Category (#{cat.id})")
                self.btn_save_cat.setText("Update Category")
        finally:
            session.close()

    def delete_category(self, cat_id):
        session = Session()
        try:
            count = session.query(Expense).filter_by(category_id=cat_id).count()
            if count > 0:
                QMessageBox.warning(
                    self, "Cannot Delete",
                    f"This category cannot be deleted because it is used in {count} expense records."
                )
                return

            confirm = QMessageBox.question(
                self, "Confirm Delete", "Are you sure you want to delete this expense category?",
                QMessageBox.Yes | QMessageBox.No
            )
            if confirm == QMessageBox.Yes:
                session.query(ExpenseCategory).filter_by(id=cat_id).delete()
                session.commit()
                self.load_categories()
                self.populate_category_filter()
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", f"Failed to delete category: {e}")
        finally:
            session.close()

    def clear_category_form(self):
        self.editing_cat_id = None
        self.cat_name_input.clear()
        self.cat_desc_input.clear()
        self.cat_form_title.setText("Add Expense Category")
        self.btn_save_cat.setText("Save Category")

    # -------------------------------------------------------------
    # TAB 3: EXPENSE ANALYTICS & MONTHLY BREAKDOWN
    # -------------------------------------------------------------
    def setup_analytics_tab(self):
        layout = QVBoxLayout(self.analytics_tab)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(14)

        # Top Control: Month & Year Picker
        ctrl_frame = QFrame()
        ctrl_frame.setProperty("class", "CardFrame")
        c_layout = QHBoxLayout(ctrl_frame)
        c_layout.setContentsMargins(12, 10, 12, 10)
        c_layout.setSpacing(10)

        c_layout.addWidget(QLabel("Select Month & Year:"))
        today = datetime.date.today()
        self.analytics_month = QComboBox()
        months = ["January", "February", "March", "April", "May", "June",
                  "July", "August", "September", "October", "November", "December"]
        for i, m in enumerate(months, 1):
            self.analytics_month.addItem(m, i)
        self.analytics_month.setCurrentIndex(today.month - 1)
        self.analytics_month.currentIndexChanged.connect(self.load_analytics)
        c_layout.addWidget(self.analytics_month)

        self.analytics_year = QComboBox()
        for yr in range(today.year - 3, today.year + 2):
            self.analytics_year.addItem(str(yr), yr)
        self.analytics_year.setCurrentText(str(today.year))
        self.analytics_year.currentIndexChanged.connect(self.load_analytics)
        c_layout.addWidget(self.analytics_year)

        c_layout.addStretch()
        layout.addWidget(ctrl_frame)

        # Monthly KPI cards
        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(15)
        self.card_an_total = self._create_kpi_card("TOTAL EXPENSES", "₹0.00", "#ef4444")
        self.card_an_daily_avg = self._create_kpi_card("AVG DAILY EXPENSE", "₹0.00", "#f59e0b")
        self.card_an_top_cat = self._create_kpi_card("TOP EXPENSE CATEGORY", "N/A", "#6366f1")
        self.card_an_txns = self._create_kpi_card("TOTAL TRANSACTIONS", "0", "#10b981")

        kpi_row.addWidget(self.card_an_total)
        kpi_row.addWidget(self.card_an_daily_avg)
        kpi_row.addWidget(self.card_an_top_cat)
        kpi_row.addWidget(self.card_an_txns)
        layout.addLayout(kpi_row)

        # Analytics Table
        table_frame = QFrame()
        table_frame.setProperty("class", "CardFrame")
        tb_layout = QVBoxLayout(table_frame)
        tb_layout.setContentsMargins(15, 15, 15, 15)

        tb_title = QLabel("Category-wise Monthly Expense Distribution")
        tb_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #0f172a; margin-bottom: 6px;")
        tb_layout.addWidget(tb_title)

        self.analytics_table = QTableWidget()
        self.analytics_table.setColumnCount(4)
        self.analytics_table.setHorizontalHeaderLabels([
            "Expense Category", "Transactions Count", "Total Spent (₹)", "% Share"
        ])
        an_hdr = self.analytics_table.horizontalHeader()
        an_hdr.setSectionResizeMode(QHeaderView.Stretch)
        an_hdr.setSectionResizeMode(0, QHeaderView.Stretch)
        self.analytics_table.verticalHeader().setVisible(False)
        self.analytics_table.verticalHeader().setDefaultSectionSize(44)
        tb_layout.addWidget(self.analytics_table)

        layout.addWidget(table_frame, 1)

    # -------------------------------------------------------------
    # DATA LOADING & FILTERING
    # -------------------------------------------------------------
    def populate_category_filter(self):
        cur_data = self.filter_category.currentData()
        self.filter_category.blockSignals(True)
        self.filter_category.clear()
        self.filter_category.addItem("All Categories", None)
        session = Session()
        try:
            cats = session.query(ExpenseCategory).filter_by(is_active=True).order_by(ExpenseCategory.name).all()
            for c in cats:
                self.filter_category.addItem(c.name, c.id)
            if cur_data:
                idx = self.filter_category.findData(cur_data)
                if idx >= 0:
                    self.filter_category.setCurrentIndex(idx)
        finally:
            session.close()
        self.filter_category.blockSignals(False)

    def load_data(self):
        self.populate_category_filter()
        self.apply_filters()
        self.load_categories()
        self.load_analytics()

    def refresh_data(self):
        self.load_data()

    def apply_filters(self):
        session = Session()
        try:
            query = session.query(Expense)

            # Date Range Filter
            today = datetime.date.today()
            date_mode = self.filter_date_range.currentText()
            if date_mode == "Today":
                query = query.filter(Expense.date == today)
            elif date_mode == "Yesterday":
                yesterday = today - datetime.timedelta(days=1)
                query = query.filter(Expense.date == yesterday)
            elif date_mode == "This Week":
                start_week = today - datetime.timedelta(days=today.weekday())
                query = query.filter(Expense.date >= start_week, Expense.date <= today)
            elif date_mode == "This Month":
                start_month = today.replace(day=1)
                query = query.filter(Expense.date >= start_month, Expense.date <= today)
            elif date_mode == "Last Month":
                first_this = today.replace(day=1)
                last_prev = first_this - datetime.timedelta(days=1)
                first_prev = last_prev.replace(day=1)
                query = query.filter(Expense.date >= first_prev, Expense.date <= last_prev)
            elif date_mode == "This Year":
                start_year = today.replace(month=1, day=1)
                query = query.filter(Expense.date >= start_year, Expense.date <= today)
            elif date_mode == "Custom Range":
                q_start = self.filter_start_date.date()
                q_end = self.filter_end_date.date()
                s_date = datetime.date(q_start.year(), q_start.month(), q_start.day())
                e_date = datetime.date(q_end.year(), q_end.month(), q_end.day())
                query = query.filter(Expense.date >= s_date, Expense.date <= e_date)

            # Category filter
            cat_id = self.filter_category.currentData()
            if cat_id:
                query = query.filter(Expense.category_id == cat_id)

            # Mode filter
            mode = self.filter_mode.currentText()
            if mode != "All Modes":
                query = query.filter(Expense.payment_mode == mode)

            # Search text
            search = self.search_input.text().strip().lower()
            if search:
                query = query.filter(
                    (Expense.voucher_number.ilike(f"%{search}%")) |
                    (Expense.payee.ilike(f"%{search}%")) |
                    (Expense.reference_no.ilike(f"%{search}%")) |
                    (Expense.description.ilike(f"%{search}%"))
                )

            query = query.order_by(Expense.date.desc(), Expense.id.desc())
            self.current_expenses = query.all()

            # Populate Table
            self.table.setRowCount(len(self.current_expenses))
            for i, exp in enumerate(self.current_expenses):
                self.table.setItem(i, 0, QTableWidgetItem(exp.voucher_number))
                self.table.setItem(i, 1, QTableWidgetItem(exp.date.strftime("%Y-%m-%d") if exp.date else "-"))
                cat_name = exp.category.name if exp.category else "-"
                self.table.setItem(i, 2, QTableWidgetItem(cat_name))
                self.table.setItem(i, 3, QTableWidgetItem(exp.payee or "-"))
                self.table.setItem(i, 4, QTableWidgetItem(exp.payment_mode))

                bank_name = exp.bank_account.bank_name if exp.bank_account else "-"
                self.table.setItem(i, 5, QTableWidgetItem(bank_name))

                amt_item = QTableWidgetItem(f"{exp.amount:.2f}")
                amt_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.table.setItem(i, 6, amt_item)

                self.table.setItem(i, 7, QTableWidgetItem(exp.reference_no or "-"))
                self.table.setItem(i, 8, QTableWidgetItem(exp.description or "-"))

                # Actions
                btn_widget = QWidget()
                btn_layout = QHBoxLayout(btn_widget)
                btn_layout.setContentsMargins(4, 2, 4, 2)
                btn_layout.setSpacing(6)

                btn_edit = QPushButton("Edit")
                btn_edit.setProperty("class", "btn-action-view")
                btn_edit.setFixedHeight(26)
                btn_edit.clicked.connect(lambda _, eid=exp.id: self.open_edit_expense_dialog(eid))

                btn_del = QPushButton("Delete")
                btn_del.setProperty("class", "btn-action-delete")
                btn_del.setFixedHeight(26)
                btn_del.clicked.connect(lambda _, eid=exp.id: self.delete_expense(eid))

                btn_layout.addWidget(btn_edit)
                btn_layout.addWidget(btn_del)
                self.table.setCellWidget(i, 9, btn_widget)

            # Update KPI Cards
            # Today's expenses
            today_exp = session.query(Expense).filter(Expense.date == today).all()
            tot_today = sum(e.amount for e in today_exp)
            self.card_today.lbl_val.setText(f"₹{tot_today:,.2f}")

            # This month's expenses
            first_day = today.replace(day=1)
            month_exp = session.query(Expense).filter(Expense.date >= first_day, Expense.date <= today).all()
            tot_month = sum(e.amount for e in month_exp)
            tot_cash = sum(e.amount for e in month_exp if e.payment_mode == 'Cash')
            tot_bank = sum(e.amount for e in month_exp if e.payment_mode == 'Bank')

            self.card_month.lbl_val.setText(f"₹{tot_month:,.2f}")
            self.card_cash.lbl_val.setText(f"₹{tot_cash:,.2f}")
            self.card_bank.lbl_val.setText(f"₹{tot_bank:,.2f}")

        finally:
            session.close()

    def load_categories(self):
        session = Session()
        try:
            cats = session.query(ExpenseCategory).order_by(ExpenseCategory.name).all()
            self.cat_table.setRowCount(len(cats))
            for i, c in enumerate(cats):
                self.cat_table.setItem(i, 0, QTableWidgetItem(str(c.id)))
                self.cat_table.setItem(i, 1, QTableWidgetItem(c.name))
                self.cat_table.setItem(i, 2, QTableWidgetItem(c.description or "-"))

                # Count & Total Spent
                expenses = session.query(Expense).filter_by(category_id=c.id).all()
                count = len(expenses)
                tot_spent = sum(e.amount for e in expenses)

                self.cat_table.setItem(i, 3, QTableWidgetItem(str(count)))
                self.cat_table.setItem(i, 4, QTableWidgetItem(f"₹{tot_spent:,.2f}"))

                # Actions
                btn_widget = QWidget()
                btn_layout = QHBoxLayout(btn_widget)
                btn_layout.setContentsMargins(4, 2, 4, 2)
                btn_layout.setSpacing(6)

                btn_edit = QPushButton("Edit")
                btn_edit.setProperty("class", "btn-action-view")
                btn_edit.setFixedHeight(26)
                btn_edit.clicked.connect(lambda _, cid=c.id: self.edit_category(cid))

                btn_del = QPushButton("Delete")
                btn_del.setProperty("class", "btn-action-delete")
                btn_del.setFixedHeight(26)
                btn_del.clicked.connect(lambda _, cid=c.id: self.delete_category(cid))

                btn_layout.addWidget(btn_edit)
                btn_layout.addWidget(btn_del)
                self.cat_table.setCellWidget(i, 5, btn_widget)
        finally:
            session.close()

    def load_analytics(self):
        m_idx = self.analytics_month.currentData()
        y_val = self.analytics_year.currentData()
        if not m_idx or not y_val:
            return

        session = Session()
        try:
            import calendar
            days_in_month = calendar.monthrange(y_val, m_idx)[1]
            start_date = datetime.date(y_val, m_idx, 1)
            end_date = datetime.date(y_val, m_idx, days_in_month)

            expenses = session.query(Expense).filter(
                Expense.date >= start_date, Expense.date <= end_date
            ).all()

            total_amt = sum(e.amount for e in expenses)
            total_txns = len(expenses)

            self.card_an_total.lbl_val.setText(f"₹{total_amt:,.2f}")
            self.card_an_txns.lbl_val.setText(str(total_txns))

            avg_daily = (total_amt / days_in_month) if days_in_month > 0 else 0.0
            self.card_an_daily_avg.lbl_val.setText(f"₹{avg_daily:,.2f}")

            # Group by category
            cat_totals = {}
            cat_counts = {}
            for e in expenses:
                c_name = e.category.name if e.category else "Uncategorized"
                cat_totals[c_name] = cat_totals.get(c_name, 0.0) + e.amount
                cat_counts[c_name] = cat_counts.get(c_name, 0) + 1

            if cat_totals:
                top_cat = max(cat_totals, key=cat_totals.get)
                self.card_an_top_cat.lbl_val.setText(f"{top_cat} (₹{cat_totals[top_cat]:,.0f})")
            else:
                self.card_an_top_cat.lbl_val.setText("None")

            # Fill table
            sorted_cats = sorted(cat_totals.items(), key=lambda x: x[1], reverse=True)
            self.analytics_table.setRowCount(len(sorted_cats))
            for i, (c_name, c_tot) in enumerate(sorted_cats):
                self.analytics_table.setItem(i, 0, QTableWidgetItem(c_name))
                self.analytics_table.setItem(i, 1, QTableWidgetItem(str(cat_counts.get(c_name, 0))))
                self.analytics_table.setItem(i, 2, QTableWidgetItem(f"₹{c_tot:,.2f}"))
                pct = (c_tot / total_amt * 100.0) if total_amt > 0 else 0.0
                self.analytics_table.setItem(i, 3, QTableWidgetItem(f"{pct:.1f}%"))

        finally:
            session.close()

    # -------------------------------------------------------------
    # EXPORTING
    # -------------------------------------------------------------
    def export_excel(self):
        if not hasattr(self, 'current_expenses') or not self.current_expenses:
            QMessageBox.warning(self, "No Data", "No expense records to export.")
            return

        file_path, _ = QFileDialog.getSaveFileName(self, "Save Expenses Report", "", "Excel Files (*.xlsx)")
        if not file_path:
            return

        try:
            import openpyxl
            from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Expenses"

            # Header info
            session = Session()
            shop_setting = session.query(Setting).filter_by(key='shop_name').first()
            shop_name = shop_setting.value if shop_setting else "SUN COMPUTERS"
            session.close()

            ws.append([shop_name])
            ws.append([f"Expenses Report - Generated on {datetime.date.today().strftime('%d-%m-%Y')}"])
            ws.append([])

            headers = ["Voucher #", "Date", "Category", "Paid To", "Mode", "Bank", "Amount (INR)", "Ref / Bill #", "Description"]
            ws.append(headers)

            for col in range(1, len(headers) + 1):
                cell = ws.cell(row=4, column=col)
                cell.font = Font(bold=True, color="FFFFFF")
                cell.fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
                cell.alignment = Alignment(horizontal="center")

            total_sum = 0.0
            row_idx = 5
            for exp in self.current_expenses:
                cat_name = exp.category.name if exp.category else "-"
                bank_name = exp.bank_account.bank_name if exp.bank_account else "-"
                pdate = exp.date.strftime("%Y-%m-%d") if exp.date else "-"
                ws.append([
                    exp.voucher_number, pdate, cat_name, exp.payee or "-",
                    exp.payment_mode, bank_name, exp.amount, exp.reference_no or "-", exp.description or "-"
                ])
                total_sum += exp.amount
                row_idx += 1

            # Total row
            ws.append(["TOTAL", "", "", "", "", "", total_sum, "", ""])
            tot_row = ws[row_idx]
            for c in tot_row:
                c.font = Font(bold=True)

            wb.save(file_path)
            QMessageBox.information(self, "Export Successful", f"Expenses report saved to:\n{file_path}")
            try:
                os.startfile(file_path)
            except Exception:
                pass
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export to Excel: {e}")

    def export_pdf(self):
        if not hasattr(self, 'current_expenses') or not self.current_expenses:
            QMessageBox.warning(self, "No Data", "No expense records to export.")
            return

        file_path, _ = QFileDialog.getSaveFileName(self, "Save Expenses PDF", "", "PDF Files (*.pdf)")
        if not file_path:
            return

        try:
            from reportlab.lib.pagesizes import letter, landscape
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib import colors

            session = Session()
            shop_setting = session.query(Setting).filter_by(key='shop_name').first()
            shop_name = shop_setting.value if shop_setting else "SUN COMPUTERS"
            session.close()

            doc = SimpleDocTemplate(file_path, pagesize=landscape(letter), rightMargin=20, leftMargin=20, topMargin=20, bottomMargin=20)
            elements = []
            styles = getSampleStyleSheet()

            # Shop Title
            title_style = ParagraphStyle('ShopTitle', parent=styles['Heading1'], fontSize=18, leading=22, alignment=1, textColor=colors.HexColor("#0f172a"))
            elements.append(Paragraph(shop_name, title_style))

            sub_style = ParagraphStyle('SubTitle', parent=styles['Normal'], fontSize=11, leading=14, alignment=1, textColor=colors.HexColor("#64748b"))
            elements.append(Paragraph(f"Expenses Report | Generated on: {datetime.date.today().strftime('%d-%b-%Y')}", sub_style))
            elements.append(Spacer(1, 15))

            # Table Data
            data = [["Voucher #", "Date", "Category", "Paid To", "Mode", "Amount (Rs.)", "Ref #", "Description"]]
            total_amt = 0.0
            for exp in self.current_expenses:
                cat_name = exp.category.name if exp.category else "-"
                pdate = exp.date.strftime("%d-%m-%Y") if exp.date else "-"
                amt_str = f"{exp.amount:.2f}"
                total_amt += exp.amount
                data.append([
                    exp.voucher_number, pdate, cat_name, exp.payee or "-",
                    exp.payment_mode, amt_str, exp.reference_no or "-", exp.description or "-"
                ])

            data.append(["TOTAL", "", "", "", "", f"{total_amt:,.2f}", "", ""])

            t = Table(data, colWidths=[80, 75, 110, 110, 65, 90, 80, 150])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1e293b")),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('ALIGN', (5, 1), (5, -1), 'RIGHT'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.HexColor("#ffffff"), colors.HexColor("#f8fafc")]),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor("#f1f5f9")),
            ]))
            elements.append(t)
            doc.build(elements)

            QMessageBox.information(self, "Export Successful", f"PDF report saved to:\n{file_path}")
            try:
                os.startfile(file_path)
            except Exception:
                pass
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export to PDF: {e}")

