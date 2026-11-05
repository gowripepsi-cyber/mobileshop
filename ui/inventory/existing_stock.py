import datetime
import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QLineEdit,
    QComboBox, QDateEdit, QSpinBox, QDoubleSpinBox, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QMessageBox, QFrame, QTabWidget, QDialog,
    QFileDialog
)
from PySide6.QtCore import Qt, QDate
from utils.formatters import format_inr
from database import Session
from models import Product, Category, Unit, ExistingStockMaster, ExistingStockItem
from utils.ui_helpers import enable_quick_add_auto_select, SearchableProductComboBox, AutoClearSearchableComboBox


class ExistingStockView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.stock_items = []  # list of dicts: {"product_id": int, "code": str, "name": str, "category": str, "current_stock": int, "qty": int, "unit": str, "rate": float, "selling_price": float}
        self.products_cache = {}
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)

        # Tab Widget
        self.tabs = QTabWidget()
        self.tabs.setObjectName("existing_stock_tabs")

        # Tab 1: Upload Existing Stock
        self.entry_tab = QWidget()
        self.setup_entry_tab()
        self.tabs.addTab(self.entry_tab, "Upload Existing Stock")

        # Tab 2: Upload History
        self.history_tab = QWidget()
        self.setup_history_tab()
        self.tabs.addTab(self.history_tab, "Stock Upload History")

        layout.addWidget(self.tabs)

        # Initial load
        self.refresh_data()

    def setup_entry_tab(self):
        tab_layout = QVBoxLayout(self.entry_tab)
        tab_layout.setContentsMargins(12, 12, 12, 12)
        tab_layout.setSpacing(10)

        # Header Card: Title + Subtitle + Excel Import Actions
        header_card = QFrame()
        header_card.setProperty("class", "CardFrame")
        header_layout = QHBoxLayout(header_card)
        header_layout.setContentsMargins(16, 10, 16, 10)
        header_layout.setSpacing(15)

        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        title_lbl = QLabel("Upload Existing Stock / Opening Inventory")
        title_lbl.setStyleSheet("font-size: 15px; font-weight: bold; color: #0f172a;")
        sub_lbl = QLabel("Add on-hand shop stock and initial opening inventory without supplier bills or payment records.")
        sub_lbl.setStyleSheet("font-size: 11.5px; color: #64748b;")
        title_box.addWidget(title_lbl)
        title_box.addWidget(sub_lbl)
        header_layout.addLayout(title_box, 1)

        # Excel Import Actions
        self.download_tmpl_btn = QPushButton("📥 Download Excel Template")
        self.download_tmpl_btn.setProperty("class", "btn-secondary")
        self.download_tmpl_btn.setFixedHeight(34)
        self.download_tmpl_btn.setCursor(Qt.PointingHandCursor)
        self.download_tmpl_btn.setToolTip("Download sample Excel template for bulk stock upload")
        self.download_tmpl_btn.clicked.connect(self.download_sample_template)
        header_layout.addWidget(self.download_tmpl_btn)

        self.import_excel_btn = QPushButton("📁 Import Excel / CSV")
        self.import_excel_btn.setProperty("class", "btn-secondary")
        self.import_excel_btn.setFixedHeight(34)
        self.import_excel_btn.setCursor(Qt.PointingHandCursor)
        self.import_excel_btn.setToolTip("Import existing stock from Excel or CSV file")
        self.import_excel_btn.clicked.connect(self.import_excel_csv)
        header_layout.addWidget(self.import_excel_btn)

        tab_layout.addWidget(header_card)

        # Form Card: Add Items to Stock Entry (Single Clean Row)
        form_card = QFrame()
        form_card.setProperty("class", "CardFrame")
        form_layout = QVBoxLayout(form_card)
        form_layout.setContentsMargins(16, 10, 16, 12)
        form_layout.setSpacing(8)

        card_title = QLabel("Add Stock Item")
        card_title.setStyleSheet("font-size: 13.5px; font-weight: bold; color: #0f172a;")
        form_layout.addWidget(card_title)

        row_layout = QHBoxLayout()
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(8)

        def make_field(label_text, widget, width=None, stretch=0):
            w = QWidget()
            vl = QVBoxLayout(w)
            vl.setContentsMargins(0, 0, 0, 0)
            vl.setSpacing(3)
            lbl_f = QLabel(label_text)
            lbl_f.setStyleSheet("font-size: 11.5px; font-weight: 600; color: #475569;")
            vl.addWidget(lbl_f)
            vl.addWidget(widget)
            if width:
                w.setFixedWidth(width)
            return w

        # Common input styling to guarantee EXACT same 36px height as Item Name combo box
        input_style = "min-height: 28px; padding: 2px 8px;"

        # 1. Product Code (6 digits max)
        self.product_code_input = QLineEdit()
        self.product_code_input.setPlaceholderText("Code")
        self.product_code_input.setStyleSheet(input_style)
        self.product_code_input.returnPressed.connect(self.handle_product_code_entry)
        self.product_code_input._skip_enter_nav = True

        # 2. Category Filter (50% width increased: 160px)
        self.category_combo = AutoClearSearchableComboBox()
        self.category_combo.setPlaceholderText("Category")
        self.category_combo.currentIndexChanged.connect(self.filter_products_by_category)
        self.category_combo.currentTextChanged.connect(self.filter_products_by_category)
        if self.category_combo.lineEdit():
            self.category_combo.lineEdit().textChanged.connect(self.filter_products_by_category)

        # 3. Item Name + Quick Add Button
        self.product_combo = SearchableProductComboBox()
        self.product_combo.setPlaceholderText("Select / Search Product")
        self.product_combo.currentIndexChanged.connect(self.update_fields_on_product_change)
        self.product_combo.currentTextChanged.connect(self.check_product_match)
        if self.product_combo.lineEdit():
            self.product_combo.lineEdit().textChanged.connect(self.check_product_match)

        self.add_product_btn = QPushButton("+")
        self.add_product_btn.setToolTip("Add new product to master records")
        self.add_product_btn.setProperty("class", "btn-quick-add")
        self.add_product_btn.setStyleSheet("min-height: 36px; max-height: 36px; margin: 0px; padding: 0px; font-size: 18px; font-weight: bold; border-radius: 6px;")
        self.add_product_btn.setFixedWidth(32)
        self.add_product_btn.setCursor(Qt.PointingHandCursor)
        self.add_product_btn.clicked.connect(self.handle_add_product_click)
        self.add_product_btn.hide()

        prod_widget = QWidget()
        prod_layout = QHBoxLayout(prod_widget)
        prod_layout.setContentsMargins(0, 0, 0, 0)
        prod_layout.setSpacing(4)
        prod_layout.addWidget(self.product_combo, 1)
        prod_layout.addWidget(self.add_product_btn)

        # 4. In-Stock Status Badge (matching 36px height)
        self.current_stock_lbl = QLabel("-")
        self.current_stock_lbl.setAlignment(Qt.AlignCenter)
        self.current_stock_lbl.setStyleSheet("""
            min-height: 28px;
            max-height: 28px;
            font-size: 11.5px;
            font-weight: 600;
            color: #2563eb;
            background-color: #eff6ff;
            border: 1.5px solid #bfdbfe;
            border-radius: 8px;
            padding: 2px 4px;
        """)

        # 5. Quantity (3-5 chars)
        self.qty_input = QSpinBox()
        self.qty_input.setRange(1, 99999)
        self.qty_input.setValue(1)
        self.qty_input.setStyleSheet(input_style)

        # 6. Unit
        self.unit_combo = QComboBox()
        self.unit_combo.setStyleSheet(input_style)
        self.load_units()

        # 7. Cost Price
        self.rate_input = QDoubleSpinBox()
        self.rate_input.setRange(0.0, 9999999.0)
        self.rate_input.setValue(0.0)
        self.rate_input.setDecimals(2)
        self.rate_input.setStyleSheet(input_style)

        # 8. Selling Price
        self.selling_price_input = QDoubleSpinBox()
        self.selling_price_input.setRange(0.0, 9999999.0)
        self.selling_price_input.setValue(0.0)
        self.selling_price_input.setDecimals(2)
        self.selling_price_input.setStyleSheet(input_style)

        # 9. Add Item Button (matching 36px height)
        self.add_item_btn = QPushButton("Add Item")
        self.add_item_btn.setProperty("class", "btn-success")
        self.add_item_btn.setStyleSheet("min-height: 36px; max-height: 36px; padding: 0px 10px; margin: 0px; border-radius: 8px;")
        self.add_item_btn.setCursor(Qt.PointingHandCursor)
        self.add_item_btn.clicked.connect(self.add_item_to_list)

        btn_w = QWidget()
        btn_w.setFixedWidth(85)
        btn_w_l = QVBoxLayout(btn_w)
        btn_w_l.setContentsMargins(0, 0, 0, 0)
        btn_w_l.setSpacing(3)
        lbl_spacer = QLabel(" ")
        lbl_spacer.setStyleSheet("font-size: 11.5px;")
        btn_w_l.addWidget(lbl_spacer)
        btn_w_l.addWidget(self.add_item_btn)

        f_code = make_field("Product Code", self.product_code_input, width=90)
        f_cat = make_field("Category", self.category_combo, width=160)
        f_prod = make_field("Item Name *", prod_widget)
        f_prod.setMinimumWidth(160)
        f_stock = make_field("In-Stock", self.current_stock_lbl, width=65)
        f_qty = make_field("Qty *", self.qty_input, width=70)
        f_unit = make_field("Unit", self.unit_combo, width=65)
        f_rate = make_field("Cost Price (₹)", self.rate_input, width=90)
        f_sell = make_field("Selling Price (₹)", self.selling_price_input, width=90)

        row_layout.addWidget(f_code)
        row_layout.addWidget(f_cat)
        row_layout.addWidget(f_prod, 1)  # Stretches to fill available space
        row_layout.addWidget(f_stock)
        row_layout.addWidget(f_qty)
        row_layout.addWidget(f_unit)
        row_layout.addWidget(f_rate)
        row_layout.addWidget(f_sell)
        row_layout.addWidget(btn_w)

        form_layout.addLayout(row_layout)
        tab_layout.addWidget(form_card)

        # Table Card: Items to Upload (stretch 1)
        table_card = QFrame()
        table_card.setProperty("class", "CardFrame")
        table_layout = QVBoxLayout(table_card)
        table_layout.setContentsMargins(16, 12, 16, 14)
        table_layout.setSpacing(10)

        tbl_header = QHBoxLayout()
        tbl_title = QLabel("Stock Items List")
        tbl_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #0f172a;")
        tbl_header.addWidget(tbl_title)
        tbl_header.addStretch()

        self.items_count_badge = QLabel("0 Items Added")
        self.items_count_badge.setStyleSheet("font-size: 12px; font-weight: 600; color: #475569;")
        tbl_header.addWidget(self.items_count_badge)
        table_layout.addLayout(tbl_header)

        self.table = QTableWidget()
        self.table.setColumnCount(11)
        self.table.setHorizontalHeaderLabels([
            "#", "Product Code", "Item Name", "Category", "Current Stock",
            "Added Qty (+)", "New Stock", "Unit", "Cost Rate (₹)", "Selling Price (₹)", "Action"
        ])
        header = self.table.horizontalHeader()
        for c in range(10):
            header.setSectionResizeMode(c, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)  # Item Name expands
        header.setSectionResizeMode(10, QHeaderView.Fixed)   # Action button
        self.table.setColumnWidth(10, 75)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(40)
        table_layout.addWidget(self.table)

        # Bottom Summary & Action Bar: Two clean rows
        badges_row = QHBoxLayout()
        badges_row.setSpacing(12)

        self.total_items_lbl = QLabel("Total Items: 0")
        self.total_items_lbl.setStyleSheet("font-size: 12.5px; font-weight: bold; color: #0f172a; padding: 4px 10px; background: #f1f5f9; border-radius: 4px; border: 1px solid #e2e8f0;")
        badges_row.addWidget(self.total_items_lbl)

        self.total_qty_lbl = QLabel("Total Added Qty: 0")
        self.total_qty_lbl.setStyleSheet("font-size: 12.5px; font-weight: bold; color: #2563eb; padding: 4px 10px; background: #eff6ff; border-radius: 4px; border: 1px solid #bfdbfe;")
        badges_row.addWidget(self.total_qty_lbl)

        self.total_val_lbl = QLabel("Total Valuation: ₹0.00")
        self.total_val_lbl.setStyleSheet("font-size: 12.5px; font-weight: bold; color: #16a34a; padding: 4px 10px; background: #f0fdf4; border-radius: 4px; border: 1px solid #bbf7d0;")
        badges_row.addWidget(self.total_val_lbl)
        badges_row.addStretch()
        table_layout.addLayout(badges_row)

        action_row = QHBoxLayout()
        action_row.setSpacing(12)

        action_row.addWidget(QLabel("Notes:"))
        self.notes_input = QLineEdit()
        self.notes_input.setPlaceholderText("Notes / Batch Ref (optional, e.g. Shop opening stock)")
        action_row.addWidget(self.notes_input, 1)

        self.clear_btn = QPushButton("Clear List")
        self.clear_btn.setProperty("class", "btn-secondary")
        self.clear_btn.setFixedHeight(36)
        self.clear_btn.setCursor(Qt.PointingHandCursor)
        self.clear_btn.clicked.connect(self.clear_items_list)
        action_row.addWidget(self.clear_btn)

        self.save_stock_btn = QPushButton("Save Existing Stock")
        self.save_stock_btn.setProperty("class", "btn-success")
        self.save_stock_btn.setFixedHeight(36)
        self.save_stock_btn.setMinimumWidth(180)
        self.save_stock_btn.setCursor(Qt.PointingHandCursor)
        self.save_stock_btn.clicked.connect(self.save_existing_stock)
        action_row.addWidget(self.save_stock_btn)

        table_layout.addLayout(action_row)
        tab_layout.addWidget(table_card, 1)

    def setup_history_tab(self):
        tab_layout = QVBoxLayout(self.history_tab)
        tab_layout.setContentsMargins(12, 12, 12, 12)
        tab_layout.setSpacing(10)

        # Filters Card
        filter_card = QFrame()
        filter_card.setProperty("class", "CardFrame")
        filter_layout = QHBoxLayout(filter_card)
        filter_layout.setContentsMargins(16, 10, 16, 10)
        filter_layout.setSpacing(12)

        filter_layout.addWidget(QLabel("Search:"))
        self.h_search_input = QLineEdit()
        self.h_search_input.setPlaceholderText("Search by Entry # or Notes...")
        self.h_search_input.textChanged.connect(self.load_history)
        filter_layout.addWidget(self.h_search_input, 2)

        filter_layout.addWidget(QLabel("From:"))
        self.h_from_date = QDateEdit()
        self.h_from_date.setCalendarPopup(True)
        self.h_from_date.setDate(QDate.currentDate().addMonths(-1))
        self.h_from_date.dateChanged.connect(self.load_history)
        filter_layout.addWidget(self.h_from_date)

        filter_layout.addWidget(QLabel("To:"))
        self.h_to_date = QDateEdit()
        self.h_to_date.setCalendarPopup(True)
        self.h_to_date.setDate(QDate.currentDate())
        self.h_to_date.dateChanged.connect(self.load_history)
        filter_layout.addWidget(self.h_to_date)

        self.refresh_hist_btn = QPushButton("Refresh")
        self.refresh_hist_btn.setProperty("class", "btn-secondary")
        self.refresh_hist_btn.setFixedHeight(32)
        self.refresh_hist_btn.setCursor(Qt.PointingHandCursor)
        self.refresh_hist_btn.clicked.connect(self.load_history)
        filter_layout.addWidget(self.refresh_hist_btn)

        tab_layout.addWidget(filter_card)

        # History Table Card
        hist_table_card = QFrame()
        hist_table_card.setProperty("class", "CardFrame")
        hist_table_layout = QVBoxLayout(hist_table_card)
        hist_table_layout.setContentsMargins(16, 12, 16, 14)
        hist_table_layout.setSpacing(10)

        hist_title = QLabel("Stock Upload Log")
        hist_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #0f172a;")
        hist_table_layout.addWidget(hist_title)

        self.history_table = QTableWidget()
        self.history_table.setColumnCount(7)
        self.history_table.setHorizontalHeaderLabels([
            "Entry #", "Date", "Total Items", "Total Qty", "Total Valuation (₹)", "Notes", "Actions"
        ])
        h_header = self.history_table.horizontalHeader()
        h_header.setSectionResizeMode(QHeaderView.Stretch)
        h_header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        h_header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        h_header.setSectionResizeMode(6, QHeaderView.Fixed)
        self.history_table.setColumnWidth(6, 160)
        self.history_table.verticalHeader().setVisible(False)
        self.history_table.verticalHeader().setDefaultSectionSize(46)
        hist_table_layout.addWidget(self.history_table)

        tab_layout.addWidget(hist_table_card, 1)

    # ---------------- Data Loading & Helpers ----------------

    def refresh_data(self):
        self.load_categories()
        self.load_units()
        self.refresh_products_cache()
        self.load_history()

    def load_categories(self):
        self.category_combo.blockSignals(True)
        self.category_combo.clear()
        self.category_combo.addItem("-- All Categories --", None)
        session = Session()
        try:
            cats = session.query(Category).order_by(Category.name.asc()).all()
            for c in cats:
                self.category_combo.addItem(c.name, c.id)
        except Exception as e:
            print(f"Error loading categories: {e}")
        finally:
            session.close()
        self.category_combo.blockSignals(False)

    def load_units(self):
        self.unit_combo.blockSignals(True)
        self.unit_combo.clear()
        session = Session()
        try:
            units = session.query(Unit).order_by(Unit.name.asc()).all()
            for u in units:
                self.unit_combo.addItem(u.name, u.id)
        except Exception as e:
            print(f"Error loading units: {e}")
        finally:
            session.close()

        if self.unit_combo.count() == 0:
            self.unit_combo.addItems(["Pcs", "Box", "Nos", "Kg", "Meter", "Set"])

        idx = self.unit_combo.findText("Pcs")
        if idx >= 0:
            self.unit_combo.setCurrentIndex(idx)
        self.unit_combo.blockSignals(False)

    def refresh_products_cache(self):
        session = Session()
        try:
            prods = session.query(Product).order_by(Product.name.asc()).all()
            self.products_cache = {p.id: p for p in prods}
            self.filter_products_by_category()
        except Exception as e:
            print(f"Error caching products: {e}")
        finally:
            session.close()

    def filter_products_by_category(self, *args):
        if not hasattr(self, 'products_cache'):
            return

        cat_name = self.category_combo.currentText().strip()
        cat_lower = cat_name.lower()
        is_all = not cat_lower or cat_lower in ("-- all categories --", "select category", "all")

        filtered = []
        if is_all:
            filtered = list(self.products_cache.values())
        else:
            filtered = [p for p in self.products_cache.values() if p.category and p.category.lower() == cat_lower]

        self.product_combo.set_products(filtered)

    def handle_product_code_entry(self):
        code = self.product_code_input.text().strip()
        if not code:
            return

        found = None
        for p in self.products_cache.values():
            if p.product_code and p.product_code.strip().lower() == code.lower():
                found = p
                break

        if found:
            # Set category
            if found.category:
                idx = self.category_combo.findText(found.category)
                if idx >= 0:
                    self.category_combo.setCurrentIndex(idx)

            # Select product in combo
            idx = self.product_combo.findData(found.id)
            if idx >= 0:
                self.product_combo.setCurrentIndex(idx)
            else:
                self.product_combo.addItem(found.name, found.id)
                self.product_combo.setCurrentIndex(self.product_combo.count() - 1)

            self.qty_input.setFocus()
            self.qty_input.selectAll()
        else:
            QMessageBox.information(self, "Not Found", f"No product found with code '{code}'. You can select from Item Name or click '+' to add.")

    def update_fields_on_product_change(self):
        prod_id = self.product_combo.currentData()
        if prod_id and prod_id in self.products_cache:
            prod = self.products_cache[prod_id]
            if prod.product_code:
                self.product_code_input.setText(prod.product_code)
            self.rate_input.setValue(prod.purchase_price or 0.0)
            self.selling_price_input.setValue(prod.selling_price or 0.0)
            if prod.unit:
                idx = self.unit_combo.findText(prod.unit)
                if idx >= 0:
                    self.unit_combo.setCurrentIndex(idx)
            self.current_stock_lbl.setText(f"{prod.stock_qty} {prod.unit or 'Pcs'}")
        else:
            self.current_stock_lbl.setText("-")

    def check_product_match(self):
        text = self.product_combo.currentText().strip()
        if not text or text == "Select Product":
            self.add_product_btn.hide()
            return

        exists = any(p.name.lower() == text.lower() for p in self.products_cache.values())
        if not exists:
            self.add_product_btn.show()
        else:
            self.add_product_btn.hide()

    def handle_add_product_click(self):
        from ui.masters.products import ProductDialog
        typed = self.product_combo.currentText().strip()
        if typed == "Select Product":
            typed = ""
        current_cat = self.category_combo.currentText().strip()
        def_cat = current_cat if (current_cat and current_cat != "-- All Categories --") else None

        dlg = ProductDialog(initial_name=typed, default_category=def_cat, parent=self)
        if dlg.exec() == QDialog.Accepted:
            self.refresh_products_cache()
            if hasattr(dlg, 'saved_product_id'):
                idx = self.product_combo.findData(dlg.saved_product_id)
                if idx >= 0:
                    self.product_combo.setCurrentIndex(idx)
            self.add_product_btn.hide()

    # ---------------- Item List Management ----------------

    def add_item_to_list(self):
        prod_id = self.product_combo.currentData()
        if not prod_id or prod_id not in self.products_cache:
            QMessageBox.warning(self, "Validation Error", "Please select a valid product.")
            return

        prod = self.products_cache[prod_id]
        qty = self.qty_input.value()
        if qty <= 0:
            QMessageBox.warning(self, "Validation Error", "Quantity must be greater than zero.")
            return

        rate = self.rate_input.value()
        sell_price = self.selling_price_input.value()
        unit = self.unit_combo.currentText()

        # Check if already in list
        existing_item = None
        for item in self.stock_items:
            if item["product_id"] == prod_id:
                existing_item = item
                break

        if existing_item:
            existing_item["qty"] += qty
            existing_item["rate"] = rate
            existing_item["selling_price"] = sell_price
            existing_item["unit"] = unit
        else:
            self.stock_items.append({
                "product_id": prod.id,
                "code": prod.product_code or "-",
                "name": prod.name,
                "category": prod.category or "-",
                "current_stock": prod.stock_qty,
                "qty": qty,
                "unit": unit,
                "rate": rate,
                "selling_price": sell_price
            })

        self.update_table_view()

        # Reset item entry for next input
        self.product_code_input.clear()
        self.product_combo.setCurrentIndex(-1)
        self.qty_input.setValue(1)
        self.current_stock_lbl.setText("-")
        self.product_combo.setFocus()

    def update_table_view(self):
        self.table.setRowCount(len(self.stock_items))
        total_items = len(self.stock_items)
        total_qty = 0
        total_val = 0.0

        for row, item in enumerate(self.stock_items):
            total_qty += item["qty"]
            item_val = item["qty"] * item["rate"]
            total_val += item_val

            new_stock = item["current_stock"] + item["qty"]

            # #
            self.table.setItem(row, 0, QTableWidgetItem(str(row + 1)))
            # Code
            self.table.setItem(row, 1, QTableWidgetItem(str(item["code"])))
            # Name
            self.table.setItem(row, 2, QTableWidgetItem(str(item["name"])))
            # Category
            self.table.setItem(row, 3, QTableWidgetItem(str(item["category"])))
            # Current Stock
            self.table.setItem(row, 4, QTableWidgetItem(str(item["current_stock"])))
            # Added Qty
            added_item = QTableWidgetItem(f"+{item['qty']}")
            added_item.setForeground(Qt.darkGreen)
            self.table.setItem(row, 5, added_item)
            # New Stock
            new_stock_item = QTableWidgetItem(str(new_stock))
            new_stock_item.setForeground(Qt.blue)
            self.table.setItem(row, 6, new_stock_item)
            # Unit
            self.table.setItem(row, 7, QTableWidgetItem(str(item["unit"])))
            # Rate
            self.table.setItem(row, 8, QTableWidgetItem(f"₹{format_inr(item['rate'])}"))
            # Selling Price
            self.table.setItem(row, 9, QTableWidgetItem(f"₹{format_inr(item['selling_price'])}"))

            # Remove button
            del_btn = QPushButton("Remove")
            del_btn.setProperty("class", "btn-danger")
            del_btn.setFixedHeight(28)
            del_btn.setCursor(Qt.PointingHandCursor)
            del_btn.clicked.connect(lambda checked, r=row: self.remove_item(r))
            self.table.setCellWidget(row, 10, del_btn)

        self.items_count_badge.setText(f"{total_items} Items Added")
        self.total_items_lbl.setText(f"Total Items: {total_items}")
        self.total_qty_lbl.setText(f"Total Added Qty: {total_qty}")
        self.total_val_lbl.setText(f"Total Valuation: ₹{format_inr(total_val)}")

    def remove_item(self, row):
        if 0 <= row < len(self.stock_items):
            del self.stock_items[row]
            self.update_table_view()

    def clear_items_list(self):
        if not self.stock_items:
            return
        confirm = QMessageBox.question(
            self, "Clear List", "Are you sure you want to clear the entire items list?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if confirm == QMessageBox.Yes:
            self.stock_items.clear()
            self.update_table_view()

    # ---------------- Save & Commit ----------------

    def save_existing_stock(self):
        if not self.stock_items:
            QMessageBox.warning(self, "Empty List", "Please add at least one stock item to upload.")
            return

        notes = self.notes_input.text().strip() or "Existing stock upload"
        total_items = len(self.stock_items)
        total_qty = sum(item["qty"] for item in self.stock_items)
        total_val = sum(item["qty"] * item["rate"] for item in self.stock_items)

        confirm = QMessageBox.question(
            self, "Confirm Upload",
            f"Are you sure you want to upload existing stock for {total_items} item(s)?\n\n"
            f"• Total Quantity Added: {total_qty}\n"
            f"• Total Valuation: ₹{format_inr(total_val)}\n\n"
            f"This will increment each product's stock in the system.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes
        )
        if confirm != QMessageBox.Yes:
            return

        session = Session()
        try:
            # Generate Entry Number STK-1001, etc.
            last_entry = session.query(ExistingStockMaster).order_by(ExistingStockMaster.id.desc()).first()
            if last_entry and last_entry.entry_number and last_entry.entry_number.startswith("STK-"):
                try:
                    num = int(last_entry.entry_number.split("-")[1]) + 1
                    entry_no = f"STK-{num:04d}"
                except Exception:
                    entry_no = f"STK-{(last_entry.id + 1001):04d}"
            else:
                entry_no = "STK-1001"

            master = ExistingStockMaster(
                entry_number=entry_no,
                date=datetime.date.today(),
                notes=notes,
                total_items=total_items,
                total_qty=total_qty,
                total_value=total_val
            )
            session.add(master)
            session.flush()

            # Process items & increment stock
            for item in self.stock_items:
                stock_item = ExistingStockItem(
                    master_id=master.id,
                    product_id=item["product_id"],
                    qty=item["qty"],
                    rate=item["rate"],
                    selling_price=item["selling_price"],
                    unit=item["unit"],
                    total_amount=item["qty"] * item["rate"]
                )
                session.add(stock_item)

                # Increment stock on Product
                prod = session.query(Product).get(item["product_id"])
                if prod:
                    prod.stock_qty += item["qty"]
                    if item["rate"] > 0:
                        prod.purchase_price = item["rate"]
                    if item["selling_price"] > 0:
                        prod.selling_price = item["selling_price"]

            session.commit()
            QMessageBox.information(
                self, "Upload Successful",
                f"Successfully uploaded existing stock!\n\n"
                f"Entry Number: {entry_no}\n"
                f"Items Updated: {total_items}\n"
                f"Total Units Added: {total_qty}\n"
                f"Total Valuation: ₹{format_inr(total_val)}"
            )

            # Reset form & reload
            self.stock_items.clear()
            self.notes_input.clear()
            self.update_table_view()
            self.refresh_products_cache()
            self.load_history()

            # Refresh parent window views if available
            parent_win = self.window()
            if hasattr(parent_win, 'products_view') and parent_win.products_view:
                parent_win.products_view.refresh_data()
            if hasattr(parent_win, 'purchase_view') and parent_win.purchase_view:
                parent_win.purchase_view.refresh_data()
            if hasattr(parent_win, 'sales_view') and parent_win.sales_view:
                parent_win.sales_view.refresh_data()
            if hasattr(parent_win, 'dashboard_view') and parent_win.dashboard_view:
                parent_win.dashboard_view.refresh_data()

        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", f"Failed to save existing stock: {e}")
        finally:
            session.close()

    # ---------------- History Tab ----------------

    def load_history(self):
        query_text = self.h_search_input.text().strip().lower()
        from_q = self.h_from_date.date()
        to_q = self.h_to_date.date()
        from_d = datetime.date(from_q.year(), from_q.month(), from_q.day())
        to_d = datetime.date(to_q.year(), to_q.month(), to_q.day())

        session = Session()
        try:
            q = session.query(ExistingStockMaster).filter(
                ExistingStockMaster.date >= from_d,
                ExistingStockMaster.date <= to_d
            ).order_by(ExistingStockMaster.id.desc())

            records = q.all()
            if query_text:
                records = [r for r in records if (
                    query_text in r.entry_number.lower() or
                    (r.notes and query_text in r.notes.lower())
                )]

            self.history_table.setRowCount(len(records))
            for row, r in enumerate(records):
                # Entry #
                self.history_table.setItem(row, 0, QTableWidgetItem(str(r.entry_number)))
                # Date
                self.history_table.setItem(row, 1, QTableWidgetItem(r.date.strftime("%d-%m-%Y") if r.date else "-"))
                # Total Items
                self.history_table.setItem(row, 2, QTableWidgetItem(str(r.total_items)))
                # Total Qty
                self.history_table.setItem(row, 3, QTableWidgetItem(str(r.total_qty)))
                # Total Valuation
                self.history_table.setItem(row, 4, QTableWidgetItem(f"₹{format_inr(r.total_value)}"))
                # Notes
                self.history_table.setItem(row, 5, QTableWidgetItem(str(r.notes or "-")))

                # Actions Widget (View + Revert)
                act_w = QWidget()
                act_l = QHBoxLayout(act_w)
                act_l.setContentsMargins(4, 2, 4, 2)
                act_l.setSpacing(6)

                view_btn = QPushButton("View")
                view_btn.setProperty("class", "btn-secondary")
                view_btn.setFixedHeight(28)
                view_btn.setCursor(Qt.PointingHandCursor)
                view_btn.clicked.connect(lambda checked, m_id=r.id: self.view_history_details(m_id))
                act_l.addWidget(view_btn)

                del_btn = QPushButton("Revert")
                del_btn.setProperty("class", "btn-danger")
                del_btn.setFixedHeight(28)
                del_btn.setCursor(Qt.PointingHandCursor)
                del_btn.clicked.connect(lambda checked, m_id=r.id: self.revert_history_entry(m_id))
                act_l.addWidget(del_btn)

                self.history_table.setCellWidget(row, 6, act_w)

        except Exception as e:
            print(f"Error loading stock upload history: {e}")
        finally:
            session.close()

    def view_history_details(self, master_id):
        session = Session()
        try:
            master = session.query(ExistingStockMaster).get(master_id)
            if not master:
                QMessageBox.warning(self, "Error", "Stock entry record not found.")
                return

            dlg = QDialog(self)
            dlg.setWindowTitle(f"Stock Entry Details - {master.entry_number}")
            dlg.resize(750, 450)
            dlg_l = QVBoxLayout(dlg)
            dlg_l.setContentsMargins(16, 16, 16, 16)
            dlg_l.setSpacing(12)

            info_lbl = QLabel(f"<b>Entry:</b> {master.entry_number} &nbsp;|&nbsp; <b>Date:</b> {master.date} &nbsp;|&nbsp; <b>Total Items:</b> {master.total_items} &nbsp;|&nbsp; <b>Total Qty:</b> {master.total_qty} &nbsp;|&nbsp; <b>Valuation:</b> ₹{format_inr(master.total_value)}")
            info_lbl.setStyleSheet("font-size: 13px; color: #0f172a;")
            dlg_l.addWidget(info_lbl)

            table = QTableWidget()
            table.setColumnCount(7)
            table.setHorizontalHeaderLabels(["#", "Product Code", "Product Name", "Quantity", "Unit", "Cost Rate (₹)", "Total (₹)"])
            table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
            table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
            table.verticalHeader().setVisible(False)

            table.setRowCount(len(master.items))
            for i, itm in enumerate(master.items):
                p_code = itm.product.product_code if itm.product else "-"
                p_name = itm.product.name if itm.product else "Deleted Product"
                table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
                table.setItem(i, 1, QTableWidgetItem(str(p_code)))
                table.setItem(i, 2, QTableWidgetItem(str(p_name)))
                table.setItem(i, 3, QTableWidgetItem(str(itm.qty)))
                table.setItem(i, 4, QTableWidgetItem(str(itm.unit or "Pcs")))
                table.setItem(i, 5, QTableWidgetItem(f"₹{format_inr(itm.rate)}"))
                table.setItem(i, 6, QTableWidgetItem(f"₹{format_inr(itm.total_amount)}"))

            dlg_l.addWidget(table)

            close_btn = QPushButton("Close")
            close_btn.setProperty("class", "btn-secondary")
            close_btn.clicked.connect(dlg.accept)
            dlg_l.addWidget(close_btn, 0, Qt.AlignRight)

            dlg.exec()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to view details: {e}")
        finally:
            session.close()

    def revert_history_entry(self, master_id):
        confirm = QMessageBox.question(
            self, "Confirm Revert",
            "Are you sure you want to revert/delete this stock entry batch?\n\n"
            "The added quantities will be subtracted from current stock.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if confirm != QMessageBox.Yes:
            return

        session = Session()
        try:
            master = session.query(ExistingStockMaster).get(master_id)
            if not master:
                QMessageBox.warning(self, "Error", "Stock entry record not found.")
                return

            # Revert stock quantities
            for itm in master.items:
                prod = session.query(Product).get(itm.product_id)
                if prod:
                    prod.stock_qty = max(0, prod.stock_qty - itm.qty)

            session.delete(master)
            session.commit()
            QMessageBox.information(self, "Reverted", "Stock entry batch reverted successfully.")
            self.refresh_products_cache()
            self.load_history()

            parent_win = self.window()
            if hasattr(parent_win, 'products_view') and parent_win.products_view:
                parent_win.products_view.refresh_data()
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", f"Failed to revert stock entry: {e}")
        finally:
            session.close()

    # ---------------- Excel / CSV Import & Template ----------------

    def download_sample_template(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Sample Excel Template", "sample_existing_stock_template.xlsx",
            "Excel Files (*.xlsx);;CSV Files (*.csv)"
        )
        if not file_path:
            return

        try:
            import pandas as pd
            sample_data = {
                "Product Code": ["PRD-1001", "PRD-1002", "PRD-1003"],
                "Product Name": ["Samsung Galaxy A15 (Blue)", "iPhone 15 Screen Guard (2.5D)", "Type-C Fast Charging Cable 1M"],
                "Category": ["Smartphones", "Accessories", "Cables"],
                "Brand": ["Samsung", "Apple", "Boat"],
                "Quantity": [10, 50, 25],
                "Unit": ["Pcs", "Pcs", "Pcs"],
                "Cost Price": [13500.0, 45.0, 120.0],
                "Selling Price": [15999.0, 150.0, 299.0]
            }
            df = pd.DataFrame(sample_data)
            if file_path.endswith(".csv"):
                df.to_csv(file_path, index=False)
            else:
                df.to_excel(file_path, index=False)

            QMessageBox.information(
                self, "Template Saved",
                f"Sample template saved successfully to:\n{file_path}\n\n"
                f"Fill in your existing items and use 'Import Excel / CSV' to upload."
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate template: {e}")

    def import_excel_csv(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Excel / CSV File to Import", "",
            "Excel / CSV Files (*.xlsx *.xls *.csv);;Excel Files (*.xlsx *.xls);;CSV Files (*.csv)"
        )
        if not file_path:
            return

        try:
            import pandas as pd
            if file_path.endswith(".csv"):
                df = pd.read_csv(file_path)
            else:
                df = pd.read_excel(file_path)

            # Normalize column names
            col_map = {}
            for col in df.columns:
                c_clean = str(col).strip().lower().replace("_", " ")
                if "code" in c_clean:
                    col_map["code"] = col
                elif "name" in c_clean or "item" in c_clean or "product" in c_clean:
                    col_map["name"] = col
                elif "cat" in c_clean:
                    col_map["category"] = col
                elif "brand" in c_clean:
                    col_map["brand"] = col
                elif "qty" in c_clean or "quantity" in c_clean or "stock" in c_clean:
                    col_map["qty"] = col
                elif "unit" in c_clean:
                    col_map["unit"] = col
                elif "cost" in c_clean or "purchase" in c_clean or "rate" in c_clean or "buy" in c_clean:
                    col_map["rate"] = col
                elif "sell" in c_clean or "mrp" in c_clean or "price" in c_clean:
                    col_map["selling_price"] = col

            if "name" not in col_map and "code" not in col_map:
                QMessageBox.warning(self, "Format Error", "The file must contain at least a 'Product Name' or 'Product Code' column.")
                return

            imported_count = 0
            session = Session()
            try:
                for _, row in df.iterrows():
                    code = str(row[col_map["code"]]).strip() if "code" in col_map and pd.notna(row[col_map["code"]]) else ""
                    name = str(row[col_map["name"]]).strip() if "name" in col_map and pd.notna(row[col_map["name"]]) else ""
                    if not name and not code:
                        continue

                    category = str(row[col_map["category"]]).strip() if "category" in col_map and pd.notna(row[col_map["category"]]) else "General"
                    brand = str(row[col_map["brand"]]).strip() if "brand" in col_map and pd.notna(row[col_map["brand"]]) else ""
                    unit = str(row[col_map["unit"]]).strip() if "unit" in col_map and pd.notna(row[col_map["unit"]]) else "Pcs"

                    try:
                        qty = int(row[col_map["qty"]]) if "qty" in col_map and pd.notna(row[col_map["qty"]]) else 1
                    except Exception:
                        qty = 1

                    try:
                        rate = float(row[col_map["rate"]]) if "rate" in col_map and pd.notna(row[col_map["rate"]]) else 0.0
                    except Exception:
                        rate = 0.0

                    try:
                        sell_price = float(row[col_map["selling_price"]]) if "selling_price" in col_map and pd.notna(row[col_map["selling_price"]]) else 0.0
                    except Exception:
                        sell_price = 0.0

                    # Look up product
                    prod = None
                    if code:
                        prod = session.query(Product).filter_by(product_code=code).first()
                    if not prod and name:
                        prod = session.query(Product).filter_by(name=name).first()

                    # Auto-create if not found
                    if not prod:
                        prod = Product(
                            product_code=code or None,
                            name=name,
                            category=category,
                            brand=brand,
                            unit=unit,
                            purchase_price=rate,
                            selling_price=sell_price,
                            stock_qty=0
                        )
                        session.add(prod)
                        session.flush()

                    # Add to stock items list
                    existing_item = None
                    for itm in self.stock_items:
                        if itm["product_id"] == prod.id:
                            existing_item = itm
                            break

                    if existing_item:
                        existing_item["qty"] += qty
                        if rate > 0:
                            existing_item["rate"] = rate
                        if sell_price > 0:
                            existing_item["selling_price"] = sell_price
                    else:
                        self.stock_items.append({
                            "product_id": prod.id,
                            "code": prod.product_code or "-",
                            "name": prod.name,
                            "category": prod.category or "-",
                            "current_stock": prod.stock_qty,
                            "qty": qty,
                            "unit": prod.unit or unit,
                            "rate": rate or prod.purchase_price,
                            "selling_price": sell_price or prod.selling_price
                        })

                    imported_count += 1

                session.commit()
            except Exception as e:
                session.rollback()
                raise e
            finally:
                session.close()

            self.refresh_products_cache()
            self.update_table_view()
            QMessageBox.information(
                self, "Import Successful",
                f"Successfully imported {imported_count} item(s) into the stock list!\n\n"
                f"Review the quantities and rates in the table below, then click 'Save Existing Stock' to apply them to inventory."
            )

        except Exception as e:
            QMessageBox.critical(self, "Import Failed", f"Failed to import file: {e}")
