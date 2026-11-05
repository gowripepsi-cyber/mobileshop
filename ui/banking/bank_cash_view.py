import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QLineEdit, QComboBox, 
    QDateEdit, QDoubleSpinBox, QPushButton, QTableWidget, QTableWidgetItem, 
    QHeaderView, QMessageBox, QFrame, QFormLayout, QTabWidget, QDialog, 
    QDialogButtonBox, QSpacerItem, QSizePolicy, QScrollArea
)
from PySide6.QtCore import Qt, QDate, QTimer
from PySide6.QtGui import QDoubleValidator
from sqlalchemy import func

from utils.formatters import format_inr
from database import Session
from models import (
    BankAccount, BankTransaction, CashTransaction, 
    FundTransfer, DirectTransaction, MoneyTransfer
)
from ui.masters.bank_accounts import BankAccountDialog
from utils.translator import tr


class AmountLineEdit(QLineEdit):
    """Clean amount input that starts empty with placeholder '0.00',
    clears automatically when clicked, and supports .value() and .setValue()."""

    def __init__(self, initial_val=0.0, parent=None):
        super().__init__(parent)
        self.setProperty("is_amount", True)
        self.setPlaceholderText("0.00")
        self.setClearButtonEnabled(True)
        validator = QDoubleValidator(0.0, 99999999.0, 2, self)
        validator.setNotation(QDoubleValidator.StandardNotation)
        self.setValidator(validator)
        if initial_val > 0:
            self.setText(f"{initial_val:.2f}")
        else:
            self.clear()

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        txt = self.text().strip().replace("₹", "").replace(",", "")
        if txt in ("", "0", "0.0", "0.00", "0.01"):
            QTimer.singleShot(0, self.clear)
        else:
            QTimer.singleShot(0, self.selectAll)

    def focusInEvent(self, event):
        super().focusInEvent(event)
        txt = self.text().strip().replace("₹", "").replace(",", "")
        if txt in ("", "0", "0.0", "0.00", "0.01"):
            QTimer.singleShot(0, self.clear)
        else:
            QTimer.singleShot(0, self.selectAll)

    def value(self) -> float:
        txt = self.text().replace("₹", "").replace(",", "").strip()
        try:
            return float(txt) if txt else 0.0
        except ValueError:
            return 0.0

    def setValue(self, val: float):
        if val <= 0:
            self.clear()
        else:
            self.setText(f"{val:.2f}")


class EditFundTransferDialog(QDialog):
    """Dialog to edit an existing fund transfer record and reconcile balances."""

    def __init__(self, transfer_id: int, parent=None):
        super().__init__(parent)
        self.transfer_id = transfer_id
        self.setWindowTitle(f"Edit Fund Transfer #{transfer_id}")
        self.setFixedSize(480, 420)
        self.init_ui()
        self.load_data()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        form_frame = QFrame()
        form_frame.setProperty("class", "CardFrame")
        form_layout = QFormLayout(form_frame)
        form_layout.setContentsMargins(15, 15, 15, 15)
        form_layout.setSpacing(12)

        self.date_input = QDateEdit()
        self.date_input.setCalendarPopup(True)

        self.type_combo = QComboBox()
        self.type_combo.addItems([
            "Cash to Bank (Deposit)",
            "Bank to Cash (Withdrawal)",
            "Bank to Bank Transfer"
        ])
        self.type_combo.currentIndexChanged.connect(self.handle_type_change)

        self.from_combo = QComboBox()
        self.to_combo = QComboBox()

        self.amount_input = AmountLineEdit()

        self.remarks_input = QLineEdit()
        self.remarks_input.setPlaceholderText("Notes / Cheque No / Reference")

        form_layout.addRow(tr("Transfer Date") + ":", self.date_input)
        form_layout.addRow(tr("Transfer Type") + " *:", self.type_combo)
        form_layout.addRow(tr("From Account") + " *:", self.from_combo)
        form_layout.addRow(tr("To Account") + " *:", self.to_combo)
        form_layout.addRow(tr("Amount") + " (₹) *:", self.amount_input)
        form_layout.addRow(tr("Remarks") + ":", self.remarks_input)

        layout.addWidget(form_frame)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        self.save_btn = QPushButton("💾 Save Changes")
        self.save_btn.setProperty("class", "btn-success")
        self.save_btn.setFixedHeight(36)
        self.save_btn.setCursor(Qt.PointingHandCursor)
        self.save_btn.clicked.connect(self.handle_save)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setProperty("class", "btn-secondary")
        self.cancel_btn.setFixedHeight(36)
        self.cancel_btn.setCursor(Qt.PointingHandCursor)
        self.cancel_btn.clicked.connect(self.reject)

        btn_layout.addStretch()
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addWidget(self.save_btn)
        layout.addLayout(btn_layout)

    def load_data(self):
        session = Session()
        try:
            banks = session.query(BankAccount).all()
            self.banks_cache = [(b.id, f"{b.bank_name} ({b.account_name})", b.balance) for b in banks]

            t = session.query(FundTransfer).get(self.transfer_id)
            if not t:
                QMessageBox.warning(self, "Error", "Fund transfer record not found.")
                self.reject()
                return

            self.date_input.setDate(QDate(t.date.year, t.date.month, t.date.day))
            self.amount_input.setValue(t.amount)
            self.remarks_input.setText(t.remarks or "")

            if t.from_type == 'cash' and t.to_type == 'bank':
                self.type_combo.setCurrentText("Cash to Bank (Deposit)")
            elif t.from_type == 'bank' and t.to_type == 'cash':
                self.type_combo.setCurrentText("Bank to Cash (Withdrawal)")
            else:
                self.type_combo.setCurrentText("Bank to Bank Transfer")

            self.handle_type_change()

            if t.from_type == 'bank':
                for idx in range(self.from_combo.count()):
                    data = self.from_combo.itemData(idx)
                    if data and data[0] == 'bank' and data[1] == t.from_account_id:
                        self.from_combo.setCurrentIndex(idx)
                        break
            else:
                for idx in range(self.from_combo.count()):
                    data = self.from_combo.itemData(idx)
                    if data and data[0] == 'cash':
                        self.from_combo.setCurrentIndex(idx)
                        break

            if t.to_type == 'bank':
                for idx in range(self.to_combo.count()):
                    data = self.to_combo.itemData(idx)
                    if data and data[0] == 'bank' and data[1] == t.to_account_id:
                        self.to_combo.setCurrentIndex(idx)
                        break
            else:
                for idx in range(self.to_combo.count()):
                    data = self.to_combo.itemData(idx)
                    if data and data[0] == 'cash':
                        self.to_combo.setCurrentIndex(idx)
                        break
        finally:
            session.close()

    def handle_type_change(self):
        mode = self.type_combo.currentText()
        self.from_combo.clear()
        self.to_combo.clear()

        if "Cash to Bank" in mode:
            self.from_combo.addItem("Cash Drawer", ("cash", None))
            self.from_combo.setEnabled(False)
            self.to_combo.setEnabled(True)
            for b_id, b_name, bal in getattr(self, 'banks_cache', []):
                self.to_combo.addItem(f"{b_name} [Bal: ₹{format_inr(bal)}]", ("bank", b_id))

        elif "Bank to Cash" in mode:
            self.from_combo.setEnabled(True)
            for b_id, b_name, bal in getattr(self, 'banks_cache', []):
                self.from_combo.addItem(f"{b_name} [Bal: ₹{format_inr(bal)}]", ("bank", b_id))
            self.to_combo.addItem("Cash Drawer", ("cash", None))
            self.to_combo.setEnabled(False)

        else:
            self.from_combo.setEnabled(True)
            self.to_combo.setEnabled(True)
            for b_id, b_name, bal in getattr(self, 'banks_cache', []):
                self.from_combo.addItem(f"{b_name} [Bal: ₹{format_inr(bal)}]", ("bank", b_id))
                self.to_combo.addItem(f"{b_name} [Bal: ₹{format_inr(bal)}]", ("bank", b_id))

    def handle_save(self):
        new_amount = self.amount_input.value()
        if new_amount <= 0:
            QMessageBox.warning(self, "Invalid Amount", "Please enter a valid amount greater than zero.")
            return

        from_data = self.from_combo.currentData()
        to_data = self.to_combo.currentData()

        if not from_data or not to_data:
            QMessageBox.warning(self, "Account Error", "Source and destination accounts must be selected.")
            return

        if from_data == to_data:
            QMessageBox.warning(self, "Account Error", "From and To accounts cannot be identical.")
            return

        new_date = self.date_input.date().toPython()
        new_remarks = self.remarks_input.text().strip()

        session = Session()
        try:
            t = session.query(FundTransfer).get(self.transfer_id)
            if not t:
                QMessageBox.warning(self, "Error", "Transfer record no longer exists.")
                return

            # Step 1: Rollback old balance impact
            if t.to_type == 'bank':
                old_to_bank = session.query(BankAccount).get(t.to_account_id)
                if old_to_bank:
                    old_to_bank.balance -= t.amount

            if t.from_type == 'bank':
                old_from_bank = session.query(BankAccount).get(t.from_account_id)
                if old_from_bank:
                    old_from_bank.balance += t.amount

            session.query(BankTransaction).filter_by(source_type='transfer', source_id=t.id).delete()
            session.query(CashTransaction).filter_by(source_type='transfer', source_id=t.id).delete()
            session.flush()

            # Step 2: Validate available funds for new source
            if from_data[0] == 'bank':
                new_from_bank = session.query(BankAccount).get(from_data[1])
                if not new_from_bank or new_from_bank.balance < new_amount:
                    avail = new_from_bank.balance if new_from_bank else 0.0
                    QMessageBox.warning(self, "Insufficient Funds", f"Insufficient balance in source bank.\nAvailable: ₹{format_inr(avail)}")
                    session.rollback()
                    return
                from_name = f"{new_from_bank.bank_name} ({new_from_bank.account_name})"
            else:
                cash_in = session.query(func.sum(CashTransaction.amount)).filter(CashTransaction.transaction_type == 'in').scalar() or 0.0
                cash_out = session.query(func.sum(CashTransaction.amount)).filter(CashTransaction.transaction_type == 'out').scalar() or 0.0
                cash_avail = cash_in - cash_out
                if cash_avail < new_amount:
                    QMessageBox.warning(self, "Insufficient Funds", f"Insufficient cash in drawer.\nAvailable: ₹{format_inr(cash_avail)}")
                    session.rollback()
                    return
                from_name = "Cash Drawer"

            if to_data[0] == 'bank':
                new_to_bank = session.query(BankAccount).get(to_data[1])
                to_name = f"{new_to_bank.bank_name} ({new_to_bank.account_name})" if new_to_bank else "Bank"
            else:
                to_name = "Cash Drawer"

            # Step 3: Apply new values
            t.date = new_date
            t.from_type = from_data[0]
            t.from_account_id = from_data[1] if from_data[0] == 'bank' else None
            t.to_type = to_data[0]
            t.to_account_id = to_data[1] if to_data[0] == 'bank' else None
            t.amount = new_amount
            t.remarks = new_remarks

            desc_out = f"Transfer to {to_name}. {new_remarks}"
            desc_in = f"Transfer from {from_name}. {new_remarks}"

            if from_data[0] == 'bank':
                tx_out = BankTransaction(
                    date=new_date, transaction_type='withdrawal', account_id=from_data[1],
                    amount=new_amount, source_type='transfer', source_id=t.id, description=desc_out
                )
                session.add(tx_out)
                new_from_bank.balance -= new_amount
            else:
                tx_out = CashTransaction(
                    date=new_date, transaction_type='out', amount=new_amount,
                    source_type='transfer', source_id=t.id, description=desc_out
                )
                session.add(tx_out)

            if to_data[0] == 'bank':
                tx_in = BankTransaction(
                    date=new_date, transaction_type='deposit', account_id=to_data[1],
                    amount=new_amount, source_type='transfer', source_id=t.id, description=desc_in
                )
                session.add(tx_in)
                new_to_bank.balance += new_amount
            else:
                tx_in = CashTransaction(
                    date=new_date, transaction_type='in', amount=new_amount,
                    source_type='transfer', source_id=t.id, description=desc_in
                )
                session.add(tx_in)

            session.commit()
            QMessageBox.information(self, "Success", "Fund transfer updated successfully.")
            self.accept()
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", f"Failed to update transfer: {e}")
        finally:
            session.close()


class EditDirectTransactionDialog(QDialog):
    """Dialog to edit an existing direct expense or income transaction."""

    def __init__(self, entry_id: int, parent=None):
        super().__init__(parent)
        self.entry_id = entry_id
        self.setWindowTitle(f"Edit Direct Transaction #{entry_id}")
        self.setFixedSize(460, 400)
        self.init_ui()
        self.load_data()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        form_frame = QFrame()
        form_frame.setProperty("class", "CardFrame")
        form_layout = QFormLayout(form_frame)
        form_layout.setContentsMargins(15, 15, 15, 15)
        form_layout.setSpacing(12)

        self.date_input = QDateEdit()
        self.date_input.setCalendarPopup(True)

        self.type_combo = QComboBox()
        self.type_combo.addItems(["Withdrawal / Expense", "Deposit / Income"])

        self.acc_type_combo = QComboBox()
        self.acc_type_combo.addItems(["Cash Drawer", "Bank Account"])
        self.acc_type_combo.currentIndexChanged.connect(self.handle_acc_type_change)

        self.bank_combo = QComboBox()
        self.bank_combo.setEnabled(False)

        self.amount_input = AmountLineEdit()

        self.desc_input = QLineEdit()
        self.desc_input.setPlaceholderText("Expense purpose / Income source")

        form_layout.addRow(tr("Date") + ":", self.date_input)
        form_layout.addRow(tr("Type") + " *:", self.type_combo)
        form_layout.addRow(tr("Account") + " *:", self.acc_type_combo)
        form_layout.addRow(tr("Bank Account") + ":", self.bank_combo)
        form_layout.addRow(tr("Amount") + " (₹) *:", self.amount_input)
        form_layout.addRow(tr("Description") + ":", self.desc_input)

        layout.addWidget(form_frame)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        self.save_btn = QPushButton("💾 Save Changes")
        self.save_btn.setProperty("class", "btn-success")
        self.save_btn.setFixedHeight(36)
        self.save_btn.setCursor(Qt.PointingHandCursor)
        self.save_btn.clicked.connect(self.handle_save)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setProperty("class", "btn-secondary")
        self.cancel_btn.setFixedHeight(36)
        self.cancel_btn.setCursor(Qt.PointingHandCursor)
        self.cancel_btn.clicked.connect(self.reject)

        btn_layout.addStretch()
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addWidget(self.save_btn)
        layout.addLayout(btn_layout)

    def load_data(self):
        session = Session()
        try:
            banks = session.query(BankAccount).all()
            self.bank_combo.clear()
            for b in banks:
                self.bank_combo.addItem(f"{b.bank_name} ({b.account_name}) [Bal: ₹{format_inr(b.balance)}]", b.id)

            dt = session.query(DirectTransaction).get(self.entry_id)
            if not dt:
                QMessageBox.warning(self, "Error", "Entry not found.")
                self.reject()
                return

            self.date_input.setDate(QDate(dt.date.year, dt.date.month, dt.date.day))
            self.amount_input.setValue(dt.amount)
            self.desc_input.setText(dt.description or "")

            if dt.transaction_type == 'deposit':
                self.type_combo.setCurrentText("Deposit / Income")
            else:
                self.type_combo.setCurrentText("Withdrawal / Expense")

            if dt.account_type == 'bank':
                self.acc_type_combo.setCurrentText("Bank Account")
                self.bank_combo.setEnabled(True)
                idx = self.bank_combo.findData(dt.bank_id)
                if idx >= 0:
                    self.bank_combo.setCurrentIndex(idx)
            else:
                self.acc_type_combo.setCurrentText("Cash Drawer")
                self.bank_combo.setEnabled(False)
        finally:
            session.close()

    def handle_acc_type_change(self):
        is_bank = self.acc_type_combo.currentText() == "Bank Account"
        self.bank_combo.setEnabled(is_bank)

    def handle_save(self):
        new_amount = self.amount_input.value()
        if new_amount <= 0:
            QMessageBox.warning(self, "Invalid Amount", "Please enter a valid amount greater than zero.")
            return

        tx_type = "deposit" if "Deposit" in self.type_combo.currentText() else "withdrawal"
        acc_type = "bank" if self.acc_type_combo.currentText() == "Bank Account" else "cash"
        bank_id = self.bank_combo.currentData() if acc_type == "bank" else None

        if acc_type == "bank" and not bank_id:
            QMessageBox.warning(self, "Account Error", "Please select a bank account.")
            return

        new_date = self.date_input.date().toPython()
        new_desc = self.desc_input.text().strip()

        session = Session()
        try:
            dt = session.query(DirectTransaction).get(self.entry_id)
            if not dt:
                QMessageBox.warning(self, "Error", "Entry no longer exists.")
                return

            # Step 1: Revert old direct transaction
            if dt.account_type == "bank":
                old_bank = session.query(BankAccount).get(dt.bank_id)
                if old_bank:
                    if dt.transaction_type == "deposit":
                        old_bank.balance -= dt.amount
                    else:
                        old_bank.balance += dt.amount
                session.query(BankTransaction).filter_by(source_type='direct', source_id=dt.id).delete()
            else:
                session.query(CashTransaction).filter_by(source_type='direct', source_id=dt.id).delete()
            session.flush()

            # Step 2: Validate available balance if withdrawal
            if tx_type == "withdrawal":
                if acc_type == "bank":
                    new_bank = session.query(BankAccount).get(bank_id)
                    if not new_bank or new_bank.balance < new_amount:
                        avail = new_bank.balance if new_bank else 0.0
                        QMessageBox.warning(self, "Insufficient Funds", f"Insufficient balance in {new_bank.bank_name if new_bank else 'Bank'}.\nAvailable: ₹{format_inr(avail)}")
                        session.rollback()
                        return
                else:
                    cash_in = session.query(func.sum(CashTransaction.amount)).filter(CashTransaction.transaction_type == 'in').scalar() or 0.0
                    cash_out = session.query(func.sum(CashTransaction.amount)).filter(CashTransaction.transaction_type == 'out').scalar() or 0.0
                    cash_avail = cash_in - cash_out
                    if cash_avail < new_amount:
                        QMessageBox.warning(self, "Insufficient Funds", f"Insufficient cash in drawer.\nAvailable: ₹{format_inr(cash_avail)}")
                        session.rollback()
                        return

            # Step 3: Apply new transaction
            dt.date = new_date
            dt.transaction_type = tx_type
            dt.account_type = acc_type
            dt.bank_id = bank_id
            dt.amount = new_amount
            dt.description = new_desc

            if acc_type == "bank":
                target_bank = session.query(BankAccount).get(bank_id)
                if tx_type == "deposit":
                    target_bank.balance += new_amount
                    b_tx = BankTransaction(
                        date=new_date, transaction_type='deposit', account_id=bank_id,
                        amount=new_amount, source_type='direct', source_id=dt.id, description=f"Direct Income: {new_desc}"
                    )
                else:
                    target_bank.balance -= new_amount
                    b_tx = BankTransaction(
                        date=new_date, transaction_type='withdrawal', account_id=bank_id,
                        amount=new_amount, source_type='direct', source_id=dt.id, description=f"Direct Expense: {new_desc}"
                    )
                session.add(b_tx)
            else:
                c_type = 'in' if tx_type == 'deposit' else 'out'
                prefix = "Direct Income" if tx_type == 'deposit' else "Direct Expense"
                c_tx = CashTransaction(
                    date=new_date, transaction_type=c_type, amount=new_amount,
                    source_type='direct', source_id=dt.id, description=f"{prefix}: {new_desc}"
                )
                session.add(c_tx)

            session.commit()
            QMessageBox.information(self, "Success", "Transaction updated successfully.")
            self.accept()
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", f"Failed to update entry: {e}")
        finally:
            session.close()


class BankCashView(QWidget):
    """Dedicated management view for Cash Drawer, Bank Accounts, Passbooks, and Fund Transfers."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        self.tabs = QTabWidget()
        self.tabs.setObjectName("bank_cash_tab_widget")

        # 1. Dashboard Tab (Tab 0)
        self.dashboard_tab = QWidget()
        self.setup_dashboard_tab()
        self.tabs.addTab(self.dashboard_tab, f"📊 {tr('Dashboard')}")

        # 2. Cash Drawer Tab (Tab 1)
        self.cash_tab = QWidget()
        self.setup_cash_tab()
        self.tabs.addTab(self.cash_tab, f"💵 {tr('Cash Drawer')}")

        # 3. Bank Passbook Tab (Tab 2)
        self.passbook_tab = QWidget()
        self.setup_passbook_tab()
        self.tabs.addTab(self.passbook_tab, f"🏛️ {tr('Bank Passbook')}")

        # 4. Fund Transfer Tab (Tab 3)
        self.transfer_tab = QWidget()
        self.setup_transfer_tab()
        self.tabs.addTab(self.transfer_tab, f"🔄 {tr('Fund Transfer')}")

        # 5. Direct Expenses & Income Tab (Tab 4)
        self.direct_tab = QWidget()
        self.setup_direct_tab()
        self.tabs.addTab(self.direct_tab, f"📝 {tr('Daily Expenses & Direct Income')}")

        # 6. Bank Accounts Master Tab (Tab 5 - Last place in row)
        self.bank_master_tab = QWidget()
        self.setup_bank_master_tab()
        self.tabs.addTab(self.bank_master_tab, f"🏦 {tr('Bank Accounts Master')}")

        # Aliases for backward compatibility
        self.bank_tab = self.bank_master_tab

        # Connect tab change
        self.tabs.currentChanged.connect(self.on_tab_changed)

        layout.addWidget(self.tabs)

    def on_tab_changed(self, index):
        if index == 0:
            self.load_dashboard_data()
        elif index == 1:
            self.load_cash_metrics_and_ledger()
        elif index == 2:
            self.load_bank_passbook()
        elif index == 3:
            self.populate_transfer_combos()
            self.load_transfer_history()
        elif index == 4:
            self.populate_direct_combos()
            self.load_direct_history()
        elif index == 5:
            self.load_bank_accounts()

    def set_active_tab(self, index):
        if 0 <= index < self.tabs.count():
            self.tabs.setCurrentIndex(index)
            self.refresh_data()

    def retranslate_ui(self):
        """Updates tab headers, table headers, labels, and data rows when active language changes."""
        self.tabs.setTabText(0, f"📊 {tr('Dashboard')}")
        self.tabs.setTabText(1, f"💵 {tr('Cash Drawer')}")
        self.tabs.setTabText(2, f"🏛️ {tr('Bank Passbook')}")
        self.tabs.setTabText(3, f"🔄 {tr('Fund Transfer')}")
        self.tabs.setTabText(4, f"📝 {tr('Daily Expenses & Direct Income')}")
        self.tabs.setTabText(5, f"🏦 {tr('Bank Accounts Master')}")

        # Tab 0: Dashboard
        if hasattr(self, 'dash_card_bank'):
            self.dash_card_bank.title_label.setText(tr("Total Bank Balance"))
        if hasattr(self, 'dash_card_cash'):
            self.dash_card_cash.title_label.setText(tr("Cash Drawer Balance"))
        if hasattr(self, 'dash_card_total'):
            self.dash_card_total.title_label.setText(tr("Total Liquid Funds"))
        if hasattr(self, 'dash_card_upi'):
            self.dash_card_upi.title_label.setText(tr("UPI Received Payments"))

        if hasattr(self, 'lbl_all_acc_title'):
            self.lbl_all_acc_title.setText(f"🏦 {tr('All Accounts Balance Overview')}")
        if hasattr(self, 'btn_dash_add_bank'):
            self.btn_dash_add_bank.setText(f"+ {tr('Add Account')}")

        if hasattr(self, 'dash_accounts_table'):
            self.dash_accounts_table.setHorizontalHeaderLabels([
                tr("Account / Source"), tr("Institution"), tr("Type"), tr("Today Inflows"), tr("Current Balance")
            ])

        if hasattr(self, 'lbl_upi_title'):
            self.lbl_upi_title.setText(f"📱 {tr('UPI Received Payments')}")
        if hasattr(self, 'dash_upi_table'):
            self.dash_upi_table.setHorizontalHeaderLabels([
                tr("Date"), tr("Account / Bank"), tr("Description"), f"{tr('Amount')} (+₹)"
            ])
        if hasattr(self, 'upi_period_combo'):
            curr_idx = self.upi_period_combo.currentIndex()
            self.upi_period_combo.blockSignals(True)
            self.upi_period_combo.clear()
            self.upi_period_combo.addItems([tr("All Time"), tr("Today"), tr("This Week"), tr("This Month")])
            self.upi_period_combo.setCurrentIndex(curr_idx if curr_idx >= 0 else 0)
            self.upi_period_combo.blockSignals(False)

        if hasattr(self, 'lbl_quick'):
            self.lbl_quick.setText(tr("Quick Navigation") + ":")
        if hasattr(self, 'btn_nav_cash'):
            self.btn_nav_cash.setText(f"💵 {tr('Cash Drawer')}")
        if hasattr(self, 'btn_nav_passbook'):
            self.btn_nav_passbook.setText(f"🏛️ {tr('Bank Passbook')}")
        if hasattr(self, 'btn_nav_transfer'):
            self.btn_nav_transfer.setText(f"🔄 {tr('Fund Transfer')}")
        if hasattr(self, 'btn_nav_direct'):
            self.btn_nav_direct.setText(f"📝 {tr('Daily Expenses & Direct Income')}")
        if hasattr(self, 'btn_nav_master'):
            self.btn_nav_master.setText(f"🏦 {tr('Bank Accounts Master')}")

        # Tab 1: Cash Drawer
        if hasattr(self, 'card_cash_in_hand'):
            self.card_cash_in_hand.title_label.setText(tr("Cash in Hand"))
        if hasattr(self, 'card_today_in'):
            self.card_today_in.title_label.setText(tr("Today's Cash In"))
        if hasattr(self, 'card_today_out'):
            self.card_today_out.title_label.setText(tr("Today's Cash Out"))
        if hasattr(self, 'card_bank_balance'):
            self.card_bank_balance.title_label.setText(tr("Total Bank Balances"))
        if hasattr(self, 'card_bank_count'):
            self.card_bank_count.title_label.setText(tr("Registered Bank Accounts"))

        if hasattr(self, 'btn_quick_in'):
            self.btn_quick_in.setText(f"+ {tr('Quick Cash In')}")
        if hasattr(self, 'btn_quick_out'):
            self.btn_quick_out.setText(f"- {tr('Cash Expense')}")

        if hasattr(self, 'lbl_cash_filter'):
            self.lbl_cash_filter.setText(tr("Filter Period") + ":")
        if hasattr(self, 'cash_period_combo'):
            curr_idx = self.cash_period_combo.currentIndex()
            self.cash_period_combo.blockSignals(True)
            self.cash_period_combo.clear()
            self.cash_period_combo.addItems([tr("All Transactions"), tr("Today"), tr("Yesterday"), tr("This Week"), tr("This Month")])
            self.cash_period_combo.setCurrentIndex(curr_idx if curr_idx >= 0 else 0)
            self.cash_period_combo.blockSignals(False)
        if hasattr(self, 'cash_table'):
            self.cash_table.setHorizontalHeaderLabels([
                tr("Date"), tr("Description"), tr("Source / Category"), f"{tr('Cash In')} (+₹)", f"{tr('Cash Out')} (-₹)"
            ])

        # Tab 2: Bank Passbook
        if hasattr(self, 'passbook_title'):
            self.passbook_title.setText(tr("Bank Passbook Transactions"))
        if hasattr(self, 'lbl_bank_sel'):
            self.lbl_bank_sel.setText(tr("Filter by Bank") + ":")
        if hasattr(self, 'lbl_pb_period'):
            self.lbl_pb_period.setText(tr("Period") + ":")
        if hasattr(self, 'pb_period_combo'):
            curr_idx = self.pb_period_combo.currentIndex()
            self.pb_period_combo.blockSignals(True)
            self.pb_period_combo.clear()
            self.pb_period_combo.addItems([tr("All Transactions"), tr("Today"), tr("Yesterday"), tr("This Week"), tr("This Month")])
            self.pb_period_combo.setCurrentIndex(curr_idx if curr_idx >= 0 else 0)
            self.pb_period_combo.blockSignals(False)
        if hasattr(self, 'bank_tx_table'):
            self.bank_tx_table.setHorizontalHeaderLabels([
                tr("Date"), tr("Bank Account"), tr("Description"), tr("Source / Ref"), f"{tr('Deposit')} (+₹)", f"{tr('Withdrawal')} (-₹)"
            ])

        # Tab 3: Fund Transfer
        if hasattr(self, 'lbl_exec_title'):
            self.lbl_exec_title.setText(tr("Execute Fund Transfer"))
        if hasattr(self, 'lbl_hist_title'):
            self.lbl_hist_title.setText(tr("Recent Transfer History"))
        if hasattr(self, 'btn_submit_transfer'):
            self.btn_submit_transfer.setText(f"🔄 {tr('Complete Transfer')}")
        if hasattr(self, 'transfer_log_table'):
            self.transfer_log_table.setHorizontalHeaderLabels([
                tr("ID"), tr("Date"), tr("From Account"), tr("To Account"), f"{tr('Amount')} (₹)", tr("Remarks"), tr("Action")
            ])

        # Tab 4: Daily Expenses & Direct Income
        if hasattr(self, 'direct_form_title'):
            self.direct_form_title.setText(tr("Record Expense or Direct Income"))
        if hasattr(self, 'direct_log_title'):
            self.direct_log_title.setText(tr("Expenses & Direct Transactions Log"))
        if hasattr(self, 'btn_save_direct'):
            self.btn_save_direct.setText(tr("Save Entry"))
        if hasattr(self, 'direct_log_table'):
            self.direct_log_table.setHorizontalHeaderLabels([
                tr("ID"), tr("Date"), tr("Type"), tr("Account"), f"{tr('Amount')} (₹)", tr("Description"), tr("Action")
            ])

        # Always reload dashboard data so rows (Cash Drawer, Physical Cash, etc.) and footer are updated
        if hasattr(self, 'load_dashboard_data'):
            self.load_dashboard_data()

    # -------------------------------------------------------------------------
    # TAB 0: DASHBOARD (வங்கி & கல்லா டாஷ்போர்டு)
    # -------------------------------------------------------------------------
    def setup_dashboard_tab(self):
        scroll = QScrollArea(self.dashboard_tab)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        # 1. Top Stat Cards (4 Cards)
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(15)

        self.dash_card_bank = self._create_stat_card("Total Bank Balance", "₹0.00", "#6366f1")
        self.dash_card_cash = self._create_stat_card("Cash Drawer Balance", "₹0.00", "#8fd53b")
        self.dash_card_total = self._create_stat_card("Total Liquid Funds", "₹0.00", "#38bdf8")
        self.dash_card_upi = self._create_stat_card("UPI Received Payments", "₹0.00", "#f59e0b")

        cards_layout.addWidget(self.dash_card_bank)
        cards_layout.addWidget(self.dash_card_cash)
        cards_layout.addWidget(self.dash_card_total)
        cards_layout.addWidget(self.dash_card_upi)
        layout.addLayout(cards_layout)

        # 2. Main Middle Section: Split between All Accounts Table & UPI Details
        mid_layout = QHBoxLayout()
        mid_layout.setSpacing(15)

        # Left Frame: All Accounts Balance Overview
        acc_frame = QFrame()
        acc_frame.setProperty("class", "CardFrame")
        acc_vbox = QVBoxLayout(acc_frame)
        acc_vbox.setContentsMargins(15, 15, 15, 15)
        acc_vbox.setSpacing(10)

        acc_header = QHBoxLayout()
        self.lbl_all_acc_title = QLabel(f"🏦 {tr('All Accounts Balance Overview')}")
        self.lbl_all_acc_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #0f172a;")
        acc_header.addWidget(self.lbl_all_acc_title)
        acc_header.addStretch()

        self.btn_dash_add_bank = QPushButton(f"+ {tr('Add Account')}")
        self.btn_dash_add_bank.setProperty("class", "btn-success")
        self.btn_dash_add_bank.setFixedHeight(28)
        self.btn_dash_add_bank.setCursor(Qt.PointingHandCursor)
        self.btn_dash_add_bank.clicked.connect(self.handle_add_bank)
        acc_header.addWidget(self.btn_dash_add_bank)

        acc_vbox.addLayout(acc_header)

        # All Accounts Table
        self.dash_accounts_table = QTableWidget()
        self.dash_accounts_table.setColumnCount(5)
        self.dash_accounts_table.setHorizontalHeaderLabels([
            tr("Account / Source"), tr("Institution"), tr("Type"), tr("Today Inflows"), tr("Current Balance")
        ])
        self.dash_accounts_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.dash_accounts_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.dash_accounts_table.verticalHeader().setVisible(False)
        self.dash_accounts_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.dash_accounts_table.setMinimumHeight(220)
        acc_vbox.addWidget(self.dash_accounts_table)

        # Summary footer label
        self.lbl_acc_summary = QLabel("")
        self.lbl_acc_summary.setStyleSheet("color: #64748b; font-weight: bold; font-size: 12px; margin-top: 4px;")
        acc_vbox.addWidget(self.lbl_acc_summary)

        mid_layout.addWidget(acc_frame, 3)

        # Right Frame: UPI Account Received Payments
        upi_frame = QFrame()
        upi_frame.setProperty("class", "CardFrame")
        upi_vbox = QVBoxLayout(upi_frame)
        upi_vbox.setContentsMargins(15, 15, 15, 15)
        upi_vbox.setSpacing(10)

        upi_header = QHBoxLayout()
        self.lbl_upi_title = QLabel(f"📱 {tr('UPI Received Payments')}")
        self.lbl_upi_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #0f172a;")
        upi_header.addWidget(self.lbl_upi_title)
        upi_header.addStretch()

        self.upi_period_combo = QComboBox()
        self.upi_period_combo.addItems([tr("All Time"), tr("Today"), tr("This Week"), tr("This Month")])
        self.upi_period_combo.currentIndexChanged.connect(self.load_dashboard_data)
        upi_header.addWidget(self.upi_period_combo)

        upi_vbox.addLayout(upi_header)

        # UPI Highlights Bar
        upi_stats_layout = QHBoxLayout()
        upi_stats_layout.setSpacing(10)

        self.lbl_upi_amount_badge = QLabel("₹0.00")
        self.lbl_upi_amount_badge.setStyleSheet("font-size: 18px; font-weight: bold; color: #d97706;")

        self.lbl_upi_count_badge = QLabel("0 Txns")
        self.lbl_upi_count_badge.setStyleSheet("font-size: 13px; font-weight: bold; color: #0284c7; background: #e0f2fe; padding: 3px 10px; border-radius: 10px;")

        upi_stats_layout.addWidget(self.lbl_upi_amount_badge)
        upi_stats_layout.addWidget(self.lbl_upi_count_badge)
        upi_stats_layout.addStretch()
        upi_vbox.addLayout(upi_stats_layout)

        # UPI Transactions Table
        self.dash_upi_table = QTableWidget()
        self.dash_upi_table.setColumnCount(4)
        self.dash_upi_table.setHorizontalHeaderLabels([
            tr("Date"), tr("Account / Bank"), tr("Description"), tr("Amount (+₹)")
        ])
        self.dash_upi_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.dash_upi_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.dash_upi_table.verticalHeader().setVisible(False)
        self.dash_upi_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.dash_upi_table.setMinimumHeight(220)
        upi_vbox.addWidget(self.dash_upi_table)

        mid_layout.addWidget(upi_frame, 2)
        layout.addLayout(mid_layout)

        # 3. Quick Action Shortcut Pills Bar
        actions_frame = QFrame()
        actions_frame.setProperty("class", "CardFrame")
        act_layout = QHBoxLayout(actions_frame)
        act_layout.setContentsMargins(15, 10, 15, 10)
        act_layout.setSpacing(12)

        self.lbl_quick = QLabel(tr("Quick Navigation") + ":")
        self.lbl_quick.setStyleSheet("color: #94a3b8; font-weight: bold; font-size: 12px;")
        act_layout.addWidget(self.lbl_quick)

        self.btn_nav_cash = QPushButton(f"💵 {tr('Cash Drawer')}")
        self.btn_nav_cash.setProperty("class", "btn-secondary")
        self.btn_nav_cash.setCursor(Qt.PointingHandCursor)
        self.btn_nav_cash.clicked.connect(lambda: self.tabs.setCurrentIndex(1))
        act_layout.addWidget(self.btn_nav_cash)

        self.btn_nav_passbook = QPushButton(f"🏛️ {tr('Bank Passbook')}")
        self.btn_nav_passbook.setProperty("class", "btn-secondary")
        self.btn_nav_passbook.setCursor(Qt.PointingHandCursor)
        self.btn_nav_passbook.clicked.connect(lambda: self.tabs.setCurrentIndex(2))
        act_layout.addWidget(self.btn_nav_passbook)

        self.btn_nav_transfer = QPushButton(f"🔄 {tr('Fund Transfer')}")
        self.btn_nav_transfer.setProperty("class", "btn-secondary")
        self.btn_nav_transfer.setCursor(Qt.PointingHandCursor)
        self.btn_nav_transfer.clicked.connect(lambda: self.tabs.setCurrentIndex(3))
        act_layout.addWidget(self.btn_nav_transfer)

        self.btn_nav_direct = QPushButton(f"📝 {tr('Daily Expenses & Direct Income')}")
        self.btn_nav_direct.setProperty("class", "btn-secondary")
        self.btn_nav_direct.setCursor(Qt.PointingHandCursor)
        self.btn_nav_direct.clicked.connect(lambda: self.tabs.setCurrentIndex(4))
        act_layout.addWidget(self.btn_nav_direct)

        self.btn_nav_master = QPushButton(f"🏦 {tr('Bank Accounts Master')}")
        self.btn_nav_master.setProperty("class", "btn-secondary")
        self.btn_nav_master.setCursor(Qt.PointingHandCursor)
        self.btn_nav_master.clicked.connect(lambda: self.tabs.setCurrentIndex(5))
        act_layout.addWidget(self.btn_nav_master)

        act_layout.addStretch()
        layout.addWidget(actions_frame)

        # Wrap in scroll layout
        outer_layout = QVBoxLayout(self.dashboard_tab)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        scroll.setWidget(content_widget)
        outer_layout.addWidget(scroll)

    def load_dashboard_data(self):
        session = Session()
        try:
            today = datetime.date.today()
            week_start = today - datetime.timedelta(days=today.weekday())
            month_start = today.replace(day=1)

            # 1. Bank Accounts & Balances
            banks = session.query(BankAccount).all()
            total_bank_bal = sum(b.balance for b in banks)

            # 2. Cash Drawer Balance
            cash_in_all = sum(tx.amount for tx in session.query(CashTransaction).filter_by(transaction_type='in').all())
            cash_out_all = sum(tx.amount for tx in session.query(CashTransaction).filter_by(transaction_type='out').all())
            cash_bal = cash_in_all - cash_out_all

            total_liquid = total_bank_bal + cash_bal

            # Update Stat Cards
            self.dash_card_bank.value_label.setText(f"₹{format_inr(total_bank_bal)}")
            self.dash_card_cash.value_label.setText(f"₹{format_inr(cash_bal)}")
            self.dash_card_total.value_label.setText(f"₹{format_inr(total_liquid)}")

            # 3. UPI Stats and Transactions
            period = self.upi_period_combo.currentText() if hasattr(self, 'upi_period_combo') else "All Time"

            # Query UPI Bank Deposits
            q_bank = session.query(BankTransaction).join(BankAccount).filter(BankTransaction.transaction_type == 'deposit')
            q_bank = q_bank.filter(
                BankTransaction.description.ilike('%upi%') |
                BankTransaction.description.ilike('%gpay%') |
                BankTransaction.description.ilike('%phonepe%') |
                BankTransaction.description.ilike('%paytm%') |
                BankTransaction.description.ilike('%qr%') |
                BankAccount.account_type.ilike('%upi%') |
                BankAccount.bank_name.ilike('%upi%') |
                BankAccount.account_name.ilike('%upi%')
            )

            # Query UPI Money Transfers
            q_mt = session.query(MoneyTransfer).filter(MoneyTransfer.transfer_type == 'UPI')

            if period in ["Today", tr("Today")]:
                q_bank = q_bank.filter(BankTransaction.date == today)
                q_mt = q_mt.filter(MoneyTransfer.date == today)
            elif period in ["This Week", tr("This Week")]:
                q_bank = q_bank.filter(BankTransaction.date >= week_start)
                q_mt = q_mt.filter(MoneyTransfer.date >= week_start)
            elif period in ["This Month", tr("This Month")]:
                q_bank = q_bank.filter(BankTransaction.date >= month_start)
                q_mt = q_mt.filter(MoneyTransfer.date >= month_start)

            b_txs = q_bank.order_by(BankTransaction.date.desc(), BankTransaction.id.desc()).all()
            mt_txs = q_mt.order_by(MoneyTransfer.date.desc(), MoneyTransfer.id.desc()).all()

            upi_count = len(b_txs) + len(mt_txs)
            upi_amount = sum(t.amount for t in b_txs) + sum(m.amount for m in mt_txs)

            self.dash_card_upi.value_label.setText(f"₹{format_inr(upi_amount)}")
            self.lbl_upi_amount_badge.setText(f"₹{format_inr(upi_amount)}")
            self.lbl_upi_count_badge.setText(f"{upi_count} {tr('Txns')}")

            # Populate UPI Table
            all_upi_rows = []
            for t in b_txs:
                bname = t.bank_account.bank_name if t.bank_account else "Bank A/c"
                all_upi_rows.append((t.date, bname, t.description or "UPI Deposit", t.amount))
            for m in mt_txs:
                all_upi_rows.append((m.date, f"UPI: {m.upi_id or m.beneficiary_name}", f"Remittance from {m.customer_name or 'Customer'}", m.amount))
            all_upi_rows.sort(key=lambda r: r[0], reverse=True)

            self.dash_upi_table.setRowCount(len(all_upi_rows))
            for i, (dt, acc, desc, amt) in enumerate(all_upi_rows[:100]):
                self.dash_upi_table.setItem(i, 0, QTableWidgetItem(dt.strftime("%Y-%m-%d") if hasattr(dt, 'strftime') else str(dt)))
                self.dash_upi_table.setItem(i, 1, QTableWidgetItem(acc))
                self.dash_upi_table.setItem(i, 2, QTableWidgetItem(desc))
                item_amt = QTableWidgetItem(f"+ ₹{format_inr(amt)}")
                item_amt.setForeground(Qt.green)
                self.dash_upi_table.setItem(i, 3, item_amt)

            # 4. Populate All Accounts Balance Table
            today_cash_in = sum(tx.amount for tx in session.query(CashTransaction).filter(CashTransaction.transaction_type == 'in', CashTransaction.date == today).all())

            accounts_data = []
            # Cash Drawer
            accounts_data.append({
                "name": tr("Cash Drawer"),
                "inst": tr("Physical Cash"),
                "type": tr("Cash"),
                "today_in": today_cash_in,
                "balance": cash_bal,
                "is_cash": True
            })

            for b in banks:
                today_b_in = sum(tx.amount for tx in session.query(BankTransaction).filter(
                    BankTransaction.account_id == b.id,
                    BankTransaction.transaction_type == 'deposit',
                    BankTransaction.date == today
                ).all())
                is_upi = (b.account_type or "").upper() in ["UPI", "UPI / QR"] or "upi" in (b.bank_name or "").lower() or "upi" in (b.account_name or "").lower()
                accounts_data.append({
                    "name": b.account_name,
                    "inst": b.bank_name,
                    "type": "UPI / QR" if is_upi else (b.account_type or "Current"),
                    "today_in": today_b_in,
                    "balance": b.balance,
                    "is_upi": is_upi
                })

            self.dash_accounts_table.setRowCount(len(accounts_data))
            for i, acc in enumerate(accounts_data):
                icon_prefix = "💵 " if acc.get("is_cash") else ("📱 " if acc.get("is_upi") else "🏛️ ")
                self.dash_accounts_table.setItem(i, 0, QTableWidgetItem(f"{icon_prefix}{acc['name']}"))
                self.dash_accounts_table.setItem(i, 1, QTableWidgetItem(acc['inst']))
                self.dash_accounts_table.setItem(i, 2, QTableWidgetItem(acc['type']))

                in_item = QTableWidgetItem(f"+ ₹{format_inr(acc['today_in'])}")
                if acc['today_in'] > 0:
                    in_item.setForeground(Qt.green)
                self.dash_accounts_table.setItem(i, 3, in_item)

                bal_item = QTableWidgetItem(f"₹{format_inr(acc['balance'])}")
                if acc['balance'] < 1000.0:
                    bal_item.setForeground(Qt.red)
                else:
                    bal_item.setForeground(Qt.cyan)
                self.dash_accounts_table.setItem(i, 4, bal_item)

            self.lbl_acc_summary.setText(
                f"💵 {tr('Cash')}: ₹{format_inr(cash_bal)}  |  🏛️ {tr('Banks')}: ₹{format_inr(total_bank_bal)}  |  💼 {tr('Total Funds')}: ₹{format_inr(total_liquid)}"
            )

        except Exception as e:
            print(f"Error loading dashboard data: {e}")
        finally:
            session.close()

    # -------------------------------------------------------------------------
    # TAB 1: CASH DRAWER
    # -------------------------------------------------------------------------
    def setup_cash_tab(self):
        layout = QVBoxLayout(self.cash_tab)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        # Top Metric Cards
        metrics_layout = QHBoxLayout()
        metrics_layout.setSpacing(15)

        # Card 1: Live Cash in Hand
        self.card_cash_in_hand = self._create_stat_card("Cash in Hand", "₹0.00", "#8fd53b")
        metrics_layout.addWidget(self.card_cash_in_hand)

        # Card 2: Today's Cash In
        self.card_today_in = self._create_stat_card("Today's Cash In", "+ ₹0.00", "#38bdf8")
        metrics_layout.addWidget(self.card_today_in)

        # Card 3: Today's Cash Out
        self.card_today_out = self._create_stat_card("Today's Cash Out", "- ₹0.00", "#f87171")
        metrics_layout.addWidget(self.card_today_out)

        layout.addLayout(metrics_layout)

        # Filter & Action Bar
        filter_bar = QHBoxLayout()
        filter_bar.setSpacing(10)

        self.lbl_cash_filter = QLabel(tr("Filter Period") + ":")
        self.lbl_cash_filter.setStyleSheet("font-weight: bold; color: #94a3b8;")
        filter_bar.addWidget(self.lbl_cash_filter)

        self.cash_period_combo = QComboBox()
        self.cash_period_combo.addItems(["All Transactions", "Today", "Yesterday", "This Week", "This Month"])
        self.cash_period_combo.currentIndexChanged.connect(self.load_cash_ledger)
        filter_bar.addWidget(self.cash_period_combo)

        self.cash_search = QLineEdit()
        self.cash_search.setPlaceholderText("Search cash ledger by description...")
        self.cash_search.textChanged.connect(self.load_cash_ledger)
        filter_bar.addWidget(self.cash_search, 1)

        # Quick Action Buttons
        self.btn_quick_in = QPushButton(f"+ {tr('Quick Cash In')}")
        self.btn_quick_in.setStyleSheet("background-color: #8fd53b; color: #0f172a; font-weight: bold; padding: 6px 12px; border-radius: 10px;")
        self.btn_quick_in.clicked.connect(self.open_quick_cash_in)
        filter_bar.addWidget(self.btn_quick_in)

        self.btn_quick_out = QPushButton(f"- {tr('Cash Expense')}")
        self.btn_quick_out.setStyleSheet("background-color: #ef4444; color: #ffffff; font-weight: bold; padding: 6px 12px;")
        self.btn_quick_out.clicked.connect(self.open_quick_cash_out)
        filter_bar.addWidget(self.btn_quick_out)

        layout.addLayout(filter_bar)

        # Cash Ledger Table
        self.cash_table = QTableWidget()
        self.cash_table.setColumnCount(5)
        self.cash_table.setHorizontalHeaderLabels([
            "Date", "Description", "Source / Category", "Cash In (+₹)", "Cash Out (-₹)"
        ])
        self.cash_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.cash_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.cash_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.cash_table.verticalHeader().setVisible(False)
        self.cash_table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.cash_table)

    # -------------------------------------------------------------------------
    # TAB 2: BANK ACCOUNTS MASTER (வங்கி கணக்குகள் மாஸ்டர்)
    # -------------------------------------------------------------------------
    def setup_bank_master_tab(self):
        layout = QVBoxLayout(self.bank_master_tab)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        # Top Metric Cards
        metrics_layout = QHBoxLayout()
        metrics_layout.setSpacing(15)

        self.card_bank_balance = self._create_stat_card("Total Bank Balances", "₹0.00", "#6366f1")
        metrics_layout.addWidget(self.card_bank_balance)

        self.card_bank_count = self._create_stat_card("Registered Bank Accounts", "0", "#38bdf8")
        metrics_layout.addWidget(self.card_bank_count)

        layout.addLayout(metrics_layout)

        # Action & Search Bar
        top_bar = QHBoxLayout()
        top_bar.setSpacing(10)

        self.bank_search_input = QLineEdit()
        self.bank_search_input.setPlaceholderText(tr("Search bank accounts..."))
        self.bank_search_input.textChanged.connect(self.load_bank_accounts)
        top_bar.addWidget(self.bank_search_input, 4)

        self.btn_add_bank = QPushButton(f"+ {tr('Add Account')} (Ctrl+N)")
        self.btn_add_bank.setProperty("class", "btn-success")
        self.btn_add_bank.setToolTip("Add new bank account (Ctrl+N)")
        self.btn_add_bank.clicked.connect(self.handle_add_bank)
        top_bar.addWidget(self.btn_add_bank, 1)

        self.btn_edit_bank = QPushButton(f"✏️ {tr('Edit Account')}")
        self.btn_edit_bank.setProperty("class", "btn-secondary")
        self.btn_edit_bank.clicked.connect(self.handle_edit_bank)
        top_bar.addWidget(self.btn_edit_bank, 1)

        self.btn_delete_bank = QPushButton(f"🗑️ {tr('Delete')}")
        self.btn_delete_bank.setProperty("class", "btn-danger")
        self.btn_delete_bank.clicked.connect(self.handle_delete_bank)
        top_bar.addWidget(self.btn_delete_bank, 1)

        layout.addLayout(top_bar)

        # Bank Accounts Table
        self.bank_acc_table = QTableWidget()
        self.bank_acc_table.setColumnCount(6)
        self.bank_acc_table.setHorizontalHeaderLabels([
            "ID", tr("Bank Name"), tr("Account Number"), tr("Account Display Name"), tr("Account Type"), tr("Current Balance")
        ])
        self.bank_acc_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.bank_acc_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.bank_acc_table.verticalHeader().setVisible(False)
        self.bank_acc_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.bank_acc_table.setSelectionMode(QTableWidget.SingleSelection)
        self.bank_acc_table.doubleClicked.connect(self.handle_edit_bank)
        layout.addWidget(self.bank_acc_table)

        # Master compatibility aliases for permissions & shortcuts
        self.add_btn = self.btn_add_bank
        self.edit_btn = self.btn_edit_bank
        self.delete_btn = self.btn_delete_bank
        self.table = self.bank_acc_table
        self.search_input = self.bank_search_input
        self.bank_accounts_view = self

    # -------------------------------------------------------------------------
    # TAB 3: BANK PASSBOOK (வங்கி பாஸ்புக்)
    # -------------------------------------------------------------------------
    def setup_passbook_tab(self):
        layout = QVBoxLayout(self.passbook_tab)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)

        # Passbook Filter & Section
        self.passbook_title = QLabel(tr("Bank Passbook Transactions"))
        self.passbook_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #0f172a;")
        layout.addWidget(self.passbook_title)

        pb_filter_bar = QHBoxLayout()
        pb_filter_bar.setSpacing(10)

        self.lbl_bank_sel = QLabel(tr("Filter by Bank") + ":")
        self.lbl_bank_sel.setStyleSheet("font-weight: bold; color: #94a3b8;")
        pb_filter_bar.addWidget(self.lbl_bank_sel)

        self.pb_bank_filter = QComboBox()
        self.pb_bank_filter.currentIndexChanged.connect(self.load_bank_passbook)
        pb_filter_bar.addWidget(self.pb_bank_filter, 1)

        self.lbl_pb_period = QLabel(tr("Period") + ":")
        self.lbl_pb_period.setStyleSheet("font-weight: bold; color: #94a3b8;")
        pb_filter_bar.addWidget(self.lbl_pb_period)

        self.pb_period_combo = QComboBox()
        self.pb_period_combo.addItems([tr("All Transactions"), tr("Today"), tr("Yesterday"), tr("This Week"), tr("This Month")])
        self.pb_period_combo.currentIndexChanged.connect(self.load_bank_passbook)
        pb_filter_bar.addWidget(self.pb_period_combo)

        self.pb_search = QLineEdit()
        self.pb_search.setPlaceholderText(tr("Search bank passbook..."))
        self.pb_search.textChanged.connect(self.load_bank_passbook)
        pb_filter_bar.addWidget(self.pb_search, 2)

        layout.addLayout(pb_filter_bar)

        # Bank Passbook Table
        self.bank_tx_table = QTableWidget()
        self.bank_tx_table.setColumnCount(6)
        self.bank_tx_table.setHorizontalHeaderLabels([
            tr("Date"), tr("Bank Account"), tr("Description"), tr("Source / Ref"), f"{tr('Deposit')} (+₹)", f"{tr('Withdrawal')} (-₹)"
        ])
        self.bank_tx_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.bank_tx_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.bank_tx_table.verticalHeader().setVisible(False)
        self.bank_tx_table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.bank_tx_table)

    # -------------------------------------------------------------------------
    # TAB 3: FUND TRANSFER (பணப் பரிமாற்றம்)
    # -------------------------------------------------------------------------
    def setup_transfer_tab(self):
        layout = QVBoxLayout(self.transfer_tab)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        # Top Card: Transfer Form (stacked on top)
        form_frame = QFrame()
        form_frame.setProperty("class", "CardFrame")
        form_layout = QVBoxLayout(form_frame)
        form_layout.setContentsMargins(18, 14, 18, 14)
        form_layout.setSpacing(10)

        self.lbl_exec_title = QLabel(tr("Execute Fund Transfer"))
        self.lbl_exec_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #0f172a;")
        form_layout.addWidget(self.lbl_exec_title)

        grid = QGridLayout()
        grid.setHorizontalSpacing(15)
        grid.setVerticalSpacing(10)

        self.tr_type = QComboBox()
        self.tr_type.addItems([
            "Cash to Bank (Deposit)",
            "Bank to Cash (Withdrawal)",
            "Bank to Bank Transfer"
        ])
        self.tr_type.currentIndexChanged.connect(self.handle_transfer_type_change)

        self.tr_date = QDateEdit()
        self.tr_date.setCalendarPopup(True)
        self.tr_date.setDate(QDate.currentDate())

        self.tr_from_combo = QComboBox()
        self.tr_to_combo = QComboBox()

        self.tr_amount = AmountLineEdit()

        self.tr_remarks = QLineEdit()
        self.tr_remarks.setPlaceholderText("Notes / Cheque No / Reference")

        self.btn_submit_transfer = QPushButton(f"🔄 {tr('Complete Transfer')}")
        self.btn_submit_transfer.setProperty("class", "btn-success")
        self.btn_submit_transfer.setFixedHeight(36)
        self.btn_submit_transfer.setCursor(Qt.PointingHandCursor)
        self.btn_submit_transfer.clicked.connect(self.save_fund_transfer)

        def make_field(label_text, widget):
            box = QVBoxLayout()
            box.setSpacing(4)
            lbl = QLabel(label_text)
            lbl.setStyleSheet("color: #94a3b8; font-size: 12px; font-weight: bold;")
            box.addWidget(lbl)
            box.addWidget(widget)
            return box

        # Row 0: 4 columns
        grid.addLayout(make_field(f"{tr('Transfer Type')} *", self.tr_type), 0, 0)
        grid.addLayout(make_field(tr("Transfer Date"), self.tr_date), 0, 1)
        grid.addLayout(make_field(f"{tr('From Account')} *", self.tr_from_combo), 0, 2)
        grid.addLayout(make_field(f"{tr('To Account')} *", self.tr_to_combo), 0, 3)

        # Row 1: Amount, Remarks (span 2), Submit button
        grid.addLayout(make_field(f"{tr('Amount')} (₹) *", self.tr_amount), 1, 0)
        grid.addLayout(make_field(tr("Remarks"), self.tr_remarks), 1, 1, 1, 2)

        btn_box = QVBoxLayout()
        btn_box.setSpacing(4)
        btn_spacer_lbl = QLabel("")
        btn_spacer_lbl.setStyleSheet("font-size: 12px;")
        btn_box.addWidget(btn_spacer_lbl)
        btn_box.addWidget(self.btn_submit_transfer)
        grid.addLayout(btn_box, 1, 3)

        # Equal column stretch for all 4 columns
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(2, 1)
        grid.setColumnStretch(3, 1)

        form_layout.addLayout(grid)
        layout.addWidget(form_frame)

        # Bottom Card: Transfer History Log (stacked on bottom)
        history_frame = QFrame()
        history_frame.setProperty("class", "CardFrame")
        hist_layout = QVBoxLayout(history_frame)
        hist_layout.setContentsMargins(18, 14, 18, 14)
        hist_layout.setSpacing(10)

        self.lbl_hist_title = QLabel(tr("Recent Transfer History"))
        self.lbl_hist_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #0f172a;")
        hist_layout.addWidget(self.lbl_hist_title)

        self.transfer_log_table = QTableWidget()
        self.transfer_log_table.setColumnCount(7)
        self.transfer_log_table.setHorizontalHeaderLabels([
            tr("ID"), tr("Date"), tr("From Account"), tr("To Account"), f"{tr('Amount')} (₹)", tr("Remarks"), tr("Action")
        ])
        self.transfer_log_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.transfer_log_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.transfer_log_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.transfer_log_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.transfer_log_table.horizontalHeader().setSectionResizeMode(6, QHeaderView.Fixed)
        self.transfer_log_table.setColumnWidth(6, 120)
        self.transfer_log_table.verticalHeader().setVisible(False)
        self.transfer_log_table.verticalHeader().setDefaultSectionSize(48)
        self.transfer_log_table.setEditTriggers(QTableWidget.NoEditTriggers)
        hist_layout.addWidget(self.transfer_log_table)

        layout.addWidget(history_frame, 1)

    # -------------------------------------------------------------------------
    # TAB 4: DIRECT EXPENSES & INCOME (செலவுகள் & வரவு)
    # -------------------------------------------------------------------------
    def setup_direct_tab(self):
        layout = QHBoxLayout(self.direct_tab)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(20)

        # Left Card: Form
        form_frame = QFrame()
        form_frame.setProperty("class", "CardFrame")
        form_frame.setFixedWidth(400)
        form_layout = QFormLayout(form_frame)
        form_layout.setContentsMargins(15, 15, 15, 15)
        form_layout.setSpacing(12)

        self.direct_form_title = QLabel(tr("Record Expense or Direct Income"))
        self.direct_form_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #0f172a; margin-bottom: 8px;")
        form_layout.addRow(self.direct_form_title)

        self.dir_date = QDateEdit()
        self.dir_date.setCalendarPopup(True)
        self.dir_date.setDate(QDate.currentDate())

        self.dir_type = QComboBox()
        self.dir_type.addItems(["Withdrawal / Expense", "Deposit / Income"])

        self.dir_acc_type = QComboBox()
        self.dir_acc_type.addItems(["Cash Drawer", "Bank Account"])
        self.dir_acc_type.currentIndexChanged.connect(self.handle_direct_acc_type_change)

        self.dir_bank_combo = QComboBox()
        self.dir_bank_combo.setEnabled(False)

        self.dir_category = QComboBox()
        self.dir_category.setEditable(True)
        self.dir_category.addItems([
            "Shop Rent",
            "Electricity Bill",
            "Tea & Refreshments",
            "Staff Salary / Advance",
            "Stationery & Printing",
            "Transportation & Courier",
            "Shop Maintenance / Repair",
            "Marketing & Promotion",
            "Capital Injection",
            "Scrap / Old Parts Sale",
            "Commission Income",
            "Misc Income / Expense"
        ])

        self.dir_amount = AmountLineEdit()

        self.dir_desc = QLineEdit()
        self.dir_desc.setPlaceholderText("Notes / Particulars")

        form_layout.addRow("Date:", self.dir_date)
        form_layout.addRow("Type *:", self.dir_type)
        form_layout.addRow("Paid / Received Via *:", self.dir_acc_type)
        form_layout.addRow("Select Bank Account:", self.dir_bank_combo)
        form_layout.addRow("Category / Head *:", self.dir_category)
        form_layout.addRow("Amount (₹) *:", self.dir_amount)
        form_layout.addRow("Description:", self.dir_desc)

        self.btn_save_direct = QPushButton(tr("Save Entry"))
        self.btn_save_direct.setProperty("class", "btn-success")
        self.btn_save_direct.setFixedHeight(40)
        self.btn_save_direct.clicked.connect(self.save_direct_entry)
        form_layout.addRow("", self.btn_save_direct)

        layout.addWidget(form_frame)

        # Right Card: Log Table
        log_frame = QFrame()
        log_frame.setProperty("class", "CardFrame")
        log_layout = QVBoxLayout(log_frame)
        log_layout.setContentsMargins(15, 15, 15, 15)

        self.direct_log_title = QLabel(tr("Expenses & Direct Transactions Log"))
        self.direct_log_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #0f172a; margin-bottom: 10px;")
        log_layout.addWidget(self.direct_log_title)

        self.direct_log_table = QTableWidget()
        self.direct_log_table.setColumnCount(7)
        self.direct_log_table.setHorizontalHeaderLabels([
            "ID", "Date", "Type", "Account", "Amount (₹)", "Description", "Action"
        ])
        self.direct_log_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.direct_log_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.direct_log_table.horizontalHeader().setSectionResizeMode(6, QHeaderView.Fixed)
        self.direct_log_table.setColumnWidth(6, 120)
        self.direct_log_table.verticalHeader().setVisible(False)
        self.direct_log_table.verticalHeader().setDefaultSectionSize(48)
        self.direct_log_table.setEditTriggers(QTableWidget.NoEditTriggers)
        log_layout.addWidget(self.direct_log_table)

        layout.addWidget(log_frame)

    # -------------------------------------------------------------------------
    # DATA REFRESH & LOAD METHODS
    # -------------------------------------------------------------------------
    def refresh_data(self):
        """Called automatically when switching to this view."""
        self.load_dashboard_data()
        self.load_cash_metrics_and_ledger()
        self.load_bank_accounts_and_passbook()
        self.populate_transfer_combos()
        self.load_transfer_history()
        self.populate_direct_combos()
        self.load_direct_history()

    def _create_stat_card(self, title: str, initial_value: str, color_hex: str) -> QFrame:
        card = QFrame()
        card.setProperty("class", "MetricCard")
        card.setStyleSheet(f"border-left: 4px solid {color_hex};")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 14, 16, 14)
        card_layout.setSpacing(4)

        lbl_t = QLabel(tr(title))
        lbl_t.setStyleSheet("font-size: 12px; color: #64748b; font-weight: bold;")
        card_layout.addWidget(lbl_t)
        card.title_label = lbl_t

        lbl_v = QLabel(initial_value)
        lbl_v.setStyleSheet(f"font-size: 22px; font-weight: bold; color: {color_hex};")
        card_layout.addWidget(lbl_v)
        card.value_label = lbl_v

        return card

    def load_cash_metrics_and_ledger(self):
        session = Session()
        try:
            # 1. Total Cash in Hand
            cash_in_total = session.query(func.sum(CashTransaction.amount)).filter(CashTransaction.transaction_type == 'in').scalar() or 0.0
            cash_out_total = session.query(func.sum(CashTransaction.amount)).filter(CashTransaction.transaction_type == 'out').scalar() or 0.0
            cash_in_hand = cash_in_total - cash_out_total

            self.card_cash_in_hand.value_label.setText(f"₹{format_inr(cash_in_hand)}")

            # 2. Today's In/Out
            today = datetime.date.today()
            today_in = session.query(func.sum(CashTransaction.amount)).filter(
                CashTransaction.transaction_type == 'in',
                CashTransaction.date == today
            ).scalar() or 0.0

            today_out = session.query(func.sum(CashTransaction.amount)).filter(
                CashTransaction.transaction_type == 'out',
                CashTransaction.date == today
            ).scalar() or 0.0

            self.card_today_in.value_label.setText(f"+ ₹{format_inr(today_in)}")
            self.card_today_out.value_label.setText(f"- ₹{format_inr(today_out)}")

        except Exception as e:
            print(f"Error loading cash metrics: {e}")
        finally:
            session.close()

        self.load_cash_ledger()

    def load_cash_ledger(self):
        session = Session()
        try:
            query = session.query(CashTransaction).order_by(CashTransaction.date.desc(), CashTransaction.id.desc())

            period = self.cash_period_combo.currentText()
            today = datetime.date.today()
            if period == "Today":
                query = query.filter(CashTransaction.date == today)
            elif period == "Yesterday":
                yesterday = today - datetime.timedelta(days=1)
                query = query.filter(CashTransaction.date == yesterday)
            elif period == "This Week":
                week_start = today - datetime.timedelta(days=today.weekday())
                query = query.filter(CashTransaction.date >= week_start)
            elif period == "This Month":
                month_start = today.replace(day=1)
                query = query.filter(CashTransaction.date >= month_start)

            search_txt = self.cash_search.text().strip()
            if search_txt:
                query = query.filter(CashTransaction.description.like(f"%{search_txt}%"))

            rows = query.limit(200).all()
            self.cash_table.setRowCount(len(rows))

            for i, tx in enumerate(rows):
                self.cash_table.setItem(i, 0, QTableWidgetItem(tx.date.strftime("%Y-%m-%d")))
                self.cash_table.setItem(i, 1, QTableWidgetItem(tx.description or "-"))
                self.cash_table.setItem(i, 2, QTableWidgetItem(str(tx.source_type or "").capitalize()))

                if tx.transaction_type == 'in':
                    in_item = QTableWidgetItem(f"+ ₹{format_inr(tx.amount)}")
                    in_item.setForeground(Qt.green)
                    out_item = QTableWidgetItem("-")
                else:
                    in_item = QTableWidgetItem("-")
                    out_item = QTableWidgetItem(f"- ₹{format_inr(tx.amount)}")
                    out_item.setForeground(Qt.red)

                self.cash_table.setItem(i, 3, in_item)
                self.cash_table.setItem(i, 4, out_item)
        except Exception as e:
            print(f"Error loading cash ledger: {e}")
        finally:
            session.close()

    def load_bank_accounts_and_passbook(self):
        self.load_bank_accounts()
        self.load_bank_passbook()

    def load_bank_accounts(self):
        session = Session()
        try:
            banks = session.query(BankAccount).all()
            total_bal = sum(b.balance for b in banks)

            self.card_bank_balance.value_label.setText(f"₹{format_inr(total_bal)}")
            self.card_bank_count.value_label.setText(str(len(banks)))

            search_txt = self.bank_search_input.text().strip().lower() if hasattr(self, 'bank_search_input') else ""
            if search_txt:
                filtered_banks = [
                    b for b in banks
                    if search_txt in (b.bank_name or "").lower()
                    or search_txt in (b.account_name or "").lower()
                    or search_txt in (b.account_number or "").lower()
                    or search_txt in (b.account_type or "").lower()
                ]
            else:
                filtered_banks = banks

            # Populate Accounts Table
            self.bank_acc_table.setRowCount(len(filtered_banks))
            for i, a in enumerate(filtered_banks):
                self.bank_acc_table.setItem(i, 0, QTableWidgetItem(str(a.id)))
                self.bank_acc_table.setItem(i, 1, QTableWidgetItem(a.bank_name))
                self.bank_acc_table.setItem(i, 2, QTableWidgetItem(a.account_number or ""))
                self.bank_acc_table.setItem(i, 3, QTableWidgetItem(a.account_name))
                self.bank_acc_table.setItem(i, 4, QTableWidgetItem(a.account_type or "Current"))

                bal_item = QTableWidgetItem(f"₹{format_inr(a.balance)}")
                if a.balance < 1000.0:
                    bal_item.setForeground(Qt.red)
                else:
                    bal_item.setForeground(Qt.cyan)
                self.bank_acc_table.setItem(i, 5, bal_item)

            # Update passbook bank filter combo
            if hasattr(self, 'pb_bank_filter'):
                cur_bank_id = self.pb_bank_filter.currentData()
                self.pb_bank_filter.blockSignals(True)
                self.pb_bank_filter.clear()
                self.pb_bank_filter.addItem(tr("All Registered Banks"), -1)
                for b in banks:
                    self.pb_bank_filter.addItem(f"{b.bank_name} - {b.account_name} ({b.account_number or 'No A/C'})", b.id)
                if cur_bank_id is not None:
                    idx = self.pb_bank_filter.findData(cur_bank_id)
                    if idx >= 0:
                        self.pb_bank_filter.setCurrentIndex(idx)
                self.pb_bank_filter.blockSignals(False)

        except Exception as e:
            print(f"Error loading bank accounts: {e}")
        finally:
            session.close()

    def load_bank_passbook(self):
        session = Session()
        try:
            query = session.query(BankTransaction).order_by(BankTransaction.date.desc(), BankTransaction.id.desc())

            bank_id = self.pb_bank_filter.currentData()
            if bank_id is not None and bank_id != -1:
                query = query.filter(BankTransaction.account_id == bank_id)

            period = self.pb_period_combo.currentText()
            today = datetime.date.today()
            if period == "Today":
                query = query.filter(BankTransaction.date == today)
            elif period == "Yesterday":
                yesterday = today - datetime.timedelta(days=1)
                query = query.filter(BankTransaction.date == yesterday)
            elif period == "This Week":
                week_start = today - datetime.timedelta(days=today.weekday())
                query = query.filter(BankTransaction.date >= week_start)
            elif period == "This Month":
                month_start = today.replace(day=1)
                query = query.filter(BankTransaction.date >= month_start)

            search_txt = self.pb_search.text().strip()
            if search_txt:
                query = query.filter(BankTransaction.description.like(f"%{search_txt}%"))

            rows = query.limit(200).all()
            self.bank_tx_table.setRowCount(len(rows))

            for i, tx in enumerate(rows):
                self.bank_tx_table.setItem(i, 0, QTableWidgetItem(tx.date.strftime("%Y-%m-%d")))
                bname = tx.bank_account.bank_name if tx.bank_account else "Unknown Bank"
                self.bank_tx_table.setItem(i, 1, QTableWidgetItem(bname))
                self.bank_tx_table.setItem(i, 2, QTableWidgetItem(tx.description or "-"))
                self.bank_tx_table.setItem(i, 3, QTableWidgetItem(str(tx.source_type or "").capitalize()))

                if tx.transaction_type == 'deposit':
                    dep_item = QTableWidgetItem(f"+ ₹{format_inr(tx.amount)}")
                    dep_item.setForeground(Qt.green)
                    with_item = QTableWidgetItem("-")
                else:
                    dep_item = QTableWidgetItem("-")
                    with_item = QTableWidgetItem(f"- ₹{format_inr(tx.amount)}")
                    with_item.setForeground(Qt.red)

                self.bank_tx_table.setItem(i, 4, dep_item)
                self.bank_tx_table.setItem(i, 5, with_item)

        except Exception as e:
            print(f"Error loading bank passbook: {e}")
        finally:
            session.close()

    def handle_add_bank(self):
        dlg = BankAccountDialog(parent=self)
        if dlg.exec() == QDialog.Accepted:
            self.refresh_data()

    def handle_edit_bank(self):
        selected = self.bank_acc_table.selectedItems()
        if not selected:
            QMessageBox.information(self, tr("Select Account"), tr("Please select a bank account from the table to edit."))
            return

        row = selected[0].row()
        acc_id = int(self.bank_acc_table.item(row, 0).text())

        session = Session()
        try:
            acc = session.query(BankAccount).get(acc_id)
            if acc:
                dlg = BankAccountDialog(account=acc, parent=self)
                if dlg.exec() == QDialog.Accepted:
                    self.refresh_data()
        finally:
            session.close()

    def handle_delete_bank(self):
        selected = self.bank_acc_table.selectedItems()
        if not selected:
            QMessageBox.information(self, tr("No Selection"), tr("Please select a bank account to delete."))
            return

        row = selected[0].row()
        acc_id = int(self.bank_acc_table.item(row, 0).text())

        confirm = QMessageBox.question(
            self, tr("Confirm Delete"), 
            tr("Are you sure you want to delete this bank account? This will also remove associated transaction ledgers."),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if confirm == QMessageBox.Yes:
            session = Session()
            try:
                acc = session.query(BankAccount).get(acc_id)
                if acc:
                    session.query(BankTransaction).filter_by(account_id=acc.id).delete()
                    session.delete(acc)
                    session.commit()
                    self.refresh_data()
            except Exception as e:
                session.rollback()
                QMessageBox.critical(self, tr("Error"), f"Could not delete bank account: {e}")
            finally:
                session.close()

    # -------------------------------------------------------------------------
    # TAB 3 LOGIC: FUND TRANSFER
    # -------------------------------------------------------------------------
    def populate_transfer_combos(self):
        session = Session()
        try:
            banks = session.query(BankAccount).all()
            self.tr_banks_cache = [(b.id, f"{b.bank_name} ({b.account_name})", b.balance) for b in banks]
            self.handle_transfer_type_change()
        finally:
            session.close()

    def handle_transfer_type_change(self):
        mode = self.tr_type.currentText()
        self.tr_from_combo.clear()
        self.tr_to_combo.clear()

        if "Cash to Bank" in mode:
            self.tr_from_combo.addItem("Cash Drawer", ("cash", None))
            self.tr_from_combo.setEnabled(False)
            self.tr_to_combo.setEnabled(True)
            for b_id, b_name, bal in getattr(self, 'tr_banks_cache', []):
                self.tr_to_combo.addItem(f"{b_name} [Bal: ₹{format_inr(bal)}]", ("bank", b_id))

        elif "Bank to Cash" in mode:
            self.tr_from_combo.setEnabled(True)
            for b_id, b_name, bal in getattr(self, 'tr_banks_cache', []):
                self.tr_from_combo.addItem(f"{b_name} [Bal: ₹{format_inr(bal)}]", ("bank", b_id))
            self.tr_to_combo.addItem("Cash Drawer", ("cash", None))
            self.tr_to_combo.setEnabled(False)

        else: # Bank to Bank
            self.tr_from_combo.setEnabled(True)
            self.tr_to_combo.setEnabled(True)
            for b_id, b_name, bal in getattr(self, 'tr_banks_cache', []):
                self.tr_from_combo.addItem(f"{b_name} [Bal: ₹{format_inr(bal)}]", ("bank", b_id))
                self.tr_to_combo.addItem(f"{b_name} [Bal: ₹{format_inr(bal)}]", ("bank", b_id))

    def save_fund_transfer(self):
        amount = self.tr_amount.value()
        if amount <= 0:
            QMessageBox.warning(self, "Invalid Amount", "Please enter a valid transfer amount greater than zero.")
            return

        from_data = self.tr_from_combo.currentData()
        to_data = self.tr_to_combo.currentData()

        if not from_data or not to_data:
            QMessageBox.warning(self, "Account Error", "Source and destination accounts must be selected.")
            return

        if from_data == to_data:
            QMessageBox.warning(self, "Account Error", "From and To accounts cannot be identical.")
            return

        tx_date = self.tr_date.date().toPython()
        remarks = self.tr_remarks.text().strip()

        session = Session()
        try:
            # Check source balance
            if from_data[0] == 'bank':
                bank_from = session.query(BankAccount).get(from_data[1])
                if not bank_from or bank_from.balance < amount:
                    available = bank_from.balance if bank_from else 0.0
                    QMessageBox.warning(self, "Insufficient Funds", f"Insufficient balance in source bank.\nAvailable: ₹{format_inr(available)}")
                    return
                from_name = f"{bank_from.bank_name} ({bank_from.account_name})"
            else:
                cash_in = session.query(func.sum(CashTransaction.amount)).filter(CashTransaction.transaction_type == 'in').scalar() or 0.0
                cash_out = session.query(func.sum(CashTransaction.amount)).filter(CashTransaction.transaction_type == 'out').scalar() or 0.0
                cash_avail = cash_in - cash_out
                if cash_avail < amount:
                    QMessageBox.warning(self, "Insufficient Funds", f"Insufficient cash in drawer.\nAvailable: ₹{format_inr(cash_avail)}")
                    return
                from_name = "Cash Drawer"

            if to_data[0] == 'bank':
                bank_to = session.query(BankAccount).get(to_data[1])
                to_name = f"{bank_to.bank_name} ({bank_to.account_name})" if bank_to else "Bank"
            else:
                to_name = "Cash Drawer"

            transfer = FundTransfer(
                date=tx_date,
                from_type=from_data[0],
                from_account_id=from_data[1] if from_data[0] == 'bank' else None,
                to_type=to_data[0],
                to_account_id=to_data[1] if to_data[0] == 'bank' else None,
                amount=amount,
                remarks=remarks
            )
            session.add(transfer)
            session.flush()

            desc_out = f"Transfer to {to_name}. {remarks}"
            desc_in = f"Transfer from {from_name}. {remarks}"

            if from_data[0] == 'bank':
                tx_out = BankTransaction(
                    date=tx_date, transaction_type='withdrawal', account_id=from_data[1],
                    amount=amount, source_type='transfer', source_id=transfer.id, description=desc_out
                )
                session.add(tx_out)
                bank_from.balance -= amount
            else:
                tx_out = CashTransaction(
                    date=tx_date, transaction_type='out', amount=amount,
                    source_type='transfer', source_id=transfer.id, description=desc_out
                )
                session.add(tx_out)

            if to_data[0] == 'bank':
                tx_in = BankTransaction(
                    date=tx_date, transaction_type='deposit', account_id=to_data[1],
                    amount=amount, source_type='transfer', source_id=transfer.id, description=desc_in
                )
                session.add(tx_in)
                bank_to.balance += amount
            else:
                tx_in = CashTransaction(
                    date=tx_date, transaction_type='in', amount=amount,
                    source_type='transfer', source_id=transfer.id, description=desc_in
                )
                session.add(tx_in)

            session.commit()
            QMessageBox.information(self, "Success", f"Transfer of ₹{format_inr(amount)} completed successfully.")
            self.tr_amount.setValue(0.0)
            self.tr_remarks.clear()
            self.refresh_data()
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", f"Failed to complete transfer: {e}")
        finally:
            session.close()

    def load_transfer_history(self):
        session = Session()
        try:
            transfers = session.query(FundTransfer).order_by(FundTransfer.id.desc()).limit(50).all()
            self.transfer_log_table.setRowCount(len(transfers))

            for i, t in enumerate(transfers):
                self.transfer_log_table.setRowHeight(i, 48)
                self.transfer_log_table.setItem(i, 0, QTableWidgetItem(str(t.id)))
                self.transfer_log_table.setItem(i, 1, QTableWidgetItem(t.date.strftime("%Y-%m-%d")))

                # Determine From Account
                if t.from_type == 'bank':
                    bank = t.from_account
                    if not bank and t.from_account_id:
                        bank = session.query(BankAccount).get(t.from_account_id)
                    from_str = f"{bank.bank_name} ({bank.account_name})" if bank and bank.account_name else (bank.bank_name if bank else f"Bank #{t.from_account_id}")
                else:
                    from_str = "Cash Drawer"

                # Determine To Account
                if t.to_type == 'bank':
                    bank = t.to_account
                    if not bank and t.to_account_id:
                        bank = session.query(BankAccount).get(t.to_account_id)
                    to_str = f"{bank.bank_name} ({bank.account_name})" if bank and bank.account_name else (bank.bank_name if bank else f"Bank #{t.to_account_id}")
                else:
                    to_str = "Cash Drawer"

                self.transfer_log_table.setItem(i, 2, QTableWidgetItem(from_str))
                self.transfer_log_table.setItem(i, 3, QTableWidgetItem(to_str))
                
                amt_item = QTableWidgetItem(f"₹{format_inr(t.amount)}")
                amt_item.setForeground(Qt.cyan)
                self.transfer_log_table.setItem(i, 4, amt_item)
                self.transfer_log_table.setItem(i, 5, QTableWidgetItem(t.remarks or "-"))

                btn_widget = QWidget()
                btn_widget.setStyleSheet("padding: 0px; margin: 0px; background: transparent;")
                btn_layout = QHBoxLayout(btn_widget)
                btn_layout.setContentsMargins(0, 0, 0, 0)
                btn_layout.setSpacing(6)
                btn_layout.setAlignment(Qt.AlignCenter)

                edit_btn = QPushButton("✏️")
                edit_btn.setFixedSize(34, 28)
                edit_btn.setStyleSheet("font-size: 13px;")
                edit_btn.setToolTip("Edit Fund Transfer")
                edit_btn.setCursor(Qt.PointingHandCursor)
                edit_btn.setProperty("class", "btn-action-icon-edit")
                edit_btn.clicked.connect(lambda checked, tid=t.id: self.edit_transfer(tid))
                btn_layout.addWidget(edit_btn)

                del_btn = QPushButton("🗑️")
                del_btn.setFixedSize(34, 28)
                del_btn.setStyleSheet("font-size: 13px;")
                del_btn.setToolTip("Delete/Revert Transfer")
                del_btn.setCursor(Qt.PointingHandCursor)
                del_btn.setProperty("class", "btn-action-icon-delete")
                del_btn.clicked.connect(lambda checked, tid=t.id: self.delete_transfer(tid))
                btn_layout.addWidget(del_btn)

                self.transfer_log_table.setCellWidget(i, 6, btn_widget)

        except Exception as e:
            print(f"Error loading transfers: {e}")
        finally:
            session.close()

    def edit_transfer(self, transfer_id: int):
        dlg = EditFundTransferDialog(transfer_id, parent=self)
        if dlg.exec() == QDialog.Accepted:
            self.refresh_data()

    def delete_transfer(self, transfer_id: int):
        confirm = QMessageBox.question(
            self, "Confirm Revert",
            "Are you sure you want to revert and delete this fund transfer?\nAccount balances will be adjusted back.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if confirm != QMessageBox.Yes:
            return

        session = Session()
        try:
            t = session.query(FundTransfer).get(transfer_id)
            if not t:
                return

            # Check if destination has enough funds to rollback
            if t.to_type == 'bank':
                to_bank = session.query(BankAccount).get(t.to_account_id)
                if to_bank:
                    if to_bank.balance < t.amount:
                        QMessageBox.warning(self, "Cannot Revert", f"Destination bank {to_bank.bank_name} has insufficient balance to revert.")
                        return
                    to_bank.balance -= t.amount
            else:
                cash_in = session.query(func.sum(CashTransaction.amount)).filter(CashTransaction.transaction_type == 'in').scalar() or 0.0
                cash_out = session.query(func.sum(CashTransaction.amount)).filter(CashTransaction.transaction_type == 'out').scalar() or 0.0
                if (cash_in - cash_out) < t.amount:
                    QMessageBox.warning(self, "Cannot Revert", "Cash drawer has insufficient balance to revert this deposit.")
                    return

            # Refund source
            if t.from_type == 'bank':
                from_bank = session.query(BankAccount).get(t.from_account_id)
                if from_bank:
                    from_bank.balance += t.amount

            # Delete related logs
            session.query(BankTransaction).filter_by(source_type='transfer', source_id=t.id).delete()
            session.query(CashTransaction).filter_by(source_type='transfer', source_id=t.id).delete()
            session.delete(t)
            session.commit()

            QMessageBox.information(self, "Success", "Transfer reverted successfully.")
            self.refresh_data()
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", f"Could not revert transfer: {e}")
        finally:
            session.close()

    # -------------------------------------------------------------------------
    # TAB 4 LOGIC: DIRECT EXPENSES & INCOME
    # -------------------------------------------------------------------------
    def populate_direct_combos(self):
        session = Session()
        try:
            banks = session.query(BankAccount).all()
            self.dir_bank_combo.clear()
            for b in banks:
                self.dir_bank_combo.addItem(f"{b.bank_name} ({b.account_name})", b.id)
        finally:
            session.close()

    def handle_direct_acc_type_change(self):
        is_bank = "Bank" in self.dir_acc_type.currentText()
        self.dir_bank_combo.setEnabled(is_bank)

    def save_direct_entry(self):
        amount = self.dir_amount.value()
        if amount <= 0:
            QMessageBox.warning(self, "Invalid Amount", "Please enter an amount greater than zero.")
            return

        tx_type_raw = self.dir_type.currentText()
        is_deposit = "Deposit" in tx_type_raw
        tx_type = "deposit" if is_deposit else "withdrawal"

        is_bank = "Bank" in self.dir_acc_type.currentText()
        account_type = "bank" if is_bank else "cash"
        bank_id = self.dir_bank_combo.currentData() if is_bank else None

        category = self.dir_category.currentText().strip()
        desc = self.dir_desc.text().strip()
        full_desc = f"[{category}] {desc}".strip()
        tx_date = self.dir_date.date().toPython()

        session = Session()
        try:
            if not is_deposit:
                # Check source balance for expense/withdrawal
                if is_bank:
                    bank = session.query(BankAccount).get(bank_id)
                    if not bank or bank.balance < amount:
                        avail = bank.balance if bank else 0.0
                        QMessageBox.warning(self, "Insufficient Funds", f"Insufficient balance in {bank.bank_name if bank else 'Bank'}.\nAvailable: ₹{format_inr(avail)}")
                        return
                else:
                    cash_in = session.query(func.sum(CashTransaction.amount)).filter(CashTransaction.transaction_type == 'in').scalar() or 0.0
                    cash_out = session.query(func.sum(CashTransaction.amount)).filter(CashTransaction.transaction_type == 'out').scalar() or 0.0
                    avail = cash_in - cash_out
                    if avail < amount:
                        QMessageBox.warning(self, "Insufficient Funds", f"Insufficient cash in drawer.\nAvailable: ₹{format_inr(avail)}")
                        return

            dt = DirectTransaction(
                date=tx_date,
                transaction_type=tx_type,
                account_type=account_type,
                bank_id=bank_id,
                amount=amount,
                description=full_desc
            )
            session.add(dt)
            session.flush()

            if is_bank:
                db_action = "deposit" if is_deposit else "withdrawal"
                bank = session.query(BankAccount).get(bank_id)
                tx = BankTransaction(
                    date=tx_date,
                    transaction_type=db_action,
                    account_id=bank_id,
                    amount=amount,
                    source_type='direct',
                    source_id=dt.id,
                    description=f"Direct {tx_type.capitalize()}: {full_desc}"
                )
                session.add(tx)
                if is_deposit:
                    bank.balance += amount
                else:
                    bank.balance -= amount
            else:
                db_action = "in" if is_deposit else "out"
                tx = CashTransaction(
                    date=tx_date,
                    transaction_type=db_action,
                    amount=amount,
                    source_type='direct',
                    source_id=dt.id,
                    description=f"Direct {tx_type.capitalize()}: {full_desc}"
                )
                session.add(tx)

            session.commit()
            QMessageBox.information(self, "Success", f"Direct entry of ₹{format_inr(amount)} recorded successfully.")
            self.dir_amount.setValue(0.0)
            self.dir_desc.clear()
            self.refresh_data()
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", f"Failed to save direct entry: {e}")
        finally:
            session.close()

    def load_direct_history(self):
        session = Session()
        try:
            records = session.query(DirectTransaction).order_by(DirectTransaction.id.desc()).limit(50).all()
            self.direct_log_table.setRowCount(len(records))

            for i, r in enumerate(records):
                self.direct_log_table.setRowHeight(i, 48)
                self.direct_log_table.setItem(i, 0, QTableWidgetItem(str(r.id)))
                self.direct_log_table.setItem(i, 1, QTableWidgetItem(r.date.strftime("%Y-%m-%d")))

                type_item = QTableWidgetItem(r.transaction_type.capitalize())
                if r.transaction_type == 'deposit':
                    type_item.setForeground(Qt.green)
                else:
                    type_item.setForeground(Qt.red)
                self.direct_log_table.setItem(i, 2, type_item)

                if r.account_type == 'bank':
                    bank = r.bank_account
                    if not bank and r.bank_id:
                        bank = session.query(BankAccount).get(r.bank_id)
                    acc_str = f"{bank.bank_name} ({bank.account_name})" if bank and bank.account_name else (bank.bank_name if bank else f"Bank #{r.bank_id}")
                else:
                    acc_str = "Cash Drawer"

                self.direct_log_table.setItem(i, 3, QTableWidgetItem(acc_str))
                self.direct_log_table.setItem(i, 4, QTableWidgetItem(f"₹{format_inr(r.amount)}"))
                self.direct_log_table.setItem(i, 5, QTableWidgetItem(r.description or "-"))

                btn_widget = QWidget()
                btn_widget.setStyleSheet("padding: 0px; margin: 0px; background: transparent;")
                btn_layout = QHBoxLayout(btn_widget)
                btn_layout.setContentsMargins(0, 0, 0, 0)
                btn_layout.setSpacing(6)
                btn_layout.setAlignment(Qt.AlignCenter)

                edit_btn = QPushButton("✏️")
                edit_btn.setFixedSize(34, 28)
                edit_btn.setStyleSheet("font-size: 13px;")
                edit_btn.setToolTip("Edit Entry")
                edit_btn.setCursor(Qt.PointingHandCursor)
                edit_btn.setProperty("class", "btn-action-icon-edit")
                edit_btn.clicked.connect(lambda checked, rid=r.id: self.edit_direct_entry(rid))
                btn_layout.addWidget(edit_btn)

                del_btn = QPushButton("🗑️")
                del_btn.setFixedSize(34, 28)
                del_btn.setStyleSheet("font-size: 13px;")
                del_btn.setToolTip("Delete/Revert Entry")
                del_btn.setCursor(Qt.PointingHandCursor)
                del_btn.setProperty("class", "btn-action-icon-delete")
                del_btn.clicked.connect(lambda checked, rid=r.id: self.delete_direct_entry(rid))
                btn_layout.addWidget(del_btn)

                self.direct_log_table.setCellWidget(i, 6, btn_widget)

        except Exception as e:
            print(f"Error loading direct records: {e}")
        finally:
            session.close()

    def edit_direct_entry(self, entry_id: int):
        dlg = EditDirectTransactionDialog(entry_id, parent=self)
        if dlg.exec() == QDialog.Accepted:
            self.refresh_data()

    def delete_direct_entry(self, entry_id: int):
        confirm = QMessageBox.question(
            self, "Confirm Revert",
            "Are you sure you want to delete and revert this direct entry?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if confirm != QMessageBox.Yes:
            return

        session = Session()
        try:
            dt = session.query(DirectTransaction).get(entry_id)
            if not dt:
                return

            if dt.account_type == "bank":
                bank = session.query(BankAccount).get(dt.bank_id)
                if bank:
                    if dt.transaction_type == "deposit":
                        if bank.balance < dt.amount:
                            QMessageBox.warning(self, "Cannot Revert", f"Insufficient balance in {bank.bank_name} to revert deposit.")
                            return
                        bank.balance -= dt.amount
                    else:
                        bank.balance += dt.amount
                session.query(BankTransaction).filter_by(source_type='direct', source_id=dt.id).delete()
            else:
                if dt.transaction_type == "deposit":
                    cash_in = session.query(func.sum(CashTransaction.amount)).filter(CashTransaction.transaction_type == 'in').scalar() or 0.0
                    cash_out = session.query(func.sum(CashTransaction.amount)).filter(CashTransaction.transaction_type == 'out').scalar() or 0.0
                    if (cash_in - cash_out) < dt.amount:
                        QMessageBox.warning(self, "Cannot Revert", "Insufficient cash in drawer to revert deposit.")
                        return
                session.query(CashTransaction).filter_by(source_type='direct', source_id=dt.id).delete()

            session.delete(dt)
            session.commit()
            QMessageBox.information(self, "Success", "Entry deleted and balance reverted successfully.")
            self.refresh_data()
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", f"Failed to delete entry: {e}")
        finally:
            session.close()

    # -------------------------------------------------------------------------
    # QUICK MODAL HELPERS (FROM CASH DRAWER TAB)
    # -------------------------------------------------------------------------
    def open_quick_cash_in(self):
        self.tabs.setCurrentIndex(self.tabs.indexOf(self.direct_tab))
        self.dir_type.setCurrentIndex(1) # Deposit / Income
        self.dir_acc_type.setCurrentIndex(0) # Cash Drawer
        self.dir_amount.setFocus()

    def open_quick_cash_out(self):
        self.tabs.setCurrentIndex(self.tabs.indexOf(self.direct_tab))
        self.dir_type.setCurrentIndex(0) # Withdrawal / Expense
        self.dir_acc_type.setCurrentIndex(0) # Cash Drawer
        self.dir_amount.setFocus()

