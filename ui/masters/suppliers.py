from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, 
                             QPushButton, QLineEdit, QLabel, QDialog, QFormLayout, QMessageBox, QHeaderView)
from PySide6.QtCore import Qt
from database import Session
from models import Supplier

class SupplierDialog(QDialog):
    def __init__(self, supplier=None, parent=None):
        super().__init__(parent)
        self.supplier = supplier
        self.setWindowTitle("Edit Supplier" if supplier else "Add New Supplier")
        self.setFixedSize(450, 420)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        self.name_input = QLineEdit()
        self.mobile_input = QLineEdit()
        self.address_input = QLineEdit()
        
        self.bank_name_input = QLineEdit()
        self.account_number_input = QLineEdit()
        self.ifsc_code_input = QLineEdit()
        self.upi_id_input = QLineEdit()
        
        self.outstanding_input = QLineEdit()
        self.outstanding_input.setText("0.00")

        form_layout.addRow("Supplier Name *:", self.name_input)
        form_layout.addRow("Contact Number *:", self.mobile_input)
        form_layout.addRow("Address:", self.address_input)
        form_layout.addRow("Bank Name:", self.bank_name_input)
        form_layout.addRow("Account Number:", self.account_number_input)
        form_layout.addRow("IFSC Code:", self.ifsc_code_input)
        form_layout.addRow("UPI ID:", self.upi_id_input)
        form_layout.addRow("Outstanding Balance (₹):", self.outstanding_input)

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
        if self.supplier:
            self.name_input.setText(self.supplier.name)
            self.mobile_input.setText(self.supplier.mobile)
            self.address_input.setText(self.supplier.address or "")
            self.bank_name_input.setText(self.supplier.bank_name or "")
            self.account_number_input.setText(self.supplier.account_number or "")
            self.ifsc_code_input.setText(self.supplier.ifsc_code or "")
            self.upi_id_input.setText(self.supplier.upi_id or "")
            self.outstanding_input.setText(str(self.supplier.outstanding_balance))

    def handle_save(self):
        name = self.name_input.text().strip()
        mobile = self.mobile_input.text().strip()
        address = self.address_input.text().strip() or None
        bank_name = self.bank_name_input.text().strip() or None
        account_number = self.account_number_input.text().strip() or None
        ifsc_code = self.ifsc_code_input.text().strip() or None
        upi_id = self.upi_id_input.text().strip() or None

        if not name or not mobile:
            QMessageBox.warning(self, "Validation Error", "Please fill in Name and Contact Number.")
            return

        try:
            outstanding = float(self.outstanding_input.text())
        except ValueError:
            QMessageBox.warning(self, "Validation Error", "Outstanding balance must be a number.")
            return

        session = Session()
        try:
            if self.supplier:
                supp = session.query(Supplier).get(self.supplier.id)
                supp.name = name
                supp.mobile = mobile
                supp.address = address
                supp.bank_name = bank_name
                supp.account_number = account_number
                supp.ifsc_code = ifsc_code
                supp.upi_id = upi_id
                supp.outstanding_balance = outstanding
            else:
                new_supp = Supplier(
                    name=name, mobile=mobile, address=address,
                    bank_name=bank_name, account_number=account_number,
                    ifsc_code=ifsc_code, upi_id=upi_id,
                    outstanding_balance=outstanding
                )
                session.add(new_supp)

            session.commit()
            self.accept()
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", f"Could not save supplier: {e}")
        finally:
            session.close()


class SuppliersView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Top search and buttons
        top_bar = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search suppliers by name or contact number...")
        self.search_input.textChanged.connect(self.refresh_data)
        top_bar.addWidget(self.search_input, 4)

        self.add_btn = QPushButton("Add Supplier")
        self.add_btn.clicked.connect(self.add_supplier)
        top_bar.addWidget(self.add_btn, 1)

        self.edit_btn = QPushButton("Edit Supplier")
        self.edit_btn.setProperty("class", "btn-secondary")
        self.edit_btn.clicked.connect(self.edit_supplier)
        top_bar.addWidget(self.edit_btn, 1)

        self.ledger_btn = QPushButton("View Ledger")
        self.ledger_btn.setProperty("class", "btn-warning")
        self.ledger_btn.clicked.connect(self.view_ledger)
        top_bar.addWidget(self.ledger_btn, 1)

        self.delete_btn = QPushButton("Delete")
        self.delete_btn.setProperty("class", "btn-danger")
        self.delete_btn.clicked.connect(self.delete_supplier)
        top_bar.addWidget(self.delete_btn, 1)

        layout.addLayout(top_bar)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "ID", "Supplier Name", "Contact Number", "Address", "Bank Details", "UPI ID", "Outstanding Balance"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.doubleClicked.connect(self.edit_supplier)
        layout.addWidget(self.table)

    def refresh_data(self):
        search_txt = self.search_input.text().strip()
        session = Session()
        try:
            query = session.query(Supplier)
            if search_txt:
                query = query.filter(
                    Supplier.name.like(f"%{search_txt}%") |
                    Supplier.mobile.like(f"%{search_txt}%")
                )
            suppliers = query.all()

            self.table.setRowCount(len(suppliers))
            for i, s in enumerate(suppliers):
                self.table.setItem(i, 0, QTableWidgetItem(str(s.id)))
                self.table.setItem(i, 1, QTableWidgetItem(s.name))
                self.table.setItem(i, 2, QTableWidgetItem(s.mobile))
                self.table.setItem(i, 3, QTableWidgetItem(s.address or "-"))
                
                # Bank Details
                bank_info = "-"
                if s.bank_name or s.account_number:
                    bank_name = s.bank_name or "N/A"
                    acc_num = s.account_number or "N/A"
                    ifsc = f" (IFSC: {s.ifsc_code})" if s.ifsc_code else ""
                    bank_info = f"{bank_name} - {acc_num}{ifsc}"
                self.table.setItem(i, 4, QTableWidgetItem(bank_info))
                
                # UPI ID
                self.table.setItem(i, 5, QTableWidgetItem(s.upi_id or "-"))
                
                # Outstanding
                bal_item = QTableWidgetItem(f"₹{s.outstanding_balance:,.2f}")
                if s.outstanding_balance > 0:
                    bal_item.setForeground(Qt.red)
                self.table.setItem(i, 6, bal_item)

        except Exception as e:
            print(f"Error loading suppliers: {e}")
        finally:
            session.close()

    def get_selected_supplier_id(self):
        selected = self.table.selectedItems()
        if not selected:
            return None
        return int(self.table.item(selected[0].row(), 0).text())

    def add_supplier(self):
        dlg = SupplierDialog(parent=self)
        if dlg.exec() == QDialog.Accepted:
            self.refresh_data()

    def edit_supplier(self):
        supp_id = self.get_selected_supplier_id()
        if supp_id is None:
            QMessageBox.information(self, "No Selection", "Please select a supplier to edit.")
            return

        session = Session()
        try:
            supp = session.query(Supplier).get(supp_id)
            if supp:
                dlg = SupplierDialog(supplier=supp, parent=self)
                if dlg.exec() == QDialog.Accepted:
                    self.refresh_data()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not load supplier details: {e}")
        finally:
            session.close()

    def delete_supplier(self):
        supp_id = self.get_selected_supplier_id()
        if supp_id is None:
            QMessageBox.information(self, "No Selection", "Please select a supplier to delete.")
            return

        confirm = QMessageBox.question(
            self, "Confirm Delete", "Are you sure you want to delete this supplier? This might affect invoice and outstanding balance records.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if confirm == QMessageBox.Yes:
            session = Session()
            try:
                supp = session.query(Supplier).get(supp_id)
                if supp:
                    session.delete(supp)
                    session.commit()
                    self.refresh_data()
            except Exception as e:
                session.rollback()
                QMessageBox.critical(self, "Error", f"Could not delete supplier: {e}")
            finally:
                session.close()

    def view_ledger(self):
        supp_id = self.get_selected_supplier_id()
        if supp_id is None:
            QMessageBox.information(self, "No Selection", "Please select a supplier to view ledger.")
            return

        session = Session()
        try:
            supp = session.query(Supplier).get(supp_id)
            if supp:
                from ui.masters.ledger_dialog import LedgerBreakupDialog
                dlg = LedgerBreakupDialog(party_type='supplier', party_id=supp.id, party_name=supp.name, parent=self)
                dlg.exec()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not load supplier ledger: {e}")
        finally:
            session.close()
