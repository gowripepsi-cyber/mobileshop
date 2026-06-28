from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, 
                             QPushButton, QLineEdit, QLabel, QDialog, QFormLayout, QMessageBox, QHeaderView)
from PySide6.QtCore import Qt
from database import Session
from models import Customer

class CustomerDialog(QDialog):
    def __init__(self, customer=None, initial_name="", parent=None):
        super().__init__(parent)
        self.customer = customer
        self.initial_name = initial_name
        self.setWindowTitle("Edit Customer" if customer else "Add New Customer")
        self.setFixedSize(400, 360)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        self.name_input = QLineEdit()
        self.mobile_input = QLineEdit()
        self.address_input = QLineEdit()
        self.gst_input = QLineEdit()
        self.outstanding_input = QLineEdit()
        self.outstanding_input.setText("0.00")

        if not self.customer and self.initial_name:
            self.name_input.setText(self.initial_name)

        form_layout.addRow("Customer Name *:", self.name_input)
        form_layout.addRow("Mobile Number *:", self.mobile_input)
        form_layout.addRow("Address:", self.address_input)
        form_layout.addRow("GSTIN (Optional):", self.gst_input)
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
        if self.customer:
            self.name_input.setText(self.customer.name)
            self.mobile_input.setText(self.customer.mobile)
            self.address_input.setText(self.customer.address or "")
            self.gst_input.setText(self.customer.gst or "")
            self.outstanding_input.setText(str(self.customer.outstanding_balance))

    def handle_save(self):
        name = self.name_input.text().strip()
        mobile = self.mobile_input.text().strip()
        address = self.address_input.text().strip() or None
        gst = self.gst_input.text().strip() or None

        if not name or not mobile:
            QMessageBox.warning(self, "Validation Error", "Please fill in Name and Mobile Number.")
            return

        try:
            outstanding = float(self.outstanding_input.text())
        except ValueError:
            QMessageBox.warning(self, "Validation Error", "Outstanding balance must be a number.")
            return

        session = Session()
        try:
            if self.customer:
                cust = session.query(Customer).get(self.customer.id)
                cust.name = name
                cust.mobile = mobile
                cust.address = address
                cust.gst = gst
                cust.outstanding_balance = outstanding
                self.saved_customer_id = cust.id
                self.saved_customer_name = cust.name
            else:
                new_cust = Customer(
                    name=name, mobile=mobile, address=address, gst=gst,
                    outstanding_balance=outstanding
                )
                session.add(new_cust)
                session.flush()
                self.saved_customer_id = new_cust.id
                self.saved_customer_name = new_cust.name

            session.commit()
            self.accept()
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", f"Could not save customer: {e}")
        finally:
            session.close()


class CustomersView(QWidget):
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
        self.search_input.setPlaceholderText("Search customers by name or mobile number...")
        self.search_input.textChanged.connect(self.refresh_data)
        top_bar.addWidget(self.search_input, 4)

        self.add_btn = QPushButton("Add Customer (Ctrl+N)")
        self.add_btn.setToolTip("Add new customer (Ctrl+N)")
        self.add_btn.clicked.connect(self.add_customer)
        top_bar.addWidget(self.add_btn, 1)

        self.edit_btn = QPushButton("Edit Customer")
        self.edit_btn.setProperty("class", "btn-secondary")
        self.edit_btn.clicked.connect(self.edit_customer)
        top_bar.addWidget(self.edit_btn, 1)

        self.ledger_btn = QPushButton("View Ledger")
        self.ledger_btn.setProperty("class", "btn-warning")
        self.ledger_btn.clicked.connect(self.view_ledger)
        top_bar.addWidget(self.ledger_btn, 1)

        self.delete_btn = QPushButton("Delete")
        self.delete_btn.setProperty("class", "btn-danger")
        self.delete_btn.clicked.connect(self.delete_customer)
        top_bar.addWidget(self.delete_btn, 1)

        layout.addLayout(top_bar)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "ID", "Customer Name", "Mobile Number", "Address", "GSTIN", "Outstanding Balance"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.doubleClicked.connect(self.edit_customer)
        layout.addWidget(self.table)

    def refresh_data(self):
        search_txt = self.search_input.text().strip()
        session = Session()
        try:
            query = session.query(Customer)
            if search_txt:
                query = query.filter(
                    Customer.name.like(f"%{search_txt}%") |
                    Customer.mobile.like(f"%{search_txt}%")
                )
            customers = query.all()

            self.table.setRowCount(len(customers))
            for i, c in enumerate(customers):
                self.table.setItem(i, 0, QTableWidgetItem(str(c.id)))
                self.table.setItem(i, 1, QTableWidgetItem(c.name))
                self.table.setItem(i, 2, QTableWidgetItem(c.mobile))
                self.table.setItem(i, 3, QTableWidgetItem(c.address or "-"))
                self.table.setItem(i, 4, QTableWidgetItem(c.gst or "-"))
                
                bal_item = QTableWidgetItem(f"₹{c.outstanding_balance:,.2f}")
                if c.outstanding_balance > 0:
                    bal_item.setForeground(Qt.yellow)
                self.table.setItem(i, 5, bal_item)

        except Exception as e:
            print(f"Error loading customers: {e}")
        finally:
            session.close()

    def get_selected_customer_id(self):
        selected = self.table.selectedItems()
        if not selected:
            return None
        return int(self.table.item(selected[0].row(), 0).text())

    def add_customer(self):
        dlg = CustomerDialog(parent=self)
        if dlg.exec() == QDialog.Accepted:
            self.refresh_data()

    def edit_customer(self):
        cust_id = self.get_selected_customer_id()
        if cust_id is None:
            QMessageBox.information(self, "No Selection", "Please select a customer to edit.")
            return

        session = Session()
        try:
            cust = session.query(Customer).get(cust_id)
            if cust:
                dlg = CustomerDialog(customer=cust, parent=self)
                if dlg.exec() == QDialog.Accepted:
                    self.refresh_data()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not load customer details: {e}")
        finally:
            session.close()

    def delete_customer(self):
        cust_id = self.get_selected_customer_id()
        if cust_id is None:
            QMessageBox.information(self, "No Selection", "Please select a customer to delete.")
            return

        confirm = QMessageBox.question(
            self, "Confirm Delete", "Are you sure you want to delete this customer record? All service history and sales linking to this customer will lose integrity.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if confirm == QMessageBox.Yes:
            session = Session()
            try:
                cust = session.query(Customer).get(cust_id)
                if cust:
                    session.delete(cust)
                    session.commit()
                    self.refresh_data()
            except Exception as e:
                session.rollback()
                QMessageBox.critical(self, "Error", f"Could not delete customer: {e}")
            finally:
                session.close()

    def view_ledger(self):
        cust_id = self.get_selected_customer_id()
        if cust_id is None:
            QMessageBox.information(self, "No Selection", "Please select a customer to view ledger.")
            return

        session = Session()
        try:
            cust = session.query(Customer).get(cust_id)
            if cust:
                from ui.masters.ledger_dialog import LedgerBreakupDialog
                dlg = LedgerBreakupDialog(party_type='customer', party_id=cust.id, party_name=cust.name, parent=self)
                dlg.exec()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not load customer ledger: {e}")
        finally:
            session.close()
