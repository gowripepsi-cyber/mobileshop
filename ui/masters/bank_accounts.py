from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, 
                             QPushButton, QLineEdit, QLabel, QDialog, QFormLayout, QMessageBox, QHeaderView,
                             QComboBox)
from PySide6.QtCore import Qt
from database import Session
from models import BankAccount, BankTransaction

class BankAccountDialog(QDialog):
    def __init__(self, account=None, parent=None):
        super().__init__(parent)
        self.account = account
        self.setWindowTitle("Edit Bank Account" if account else "Add Bank Account")
        self.setFixedSize(400, 320)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        self.bank_name_input = QLineEdit()
        self.account_number_input = QLineEdit()
        self.account_name_input = QLineEdit()
        
        self.account_type_combo = QComboBox()
        self.account_type_combo.addItems(["Saving", "Current"])
        # Default to Current as per database column default
        self.account_type_combo.setCurrentText("Current")

        self.balance_input = QLineEdit()
        self.balance_input.setText("0.00")

        form_layout.addRow("Bank Name *:", self.bank_name_input)
        form_layout.addRow("Account Number:", self.account_number_input)
        form_layout.addRow("Account Display Name *:", self.account_name_input)
        form_layout.addRow("Account Type:", self.account_type_combo)
        form_layout.addRow("Opening Balance (₹):", self.balance_input)

        layout.addLayout(form_layout)

        # Buttons
        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self.handle_save)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setProperty("class", "btn-secondary")
        self.cancel_btn.clicked.connect(self.reject)

        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)

        # Populate if editing
        if self.account:
            self.bank_name_input.setText(self.account.bank_name)
            self.account_number_input.setText(self.account.account_number or "")
            self.account_name_input.setText(self.account.account_name)
            
            idx = self.account_type_combo.findText(self.account.account_type or "Current")
            if idx >= 0:
                self.account_type_combo.setCurrentIndex(idx)
                
            self.balance_input.setText(str(self.account.balance))
            self.balance_input.setEnabled(False) # Prevent modifying opening balance directly after creation

    def handle_save(self):
        bank_name = self.bank_name_input.text().strip()
        account_number = self.account_number_input.text().strip() or None
        account_name = self.account_name_input.text().strip()
        account_type = self.account_type_combo.currentText()

        if not bank_name or not account_name:
            QMessageBox.warning(self, "Validation Error", "Please fill in Bank Name and Account Name.")
            return

        try:
            balance = float(self.balance_input.text())
        except ValueError:
            QMessageBox.warning(self, "Validation Error", "Opening balance must be a number.")
            return

        session = Session()
        try:
            if self.account:
                acc = session.query(BankAccount).get(self.account.id)
                acc.bank_name = bank_name
                acc.account_number = account_number
                acc.account_name = account_name
                acc.account_type = account_type
            else:
                new_acc = BankAccount(
                    bank_name=bank_name,
                    account_number=account_number,
                    account_name=account_name,
                    account_type=account_type,
                    balance=balance
                )
                session.add(new_acc)
                session.commit() # Get new account ID
                
                # If opening balance is > 0, log a transaction
                if balance > 0:
                    tx = BankTransaction(
                        account_id=new_acc.id,
                        transaction_type='deposit',
                        amount=balance,
                        source_type='direct',
                        description="Opening Balance"
                    )
                    session.add(tx)

            session.commit()
            self.accept()
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", f"Could not save bank account: {e}")
        finally:
            session.close()


class BankAccountsView(QWidget):
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
        self.search_input.setPlaceholderText("Search bank accounts...")
        self.search_input.textChanged.connect(self.refresh_data)
        top_bar.addWidget(self.search_input, 4)

        self.add_btn = QPushButton("Add Account")
        self.add_btn.clicked.connect(self.add_account)
        top_bar.addWidget(self.add_btn, 1)

        self.edit_btn = QPushButton("Edit Account")
        self.edit_btn.setProperty("class", "btn-secondary")
        self.edit_btn.clicked.connect(self.edit_account)
        top_bar.addWidget(self.edit_btn, 1)

        self.delete_btn = QPushButton("Delete")
        self.delete_btn.setProperty("class", "btn-danger")
        self.delete_btn.clicked.connect(self.delete_account)
        top_bar.addWidget(self.delete_btn, 1)

        layout.addLayout(top_bar)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "ID", "Bank Name", "Account Number", "Account Display Name", "Account Type", "Current Balance"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.doubleClicked.connect(self.edit_account)
        layout.addWidget(self.table)

    def refresh_data(self):
        search_txt = self.search_input.text().strip()
        session = Session()
        try:
            query = session.query(BankAccount)
            if search_txt:
                query = query.filter(
                    BankAccount.bank_name.like(f"%{search_txt}%") |
                    BankAccount.account_name.like(f"%{search_txt}%") |
                    BankAccount.account_number.like(f"%{search_txt}%")
                )
            accounts = query.all()

            self.table.setRowCount(len(accounts))
            for i, a in enumerate(accounts):
                self.table.setItem(i, 0, QTableWidgetItem(str(a.id)))
                self.table.setItem(i, 1, QTableWidgetItem(a.bank_name))
                self.table.setItem(i, 2, QTableWidgetItem(a.account_number or ""))
                self.table.setItem(i, 3, QTableWidgetItem(a.account_name))
                self.table.setItem(i, 4, QTableWidgetItem(a.account_type or "Current"))
                
                bal_item = QTableWidgetItem(f"₹{a.balance:,.2f}")
                if a.balance < 1000.0:
                    bal_item.setForeground(Qt.red)
                self.table.setItem(i, 5, bal_item)

        except Exception as e:
            print(f"Error loading bank accounts: {e}")
        finally:
            session.close()

    def get_selected_account_id(self):
        selected = self.table.selectedItems()
        if not selected:
            return None
        return int(self.table.item(selected[0].row(), 0).text())

    def add_account(self):
        dlg = BankAccountDialog(parent=self)
        if dlg.exec() == QDialog.Accepted:
            self.refresh_data()

    def edit_account(self):
        acc_id = self.get_selected_account_id()
        if acc_id is None:
            QMessageBox.information(self, "No Selection", "Please select a bank account to edit.")
            return

        session = Session()
        try:
            acc = session.query(BankAccount).get(acc_id)
            if acc:
                dlg = BankAccountDialog(account=acc, parent=self)
                if dlg.exec() == QDialog.Accepted:
                    self.refresh_data()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not load account details: {e}")
        finally:
            session.close()

    def delete_account(self):
        acc_id = self.get_selected_account_id()
        if acc_id is None:
            QMessageBox.information(self, "No Selection", "Please select an account to delete.")
            return

        confirm = QMessageBox.question(
            self, "Confirm Delete", "Are you sure you want to delete this bank account? This might result in loss of transaction ledgers linked to this bank.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if confirm == QMessageBox.Yes:
            session = Session()
            try:
                acc = session.query(BankAccount).get(acc_id)
                if acc:
                    # Clear bank transactions first if database constraints are set
                    session.query(BankTransaction).filter_by(account_id=acc.id).delete()
                    session.delete(acc)
                    session.commit()
                    self.refresh_data()
            except Exception as e:
                session.rollback()
                QMessageBox.critical(self, "Error", f"Could not delete bank account: {e}")
            finally:
                session.close()
