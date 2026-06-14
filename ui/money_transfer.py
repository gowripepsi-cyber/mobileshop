import datetime
import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox, 
                             QDateEdit, QDoubleSpinBox, QPushButton, QTableWidget, QTableWidgetItem, 
                             QHeaderView, QMessageBox, QFrame, QFormLayout, QFileDialog, QApplication,
                             QRadioButton)
from PySide6.QtCore import Qt, QDate
from database import Session, Setting
from models import MoneyTransfer, BankAccount, CashTransaction, BankTransaction
from utils.pdf_generator import generate_money_transfer_pdf
from sqlalchemy import func

class MoneyTransferView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def create_field_group(self, label_text, widget):
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        lbl = QLabel(label_text)
        lbl.setStyleSheet("font-weight: 500; color: #94a3b8; font-size: 11px;")
        layout.addWidget(lbl)
        layout.addWidget(widget)
        return container

    def init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(15)

        # 1. KPI Cards Row at the top
        kpi_layout = QHBoxLayout()
        kpi_layout.setSpacing(15)

        self.kpi_total_amt = self.create_kpi_card("Total Transferred Amount", "₹0.00", "#6366f1")
        self.kpi_total_charges = self.create_kpi_card("Total Service Charges", "₹0.00", "#10b981")
        self.kpi_completed = self.create_kpi_card("Completed Transfers", "0", "#06b6d4")
        self.kpi_pending = self.create_kpi_card("Pending Transfers", "0", "#ef4444")

        kpi_layout.addWidget(self.kpi_total_amt)
        kpi_layout.addWidget(self.kpi_total_charges)
        kpi_layout.addWidget(self.kpi_completed)
        kpi_layout.addWidget(self.kpi_pending)
        
        self.main_layout.addLayout(kpi_layout)

        # 2. Main Content Split (Form on Left, Log on Right)
        split_layout = QHBoxLayout()
        split_layout.setSpacing(20)

        # Left Column: Form Card
        self.form_frame = QFrame()
        self.form_frame.setProperty("class", "CardFrame")
        self.form_frame.setFixedWidth(400)
        form_layout = QVBoxLayout(self.form_frame)
        form_layout.setContentsMargins(15, 15, 15, 15)
        form_layout.setSpacing(10)

        self.form_title = QLabel("New Money Transfer")
        self.form_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #ffffff; margin-bottom: 2px;")
        form_layout.addWidget(self.form_title)

        # Row 1: Dates (Transfer Date & Deadline Date)
        row1 = QWidget()
        row1_layout = QHBoxLayout(row1)
        row1_layout.setContentsMargins(0, 0, 0, 0)
        row1_layout.setSpacing(10)
        
        self.t_date = QDateEdit()
        self.t_date.setCalendarPopup(True)
        self.t_date.setDate(QDate.currentDate())
        
        self.t_deadline = QDateEdit()
        self.t_deadline.setCalendarPopup(True)
        self.t_deadline.setDate(QDate.currentDate().addDays(1))
        
        row1_layout.addWidget(self.create_field_group("Transfer Date:", self.t_date))
        row1_layout.addWidget(self.create_field_group("Deadline Date *:", self.t_deadline))
        form_layout.addWidget(row1)

        # Row 2: Sender & Beneficiary
        row2 = QWidget()
        row2_layout = QHBoxLayout(row2)
        row2_layout.setContentsMargins(0, 0, 0, 0)
        row2_layout.setSpacing(10)
        
        self.t_cust_name = QLineEdit()
        self.t_cust_name.setPlaceholderText("Sender Customer Name")
        
        self.t_beneficiary_name = QLineEdit()
        self.t_beneficiary_name.setPlaceholderText("Beneficiary Full Name")
        
        row2_layout.addWidget(self.create_field_group("Sender Name *:", self.t_cust_name))
        row2_layout.addWidget(self.create_field_group("Beneficiary Name *:", self.t_beneficiary_name))
        form_layout.addWidget(row2)

        # Row 3: Transfer Type (Radio Buttons)
        row3 = QWidget()
        row3_layout = QHBoxLayout(row3)
        row3_layout.setContentsMargins(0, 0, 0, 0)
        row3_layout.setSpacing(10)
        
        self.r_upi = QRadioButton("UPI")
        self.r_bank = QRadioButton("Bank Transfer")
        self.r_upi.setChecked(True)
        
        self.r_upi.toggled.connect(self.on_transfer_type_changed)
        self.r_bank.toggled.connect(self.on_transfer_type_changed)
        
        radio_container = QWidget()
        radio_layout = QHBoxLayout(radio_container)
        radio_layout.setContentsMargins(5, 5, 5, 5)
        radio_layout.setSpacing(15)
        radio_layout.addWidget(self.r_upi)
        radio_layout.addWidget(self.r_bank)
        
        row3_layout.addWidget(self.create_field_group("Transfer Type *:", radio_container))
        form_layout.addWidget(row3)

        # Row 4: Dynamic Fields Container (Full Width)
        self.dynamic_container = QWidget()
        dyn_layout = QHBoxLayout(self.dynamic_container)
        dyn_layout.setContentsMargins(0, 0, 0, 0)
        dyn_layout.setSpacing(0)
        
        self.t_upi_id = QLineEdit()
        self.t_upi_id.setPlaceholderText("UPI ID or UPI Mobile Number")
        self.upi_widget = self.create_field_group("UPI ID / Mobile *:", self.t_upi_id)
        
        self.bank_widget = QWidget()
        bank_h = QHBoxLayout(self.bank_widget)
        bank_h.setContentsMargins(0, 0, 0, 0)
        bank_h.setSpacing(10)
        
        self.t_bank_account_no = QLineEdit()
        self.t_bank_account_no.setPlaceholderText("Bank Account Number")
        self.t_ifsc = QLineEdit()
        self.t_ifsc.setPlaceholderText("IFSC Code")
        
        bank_h.addWidget(self.create_field_group("Account Number *:", self.t_bank_account_no))
        bank_h.addWidget(self.create_field_group("IFSC Code *:", self.t_ifsc))
        self.bank_widget.hide()
        
        dyn_layout.addWidget(self.upi_widget)
        dyn_layout.addWidget(self.bank_widget)
        form_layout.addWidget(self.dynamic_container)

        # Row 5: Amount & Service Charge
        row5 = QWidget()
        row5_layout = QHBoxLayout(row5)
        row5_layout.setContentsMargins(0, 0, 0, 0)
        row5_layout.setSpacing(10)
        
        self.t_amount = QDoubleSpinBox()
        self.t_amount.setRange(0.01, 9999999.0)
        self.t_amount.setDecimals(2)
        
        self.t_charge = QDoubleSpinBox()
        self.t_charge.setRange(0.0, 999999.0)
        self.t_charge.setDecimals(2)
        
        row5_layout.addWidget(self.create_field_group("Amount (₹) *:", self.t_amount))
        row5_layout.addWidget(self.create_field_group("Service Charge (₹):", self.t_charge))
        form_layout.addWidget(row5)

        # Row 6: Shop Payout Bank (Always Bank)
        self.t_payout_bank = QComboBox()
        form_layout.addWidget(self.create_field_group("Payout Bank Account (Online Transfer) *:", self.t_payout_bank))

        # Row 7: Remarks (Full Width - Last Input Field)
        self.t_remarks = QLineEdit()
        self.t_remarks.setPlaceholderText("Optional remarks")
        form_layout.addWidget(self.create_field_group("Remarks:", self.t_remarks))

        # Row 8: Submit button
        self.save_btn = QPushButton("Submit Money Transfer")
        self.save_btn.setProperty("class", "btn-success")
        self.save_btn.clicked.connect(self.save_transfer)
        form_layout.addWidget(self.save_btn)

        split_layout.addWidget(self.form_frame)

        # Right Column: Search filters + Grid Log
        history_frame = QFrame()
        history_frame.setProperty("class", "CardFrame")
        history_layout = QVBoxLayout(history_frame)
        history_layout.setContentsMargins(15, 15, 15, 15)
        history_layout.setSpacing(10)

        # Filters panel
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(10)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search Sender, Beneficiary, Tx #...")
        self.search_input.textChanged.connect(self.refresh_data)
        filter_layout.addWidget(self.search_input, 2)

        self.f_type = QComboBox()
        self.f_type.addItems(["All Types", "UPI", "Bank Transfer"])
        self.f_type.currentIndexChanged.connect(self.refresh_data)
        filter_layout.addWidget(self.f_type, 1)

        self.f_status = QComboBox()
        self.f_status.addItems(["All Statuses", "Pending", "Completed"])
        self.f_status.currentIndexChanged.connect(self.refresh_data)
        filter_layout.addWidget(self.f_status, 1)

        # Date pickers
        self.f_start_date = QDateEdit()
        self.f_start_date.setCalendarPopup(True)
        # default from 30 days ago
        self.f_start_date.setDate(QDate.currentDate().addDays(-30))
        self.f_start_date.dateChanged.connect(self.refresh_data)
        filter_layout.addWidget(self.f_start_date, 1)

        self.f_end_date = QDateEdit()
        self.f_end_date.setCalendarPopup(True)
        self.f_end_date.setDate(QDate.currentDate().addDays(30))
        self.f_end_date.dateChanged.connect(self.refresh_data)
        filter_layout.addWidget(self.f_end_date, 1)

        history_layout.addLayout(filter_layout)

        # Table Grid
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "Tx #", "Date", "Sender", "Beneficiary", "Type", "Amount (Fee)", "Status", "Actions"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(7, QHeaderView.Fixed)
        self.table.setColumnWidth(7, 230)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(45)
        history_layout.addWidget(self.table)

        split_layout.addWidget(history_frame)

        self.main_layout.addLayout(split_layout)

    def create_kpi_card(self, title, val, border_color):
        card = QFrame()
        card.setProperty("class", "MetricCard")
        card.setStyleSheet(f"border-left: 4px solid {border_color};")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(15, 12, 15, 12)
        
        title_lbl = QLabel(title)
        title_lbl.setProperty("class", "MetricTitle")
        val_lbl = QLabel(val)
        val_lbl.setProperty("class", "MetricValue")
        val_lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
        
        card_layout.addWidget(title_lbl)
        card_layout.addWidget(val_lbl)
        
        card.val_label = val_lbl # Store ref to update later
        return card

    def on_transfer_type_changed(self):
        if self.r_upi.isChecked():
            self.upi_widget.show()
            self.bank_widget.hide()
        else:
            self.upi_widget.hide()
            self.bank_widget.show()



    def refresh_data(self):
        session = Session()
        try:
            # 1. Update KPI Statistics
            total_amt = session.query(func.sum(MoneyTransfer.amount)).scalar() or 0.0
            total_charges = session.query(func.sum(MoneyTransfer.service_charge)).scalar() or 0.0
            completed_count = session.query(MoneyTransfer).filter_by(status='Completed').count()
            pending_count = session.query(MoneyTransfer).filter_by(status='Pending').count()

            self.kpi_total_amt.val_label.setText(f"₹{total_amt:,.2f}")
            self.kpi_total_charges.val_label.setText(f"₹{total_charges:,.2f}")
            self.kpi_completed.val_label.setText(str(completed_count))
            self.kpi_pending.val_label.setText(str(pending_count))

            # 2. Populate Bank dropdown if empty
            if self.t_payout_bank.count() == 0:
                banks = session.query(BankAccount).all()
                self.banks_cache = banks
                self.t_payout_bank.blockSignals(True)
                for b in banks:
                    self.t_payout_bank.addItem(f"{b.bank_name} ({b.account_name})", b.id)
                self.t_payout_bank.blockSignals(False)

            # Suggest unique transaction number if form is blank
            if not self.save_btn.property("is_edit") and not self.t_cust_name.text().strip():
                last_mt = session.query(MoneyTransfer).order_by(MoneyTransfer.id.desc()).first()
                next_no = f"MT-{last_mt.id + 10001}" if last_mt else "MT-10001"
                self.save_btn.setProperty("tx_no", next_no)
                self.form_title.setText(f"New Money Transfer (No: {next_no})")

            # 3. Populate Grid Table using search filters
            query = session.query(MoneyTransfer)
            
            # Search filter
            search = self.search_input.text().strip()
            if search:
                query = query.filter(
                    (MoneyTransfer.transaction_number.ilike(f"%{search}%")) |
                    (MoneyTransfer.customer_name.ilike(f"%{search}%")) |
                    (MoneyTransfer.beneficiary_name.ilike(f"%{search}%"))
                )

            # Transfer Type filter
            selected_type = self.f_type.currentText()
            if selected_type != "All Types":
                query = query.filter(MoneyTransfer.transfer_type == selected_type)

            # Status filter
            selected_status = self.f_status.currentText()
            if selected_status != "All Statuses":
                query = query.filter(MoneyTransfer.status == selected_status)

            # Date Range filter
            q_start = self.f_start_date.date()
            start_d = datetime.date(q_start.year(), q_start.month(), q_start.day())
            q_end = self.f_end_date.date()
            end_d = datetime.date(q_end.year(), q_end.month(), q_end.day())
            query = query.filter(MoneyTransfer.date.between(start_d, end_d))

            transfers = query.order_by(MoneyTransfer.id.desc()).all()
            self.table.setRowCount(len(transfers))
            for i, t in enumerate(transfers):
                self.table.setItem(i, 0, QTableWidgetItem(t.transaction_number))
                self.table.setItem(i, 1, QTableWidgetItem(t.date.strftime("%Y-%m-%d")))
                self.table.setItem(i, 2, QTableWidgetItem(t.customer_name))
                self.table.setItem(i, 3, QTableWidgetItem(t.beneficiary_name))
                self.table.setItem(i, 4, QTableWidgetItem(t.transfer_type))
                self.table.setItem(i, 5, QTableWidgetItem(f"₹{t.amount:,.2f} (+₹{t.service_charge:,.2f})"))
                
                status_item = QTableWidgetItem(t.status)
                if t.status == 'Completed':
                    status_item.setForeground(Qt.green)
                else:
                    status_item.setForeground(Qt.yellow)
                self.table.setItem(i, 6, status_item)

                # Actions Panel
                actions_widget = QWidget()
                actions_layout = QHBoxLayout(actions_widget)
                actions_layout.setContentsMargins(4, 2, 4, 2)
                actions_layout.setSpacing(5)
                actions_layout.setAlignment(Qt.AlignCenter)

                status_btn = QPushButton("Toggle")
                status_btn.setProperty("class", "btn-action-view")
                status_btn.clicked.connect(lambda checked, tid=t.id: self.toggle_transfer_status(tid))
                actions_layout.addWidget(status_btn)

                print_btn = QPushButton("Receipt")
                print_btn.setProperty("class", "btn-action-print")
                print_btn.clicked.connect(lambda checked, tid=t.id: self.print_transfer_receipt(tid))
                actions_layout.addWidget(print_btn)

                del_btn = QPushButton("Delete")
                del_btn.setProperty("class", "btn-action-delete")
                del_btn.clicked.connect(lambda checked, tid=t.id: self.delete_transfer(tid))
                actions_layout.addWidget(del_btn)

                self.table.setCellWidget(i, 7, actions_widget)

        except Exception as e:
            print(f"Error loading Money Transfer view data: {e}")
        finally:
            session.close()

    def save_transfer(self):
        sender = self.t_cust_name.text().strip()
        beneficiary = self.t_beneficiary_name.text().strip()
        t_type = "UPI" if self.r_upi.isChecked() else "Bank Transfer"
        amount = self.t_amount.value()
        charge = self.t_charge.value()
        remarks = self.t_remarks.text().strip() or None

        date_q = self.t_date.date()
        tx_date = datetime.date(date_q.year(), date_q.month(), date_q.day())

        dl_q = self.t_deadline.date()
        dl_date = datetime.date(dl_q.year(), dl_q.month(), dl_q.day())

        # Sub-fields
        upi_id = self.t_upi_id.text().strip() if t_type == "UPI" else None
        bank_acc = self.t_bank_account_no.text().strip() if t_type == "Bank Transfer" else None
        ifsc = self.t_ifsc.text().strip() if t_type == "Bank Transfer" else None

        pay_mode = "Cash"
        pay_bank_id = None

        payout_mode = "Bank"
        payout_bank_id = self.t_payout_bank.currentData()

        if not payout_bank_id:
            QMessageBox.warning(self, "Validation Error", "Please select a Payout Bank Account.")
            return

        # Validation
        if not sender or not beneficiary:
            QMessageBox.warning(self, "Validation Error", "Please enter Sender Name and Beneficiary Name.")
            return

        if t_type == "UPI" and not upi_id:
            QMessageBox.warning(self, "Validation Error", "UPI ID / Mobile Number is required.")
            return

        if t_type == "Bank Transfer" and (not bank_acc or not ifsc):
            QMessageBox.warning(self, "Validation Error", "Bank Account Number and IFSC Code are required.")
            return

        if amount <= 0:
            QMessageBox.warning(self, "Validation Error", "Transfer Amount must be greater than zero.")
            return

        tx_no = self.save_btn.property("tx_no") or "MT-XXXXX"

        session = Session()
        try:
            # Verification of Payout funds
            bank_po = session.query(BankAccount).get(payout_bank_id)
            if not bank_po:
                QMessageBox.warning(self, "Error", "Payout bank account not found.")
                session.close()
                return
            payout_target_name = f"{bank_po.bank_name} ({bank_po.account_name})"
            if bank_po.balance < amount:
                QMessageBox.warning(self, "Insufficient Funds", f"Insufficient balance in payout account {payout_target_name}.\nAvailable: ₹{bank_po.balance:,.2f}")
                session.close()
                return

            total_amt = amount + charge

            # Save Transfer record
            new_mt = MoneyTransfer(
                transaction_number=tx_no,
                date=tx_date,
                customer_name=sender,
                beneficiary_name=beneficiary,
                transfer_type=t_type,
                upi_id=upi_id,
                bank_account_number=bank_acc,
                ifsc_code=ifsc,
                amount=amount,
                service_charge=charge,
                total_amount=total_amt,
                deadline_date=dl_date,
                remarks=remarks,
                status='Pending',
                payment_mode=pay_mode,
                payment_bank_id=pay_bank_id,
                payout_mode=payout_mode,
                payout_bank_id=payout_bank_id
            )
            session.add(new_mt)
            session.flush() # get id

            # Log Ledger Inflow (payment from customer)
            desc_in = f"Inflow for Money Transfer {tx_no} from customer {sender}"
            if pay_mode == "Cash":
                tx_in = CashTransaction(
                    date=tx_date, transaction_type='in', amount=total_amt,
                    source_type='direct', source_id=new_mt.id, description=desc_in
                )
                session.add(tx_in)
            else:
                tx_in = BankTransaction(
                    date=tx_date, transaction_type='deposit', account_id=pay_bank_id,
                    amount=total_amt, source_type='direct', source_id=new_mt.id, description=desc_in
                )
                session.add(tx_in)
                pay_bank_obj = session.query(BankAccount).get(pay_bank_id)
                pay_bank_obj.balance += total_amt

            # Log Ledger Outflow (transfer routed out by shop)
            desc_out = f"Outflow for Money Transfer {tx_no} to beneficiary {beneficiary}"
            if payout_mode == "Cash":
                tx_out = CashTransaction(
                    date=tx_date, transaction_type='out', amount=amount,
                    source_type='direct', source_id=new_mt.id, description=desc_out
                )
                session.add(tx_out)
            else:
                tx_out = BankTransaction(
                    date=tx_date, transaction_type='withdrawal', account_id=payout_bank_id,
                    amount=amount, source_type='direct', source_id=new_mt.id, description=desc_out
                )
                session.add(tx_out)
                payout_bank_obj = session.query(BankAccount).get(payout_bank_id)
                payout_bank_obj.balance -= amount

            session.commit()
            QMessageBox.information(self, "Success", f"Money Transfer {tx_no} submitted successfully.")

            # Clear inputs
            self.t_cust_name.clear()
            self.t_beneficiary_name.clear()
            self.t_upi_id.clear()
            self.t_bank_account_no.clear()
            self.t_ifsc.clear()
            self.t_amount.setValue(0.0)
            self.t_charge.setValue(0.0)
            self.t_remarks.clear()
            self.refresh_data()
            
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", f"Failed to save Money Transfer: {e}")
        finally:
            session.close()

    def toggle_transfer_status(self, transfer_id):
        session = Session()
        try:
            mt = session.query(MoneyTransfer).get(transfer_id)
            if mt:
                mt.status = 'Completed' if mt.status == 'Pending' else 'Pending'
                session.commit()
                self.refresh_data()
        except Exception as e:
            print(f"Error toggling transfer status: {e}")
        finally:
            session.close()

    def print_transfer_receipt(self, transfer_id):
        session = Session()
        try:
            t = session.query(MoneyTransfer).get(transfer_id)
            if not t:
                QMessageBox.warning(self, "Error", "Transaction record not found.")
                return
                
            # Retrieve Settings
            s_name = session.query(Setting).filter_by(key='shop_name').first().value
            s_contact = session.query(Setting).filter_by(key='shop_contact').first().value
            s_address = session.query(Setting).filter_by(key='shop_address').first().value
            s_gst = session.query(Setting).filter_by(key='shop_gst').first().value

            # Prepare PDF data
            pdf_data = {
                "shop_name": s_name,
                "shop_contact": s_contact,
                "shop_address": s_address,
                "shop_gst": s_gst,
                "transaction_number": t.transaction_number,
                "date": t.date.strftime("%Y-%m-%d"),
                "customer_name": t.customer_name,
                "beneficiary_name": t.beneficiary_name,
                "transfer_type": t.transfer_type,
                "upi_id": t.upi_id,
                "bank_account_number": t.bank_account_number,
                "ifsc_code": t.ifsc_code,
                "amount": t.amount,
                "service_charge": t.service_charge,
                "total_amount": t.total_amount,
                "deadline_date": t.deadline_date.strftime("%Y-%m-%d"),
                "status": t.status,
                "remarks": t.remarks
            }

            os.makedirs("invoices", exist_ok=True)
            path = os.path.abspath(f"invoices/transfer_{t.transaction_number}.pdf")
            generate_money_transfer_pdf(pdf_data, path)
            
            QMessageBox.information(self, "Success", f"Transfer Receipt PDF generated at:\n{path}")
            try:
                os.startfile(path)
            except Exception as e:
                print(f"Could not auto-open PDF: {e}")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to print receipt: {e}")
        finally:
            session.close()

    def delete_transfer(self, transfer_id):
        confirm = QMessageBox.question(
            self, "Confirm Delete", 
            "Are you sure you want to delete/revert this money transfer record?\nThe ledger transactions and bank balances will be reverted.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if confirm != QMessageBox.Yes:
            return

        session = Session()
        try:
            mt = session.query(MoneyTransfer).get(transfer_id)
            if not mt:
                QMessageBox.warning(self, "Error", "Record not found.")
                session.close()
                return

            # Revert Payment (Inflow)
            if mt.payment_mode == 'Bank':
                bank_pay = session.query(BankAccount).get(mt.payment_bank_id)
                if bank_pay:
                    if bank_pay.balance < mt.total_amount:
                        QMessageBox.warning(self, "Validation Error", f"Cannot delete. Customer payment bank {bank_pay.bank_name} has insufficient balance to revert.")
                        session.close()
                        return
                    bank_pay.balance -= mt.total_amount
            else:
                cash_in = session.query(func.sum(CashTransaction.amount)).filter(CashTransaction.transaction_type == 'in').scalar() or 0.0
                cash_out = session.query(func.sum(CashTransaction.amount)).filter(CashTransaction.transaction_type == 'out').scalar() or 0.0
                cash_balance = cash_in - cash_out
                if cash_balance < mt.total_amount:
                    QMessageBox.warning(self, "Validation Error", f"Cannot delete. Cash Ledger has insufficient balance to revert customer's payment.")
                    session.close()
                    return

            # Revert Payout (Outflow)
            if mt.payout_mode == 'Bank':
                bank_po = session.query(BankAccount).get(mt.payout_bank_id)
                if bank_po:
                    bank_po.balance += mt.amount

            # Delete related ledger entries
            cash_txs = session.query(CashTransaction).filter(
                (CashTransaction.source_type == 'direct') & (CashTransaction.source_id == mt.id)
            ).all()
            for tx in cash_txs:
                session.delete(tx)

            bank_txs = session.query(BankTransaction).filter(
                (BankTransaction.source_type == 'direct') & (BankTransaction.source_id == mt.id)
            ).all()
            for tx in bank_txs:
                session.delete(tx)

            # Delete money transfer record
            session.delete(mt)
            session.commit()
            
            QMessageBox.information(self, "Success", "Money Transfer record reverted and deleted successfully.")
            self.refresh_data()
            
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", f"Failed to revert/delete transfer: {e}")
        finally:
            session.close()
