import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QLineEdit, QComboBox, 
    QDateEdit, QDoubleSpinBox, QPushButton, QTableWidget, QTableWidgetItem, 
    QHeaderView, QMessageBox, QFrame, QFormLayout, QTabWidget, QDialog, 
    QDialogButtonBox, QSpacerItem, QSizePolicy
)
from PySide6.QtCore import Qt, QDate, QTimer
from PySide6.QtGui import QDoubleValidator
from sqlalchemy import func

from database import Session
from models import (
    BankAccount, BankTransaction, CashTransaction, 
    FundTransfer, DirectTransaction
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
                self.to_combo.addItem(f"{b_name} [Bal: ₹{bal:,.2f}]", ("bank", b_id))

        elif "Bank to Cash" in mode:
            self.from_combo.setEnabled(True)
            for b_id, b_name, bal in getattr(self, 'banks_cache', []):
                self.from_combo.addItem(f"{b_name} [Bal: ₹{bal:,.2f}]", ("bank", b_id))
            self.to_combo.addItem("Cash Drawer", ("cash", None))
            self.to_combo.setEnabled(False)

        else:
            self.from_combo.setEnabled(True)
            self.to_combo.setEnabled(True)
            for b_id, b_name, bal in getattr(self, 'banks_cache', []):
                self.from_combo.addItem(f"{b_name} [Bal: ₹{bal:,.2f}]", ("bank", b_id))
                self.to_combo.addItem(f"{b_name} [Bal: ₹{bal:,.2f}]", ("bank", b_id))

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
                    QMessageBox.warning(self, "Insufficient Funds", f"Insufficient balance in source bank.\nAvailable: ₹{avail:,.2f}")
                    session.rollback()
                    return
                from_name = f"{new_from_bank.bank_name} ({new_from_bank.account_name})"
            else:
                cash_in = session.query(func.sum(CashTransaction.amount)).filter(CashTransaction.transaction_type == 'in').scalar() or 0.0
                cash_out = session.query(func.sum(CashTransaction.amount)).filter(CashTransaction.transaction_type == 'out').scalar() or 0.0
                cash_avail = cash_in - cash_out
                if cash_avail < new_amount:
                    QMessageBox.warning(self, "Insufficient Funds", f"Insufficient cash in drawer.\nAvailable: ₹{cash_avail:,.2f}")
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
                self.bank_combo.addItem(f"{b.bank_name} ({b.account_name}) [Bal: ₹{b.balance:,.2f}]", b.id)

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
                        QMessageBox.warning(self, "Insufficient Funds", f"Insufficient balance in {new_bank.bank_name if new_bank else 'Bank'}.\nAvailable: ₹{avail:,.2f}")
                        session.rollback()
                        return
                else:
                    cash_in = session.query(func.sum(CashTransaction.amount)).filter(CashTransaction.transaction_type == 'in').scalar() or 0.0
                    cash_out = session.query(func.sum(CashTransaction.amount)).filter(CashTransaction.transaction_type == 'out').scalar() or 0.0
                    cash_avail = cash_in - cash_out
                    if cash_avail < new_amount:
                        QMessageBox.warning(self, "Insufficient Funds", f"Insufficient cash in drawer.\nAvailable: ₹{cash_avail:,.2f}")
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

        # 1. Cash Drawer Tab
        self.cash_tab = QWidget()
        self.setup_cash_tab()
        self.tabs.addTab(self.cash_tab, f"💵 {tr('Cash Drawer')}")

        # 2. Bank Accounts & Passbook Tab
        self.bank_tab = QWidget()
        self.setup_bank_tab()
        self.tabs.addTab(self.bank_tab, f"🏛️ {tr('Bank Accounts & Passbook')}")

        # 3. Fund Transfer Tab
        self.transfer_tab = QWidget()
        self.setup_transfer_tab()
        self.tabs.addTab(self.transfer_tab, f"🔄 {tr('Fund Transfer')}")

        # 4. Direct Expenses & Income Tab
        self.direct_tab = QWidget()
        self.setup_direct_tab()
        self.tabs.addTab(self.direct_tab, f"📝 {tr('Daily Expenses & Direct Income')}")

        layout.addWidget(self.tabs)

    def retranslate_ui(self):
        """Updates tab headers and labels when active language changes."""
        self.tabs.setTabText(0, f"💵 {tr('Cash Drawer')}")
        self.tabs.setTabText(1, f"🏛️ {tr('Bank Accounts & Passbook')}")
        self.tabs.setTabText(2, f"🔄 {tr('Fund Transfer')}")
        self.tabs.setTabText(3, f"📝 {tr('Daily Expenses & Direct Income')}")

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
        if hasattr(self, 'direct_log_table'):
            self.direct_log_table.setHorizontalHeaderLabels([
                tr("ID"), tr("Date"), tr("Type"), tr("Account"), f"{tr('Amount')} (₹)", tr("Description"), tr("Action")
            ])

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
        self.card_cash_in_hand = self._create_stat_card("Cash in Hand", "₹0.00", "#10b981")
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

        lbl_filter = QLabel("Filter Period:")
        lbl_filter.setStyleSheet("font-weight: bold; color: #94a3b8;")
        filter_bar.addWidget(lbl_filter)

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
        self.btn_quick_in.setStyleSheet("background-color: #10b981; color: #ffffff; font-weight: bold; padding: 6px 12px;")
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
    # TAB 2: BANK ACCOUNTS & PASSBOOK (வங்கிக் கணக்குகள்)
    # -------------------------------------------------------------------------
    def setup_bank_tab(self):
        layout = QVBoxLayout(self.bank_tab)
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

        # Bank Accounts Management Bar
        bank_mgmt_frame = QFrame()
        bank_mgmt_frame.setProperty("class", "CardFrame")
        bm_layout = QVBoxLayout(bank_mgmt_frame)
        bm_layout.setContentsMargins(12, 12, 12, 12)
        bm_layout.setSpacing(10)

        bm_top = QHBoxLayout()
        bm_title = QLabel("Bank Accounts Overview")
        bm_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #ffffff;")
        bm_top.addWidget(bm_title)
        bm_top.addStretch()

        self.btn_add_bank = QPushButton("+ Add Bank Account")
        self.btn_add_bank.setProperty("class", "btn-success")
        self.btn_add_bank.clicked.connect(self.handle_add_bank)
        bm_top.addWidget(self.btn_add_bank)

        self.btn_edit_bank = QPushButton("Edit Bank")
        self.btn_edit_bank.setProperty("class", "btn-secondary")
        self.btn_edit_bank.clicked.connect(self.handle_edit_bank)
        bm_top.addWidget(self.btn_edit_bank)

        bm_layout.addLayout(bm_top)

        # Bank Accounts Table
        self.bank_acc_table = QTableWidget()
        self.bank_acc_table.setColumnCount(6)
        self.bank_acc_table.setHorizontalHeaderLabels([
            "ID", "Bank Name", "Account Number", "Account Display Name", "Account Type", "Current Balance"
        ])
        self.bank_acc_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.bank_acc_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.bank_acc_table.verticalHeader().setVisible(False)
        self.bank_acc_table.setFixedHeight(140)
        self.bank_acc_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.bank_acc_table.setSelectionMode(QTableWidget.SingleSelection)
        self.bank_acc_table.doubleClicked.connect(self.handle_edit_bank)
        bm_layout.addWidget(self.bank_acc_table)

        layout.addWidget(bank_mgmt_frame)

        # Passbook Filter & Section
        passbook_title = QLabel("Bank Passbook Transactions")
        passbook_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #ffffff; margin-top: 5px;")
        layout.addWidget(passbook_title)

        pb_filter_bar = QHBoxLayout()
        pb_filter_bar.setSpacing(10)

        lbl_bank_sel = QLabel("Filter by Bank:")
        lbl_bank_sel.setStyleSheet("font-weight: bold; color: #94a3b8;")
        pb_filter_bar.addWidget(lbl_bank_sel)

        self.pb_bank_filter = QComboBox()
        self.pb_bank_filter.currentIndexChanged.connect(self.load_bank_passbook)
        pb_filter_bar.addWidget(self.pb_bank_filter, 1)

        lbl_pb_period = QLabel("Period:")
        lbl_pb_period.setStyleSheet("font-weight: bold; color: #94a3b8;")
        pb_filter_bar.addWidget(lbl_pb_period)

        self.pb_period_combo = QComboBox()
        self.pb_period_combo.addItems(["All Transactions", "Today", "Yesterday", "This Week", "This Month"])
        self.pb_period_combo.currentIndexChanged.connect(self.load_bank_passbook)
        pb_filter_bar.addWidget(self.pb_period_combo)

        self.pb_search = QLineEdit()
        self.pb_search.setPlaceholderText("Search bank passbook...")
        self.pb_search.textChanged.connect(self.load_bank_passbook)
        pb_filter_bar.addWidget(self.pb_search, 2)

        layout.addLayout(pb_filter_bar)

        # Bank Passbook Table
        self.bank_tx_table = QTableWidget()
        self.bank_tx_table.setColumnCount(6)
        self.bank_tx_table.setHorizontalHeaderLabels([
            "Date", "Bank Account", "Description", "Source / Ref", "Deposit (+₹)", "Withdrawal (-₹)"
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
        self.lbl_exec_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #ffffff;")
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
        self.lbl_hist_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #ffffff;")
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

        lbl_title = QLabel("Record Expense or Direct Income")
        lbl_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #ffffff; margin-bottom: 8px;")
        form_layout.addRow(lbl_title)

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

        self.btn_save_direct = QPushButton("Save Entry")
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

        log_title = QLabel("Expenses & Direct Transactions Log")
        log_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #ffffff; margin-bottom: 10px;")
        log_layout.addWidget(log_title)

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
        self.load_cash_metrics_and_ledger()
        self.load_bank_accounts_and_passbook()
        self.populate_transfer_combos()
        self.load_transfer_history()
        self.populate_direct_combos()
        self.load_direct_history()

    def _create_stat_card(self, title: str, initial_value: str, color_hex: str) -> QFrame:
        card = QFrame()
        card.setProperty("class", "CardFrame")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(15, 12, 15, 12)
        card_layout.setSpacing(4)

        lbl_t = QLabel(tr(title))
        lbl_t.setStyleSheet("font-size: 12px; color: #94a3b8; font-weight: bold;")
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

            self.card_cash_in_hand.value_label.setText(f"₹{cash_in_hand:,.2f}")

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

            self.card_today_in.value_label.setText(f"+ ₹{today_in:,.2f}")
            self.card_today_out.value_label.setText(f"- ₹{today_out:,.2f}")

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
                    in_item = QTableWidgetItem(f"+ ₹{tx.amount:,.2f}")
                    in_item.setForeground(Qt.green)
                    out_item = QTableWidgetItem("-")
                else:
                    in_item = QTableWidgetItem("-")
                    out_item = QTableWidgetItem(f"- ₹{tx.amount:,.2f}")
                    out_item.setForeground(Qt.red)

                self.cash_table.setItem(i, 3, in_item)
                self.cash_table.setItem(i, 4, out_item)
        except Exception as e:
            print(f"Error loading cash ledger: {e}")
        finally:
            session.close()

    def load_bank_accounts_and_passbook(self):
        session = Session()
        try:
            banks = session.query(BankAccount).all()
            total_bal = sum(b.balance for b in banks)

            self.card_bank_balance.value_label.setText(f"₹{total_bal:,.2f}")
            self.card_bank_count.value_label.setText(str(len(banks)))

            # Populate Accounts Table
            self.bank_acc_table.setRowCount(len(banks))
            for i, a in enumerate(banks):
                self.bank_acc_table.setItem(i, 0, QTableWidgetItem(str(a.id)))
                self.bank_acc_table.setItem(i, 1, QTableWidgetItem(a.bank_name))
                self.bank_acc_table.setItem(i, 2, QTableWidgetItem(a.account_number or ""))
                self.bank_acc_table.setItem(i, 3, QTableWidgetItem(a.account_name))
                self.bank_acc_table.setItem(i, 4, QTableWidgetItem(a.account_type or "Current"))

                bal_item = QTableWidgetItem(f"₹{a.balance:,.2f}")
                if a.balance < 1000.0:
                    bal_item.setForeground(Qt.red)
                else:
                    bal_item.setForeground(Qt.cyan)
                self.bank_acc_table.setItem(i, 5, bal_item)

            # Update passbook bank filter combo
            cur_bank_id = self.pb_bank_filter.currentData()
            self.pb_bank_filter.blockSignals(True)
            self.pb_bank_filter.clear()
            self.pb_bank_filter.addItem("All Registered Banks", -1)
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

        self.load_bank_passbook()

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
                    dep_item = QTableWidgetItem(f"+ ₹{tx.amount:,.2f}")
                    dep_item.setForeground(Qt.green)
                    with_item = QTableWidgetItem("-")
                else:
                    dep_item = QTableWidgetItem("-")
                    with_item = QTableWidgetItem(f"- ₹{tx.amount:,.2f}")
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
            QMessageBox.information(self, "Select Account", "Please select a bank account from the table to edit.")
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
                self.tr_to_combo.addItem(f"{b_name} [Bal: ₹{bal:,.2f}]", ("bank", b_id))

        elif "Bank to Cash" in mode:
            self.tr_from_combo.setEnabled(True)
            for b_id, b_name, bal in getattr(self, 'tr_banks_cache', []):
                self.tr_from_combo.addItem(f"{b_name} [Bal: ₹{bal:,.2f}]", ("bank", b_id))
            self.tr_to_combo.addItem("Cash Drawer", ("cash", None))
            self.tr_to_combo.setEnabled(False)

        else: # Bank to Bank
            self.tr_from_combo.setEnabled(True)
            self.tr_to_combo.setEnabled(True)
            for b_id, b_name, bal in getattr(self, 'tr_banks_cache', []):
                self.tr_from_combo.addItem(f"{b_name} [Bal: ₹{bal:,.2f}]", ("bank", b_id))
                self.tr_to_combo.addItem(f"{b_name} [Bal: ₹{bal:,.2f}]", ("bank", b_id))

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
                    QMessageBox.warning(self, "Insufficient Funds", f"Insufficient balance in source bank.\nAvailable: ₹{available:,.2f}")
                    return
                from_name = f"{bank_from.bank_name} ({bank_from.account_name})"
            else:
                cash_in = session.query(func.sum(CashTransaction.amount)).filter(CashTransaction.transaction_type == 'in').scalar() or 0.0
                cash_out = session.query(func.sum(CashTransaction.amount)).filter(CashTransaction.transaction_type == 'out').scalar() or 0.0
                cash_avail = cash_in - cash_out
                if cash_avail < amount:
                    QMessageBox.warning(self, "Insufficient Funds", f"Insufficient cash in drawer.\nAvailable: ₹{cash_avail:,.2f}")
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
            QMessageBox.information(self, "Success", f"Transfer of ₹{amount:,.2f} completed successfully.")
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
                
                amt_item = QTableWidgetItem(f"₹{t.amount:,.2f}")
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
                        QMessageBox.warning(self, "Insufficient Funds", f"Insufficient balance in {bank.bank_name if bank else 'Bank'}.\nAvailable: ₹{avail:,.2f}")
                        return
                else:
                    cash_in = session.query(func.sum(CashTransaction.amount)).filter(CashTransaction.transaction_type == 'in').scalar() or 0.0
                    cash_out = session.query(func.sum(CashTransaction.amount)).filter(CashTransaction.transaction_type == 'out').scalar() or 0.0
                    avail = cash_in - cash_out
                    if avail < amount:
                        QMessageBox.warning(self, "Insufficient Funds", f"Insufficient cash in drawer.\nAvailable: ₹{avail:,.2f}")
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
            QMessageBox.information(self, "Success", f"Direct entry of ₹{amount:,.2f} recorded successfully.")
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
                self.direct_log_table.setItem(i, 4, QTableWidgetItem(f"₹{r.amount:,.2f}"))
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
        self.tabs.setCurrentIndex(3) # Switch to Direct tab
        self.dir_type.setCurrentIndex(1) # Deposit / Income
        self.dir_acc_type.setCurrentIndex(0) # Cash Drawer
        self.dir_amount.setFocus()

    def open_quick_cash_out(self):
        self.tabs.setCurrentIndex(3) # Switch to Direct tab
        self.dir_type.setCurrentIndex(0) # Withdrawal / Expense
        self.dir_acc_type.setCurrentIndex(0) # Cash Drawer
        self.dir_amount.setFocus()

