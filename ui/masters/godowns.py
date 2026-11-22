from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLineEdit, QLabel, QDialog, QFormLayout, QMessageBox,
    QHeaderView, QComboBox, QCheckBox, QTextEdit, QSpinBox, QDoubleSpinBox,
    QDateEdit, QFrame, QSplitter, QGroupBox
)
from PySide6.QtCore import Qt, QDate
from sqlalchemy import func
from database import (
    Session, generate_next_godown_code, generate_next_transfer_number,
    get_godown_stock, adjust_godown_stock, get_shop_stock, get_location_stock
)
from models import (
    Godown, GodownStock, GodownTransfer, GodownTransferItem, Product, Unit
)
from utils.unit_converter import get_product_unit_info, calculate_base_qty, format_stock_display
from utils.translator import tr


class GodownDialog(QDialog):
    """Dialog for creating or editing a Godown/Warehouse."""
    def __init__(self, godown=None, parent=None):
        super().__init__(parent)
        self.godown = godown
        self.saved_godown_id = None
        self.setWindowTitle("Edit Godown" if godown else "Add New Godown")
        self.setFixedSize(500, 480)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        form_layout = QFormLayout()
        form_layout.setSpacing(12)

        session = Session()
        try:
            suggested_code = generate_next_godown_code(session) if not self.godown else self.godown.code
        finally:
            session.close()

        self.code_input = QLineEdit()
        self.code_input.setText(suggested_code)
        self.code_input.setFixedHeight(34)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g. Main Shop Godown, Warehouse 1, Basement Store")
        self.name_input.setFixedHeight(34)

        self.location_input = QLineEdit()
        self.location_input.setPlaceholderText("e.g. Ground Floor, Rear Storage, Market Complex")
        self.location_input.setFixedHeight(34)

        self.contact_person_input = QLineEdit()
        self.contact_person_input.setPlaceholderText("e.g. Ramesh Kumar, Store Keeper")
        self.contact_person_input.setFixedHeight(34)

        self.contact_phone_input = QLineEdit()
        self.contact_phone_input.setPlaceholderText("e.g. 9876543210")
        self.contact_phone_input.setFixedHeight(34)

        self.is_active_check = QCheckBox("Active Godown")
        self.is_active_check.setChecked(True)

        self.notes_input = QTextEdit()
        self.notes_input.setPlaceholderText("Optional notes or description...")
        self.notes_input.setFixedHeight(50)

        form_layout.addRow("Godown Code *:", self.code_input)
        form_layout.addRow("Godown Name *:", self.name_input)
        form_layout.addRow("Location / Address:", self.location_input)
        form_layout.addRow("Contact Person:", self.contact_person_input)
        form_layout.addRow("Contact Phone:", self.contact_phone_input)
        form_layout.addRow("", self.is_active_check)
        form_layout.addRow("Notes:", self.notes_input)

        layout.addLayout(form_layout)

        # Buttons
        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("Save Godown")
        self.save_btn.setProperty("class", "btn-success")
        self.save_btn.setFixedHeight(36)
        self.save_btn.clicked.connect(self.handle_save)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setProperty("class", "btn-secondary")
        self.cancel_btn.setFixedHeight(36)
        self.cancel_btn.clicked.connect(self.reject)

        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)

        if self.godown:
            self.code_input.setText(self.godown.code or "")
            self.name_input.setText(self.godown.name or "")
            self.location_input.setText(self.godown.location or "")
            self.contact_person_input.setText(self.godown.contact_person or "")
            self.contact_phone_input.setText(self.godown.contact_phone or "")
            self.is_active_check.setChecked(bool(self.godown.is_active))
            self.notes_input.setText(self.godown.notes or "")

    def handle_save(self):
        code = self.code_input.text().strip()
        name = self.name_input.text().strip()
        location = self.location_input.text().strip() or None
        contact_person = self.contact_person_input.text().strip() or None
        contact_phone = self.contact_phone_input.text().strip() or None
        is_active = self.is_active_check.isChecked()
        notes = self.notes_input.toPlainText().strip() or None

        if not code:
            QMessageBox.warning(self, "Validation Error", "Godown Code is required.")
            self.code_input.setFocus()
            return

        if not name:
            QMessageBox.warning(self, "Validation Error", "Godown Name is required.")
            self.name_input.setFocus()
            return

        session = Session()
        try:
            # Check code uniqueness
            existing_code = session.query(Godown).filter(Godown.code.ilike(code)).first()
            if existing_code and (not self.godown or existing_code.id != self.godown.id):
                QMessageBox.warning(self, "Validation Error", f"A godown with code '{code}' already exists.")
                self.code_input.setFocus()
                return

            # Check name uniqueness
            existing_name = session.query(Godown).filter(Godown.name.ilike(name)).first()
            if existing_name and (not self.godown or existing_name.id != self.godown.id):
                QMessageBox.warning(self, "Validation Error", f"A godown with name '{name}' already exists.")
                self.name_input.setFocus()
                return

            if self.godown:
                g = session.query(Godown).get(self.godown.id)
                g.code = code
                g.name = name
                g.location = location
                g.contact_person = contact_person
                g.contact_phone = contact_phone
                g.is_active = is_active
                g.notes = notes
                session.commit()
                self.saved_godown_id = g.id
            else:
                new_g = Godown(
                    code=code,
                    name=name,
                    location=location,
                    contact_person=contact_person,
                    contact_phone=contact_phone,
                    is_default=False,
                    is_active=is_active,
                    notes=notes
                )
                session.add(new_g)
                session.commit()
                self.saved_godown_id = new_g.id

            self.accept()
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", f"Failed to save godown: {e}")
        finally:
            session.close()


class GodownStockDialog(QDialog):
    """Dialog displaying physical stock for all products inside a specific Godown."""
    def __init__(self, godown_id, parent=None):
        super().__init__(parent)
        self.godown_id = godown_id
        self.setWindowTitle("Godown Stock Register")
        self.resize(850, 520)
        self.init_ui()
        self.load_stock_data()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Header Info Card
        session = Session()
        try:
            godown = session.query(Godown).get(self.godown_id)
            g_name = godown.name if godown else "Unknown Godown"
            g_code = godown.code if godown else ""
            g_loc = (godown.location or "No location specified") if godown else "No location specified"
        finally:
            session.close()

        header_frame = QFrame()
        header_frame.setProperty("class", "CardFrame")
        header_frame.setStyleSheet("background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 10px;")
        h_layout = QHBoxLayout(header_frame)
        h_layout.setContentsMargins(10, 8, 10, 8)

        info_lbl = QLabel(f"<b>🏢 {g_name}</b> &nbsp;&nbsp;|&nbsp;&nbsp; Code: <code>{g_code}</code> &nbsp;&nbsp;|&nbsp;&nbsp; Location: {g_loc}")
        info_lbl.setStyleSheet("font-size: 13.5px; color: #1e293b;")
        h_layout.addWidget(info_lbl)
        h_layout.addStretch()

        self.summary_badge = QLabel("0 Items | Total Qty: 0")
        self.summary_badge.setStyleSheet("font-size: 12px; font-weight: bold; background: #e0f2fe; color: #0369a1; padding: 4px 10px; border-radius: 6px;")
        h_layout.addWidget(self.summary_badge)
        layout.addWidget(header_frame)

        # Search Bar & Filter
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search products by name, code, category, brand...")
        self.search_input.setFixedHeight(36)
        self.search_input.textChanged.connect(self.filter_stock_table)
        search_layout.addWidget(self.search_input, 3)

        self.stock_filter_combo = QComboBox()
        self.stock_filter_combo.addItems(["All Products", "In-Stock Only (> 0)", "Low Stock Alert", "Zero Stock"])
        self.stock_filter_combo.setFixedHeight(36)
        self.stock_filter_combo.currentIndexChanged.connect(self.filter_stock_table)
        search_layout.addWidget(self.stock_filter_combo, 1)

        layout.addLayout(search_layout)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "Code", "Product Name", "Category", "Brand / Model",
            "Unit", "Godown Stock", "Total Shop Stock", "Status"
        ])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.table)

        # Bottom Bar
        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()

        close_btn = QPushButton("Close")
        close_btn.setProperty("class", "btn-secondary")
        close_btn.setFixedHeight(36)
        close_btn.setFixedWidth(100)
        close_btn.clicked.connect(self.accept)
        bottom_layout.addWidget(close_btn)
        layout.addLayout(bottom_layout)

    def load_stock_data(self):
        session = Session()
        try:
            self.all_items = []
            products = session.query(Product).order_by(Product.name).all()
            total_items_in_gdn = 0
            total_qty_in_gdn = 0.0

            for p in products:
                main_u, sub_u, rate = get_product_unit_info(p, session)
                g_stock_qty = get_godown_stock(session, self.godown_id, p.id)
                overall_qty = p.stock_qty or 0.0

                if g_stock_qty > 0:
                    total_items_in_gdn += 1
                    total_qty_in_gdn += g_stock_qty

                g_stock_disp = format_stock_display(g_stock_qty, main_u, sub_u, rate)
                overall_disp = format_stock_display(overall_qty, main_u, sub_u, rate)

                # Status
                if g_stock_qty <= 0:
                    status = "Out of Stock"
                    status_color = "#ef4444"
                elif p.low_stock_limit and g_stock_qty <= p.low_stock_limit:
                    status = "Low Stock"
                    status_color = "#f59e0b"
                else:
                    status = "In Stock"
                    status_color = "#10b981"

                item_data = {
                    "product_id": p.id,
                    "code": p.product_code or "-",
                    "name": p.name,
                    "category": p.category or "-",
                    "brand_model": p.brand_model or "-",
                    "unit": p.unit or "Pcs",
                    "godown_stock_qty": g_stock_qty,
                    "godown_stock_disp": g_stock_disp,
                    "overall_qty": overall_qty,
                    "overall_disp": overall_disp,
                    "status": status,
                    "status_color": status_color,
                    "low_limit": p.low_stock_limit or 5
                }
                self.all_items.append(item_data)

            self.summary_badge.setText(f"Stored Items: {total_items_in_gdn} | Total Stock: {total_qty_in_gdn:g}")
            self.filter_stock_table()
        finally:
            session.close()

    def filter_stock_table(self):
        q = self.search_input.text().strip().lower()
        filter_mode = self.stock_filter_combo.currentIndex()

        filtered = []
        for item in self.all_items:
            # Search query match
            if q:
                match = (
                    q in item["code"].lower() or
                    q in item["name"].lower() or
                    q in item["category"].lower() or
                    q in item["brand_model"].lower()
                )
                if not match:
                    continue

            # Dropdown filter
            if filter_mode == 1 and item["godown_stock_qty"] <= 0:  # In-Stock Only
                continue
            elif filter_mode == 2:  # Low Stock Alert
                if item["godown_stock_qty"] <= 0 or item["godown_stock_qty"] > item["low_limit"]:
                    continue
            elif filter_mode == 3 and item["godown_stock_qty"] > 0:  # Zero Stock
                continue

            filtered.append(item)

        self.table.setRowCount(len(filtered))
        for row, item in enumerate(filtered):
            # Code
            c_item = QTableWidgetItem(item["code"])
            c_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 0, c_item)

            # Name
            self.table.setItem(row, 1, QTableWidgetItem(item["name"]))

            # Category
            cat_item = QTableWidgetItem(item["category"])
            cat_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 2, cat_item)

            # Brand/Model
            self.table.setItem(row, 3, QTableWidgetItem(item["brand_model"]))

            # Unit
            u_item = QTableWidgetItem(item["unit"])
            u_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 4, u_item)

            # Godown Stock
            g_item = QTableWidgetItem(item["godown_stock_disp"])
            g_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            g_item.setForeground(Qt.black)
            self.table.setItem(row, 5, g_item)

            # Total Shop Stock
            o_item = QTableWidgetItem(item["overall_disp"])
            o_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(row, 6, o_item)

            # Status Badge
            st_item = QTableWidgetItem(item["status"])
            st_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 7, st_item)


class GodownTransferDialog(QDialog):
    """Dialog for inter-godown inventory stock transfer."""
    def __init__(self, from_godown_id=None, parent=None):
        super().__init__(parent)
        self.preselected_from_id = from_godown_id
        self.transfer_items = []
        self.setWindowTitle("Inter-Godown Stock Transfer")
        self.resize(780, 560)
        self.init_ui()
        self.populate_godowns()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        # Header Details Card
        top_frame = QFrame()
        top_frame.setProperty("class", "CardFrame")
        top_frame.setStyleSheet("background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px;")
        top_layout = QVBoxLayout(top_frame)
        top_layout.setContentsMargins(10, 8, 10, 8)
        top_layout.setSpacing(10)

        r1 = QHBoxLayout()
        r1.setSpacing(12)

        session = Session()
        try:
            suggested_trf = generate_next_transfer_number(session)
        finally:
            session.close()

        lbl_no = QLabel("Transfer No.:")
        lbl_no.setStyleSheet("font-weight: 600; color: #475569;")
        self.trf_no_input = QLineEdit(suggested_trf)
        self.trf_no_input.setFixedWidth(150)
        self.trf_no_input.setFixedHeight(34)
        r1.addWidget(lbl_no)
        r1.addWidget(self.trf_no_input)

        lbl_date = QLabel("Transfer Date:")
        lbl_date.setStyleSheet("font-weight: 600; color: #475569;")
        self.date_input = QDateEdit()
        self.date_input.setCalendarPopup(True)
        self.date_input.setDate(QDate.currentDate())
        self.date_input.setFixedHeight(34)
        self.date_input.setFixedWidth(120)
        r1.addWidget(lbl_date)
        r1.addWidget(self.date_input)
        r1.addStretch()

        top_layout.addLayout(r1)

        r2 = QHBoxLayout()
        r2.setSpacing(12)

        lbl_from = QLabel("From Godown *:")
        lbl_from.setStyleSheet("font-weight: 600; color: #1e293b;")
        self.from_godown_combo = QComboBox()
        self.from_godown_combo.setFixedHeight(36)
        self.from_godown_combo.currentIndexChanged.connect(self.on_godown_selection_changed)
        r2.addWidget(lbl_from)
        r2.addWidget(self.from_godown_combo, 1)

        arrow_lbl = QLabel("➔")
        arrow_lbl.setStyleSheet("font-size: 18px; font-weight: bold; color: #64748b;")
        r2.addWidget(arrow_lbl)

        lbl_to = QLabel("To Godown *:")
        lbl_to.setStyleSheet("font-weight: 600; color: #1e293b;")
        self.to_godown_combo = QComboBox()
        self.to_godown_combo.setFixedHeight(36)
        r2.addWidget(lbl_to)
        r2.addWidget(self.to_godown_combo, 1)

        top_layout.addLayout(r2)
        layout.addWidget(top_frame)

        # Item Selection Group
        item_group = QGroupBox("Select Product && Quantity to Transfer")
        item_group.setStyleSheet("QGroupBox { font-weight: bold; color: #0f172a; margin-top: 6px; } QGroupBox::title { subcontrol-origin: margin; left: 10px; }")
        ig_layout = QVBoxLayout(item_group)
        ig_layout.setContentsMargins(10, 14, 10, 10)
        ig_layout.setSpacing(8)

        row_item = QHBoxLayout()
        row_item.setSpacing(8)

        lbl_prod = QLabel("Product:")
        lbl_prod.setStyleSheet("font-weight: 600;")
        self.product_combo = QComboBox()
        self.product_combo.setEditable(True)
        self.product_combo.setInsertPolicy(QComboBox.NoInsert)
        self.product_combo.setFixedHeight(36)
        self.product_combo.currentIndexChanged.connect(self.on_product_selected)
        row_item.addWidget(lbl_prod)
        row_item.addWidget(self.product_combo, 3)

        lbl_qty = QLabel("Qty:")
        lbl_qty.setStyleSheet("font-weight: 600;")
        self.qty_input = QDoubleSpinBox()
        self.qty_input.setRange(0.01, 999999.0)
        self.qty_input.setValue(1.0)
        self.qty_input.setFixedHeight(36)
        self.qty_input.setFixedWidth(90)
        row_item.addWidget(lbl_qty)
        row_item.addWidget(self.qty_input)

        lbl_unit = QLabel("Unit:")
        lbl_unit.setStyleSheet("font-weight: 600;")
        self.unit_combo = QComboBox()
        self.unit_combo.setFixedHeight(36)
        self.unit_combo.setFixedWidth(80)
        row_item.addWidget(lbl_unit)
        row_item.addWidget(self.unit_combo)

        self.add_item_btn = QPushButton("+ Add to Transfer")
        self.add_item_btn.setProperty("class", "btn-primary")
        self.add_item_btn.setFixedHeight(36)
        self.add_item_btn.clicked.connect(self.add_item_to_transfer)
        row_item.addWidget(self.add_item_btn)

        ig_layout.addLayout(row_item)

        # Available stock hint
        self.stock_hint_lbl = QLabel("")
        self.stock_hint_lbl.setStyleSheet("font-size: 11.5px; color: #0369a1; font-weight: 500;")
        ig_layout.addWidget(self.stock_hint_lbl)

        layout.addWidget(item_group)

        # Transfer Items Table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Code", "Product Name", "Transfer Qty", "Unit", "Base Qty", "Action"
        ])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.table)

        # Remarks and Summary
        bot_row = QHBoxLayout()
        self.notes_input = QLineEdit()
        self.notes_input.setPlaceholderText("Optional transfer notes / reference...")
        self.notes_input.setFixedHeight(36)
        bot_row.addWidget(self.notes_input, 2)

        self.summary_lbl = QLabel("Total Items: 0 | Total Qty: 0")
        self.summary_lbl.setStyleSheet("font-size: 12.5px; font-weight: bold; color: #1e293b; padding: 4px 10px;")
        bot_row.addWidget(self.summary_lbl)
        layout.addLayout(bot_row)

        # Action Buttons
        btn_layout = QHBoxLayout()
        self.transfer_btn = QPushButton("Complete Transfer")
        self.transfer_btn.setProperty("class", "btn-success")
        self.transfer_btn.setFixedHeight(38)
        self.transfer_btn.clicked.connect(self.save_transfer)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setProperty("class", "btn-secondary")
        self.cancel_btn.setFixedHeight(38)
        self.cancel_btn.clicked.connect(self.reject)

        btn_layout.addStretch()
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addWidget(self.transfer_btn)
        layout.addLayout(btn_layout)

    def populate_godowns(self):
        session = Session()
        try:
            godowns = session.query(Godown).filter_by(is_active=True).order_by(Godown.name).all()
            self.from_godown_combo.blockSignals(True)
            self.to_godown_combo.blockSignals(True)
            self.from_godown_combo.clear()
            self.to_godown_combo.clear()

            # Main Shop is the primary location
            self.from_godown_combo.addItem("🏬 Main Shop", None)
            self.to_godown_combo.addItem("🏬 Main Shop", None)

            for g in godowns:
                disp = f"🏢 {g.name} ({g.code})"
                self.from_godown_combo.addItem(disp, g.id)
                self.to_godown_combo.addItem(disp, g.id)

            if self.preselected_from_id:
                idx = self.from_godown_combo.findData(self.preselected_from_id)
                if idx >= 0:
                    self.from_godown_combo.setCurrentIndex(idx)
                    self.to_godown_combo.setCurrentIndex(0)  # default to Main Shop
                else:
                    self.from_godown_combo.setCurrentIndex(0)
                    self.to_godown_combo.setCurrentIndex(1 if godowns else 0)
            else:
                self.from_godown_combo.setCurrentIndex(0)
                self.to_godown_combo.setCurrentIndex(1 if godowns else 0)

            self.from_godown_combo.blockSignals(False)
            self.to_godown_combo.blockSignals(False)
            self.load_products_for_source_godown()
        finally:
            session.close()

    def on_godown_selection_changed(self):
        self.load_products_for_source_godown()

    def load_products_for_source_godown(self):
        source_id = self.from_godown_combo.currentData()
        self.product_combo.clear()

        session = Session()
        try:
            products = session.query(Product).order_by(Product.name).all()
            for p in products:
                stock = get_location_stock(session, source_id, p.id)
                disp = f"{p.name} [{p.product_code or '-'}] (Avail: {stock:g} {p.unit or 'Pcs'})"
                self.product_combo.addItem(disp, p.id)

            self.on_product_selected()
        finally:
            session.close()

    def on_product_selected(self):
        prod_id = self.product_combo.currentData()
        source_id = self.from_godown_combo.currentData()
        self.unit_combo.clear()

        if not prod_id:
            self.stock_hint_lbl.setText("")
            return

        session = Session()
        try:
            p = session.query(Product).get(prod_id)
            if not p:
                return

            main_u, sub_u, rate = get_product_unit_info(p, session)
            self.unit_combo.addItem(main_u)
            if sub_u and sub_u != main_u:
                self.unit_combo.addItem(sub_u)

            stock = get_location_stock(session, source_id, p.id)
            stock_disp = format_stock_display(stock, main_u, sub_u, rate)
            source_name = "Main Shop" if not source_id else self.from_godown_combo.currentText().split(" (")[0].replace("🏢 ", "")
            self.stock_hint_lbl.setText(f"📦 Available in {source_name}: <b>{stock_disp}</b>")
        finally:
            session.close()

    def add_item_to_transfer(self):
        prod_id = self.product_combo.currentData()
        source_id = self.from_godown_combo.currentData()
        qty = self.qty_input.value()
        sel_unit = self.unit_combo.currentText().strip()

        if not prod_id:
            QMessageBox.warning(self, "Selection Error", "Please select a product.")
            return

        if qty <= 0:
            QMessageBox.warning(self, "Invalid Quantity", "Transfer quantity must be greater than zero.")
            return

        session = Session()
        try:
            prod = session.query(Product).get(prod_id)
            if not prod:
                return

            base_qty = calculate_base_qty(prod, qty, sel_unit, session)
            available_stock = get_location_stock(session, source_id, prod_id)

            # Check if already added in current transfer batch
            already_added_base = sum(
                item["base_qty"] for item in self.transfer_items if item["product_id"] == prod_id
            )

            if (already_added_base + base_qty) > available_stock:
                main_u, sub_u, rate = get_product_unit_info(prod, session)
                avail_disp = format_stock_display(available_stock, main_u, sub_u, rate)
                source_name = "Main Shop" if not source_id else "source godown"
                QMessageBox.warning(
                    self, "Insufficient Stock",
                    f"Cannot transfer {qty} {sel_unit}.\n"
                    f"Available in {source_name}: {avail_disp}\n"
                    f"Already in transfer list: {already_added_base:g} base units."
                )
                return

            item_data = {
                "product_id": prod.id,
                "code": prod.product_code or "-",
                "name": prod.name,
                "qty": qty,
                "unit": sel_unit,
                "base_qty": base_qty
            }
            self.transfer_items.append(item_data)
            self.refresh_transfer_table()
            self.qty_input.setValue(1.0)
        finally:
            session.close()

    def refresh_transfer_table(self):
        self.table.setRowCount(len(self.transfer_items))
        total_qty = 0.0

        for row, item in enumerate(self.transfer_items):
            total_qty += item["qty"]

            c_item = QTableWidgetItem(item["code"])
            c_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 0, c_item)

            self.table.setItem(row, 1, QTableWidgetItem(item["name"]))

            q_item = QTableWidgetItem(f"{item['qty']:g}")
            q_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(row, 2, q_item)

            u_item = QTableWidgetItem(item["unit"])
            u_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 3, u_item)

            b_item = QTableWidgetItem(f"{item['base_qty']:g}")
            b_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(row, 4, b_item)

            del_btn = QPushButton("Remove")
            del_btn.setProperty("class", "btn-danger")
            del_btn.setFixedHeight(28)
            del_btn.clicked.connect(lambda _, r=row: self.remove_item(r))
            self.table.setCellWidget(row, 5, del_btn)

        self.summary_lbl.setText(f"Total Items: {len(self.transfer_items)} | Total Qty: {total_qty:g}")

    def remove_item(self, row):
        if 0 <= row < len(self.transfer_items):
            self.transfer_items.pop(row)
            self.refresh_transfer_table()

    def save_transfer(self):
        trf_no = self.trf_no_input.text().strip()
        from_id = self.from_godown_combo.currentData()
        to_id = self.to_godown_combo.currentData()
        trf_date = self.date_input.date().toPython()
        notes = self.notes_input.text().strip() or None

        if not trf_no:
            QMessageBox.warning(self, "Validation Error", "Transfer Number is required.")
            return

        if from_id == to_id:
            QMessageBox.warning(self, "Validation Error", "Source and Destination locations cannot be the same.")
            return

        if not self.transfer_items:
            QMessageBox.warning(self, "Validation Error", "Please add at least one product to transfer.")
            return

        session = Session()
        try:
            # Check transfer number uniqueness
            existing = session.query(GodownTransfer).filter_by(transfer_number=trf_no).first()
            if existing:
                QMessageBox.warning(self, "Validation Error", f"Transfer Number '{trf_no}' already exists.")
                return

            # Verify stock availability for all items before committing
            for item in self.transfer_items:
                current_stock = get_location_stock(session, from_id, item["product_id"])
                if current_stock < item["base_qty"]:
                    p = session.query(Product).get(item["product_id"])
                    p_name = p.name if p else "Product"
                    source_name = "Main Shop" if not from_id else "source godown"
                    QMessageBox.warning(
                        self, "Stock Changed",
                        f"Insufficient stock for {p_name} in {source_name}. Available: {current_stock:g}, Required: {item['base_qty']:g}."
                    )
                    return

            # Create Master Transfer record
            transfer = GodownTransfer(
                transfer_number=trf_no,
                date=trf_date,
                from_godown_id=from_id,
                to_godown_id=to_id,
                total_items=len(self.transfer_items),
                total_qty=sum(i["qty"] for i in self.transfer_items),
                notes=notes
            )
            session.add(transfer)
            session.flush()

            # Create items and adjust stocks
            for item in self.transfer_items:
                trf_item = GodownTransferItem(
                    transfer_id=transfer.id,
                    product_id=item["product_id"],
                    qty=item["qty"],
                    base_qty=item["base_qty"],
                    unit=item["unit"]
                )
                session.add(trf_item)

                # Deduct from source godown if from_id is a godown
                if from_id:
                    adjust_godown_stock(session, from_id, item["product_id"], -item["base_qty"])

                # Add to destination godown if to_id is a godown
                if to_id:
                    adjust_godown_stock(session, to_id, item["product_id"], +item["base_qty"])

            session.commit()
            QMessageBox.information(
                self, "Transfer Completed",
                f"Stock transfer {trf_no} completed successfully!\n"
                f"{len(self.transfer_items)} items moved successfully."
            )
            self.accept()
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Transfer Error", f"Failed to complete stock transfer: {e}")
        finally:
            session.close()


class GodownsView(QWidget):
    """Main view for Godowns Master management in Master Records."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)

        # Informative Banner
        info_frame = QFrame()
        info_frame.setStyleSheet("""
            QFrame {
                background-color: #f0fdf4;
                border: 1px solid #bbf7d0;
                border-radius: 8px;
                padding: 10px 14px;
            }
        """)
        info_layout = QHBoxLayout(info_frame)
        info_layout.setContentsMargins(4, 2, 4, 2)
        info_layout.setSpacing(10)
        
        info_icon = QLabel("🏬")
        info_icon.setStyleSheet("font-size: 20px;")
        info_lbl = QLabel(
            "<b>Default Receiving & Sales:</b> All purchases and counter sales default to the <b>Main Shop</b>. "
            "Godowns/Warehouses are <b>optional</b> secondary storage facilities for bulk inventory and warehousing."
        )
        info_lbl.setStyleSheet("font-size: 12.5px; color: #166534;")
        info_layout.addWidget(info_icon)
        info_layout.addWidget(info_lbl, 1)
        layout.addWidget(info_frame)

        # Top Bar (Search & Action Buttons)
        top_bar = QHBoxLayout()
        top_bar.setSpacing(10)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search godowns by name, code, location, contact...")
        self.search_input.setFixedHeight(38)
        self.search_input.textChanged.connect(self.refresh_data)
        top_bar.addWidget(self.search_input, 3)

        self.status_filter_combo = QComboBox()
        self.status_filter_combo.addItems(["All Godowns", "Active Only", "Inactive Only"])
        self.status_filter_combo.setFixedHeight(38)
        self.status_filter_combo.currentIndexChanged.connect(self.refresh_data)
        top_bar.addWidget(self.status_filter_combo, 1)

        self.add_btn = QPushButton("+ Add Godown (Ctrl+N)")
        self.add_btn.setToolTip("Add new godown (Ctrl+N)")
        self.add_btn.setFixedHeight(38)
        self.add_btn.clicked.connect(self.add_godown)
        top_bar.addWidget(self.add_btn)

        self.transfer_btn = QPushButton("📦 Stock Transfer")
        self.transfer_btn.setToolTip("Transfer stock between Main Shop and godowns")
        self.transfer_btn.setProperty("class", "btn-primary")
        self.transfer_btn.setFixedHeight(38)
        self.transfer_btn.clicked.connect(self.open_stock_transfer)
        top_bar.addWidget(self.transfer_btn)

        self.view_stock_btn = QPushButton("📋 View Stock")
        self.view_stock_btn.setToolTip("View stock stored in selected godown")
        self.view_stock_btn.setProperty("class", "btn-secondary")
        self.view_stock_btn.setFixedHeight(38)
        self.view_stock_btn.clicked.connect(self.view_godown_stock)
        top_bar.addWidget(self.view_stock_btn)

        self.edit_btn = QPushButton("Edit")
        self.edit_btn.setProperty("class", "btn-secondary")
        self.edit_btn.setFixedHeight(38)
        self.edit_btn.clicked.connect(self.edit_godown)
        top_bar.addWidget(self.edit_btn)

        self.delete_btn = QPushButton("Deactivate")
        self.delete_btn.setProperty("class", "btn-danger")
        self.delete_btn.setFixedHeight(38)
        self.delete_btn.clicked.connect(self.delete_or_deactivate_godown)
        top_bar.addWidget(self.delete_btn)

        layout.addLayout(top_bar)

        # Godowns Table
        self.table = QTableWidget()
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels([
            "ID", "Code", "Godown Name", "Location", "Contact Person",
            "Contact Phone", "Stock Items", "Total Qty", "Status"
        ])
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.doubleClicked.connect(self.view_godown_stock)
        layout.addWidget(self.table)

        self.refresh_data()

    def refresh_data(self):
        session = Session()
        try:
            query = session.query(Godown)
            filter_mode = self.status_filter_combo.currentIndex()
            if filter_mode == 1:
                query = query.filter_by(is_active=True)
            elif filter_mode == 2:
                query = query.filter_by(is_active=False)

            search_text = self.search_input.text().strip()
            if search_text:
                term = f"%{search_text}%"
                query = query.filter(
                    (Godown.name.ilike(term)) |
                    (Godown.code.ilike(term)) |
                    (Godown.location.ilike(term)) |
                    (Godown.contact_person.ilike(term)) |
                    (Godown.contact_phone.ilike(term))
                )

            godowns = query.order_by(Godown.is_default.desc(), Godown.name).all()

            self.table.setRowCount(len(godowns))
            for row, g in enumerate(godowns):
                # ID
                id_item = QTableWidgetItem(str(g.id))
                id_item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, 0, id_item)

                # Code
                code_item = QTableWidgetItem(g.code or "-")
                code_item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, 1, code_item)

                # Name
                name_item = QTableWidgetItem(g.name)
                self.table.setItem(row, 2, name_item)

                # Location
                self.table.setItem(row, 3, QTableWidgetItem(g.location or "-"))

                # Contact Person
                self.table.setItem(row, 4, QTableWidgetItem(g.contact_person or "-"))

                # Contact Phone
                p_item = QTableWidgetItem(g.contact_phone or "-")
                p_item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, 5, p_item)

                # Stock Items Count & Total Qty
                stocks = session.query(GodownStock).filter(
                    GodownStock.godown_id == g.id,
                    GodownStock.stock_qty > 0
                ).all()
                stored_items_count = len(stocks)
                stored_total_qty = sum(s.stock_qty for s in stocks)

                cnt_item = QTableWidgetItem(str(stored_items_count))
                cnt_item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, 6, cnt_item)

                qty_item = QTableWidgetItem(f"{stored_total_qty:g}")
                qty_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.table.setItem(row, 7, qty_item)

                # Status
                st_text = "Active" if g.is_active else "Inactive"
                st_item = QTableWidgetItem(st_text)
                st_item.setTextAlignment(Qt.AlignCenter)
                if not g.is_active:
                    st_item.setForeground(Qt.red)
                self.table.setItem(row, 8, st_item)
        finally:
            session.close()

    def get_selected_godown(self):
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "Selection Required", "Please select a godown from the table.")
            return None
        row = selected_rows[0].row()
        godown_id = int(self.table.item(row, 0).text())
        session = Session()
        try:
            return session.query(Godown).get(godown_id)
        finally:
            session.close()

    def add_godown(self):
        dialog = GodownDialog(parent=self)
        if dialog.exec_():
            self.refresh_data()

    def edit_godown(self):
        godown = self.get_selected_godown()
        if not godown:
            return
        dialog = GodownDialog(godown=godown, parent=self)
        if dialog.exec_():
            self.refresh_data()

    def view_godown_stock(self):
        godown = self.get_selected_godown()
        if not godown:
            return
        dialog = GodownStockDialog(godown_id=godown.id, parent=self)
        dialog.exec_()

    def open_stock_transfer(self):
        selected = self.get_selected_godown()
        from_id = selected.id if selected else None
        dialog = GodownTransferDialog(from_godown_id=from_id, parent=self)
        if dialog.exec_():
            self.refresh_data()

    def set_as_default(self):
        godown = self.get_selected_godown()
        if not godown:
            return

        if godown.is_default:
            QMessageBox.information(self, "Already Default", f"'{godown.name}' is already the default godown.")
            return

        session = Session()
        try:
            session.query(Godown).update({Godown.is_default: False})
            g = session.query(Godown).get(godown.id)
            g.is_default = True
            g.is_active = True
            session.commit()
            QMessageBox.information(self, "Default Updated", f"'{godown.name}' is now set as the primary default godown.")
            self.refresh_data()
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", f"Failed to set default godown: {e}")
        finally:
            session.close()

    def delete_or_deactivate_godown(self):
        godown = self.get_selected_godown()
        if not godown:
            return

        session = Session()
        try:
            # Check if godown holds active stock
            active_stock = session.query(func.sum(GodownStock.stock_qty)).filter(
                GodownStock.godown_id == godown.id,
                GodownStock.stock_qty > 0
            ).scalar() or 0.0

            if active_stock > 0:
                # If it has stock, do not hard-delete; offer deactivation
                reply = QMessageBox.question(
                    self, "Active Stock Present",
                    f"'{godown.name}' currently has {active_stock:g} units of stock stored.\n\n"
                    f"Do you want to deactivate this godown instead of deleting it?\n"
                    f"(Use 'Inter-Godown Stock Transfer' if you wish to move this stock to another godown first).",
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes
                )
                if reply == QMessageBox.Yes:
                    g = session.query(Godown).get(godown.id)
                    g.is_active = False
                    session.commit()
                    QMessageBox.information(self, "Godown Deactivated", f"'{godown.name}' has been marked inactive.")
                    self.refresh_data()
                return

            reply = QMessageBox.question(
                self, "Confirm Delete",
                f"Are you sure you want to delete godown '{godown.name}' ({godown.code})?\nThis cannot be undone.",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                g = session.query(Godown).get(godown.id)
                session.delete(g)
                session.commit()
                QMessageBox.information(self, "Deleted", f"Godown '{godown.name}' deleted successfully.")
                self.refresh_data()
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", f"Failed to delete or deactivate godown: {e}")
        finally:
            session.close()

    def retranslate_ui(self):
        pass
