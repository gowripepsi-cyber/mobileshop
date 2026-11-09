import os
import datetime
from PySide6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QLineEdit, QComboBox, QDateEdit, QSpinBox, QDoubleSpinBox, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QFrame,
    QTabWidget, QAbstractItemView, QScrollArea, QSizePolicy
)
from PySide6.QtCore import Qt, QDate
from utils.formatters import format_inr
from database import Session, generate_next_po_number, Setting
from models import Product, Supplier, Category, Unit, PurchaseOrderMaster, PurchaseOrderItem
from utils.ui_helpers import SearchableProductComboBox, AutoClearSearchableComboBox
from utils.pdf_generator import generate_purchase_order_pdf
from utils.translator import tr


class PurchaseOrderDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Purchase Order - Low Stock Inventory")
        self.setMinimumSize(1150, 720)
        self.resize(1180, 760)
        self.setWindowFlags(self.windowFlags() | Qt.WindowMinMaxButtonsHint)

        # Caches
        self.products_cache = {}
        self.suppliers_cache = {}

        self.init_ui()
        self.load_reference_data()
        self.load_low_stock_items()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(14, 14, 14, 14)
        main_layout.setSpacing(10)

        # Tabs
        self.tabs = QTabWidget()
        self.tabs.setObjectName("po_tabs")

        # Tab 1: Create PO
        self.create_tab = QWidget()
        self.setup_create_tab()
        self.tabs.addTab(self.create_tab, "🛒 Create Purchase Order")

        # Tab 2: PO History
        self.history_tab = QWidget()
        self.setup_history_tab()
        self.tabs.addTab(self.history_tab, "📋 Purchase Order History")

        self.tabs.currentChanged.connect(self.on_tab_changed)
        main_layout.addWidget(self.tabs)

    # -------------------------------------------------------------------------
    # TAB 1: CREATE PURCHASE ORDER
    # -------------------------------------------------------------------------
    def setup_create_tab(self):
        tab_layout = QVBoxLayout(self.create_tab)
        tab_layout.setContentsMargins(8, 8, 8, 8)
        tab_layout.setSpacing(10)

        # Helper to build consistent label+widget field with guaranteed alignment
        def make_field(label_text, widget, width=None, stretch=False):
            box = QWidget()
            vl = QVBoxLayout(box)
            vl.setContentsMargins(0, 0, 0, 0)
            vl.setSpacing(4)
            lbl = QLabel(label_text)
            lbl.setStyleSheet("font-size: 11.5px; font-weight: 600; color: #475569; min-height: 18px; max-height: 18px;")
            vl.addWidget(lbl)
            vl.addWidget(widget)
            if width:
                box.setFixedWidth(width)
            if stretch:
                box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            return box

        common_input_style = (
            "min-height: 32px; font-size: 12px; color: #0f172a; "
            "padding: 2px 8px; border-radius: 6px;"
        )

        # =====================================================================
        # CARD 1: ORDER & SUPPLIER DETAILS (Compact 2-Row Card)
        # =====================================================================
        order_card = QFrame()
        order_card.setProperty("class", "CardFrame")
        order_layout = QVBoxLayout(order_card)
        order_layout.setContentsMargins(14, 10, 14, 10)
        order_layout.setSpacing(8)

        card1_title = QLabel("Order & Supplier Information (Editable)")
        card1_title.setStyleSheet("font-size: 13px; font-weight: bold; color: #0f172a;")
        order_layout.addWidget(card1_title)

        # Row 1: PO Number, Order Date, Expected Delivery, Status, Order Notes
        row1 = QHBoxLayout()
        row1.setContentsMargins(0, 0, 0, 0)
        row1.setSpacing(10)

        self.po_number_edit = QLineEdit()
        self.po_number_edit.setStyleSheet(common_input_style + " font-weight: bold; color: #d97706;")
        f_po = make_field("PO Number *", self.po_number_edit, width=130)

        self.po_date_edit = QDateEdit()
        self.po_date_edit.setCalendarPopup(True)
        self.po_date_edit.setDate(QDate.currentDate())
        self.po_date_edit.setStyleSheet(common_input_style)
        f_date = make_field("Order Date", self.po_date_edit, width=120)

        self.exp_date_edit = QDateEdit()
        self.exp_date_edit.setCalendarPopup(True)
        self.exp_date_edit.setDate(QDate.currentDate().addDays(3))
        self.exp_date_edit.setStyleSheet(common_input_style)
        f_exp = make_field("Expected Delivery", self.exp_date_edit, width=120)

        self.status_combo = QComboBox()
        self.status_combo.addItems(["Pending", "Ordered", "Approved", "Completed", "Cancelled"])
        self.status_combo.setStyleSheet(common_input_style)
        f_status = make_field("Status", self.status_combo, width=120)

        self.notes_edit = QLineEdit()
        self.notes_edit.setPlaceholderText("Urgent low stock replenishment...")
        self.notes_edit.setText("Urgent order for replenishment of low stock.")
        self.notes_edit.setStyleSheet(common_input_style)
        f_notes = make_field("Order Notes / Remarks", self.notes_edit, stretch=True)

        row1.addWidget(f_po)
        row1.addWidget(f_date)
        row1.addWidget(f_exp)
        row1.addWidget(f_status)
        row1.addWidget(f_notes, 1)
        order_layout.addLayout(row1)

        # Row 2: Supplier Combo, Mobile, Address, GSTIN, Clear Button
        row2 = QHBoxLayout()
        row2.setContentsMargins(0, 0, 0, 0)
        row2.setSpacing(10)

        self.supplier_combo = AutoClearSearchableComboBox()
        self.supplier_combo.setStyleSheet(common_input_style)
        self.supplier_combo.currentIndexChanged.connect(self.on_supplier_selected)
        f_s_combo = make_field("Supplier *", self.supplier_combo, width=280)

        self.supp_mobile_edit = QLineEdit()
        self.supp_mobile_edit.setPlaceholderText("Phone / Mobile")
        self.supp_mobile_edit.setStyleSheet(common_input_style)
        f_s_mob = make_field("Contact / Mobile", self.supp_mobile_edit, width=140)

        self.supp_address_edit = QLineEdit()
        self.supp_address_edit.setPlaceholderText("Supplier Address")
        self.supp_address_edit.setStyleSheet(common_input_style)
        f_s_addr = make_field("Address", self.supp_address_edit, stretch=True)

        self.supp_gst_edit = QLineEdit()
        self.supp_gst_edit.setPlaceholderText("GSTIN")
        self.supp_gst_edit.setStyleSheet(common_input_style)
        f_s_gst = make_field("GSTIN", self.supp_gst_edit, width=140)

        # Clear Supplier Button (Exact same height and baseline alignment as textboxes!)
        clear_box = QWidget()
        clear_box.setFixedWidth(85)
        clear_box_l = QVBoxLayout(clear_box)
        clear_box_l.setContentsMargins(0, 0, 0, 0)
        clear_box_l.setSpacing(4)
        lbl_clr_spacer = QLabel(" ")
        lbl_clr_spacer.setStyleSheet("min-height: 18px; max-height: 18px;")
        self.clear_supp_btn = QPushButton("↺ Clear")
        self.clear_supp_btn.setProperty("class", "btn-secondary")
        self.clear_supp_btn.setStyleSheet("min-height: 32px; max-height: 32px; font-size: 11.5px; padding: 0px 8px; margin: 0px;")
        self.clear_supp_btn.setCursor(Qt.PointingHandCursor)
        self.clear_supp_btn.clicked.connect(self.clear_supplier_fields)
        clear_box_l.addWidget(lbl_clr_spacer)
        clear_box_l.addWidget(self.clear_supp_btn)

        row2.addWidget(f_s_combo)
        row2.addWidget(f_s_mob)
        row2.addWidget(f_s_addr, 1)
        row2.addWidget(f_s_gst)
        row2.addWidget(clear_box)
        order_layout.addLayout(row2)

        tab_layout.addWidget(order_card)

        # =====================================================================
        # CARD 2: ADD ADDITIONAL ITEM (Perfect Pixel-Level Baseline Alignment)
        # =====================================================================
        add_card = QFrame()
        add_card.setProperty("class", "CardFrame")
        add_layout = QVBoxLayout(add_card)
        add_layout.setContentsMargins(14, 10, 14, 10)
        add_layout.setSpacing(8)

        card2_title = QLabel("Add Additional Item to Purchase Order (Addable)")
        card2_title.setStyleSheet("font-size: 13px; font-weight: bold; color: #0f172a;")
        add_layout.addWidget(card2_title)

        add_row = QHBoxLayout()
        add_row.setContentsMargins(0, 0, 0, 0)
        add_row.setSpacing(8)

        # 1. Product Code
        self.add_code_edit = QLineEdit()
        self.add_code_edit.setPlaceholderText("Code")
        self.add_code_edit.setStyleSheet(common_input_style)
        self.add_code_edit.returnPressed.connect(self.on_code_entered)
        f_code = make_field("Product Code", self.add_code_edit, width=95)

        # 2. Category Filter (50% wider, 160px)
        self.add_cat_combo = AutoClearSearchableComboBox()
        self.add_cat_combo.setPlaceholderText("Category")
        self.add_cat_combo.setStyleSheet(common_input_style)
        self.add_cat_combo.currentIndexChanged.connect(self.filter_products_by_category)
        if self.add_cat_combo.lineEdit():
            self.add_cat_combo.lineEdit().textChanged.connect(self.filter_products_by_category)
        f_cat = make_field("Category", self.add_cat_combo, width=160)

        # 3. Product Selector / Item Name
        self.add_prod_combo = SearchableProductComboBox()
        self.add_prod_combo.setPlaceholderText("Select / Search Product")
        self.add_prod_combo.setStyleSheet(common_input_style)
        self.add_prod_combo.currentIndexChanged.connect(self.on_product_selected_to_add)
        f_prod = make_field("Item Name *", self.add_prod_combo, stretch=True)

        # 4. Stock Status Badge
        self.add_stock_badge = QLabel("Available: -")
        self.add_stock_badge.setAlignment(Qt.AlignCenter)
        self.add_stock_badge.setStyleSheet(
            "min-height: 32px; max-height: 32px; font-size: 11.5px; font-weight: 600; "
            "color: #2563eb; background-color: #eff6ff; border: 1.5px solid #bfdbfe; "
            "border-radius: 6px; padding: 0px 6px;"
        )
        f_stock = make_field("Stock Status", self.add_stock_badge, width=105)

        # 5. Quantity
        self.add_qty_spin = QSpinBox()
        self.add_qty_spin.setRange(1, 99999)
        self.add_qty_spin.setValue(1)
        self.add_qty_spin.setAlignment(Qt.AlignCenter)
        self.add_qty_spin.setStyleSheet(common_input_style + " font-weight: bold;")
        f_qty = make_field("Order Qty *", self.add_qty_spin, width=85)

        # 6. Unit
        self.add_unit_combo = QComboBox()
        self.add_unit_combo.addItems(["Pcs", "Box", "Nos", "Set", "Kg", "Mtr", "Packet"])
        self.add_unit_combo.setStyleSheet(common_input_style)
        self.add_unit_combo.view().setMinimumWidth(110)
        f_unit = make_field("Unit", self.add_unit_combo, width=85)

        # 7. Rate
        self.add_rate_spin = QDoubleSpinBox()
        self.add_rate_spin.setRange(0.0, 999999.0)
        self.add_rate_spin.setDecimals(2)
        self.add_rate_spin.setValue(0.0)
        self.add_rate_spin.setAlignment(Qt.AlignRight)
        self.add_rate_spin.setStyleSheet(common_input_style + " font-weight: bold;")
        f_rate = make_field("Est. Rate (₹)", self.add_rate_spin, width=100)

        # 8. Add Item Button (Exact same height and baseline alignment!)
        add_btn_box = QWidget()
        add_btn_box.setFixedWidth(120)
        add_btn_l = QVBoxLayout(add_btn_box)
        add_btn_l.setContentsMargins(0, 0, 0, 0)
        add_btn_l.setSpacing(4)
        lbl_add_spacer = QLabel(" ")
        lbl_add_spacer.setStyleSheet("min-height: 18px; max-height: 18px;")
        self.add_btn = QPushButton("➕ Add to Order")
        self.add_btn.setStyleSheet(
            "min-height: 32px; max-height: 32px; font-size: 11.5px; font-weight: bold; "
            "background-color: #f59e0b; color: white; border-radius: 6px; padding: 0px 10px; margin: 0px;"
        )
        self.add_btn.setCursor(Qt.PointingHandCursor)
        self.add_btn.clicked.connect(self.add_custom_item_to_table)
        add_btn_l.addWidget(lbl_add_spacer)
        add_btn_l.addWidget(self.add_btn)

        add_row.addWidget(f_code)
        add_row.addWidget(f_cat)
        add_row.addWidget(f_prod, 1)
        add_row.addWidget(f_stock)
        add_row.addWidget(f_qty)
        add_row.addWidget(f_unit)
        add_row.addWidget(f_rate)
        add_row.addWidget(add_btn_box)

        add_layout.addLayout(add_row)
        tab_layout.addWidget(add_card)

        # =====================================================================
        # CARD 3: ITEMS TABLE & SUMMARY / ACTIONS (Unified & Spacious)
        # =====================================================================
        table_card = QFrame()
        table_card.setProperty("class", "CardFrame")
        table_card_layout = QVBoxLayout(table_card)
        table_card_layout.setContentsMargins(14, 10, 14, 10)
        table_card_layout.setSpacing(8)

        table_header = QHBoxLayout()
        self.table_title = QLabel("Purchase Order Items (Preloaded from Low Stock Alert)")
        self.table_title.setStyleSheet("font-size: 13px; font-weight: bold; color: #0f172a;")
        table_header.addWidget(self.table_title)
        table_header.addStretch()

        self.reload_low_stock_btn = QPushButton("↺ Reload Low Stock Items")
        self.reload_low_stock_btn.setFixedHeight(28)
        self.reload_low_stock_btn.setProperty("class", "btn-secondary")
        self.reload_low_stock_btn.setCursor(Qt.PointingHandCursor)
        self.reload_low_stock_btn.clicked.connect(self.load_low_stock_items)
        table_header.addWidget(self.reload_low_stock_btn)
        table_card_layout.addLayout(table_header)

        # Items Table
        self.items_table = QTableWidget()
        self.items_table.setColumnCount(11)
        self.items_table.setHorizontalHeaderLabels([
            "S.N", "Code", "Item Name", "Brand / Model",
            "Stock", "Limit", "Order Qty", "Unit",
            "Est. Rate (₹)", "Total (₹)", "Action"
        ])
        header = self.items_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        header.setSectionResizeMode(1, QHeaderView.Fixed)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.Interactive)
        header.setSectionResizeMode(4, QHeaderView.Fixed)
        header.setSectionResizeMode(5, QHeaderView.Fixed)
        header.setSectionResizeMode(6, QHeaderView.Fixed)
        header.setSectionResizeMode(7, QHeaderView.Fixed)
        header.setSectionResizeMode(8, QHeaderView.Fixed)
        header.setSectionResizeMode(9, QHeaderView.Fixed)
        header.setSectionResizeMode(10, QHeaderView.Fixed)

        self.items_table.setColumnWidth(0, 42)   # S.N
        self.items_table.setColumnWidth(1, 75)   # Code
        self.items_table.setColumnWidth(3, 125)  # Brand / Model
        self.items_table.setColumnWidth(4, 65)   # Stock
        self.items_table.setColumnWidth(5, 65)   # Limit
        self.items_table.setColumnWidth(6, 115)  # Order Qty (widened to fit spinbox & header)
        self.items_table.setColumnWidth(7, 75)   # Unit (widened for full visibility)
        self.items_table.setColumnWidth(8, 135)  # Est. Rate (₹) (widened for complete digits & header)
        self.items_table.setColumnWidth(9, 125)  # Total (₹) (widened for complete currency totals)
        self.items_table.setColumnWidth(10, 100) # Action (widened for full delete button & header)

        self.items_table.verticalHeader().setVisible(False)
        self.items_table.verticalHeader().setDefaultSectionSize(58)
        self.items_table.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)
        self.items_table.setSelectionMode(QAbstractItemView.NoSelection)
        self.items_table.setFocusPolicy(Qt.NoFocus)
        self.items_table.setMinimumHeight(240)
        table_card_layout.addWidget(self.items_table, 1)

        # Bottom Summary & Action Bar inside table card
        bottom_layout = QHBoxLayout()
        bottom_layout.setContentsMargins(0, 4, 0, 0)
        bottom_layout.setSpacing(16)

        self.lbl_summary_items = QLabel("Total Items: 0")
        self.lbl_summary_items.setStyleSheet("font-weight: bold; color: #475569; font-size: 12.5px; background: #f1f5f9; padding: 4px 10px; border-radius: 4px; border: 1px solid #e2e8f0;")
        bottom_layout.addWidget(self.lbl_summary_items)

        self.lbl_summary_qty = QLabel("Total Qty: 0 Units")
        self.lbl_summary_qty.setStyleSheet("font-weight: bold; color: #2563eb; font-size: 12.5px; background: #eff6ff; padding: 4px 10px; border-radius: 4px; border: 1px solid #bfdbfe;")
        bottom_layout.addWidget(self.lbl_summary_qty)

        self.lbl_summary_total = QLabel("Estimated Total: ₹0.00")
        self.lbl_summary_total.setStyleSheet("font-weight: bold; color: #d97706; font-size: 14px; background: #fefce8; padding: 4px 12px; border-radius: 4px; border: 1px solid #fde68a;")
        bottom_layout.addWidget(self.lbl_summary_total)

        bottom_layout.addStretch()

        self.save_btn = QPushButton("💾 Save Purchase Order")
        self.save_btn.setFixedHeight(36)
        self.save_btn.setFixedWidth(195)
        self.save_btn.setStyleSheet("font-size: 12px; font-weight: bold; background-color: #f59e0b; color: white; border-radius: 6px;")
        self.save_btn.setCursor(Qt.PointingHandCursor)
        self.save_btn.clicked.connect(lambda: self.save_purchase_order(show_msg=True))
        bottom_layout.addWidget(self.save_btn)

        self.print_btn = QPushButton("📄 Print Preview / PDF")
        self.print_btn.setFixedHeight(36)
        self.print_btn.setFixedWidth(180)
        self.print_btn.setStyleSheet("font-size: 12px; font-weight: bold; background-color: #8fd53b; color: #0f172a; border-radius: 6px;")
        self.print_btn.setCursor(Qt.PointingHandCursor)
        self.print_btn.clicked.connect(self.export_and_open_pdf)
        bottom_layout.addWidget(self.print_btn)

        self.close_btn = QPushButton("Close")
        self.close_btn.setFixedHeight(36)
        self.close_btn.setFixedWidth(90)
        self.close_btn.setProperty("class", "btn-secondary")
        self.close_btn.setCursor(Qt.PointingHandCursor)
        self.close_btn.clicked.connect(self.reject)
        bottom_layout.addWidget(self.close_btn)

        table_card_layout.addLayout(bottom_layout)
        tab_layout.addWidget(table_card, 1)

    # -------------------------------------------------------------------------
    # TAB 2: PURCHASE ORDER HISTORY
    # -------------------------------------------------------------------------
    def setup_history_tab(self):
        hist_layout = QVBoxLayout(self.history_tab)
        hist_layout.setContentsMargins(10, 10, 10, 10)
        hist_layout.setSpacing(10)

        # Filter bar
        filter_card = QFrame()
        filter_card.setProperty("class", "CardFrame")
        f_layout = QHBoxLayout(filter_card)
        f_layout.setContentsMargins(12, 8, 12, 8)
        f_layout.setSpacing(12)

        self.hist_search_edit = QLineEdit()
        self.hist_search_edit.setPlaceholderText("🔍 Search by PO number, supplier name, mobile...")
        self.hist_search_edit.setFixedHeight(32)
        self.hist_search_edit.textChanged.connect(self.filter_history_table)
        f_layout.addWidget(self.hist_search_edit, 1)

        self.hist_status_combo = QComboBox()
        self.hist_status_combo.addItems(["All Statuses", "Pending", "Ordered", "Approved", "Completed", "Cancelled"])
        self.hist_status_combo.setFixedHeight(32)
        self.hist_status_combo.setFixedWidth(140)
        self.hist_status_combo.currentIndexChanged.connect(self.filter_history_table)
        f_layout.addWidget(self.hist_status_combo)

        self.hist_refresh_btn = QPushButton("↺ Refresh")
        self.hist_refresh_btn.setFixedHeight(32)
        self.hist_refresh_btn.setFixedWidth(100)
        self.hist_refresh_btn.setProperty("class", "btn-secondary")
        self.hist_refresh_btn.setCursor(Qt.PointingHandCursor)
        self.hist_refresh_btn.clicked.connect(self.load_history_data)
        f_layout.addWidget(self.hist_refresh_btn)

        hist_layout.addWidget(filter_card)

        # History Table
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(9)
        self.history_table.setHorizontalHeaderLabels([
            "PO Number", "Date", "Supplier Name", "Mobile",
            "Items", "Qty", "Total (₹)", "Status", "Actions"
        ])
        h_header = self.history_table.horizontalHeader()
        h_header.setSectionResizeMode(QHeaderView.Stretch)
        h_header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        h_header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        h_header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        h_header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        h_header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        h_header.setSectionResizeMode(7, QHeaderView.ResizeToContents)
        h_header.setSectionResizeMode(8, QHeaderView.Fixed)
        self.history_table.setColumnWidth(8, 240)

        self.history_table.verticalHeader().setVisible(False)
        self.history_table.verticalHeader().setDefaultSectionSize(58)
        self.history_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.history_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        hist_layout.addWidget(self.history_table, 1)

    # -------------------------------------------------------------------------
    # ROW WIDGET HELPERS
    # -------------------------------------------------------------------------
    def get_row_name_edit(self, row):
        w = self.items_table.cellWidget(row, 2)
        if isinstance(w, QLineEdit):
            return w
        return w.findChild(QLineEdit) if w else None

    def get_row_qty_spin(self, row):
        w = self.items_table.cellWidget(row, 6)
        if isinstance(w, QSpinBox):
            return w
        return w.findChild(QSpinBox) if w else None

    def get_row_rate_spin(self, row):
        w = self.items_table.cellWidget(row, 8)
        if isinstance(w, QDoubleSpinBox):
            return w
        return w.findChild(QDoubleSpinBox) if w else None

    # -------------------------------------------------------------------------
    # DATA LOADING & POPULATION
    # -------------------------------------------------------------------------
    def load_reference_data(self):
        session = Session()
        try:
            self.po_number_edit.setText(generate_next_po_number(session))

            # Suppliers
            self.suppliers_cache.clear()
            self.supplier_combo.clear()
            self.supplier_combo.addItem("-- Select Registered Supplier / Custom --", None)
            suppliers = session.query(Supplier).order_by(Supplier.name).all()
            for s in suppliers:
                self.suppliers_cache[s.id] = s
                self.supplier_combo.addItem(f"{s.name} ({s.mobile})", s.id)
            self.supplier_combo.update_completer()

            # Dynamically calculate maximum width so popup expands fully to fit all supplier names & phones
            fm = self.supplier_combo.fontMetrics()
            max_w = 340
            for i in range(self.supplier_combo.count()):
                w = fm.horizontalAdvance(self.supplier_combo.itemText(i)) + 40
                if w > max_w:
                    max_w = w
            self.supplier_combo.view().setMinimumWidth(max_w)
            if self.supplier_combo.completer() and self.supplier_combo.completer().popup():
                self.supplier_combo.completer().popup().setMinimumWidth(max_w)

            # Categories
            self.add_cat_combo.clear()
            self.add_cat_combo.addItem("All Categories", None)
            cats = session.query(Category).order_by(Category.name).all()
            for c in cats:
                self.add_cat_combo.addItem(c.name, c.id)

            # Products
            self.products_cache.clear()
            prods = session.query(Product).order_by(Product.name).all()
            prod_list = []
            for p in prods:
                self.products_cache[p.id] = p
                prod_list.append(p)
            self.add_prod_combo.set_products(prod_list)

        except Exception as e:
            print(f"Error loading reference data in PurchaseOrderDialog: {e}")
        finally:
            session.close()

    def load_low_stock_items(self):
        session = Session()
        try:
            self.items_table.setRowCount(0)
            low_stock_prods = session.query(Product).filter(Product.stock_qty <= Product.low_stock_limit).all()

            if not low_stock_prods:
                self.table_title.setText("Purchase Order Items (No items currently below low limit - use Add bar above)")
                self.recalculate_totals()
                return

            self.table_title.setText(f"Purchase Order Items ({len(low_stock_prods)} Low Stock Items Preloaded)")
            for p in low_stock_prods:
                def_qty = max(1, p.low_stock_limit - p.stock_qty)
                def_rate = float(p.purchase_price or 0.0)
                unit_val = p.unit or 'Pcs'
                bm_val = p.brand_model or p.brand or "-"

                self.append_item_row(
                    product_id=p.id,
                    product_code=p.product_code or "-",
                    item_name=p.name,
                    brand_model=bm_val,
                    stock=p.stock_qty,
                    limit=p.low_stock_limit,
                    qty=def_qty,
                    unit=unit_val,
                    rate=def_rate
                )

            self.recalculate_totals()

        except Exception as e:
            print(f"Error loading low stock items: {e}")
        finally:
            session.close()

    def append_item_row(self, product_id, product_code, item_name, brand_model, stock, limit, qty, unit, rate):
        row = self.items_table.rowCount()
        self.items_table.insertRow(row)
        self.items_table.setRowHeight(row, 58)

        # 0. S.No
        sn_item = QTableWidgetItem(str(row + 1))
        sn_item.setTextAlignment(Qt.AlignCenter)
        self.items_table.setItem(row, 0, sn_item)

        # 1. Code
        code_item = QTableWidgetItem(product_code)
        code_item.setTextAlignment(Qt.AlignCenter)
        self.items_table.setItem(row, 1, code_item)

        # 2. Item Name (Container + QLineEdit with clean vertical clearance)
        name_container = QWidget()
        name_container.setStyleSheet("background: transparent; margin: 0px; padding: 0px;")
        name_layout = QHBoxLayout(name_container)
        name_layout.setContentsMargins(4, 0, 4, 0)
        name_layout.setSpacing(0)
        name_edit = QLineEdit(item_name)
        name_edit.setFixedHeight(28)
        name_edit.setStyleSheet(
            "QLineEdit { background: #ffffff; border: 1.5px solid #cbd5e1; border-radius: 6px; "
            "padding: 0px 8px !important; min-height: 28px !important; max-height: 28px !important; height: 28px !important; "
            "font-size: 12px; color: #0f172a; margin: 0px !important; } "
            "QLineEdit:focus { border: 1.5px solid #3b82f6; background-color: #f8fafc; }"
        )
        name_edit.textChanged.connect(self.recalculate_totals)
        name_edit.setProperty("product_id", product_id)
        name_layout.addWidget(name_edit)
        self.items_table.setCellWidget(row, 2, name_container)

        # 3. Brand / Model
        bm_item = QTableWidgetItem(brand_model)
        bm_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.items_table.setItem(row, 3, bm_item)

        # 4. Stock
        stock_item = QTableWidgetItem(str(stock))
        stock_item.setTextAlignment(Qt.AlignCenter)
        try:
            if int(stock) <= 0:
                stock_item.setForeground(Qt.red)
        except (ValueError, TypeError):
            pass
        self.items_table.setItem(row, 4, stock_item)

        # 5. Limit
        limit_item = QTableWidgetItem(str(limit))
        limit_item.setTextAlignment(Qt.AlignCenter)
        self.items_table.setItem(row, 5, limit_item)

        # 6. Order Qty (Container + QSpinBox with clean vertical clearance)
        qty_container = QWidget()
        qty_container.setStyleSheet("background: transparent; margin: 0px; padding: 0px;")
        qty_layout = QHBoxLayout(qty_container)
        qty_layout.setContentsMargins(4, 0, 4, 0)
        qty_layout.setSpacing(0)
        qty_layout.setAlignment(Qt.AlignCenter)
        qty_spin = QSpinBox()
        qty_spin.setRange(1, 99999)
        qty_spin.setValue(qty)
        qty_spin.setFixedSize(90, 28)
        qty_spin.setAlignment(Qt.AlignCenter)
        qty_spin.setStyleSheet(
            "QSpinBox { background: #ffffff; border: 1.5px solid #cbd5e1; border-radius: 6px; "
            "padding: 0px 4px !important; min-height: 28px !important; max-height: 28px !important; height: 28px !important; "
            "font-weight: bold; font-size: 12px; color: #0f172a; margin: 0px !important; } "
            "QSpinBox:focus { border: 1.5px solid #3b82f6; background-color: #f8fafc; }"
        )
        qty_spin.valueChanged.connect(self.recalculate_totals)
        qty_layout.addWidget(qty_spin)
        self.items_table.setCellWidget(row, 6, qty_container)

        # 7. Unit
        unit_item = QTableWidgetItem(unit)
        unit_item.setTextAlignment(Qt.AlignCenter)
        self.items_table.setItem(row, 7, unit_item)

        # 8. Rate (Container + QDoubleSpinBox with clean vertical clearance)
        rate_container = QWidget()
        rate_container.setStyleSheet("background: transparent; margin: 0px; padding: 0px;")
        rate_layout = QHBoxLayout(rate_container)
        rate_layout.setContentsMargins(4, 0, 4, 0)
        rate_layout.setSpacing(0)
        rate_layout.setAlignment(Qt.AlignCenter)
        rate_spin = QDoubleSpinBox()
        rate_spin.setRange(0.0, 999999.0)
        rate_spin.setDecimals(2)
        rate_spin.setValue(rate)
        rate_spin.setFixedSize(110, 28)
        rate_spin.setAlignment(Qt.AlignRight)
        rate_spin.setStyleSheet(
            "QDoubleSpinBox { background: #ffffff; border: 1.5px solid #cbd5e1; border-radius: 6px; "
            "padding: 0px 6px !important; min-height: 28px !important; max-height: 28px !important; height: 28px !important; "
            "font-weight: bold; font-size: 12px; color: #0f172a; margin: 0px !important; } "
            "QDoubleSpinBox:focus { border: 1.5px solid #3b82f6; background-color: #f8fafc; }"
        )
        rate_spin.valueChanged.connect(self.recalculate_totals)
        rate_layout.addWidget(rate_spin)
        self.items_table.setCellWidget(row, 8, rate_container)

        # 9. Total Amount (₹)
        total_val = qty * rate
        total_item = QTableWidgetItem(f"{format_inr(total_val)}")
        total_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        total_item.setForeground(Qt.darkGreen)
        self.items_table.setItem(row, 9, total_item)

        # 10. Action: Clean Delete Button (Consistent across all rows, no stuck hover/selection)
        del_container = QWidget()
        del_container.setStyleSheet("background: transparent; margin: 0px; padding: 0px;")
        del_layout = QHBoxLayout(del_container)
        del_layout.setContentsMargins(4, 0, 4, 0)
        del_layout.setSpacing(0)
        del_layout.setAlignment(Qt.AlignCenter)
        del_btn = QPushButton("Delete")
        del_btn.setObjectName("po_table_del_btn")
        del_btn.setFixedSize(72, 26)
        del_btn.setFocusPolicy(Qt.NoFocus)
        del_btn.setStyleSheet(
            "QPushButton#po_table_del_btn { "
            "   background-color: #fee2e2; color: #dc2626; font-size: 11px; font-weight: bold; "
            "   border-radius: 6px; padding: 0px 4px !important; border: 1.5px solid #fca5a5; "
            "   min-height: 26px !important; max-height: 26px !important; height: 26px !important; margin: 0px !important;"
            "} "
            "QPushButton#po_table_del_btn:hover { "
            "   background-color: #ef4444; color: #ffffff; border: 1.5px solid #ef4444; "
            "} "
            "QPushButton#po_table_del_btn:pressed { "
            "   background-color: #b91c1c; color: #ffffff; "
            "}"
        )
        del_btn.setCursor(Qt.PointingHandCursor)
        del_btn.clicked.connect(self.handle_row_delete_clicked)
        del_layout.addWidget(del_btn)
        self.items_table.setCellWidget(row, 10, del_container)

    def handle_row_delete_clicked(self):
        button = self.sender()
        if not button:
            return
        for r in range(self.items_table.rowCount()):
            cell_w = self.items_table.cellWidget(r, 10)
            if cell_w and (cell_w == button or cell_w.findChild(QPushButton) == button):
                self.remove_item_row(r)
                break

    def remove_item_row(self, row_idx):
        if 0 <= row_idx < self.items_table.rowCount():
            self.items_table.removeRow(row_idx)
            self.re_index_rows()
            self.recalculate_totals()

    def re_index_rows(self):
        for r in range(self.items_table.rowCount()):
            sn_item = self.items_table.item(r, 0)
            if sn_item:
                sn_item.setText(str(r + 1))

    def recalculate_totals(self):
        total_items = self.items_table.rowCount()
        total_qty = 0
        total_amount = 0.0

        for r in range(total_items):
            qty_spin = self.get_row_qty_spin(r)
            rate_spin = self.get_row_rate_spin(r)

            qty = qty_spin.value() if qty_spin else 1
            rate = rate_spin.value() if rate_spin else 0.0
            row_total = qty * rate

            total_qty += qty
            total_amount += row_total

            tot_item = self.items_table.item(r, 9)
            if tot_item:
                tot_item.setText(f"{format_inr(row_total)}")

        self.lbl_summary_items.setText(f"Total Items: {total_items}")
        self.lbl_summary_qty.setText(f"Total Qty: {total_qty} Units")
        self.lbl_summary_total.setText(f"Estimated Total: ₹{format_inr(total_amount)}")

    # -------------------------------------------------------------------------
    # SUPPLIER INTERACTION
    # -------------------------------------------------------------------------
    def on_supplier_selected(self, index):
        supp_id = self.supplier_combo.currentData()
        if supp_id and supp_id in self.suppliers_cache:
            supp = self.suppliers_cache[supp_id]
            self.supp_mobile_edit.setText(supp.mobile or "")
            self.supp_address_edit.setText(supp.address or "")
            self.supp_gst_edit.setText(supp.gst or "")
        elif supp_id is None and index == 0:
            pass

    def clear_supplier_fields(self):
        self.supplier_combo.setCurrentIndex(0)
        if self.supplier_combo.lineEdit():
            self.supplier_combo.lineEdit().setText(self.supplier_combo.itemText(0))
        self.supp_mobile_edit.clear()
        self.supp_address_edit.clear()
        self.supp_gst_edit.clear()
        self.supplier_combo.setFocus()

    # -------------------------------------------------------------------------
    # ADD CUSTOM / CATALOG ITEM
    # -------------------------------------------------------------------------
    def filter_products_by_category(self):
        cat_id = self.add_cat_combo.currentData()
        session = Session()
        try:
            query = session.query(Product)
            if cat_id:
                query = query.filter_by(category_id=cat_id)
            prods = query.order_by(Product.name).all()
            self.add_prod_combo.set_products(prods)
        finally:
            session.close()

    def on_code_entered(self):
        code = self.add_code_edit.text().strip()
        if not code:
            return
        found_id = None
        for pid, p in self.products_cache.items():
            if p.product_code and p.product_code.lower() == code.lower():
                found_id = pid
                break

        if found_id:
            idx = self.add_prod_combo.findData(found_id)
            if idx >= 0:
                self.add_prod_combo.setCurrentIndex(idx)
        else:
            QMessageBox.information(self, "Not Found", f"No catalog product found with code '{code}'. You can enter item name manually.")

    def on_product_selected_to_add(self):
        prod_id = self.add_prod_combo.currentData()
        if prod_id and prod_id in self.products_cache:
            p = self.products_cache[prod_id]
            self.add_code_edit.setText(p.product_code or "")
            self.add_stock_badge.setText(f"Stock: {p.stock_qty} | Limit: {p.low_stock_limit}")
            self.add_rate_spin.setValue(float(p.purchase_price or 0.0))
            if p.unit:
                idx = self.add_unit_combo.findText(p.unit, Qt.MatchFixedString)
                if idx >= 0:
                    self.add_unit_combo.setCurrentIndex(idx)
        else:
            self.add_code_edit.clear()
            self.add_stock_badge.setText("Available: -")
            self.add_rate_spin.setValue(0.0)

    def add_custom_item_to_table(self):
        prod_id = self.add_prod_combo.currentData()
        item_name = self.add_prod_combo.currentText().strip()
        if not item_name or item_name in ("-- Select Product --", "Select / Search Product"):
            QMessageBox.warning(self, "Item Required", "Please select a product or enter an item name to add.")
            return

        code = self.add_code_edit.text().strip() or "-"
        qty = self.add_qty_spin.value()
        unit = self.add_unit_combo.currentText().strip()
        rate = self.add_rate_spin.value()

        stock_val = "-"
        limit_val = "-"
        bm_val = "-"

        if prod_id and prod_id in self.products_cache:
            p = self.products_cache[prod_id]
            stock_val = p.stock_qty
            limit_val = p.low_stock_limit
            bm_val = p.brand_model or p.brand or "-"

        self.append_item_row(
            product_id=prod_id,
            product_code=code,
            item_name=item_name,
            brand_model=bm_val,
            stock=stock_val,
            limit=limit_val,
            qty=qty,
            unit=unit,
            rate=rate
        )

        self.recalculate_totals()

        # Reset inputs
        self.add_code_edit.clear()
        self.add_prod_combo.setCurrentIndex(-1)
        self.add_qty_spin.setValue(1)
        self.add_rate_spin.setValue(0.0)
        self.add_stock_badge.setText("Available: -")

    # -------------------------------------------------------------------------
    # SAVE & EXPORT LOGIC
    # -------------------------------------------------------------------------
    def get_order_payload(self):
        po_number = self.po_number_edit.text().strip()
        if not po_number:
            QMessageBox.warning(self, "PO Number Required", "Please enter a valid PO number.")
            return None

        supp_id = self.supplier_combo.currentData()
        supp_text = self.supplier_combo.currentText().strip()
        if supp_id and supp_id in self.suppliers_cache:
            supp_name = self.suppliers_cache[supp_id].name or ""
        elif supp_text and supp_text != "-- Select Registered Supplier / Custom --":
            if " (" in supp_text and supp_text.endswith(")"):
                supp_name = supp_text.rsplit(" (", 1)[0].strip()
            else:
                supp_name = supp_text
        else:
            supp_name = ""

        if not supp_name:
            QMessageBox.warning(self, "Supplier Required", "Please select or enter a Supplier.")
            self.supplier_combo.setFocus()
            return None

        if self.items_table.rowCount() == 0:
            QMessageBox.warning(self, "No Items", "Purchase order must contain at least one item.")
            return None

        items_data = []
        for r in range(self.items_table.rowCount()):
            name_edit = self.get_row_name_edit(r)
            qty_spin = self.get_row_qty_spin(r)
            rate_spin = self.get_row_rate_spin(r)

            it_name = name_edit.text().strip() if name_edit else (self.items_table.item(r, 2).text() if self.items_table.item(r, 2) else "")
            it_qty = qty_spin.value() if qty_spin else 1
            it_rate = rate_spin.value() if rate_spin else 0.0

            pid = name_edit.property("product_id") if name_edit else None
            p_code = self.items_table.item(r, 1).text() if self.items_table.item(r, 1) else "-"
            bm = self.items_table.item(r, 3).text() if self.items_table.item(r, 3) else "-"
            unit = self.items_table.item(r, 7).text() if self.items_table.item(r, 7) else "Pcs"
            row_total = it_qty * it_rate

            items_data.append({
                "product_id": pid,
                "product_code": p_code,
                "name": it_name,
                "brand_model": bm,
                "qty": it_qty,
                "unit": unit,
                "rate": it_rate,
                "total": row_total
            })

        supp_id = self.supplier_combo.currentData()
        tot_qty = sum(it['qty'] for it in items_data)
        tot_amount = sum(it['total'] for it in items_data)

        return {
            "po_number": po_number,
            "date": self.po_date_edit.date().toPython(),
            "expected_date": self.exp_date_edit.date().toPython(),
            "status": self.status_combo.currentText(),
            "notes": self.notes_edit.text().strip(),
            "supplier_id": supp_id,
            "supplier_name": supp_name,
            "supplier_mobile": self.supp_mobile_edit.text().strip(),
            "supplier_address": self.supp_address_edit.text().strip(),
            "supplier_gst": self.supp_gst_edit.text().strip(),
            "items": items_data,
            "total_items": len(items_data),
            "total_qty": tot_qty,
            "total_amount": tot_amount
        }

    def save_purchase_order(self, show_msg=True):
        # Ensure show_msg is True when clicked from save button
        if self.sender() == self.save_btn:
            show_msg = True

        payload = self.get_order_payload()
        if not payload:
            return None

        session = Session()
        try:
            existing_po = session.query(PurchaseOrderMaster).filter_by(po_number=payload['po_number']).first()
            if existing_po:
                po_master = existing_po
                po_master.date = payload['date']
                po_master.expected_date = payload['expected_date']
                po_master.status = payload['status']
                po_master.notes = payload['notes']
                po_master.supplier_id = payload['supplier_id']
                po_master.supplier_name = payload['supplier_name']
                po_master.supplier_mobile = payload['supplier_mobile']
                po_master.supplier_address = payload['supplier_address']
                po_master.supplier_gst = payload['supplier_gst']
                po_master.total_items = payload['total_items']
                po_master.total_qty = payload['total_qty']
                po_master.total_amount = payload['total_amount']

                session.query(PurchaseOrderItem).filter_by(po_id=po_master.id).delete()
            else:
                po_master = PurchaseOrderMaster(
                    po_number=payload['po_number'],
                    date=payload['date'],
                    expected_date=payload['expected_date'],
                    status=payload['status'],
                    notes=payload['notes'],
                    supplier_id=payload['supplier_id'],
                    supplier_name=payload['supplier_name'],
                    supplier_mobile=payload['supplier_mobile'],
                    supplier_address=payload['supplier_address'],
                    supplier_gst=payload['supplier_gst'],
                    total_items=payload['total_items'],
                    total_qty=payload['total_qty'],
                    total_amount=payload['total_amount']
                )
                session.add(po_master)
                session.flush()

            for it in payload['items']:
                po_item = PurchaseOrderItem(
                    po_id=po_master.id,
                    product_id=it['product_id'],
                    product_code=it['product_code'],
                    item_name=it['name'],
                    brand_model=it['brand_model'],
                    unit=it['unit'],
                    qty=it['qty'],
                    rate=it['rate'],
                    total_amount=it['total']
                )
                session.add(po_item)

            saved_po_id = po_master.id
            saved_po_num = payload['po_number']
            session.commit()
            next_po_num = generate_next_po_number(session)

            if show_msg:
                QMessageBox.information(self, "Success", f"Purchase Order '{saved_po_num}' saved successfully!")

            # 1. Clear selected supplier data and inputs
            self.clear_supplier_fields()

            # 2. Reset dates and notes
            self.po_date_edit.setDate(QDate.currentDate())
            self.exp_date_edit.setDate(QDate.currentDate().addDays(3))
            self.notes_edit.setText("Urgent order for replenishment of low stock.")

            # 3. Reset additional item inputs
            if hasattr(self, 'add_code_input'):
                self.add_code_input.clear()
            if hasattr(self, 'add_cat_combo'):
                self.add_cat_combo.setCurrentIndex(0)
            if hasattr(self, 'add_prod_combo'):
                self.add_prod_combo.reset_items()
            if hasattr(self, 'add_qty_spin'):
                self.add_qty_spin.setValue(1)
            if hasattr(self, 'add_rate_spin'):
                self.add_rate_spin.setValue(0.0)
            if hasattr(self, 'stock_status_lbl'):
                self.stock_status_lbl.setText("Available: -")

            # 4. Reload low stock items fresh and recalculate totals
            self.load_low_stock_items()

            # 5. Set next generated PO number
            self.po_number_edit.setText(next_po_num)

            # 6. Refresh PO history tab
            self.load_history_data()

            return saved_po_id

        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", f"Failed to save Purchase Order: {e}")
            return None
        finally:
            session.close()

    def export_and_open_pdf(self):
        payload = self.get_order_payload()
        if not payload:
            return

        session = Session()
        try:
            s_name = session.query(Setting).filter_by(key='shop_name').first()
            s_contact = session.query(Setting).filter_by(key='shop_contact').first()
            s_address = session.query(Setting).filter_by(key='shop_address').first()
            s_gst = session.query(Setting).filter_by(key='shop_gst').first()

            shop_name = s_name.value if s_name else "I TECH MOBILES,"
            shop_contact = s_contact.value if s_contact else "N/A"
            shop_address = s_address.value if s_address else "N/A"
            shop_gst = s_gst.value if s_gst else "N/A"

            po_pdf_data = {
                "shop_name": shop_name,
                "shop_contact": shop_contact,
                "shop_address": shop_address,
                "shop_gst": shop_gst,
                "po_number": payload['po_number'],
                "date": payload['date'].strftime("%Y-%m-%d"),
                "expected_date": payload['expected_date'].strftime("%Y-%m-%d") if payload.get('expected_date') else "Immediate",
                "status": payload['status'],
                "notes": payload['notes'],
                "supplier_name": payload['supplier_name'],
                "supplier_mobile": payload['supplier_mobile'],
                "supplier_address": payload['supplier_address'],
                "supplier_gst": payload['supplier_gst'],
                "items": payload['items'],
                "total_items": payload['total_items'],
                "total_qty": payload['total_qty'],
                "total_amount": payload['total_amount']
            }

            os.makedirs("statements", exist_ok=True)
            safe_po = payload['po_number'].replace("/", "_").replace("\\", "_")
            pdf_path = os.path.abspath(f"statements/purchase_order_{safe_po}.pdf")

            generate_purchase_order_pdf(po_pdf_data, pdf_path)
            self.save_purchase_order(show_msg=False)

            QMessageBox.information(self, "Purchase Order Generated", f"Purchase Order PDF generated successfully at:\n{pdf_path}")
            try:
                os.startfile(pdf_path)
            except Exception as e:
                print(f"Could not auto-open PDF: {e}")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate Purchase Order PDF: {e}")
        finally:
            session.close()

    # -------------------------------------------------------------------------
    # TAB 2 LOGIC: HISTORY
    # -------------------------------------------------------------------------
    def on_tab_changed(self, index):
        if index == 1:
            self.load_history_data()

    def load_history_data(self):
        session = Session()
        try:
            records = session.query(PurchaseOrderMaster).order_by(PurchaseOrderMaster.id.desc()).all()
            for r in records:
                _ = (r.id, r.po_number, r.date, r.supplier_name, r.supplier_mobile, r.total_items, r.total_qty, r.total_amount, r.status)
            session.expunge_all()
            self.history_records = records
            self.filter_history_table()
        except Exception as e:
            print(f"Error loading PO history: {e}")
        finally:
            session.close()

    def filter_history_table(self):
        if not hasattr(self, 'history_records'):
            return

        query_text = self.hist_search_edit.text().strip().lower()
        status_filter = self.hist_status_combo.currentText()

        filtered = []
        for po in self.history_records:
            if status_filter != "All Statuses" and po.status != status_filter:
                continue

            if query_text:
                po_num = (po.po_number or "").lower()
                supp_name = (po.supplier_name or "").lower()
                supp_mob = (po.supplier_mobile or "").lower()
                if query_text not in po_num and query_text not in supp_name and query_text not in supp_mob:
                    continue

            filtered.append(po)

        self.history_table.setRowCount(len(filtered))
        for row, po in enumerate(filtered):
            self.history_table.setItem(row, 0, QTableWidgetItem(str(po.po_number)))

            d_str = po.date.strftime("%Y-%m-%d") if po.date else "-"
            self.history_table.setItem(row, 1, QTableWidgetItem(d_str))

            self.history_table.setItem(row, 2, QTableWidgetItem(str(po.supplier_name or "-")))
            self.history_table.setItem(row, 3, QTableWidgetItem(str(po.supplier_mobile or "-")))

            it_item = QTableWidgetItem(str(po.total_items))
            it_item.setTextAlignment(Qt.AlignCenter)
            self.history_table.setItem(row, 4, it_item)

            qty_item = QTableWidgetItem(str(po.total_qty))
            qty_item.setTextAlignment(Qt.AlignCenter)
            self.history_table.setItem(row, 5, qty_item)

            tot_item = QTableWidgetItem(f"₹{format_inr(po.total_amount)}")
            tot_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.history_table.setItem(row, 6, tot_item)

            st_item = QTableWidgetItem(str(po.status or "Pending"))
            st_item.setTextAlignment(Qt.AlignCenter)
            self.history_table.setItem(row, 7, st_item)

            action_widget = QWidget()
            action_widget.setStyleSheet("background: transparent; margin: 0px; padding: 0px;")
            a_layout = QHBoxLayout(action_widget)
            a_layout.setContentsMargins(4, 0, 4, 0)
            a_layout.setSpacing(6)
            a_layout.setAlignment(Qt.AlignCenter)

            btn_base = (
                "font-size: 11px; font-weight: bold; border-radius: 6px; "
                "min-height: 26px !important; max-height: 26px !important; height: 26px !important; "
                "padding: 0px 4px !important; margin: 0px !important;"
            )

            view_btn = QPushButton("View")
            view_btn.setFixedSize(62, 26)
            view_btn.setStyleSheet(f"QPushButton {{ {btn_base} background-color: #f1f5f9; color: #334155; border: 1.5px solid #cbd5e1; }} QPushButton:hover {{ background-color: #e2e8f0; }}")
            view_btn.setCursor(Qt.PointingHandCursor)
            view_btn.clicked.connect(lambda checked, p_id=po.id: self.view_po_details(p_id))
            a_layout.addWidget(view_btn)

            pdf_btn = QPushButton("PDF")
            pdf_btn.setFixedSize(54, 26)
            pdf_btn.setStyleSheet(f"QPushButton {{ {btn_base} background-color: #10b981; color: white; border: 1.5px solid #059669; }} QPushButton:hover {{ background-color: #059669; }}")
            pdf_btn.setCursor(Qt.PointingHandCursor)
            pdf_btn.clicked.connect(lambda checked, p_id=po.id: self.print_po_from_history(p_id))
            a_layout.addWidget(pdf_btn)

            del_btn = QPushButton("Delete")
            del_btn.setFixedSize(66, 26)
            del_btn.setStyleSheet(f"QPushButton {{ {btn_base} background-color: #ef4444; color: white; border: 1.5px solid #dc2626; }} QPushButton:hover {{ background-color: #dc2626; }}")
            del_btn.setCursor(Qt.PointingHandCursor)
            del_btn.clicked.connect(lambda checked, p_id=po.id: self.delete_po_from_history(p_id))
            a_layout.addWidget(del_btn)

            self.history_table.setCellWidget(row, 8, action_widget)

    def view_po_details(self, po_id):
        session = Session()
        try:
            po = session.query(PurchaseOrderMaster).filter_by(id=po_id).first()
            if not po:
                QMessageBox.warning(self, "Not Found", "Purchase order not found.")
                return

            dlg = QDialog(self)
            dlg.setWindowTitle(f"Purchase Order Details - {po.po_number}")
            dlg.setMinimumSize(750, 500)
            layout = QVBoxLayout(dlg)

            info_frame = QFrame()
            info_frame.setProperty("class", "CardFrame")
            i_layout = QGridLayout(info_frame)
            i_layout.setSpacing(8)

            i_layout.addWidget(QLabel(f"<b>PO Number:</b> {po.po_number}"), 0, 0)
            i_layout.addWidget(QLabel(f"<b>Date:</b> {po.date}"), 0, 1)
            i_layout.addWidget(QLabel(f"<b>Status:</b> {po.status}"), 0, 2)

            i_layout.addWidget(QLabel(f"<b>Supplier:</b> {po.supplier_name or 'N/A'}"), 1, 0)
            i_layout.addWidget(QLabel(f"<b>Mobile:</b> {po.supplier_mobile or 'N/A'}"), 1, 1)
            i_layout.addWidget(QLabel(f"<b>GSTIN:</b> {po.supplier_gst or 'N/A'}"), 1, 2)

            if po.notes:
                i_layout.addWidget(QLabel(f"<b>Notes:</b> {po.notes}"), 2, 0, 1, 3)

            layout.addWidget(info_frame)

            tbl = QTableWidget()
            tbl.setColumnCount(7)
            tbl.setHorizontalHeaderLabels(["S.N", "Code", "Item Name", "Brand / Model", "Qty", "Rate (₹)", "Total (₹)"])
            tbl.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            tbl.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
            tbl.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
            tbl.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
            tbl.verticalHeader().setVisible(False)
            tbl.verticalHeader().setDefaultSectionSize(40)

            items = session.query(PurchaseOrderItem).filter_by(po_id=po.id).all()
            tbl.setRowCount(len(items))
            for idx, it in enumerate(items):
                tbl.setItem(idx, 0, QTableWidgetItem(str(idx + 1)))
                tbl.setItem(idx, 1, QTableWidgetItem(it.product_code or "-"))
                tbl.setItem(idx, 2, QTableWidgetItem(it.item_name))
                tbl.setItem(idx, 3, QTableWidgetItem(it.brand_model or "-"))
                tbl.setItem(idx, 4, QTableWidgetItem(f"{it.qty} {it.unit or 'Pcs'}"))
                tbl.setItem(idx, 5, QTableWidgetItem(f"{format_inr(it.rate)}"))
                tbl.setItem(idx, 6, QTableWidgetItem(f"{format_inr(it.total_amount)}"))

            layout.addWidget(tbl, 1)

            btn_layout = QHBoxLayout()
            tot_lbl = QLabel(f"<b>Total Qty:</b> {po.total_qty} Units &nbsp;|&nbsp; <b>Total Amount:</b> ₹{format_inr(po.total_amount)}")
            tot_lbl.setStyleSheet("font-size: 13px; color: #d97706;")
            btn_layout.addWidget(tot_lbl)
            btn_layout.addStretch()

            p_btn = QPushButton("📄 Print PDF")
            p_btn.setProperty("class", "btn-success")
            p_btn.clicked.connect(lambda: self.print_po_from_history(po.id))
            btn_layout.addWidget(p_btn)

            c_btn = QPushButton("Close")
            c_btn.setProperty("class", "btn-secondary")
            c_btn.clicked.connect(dlg.accept)
            btn_layout.addWidget(c_btn)

            layout.addLayout(btn_layout)
            dlg.exec()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to view PO details: {e}")
        finally:
            session.close()

    def print_po_from_history(self, po_id):
        session = Session()
        try:
            po = session.query(PurchaseOrderMaster).filter_by(id=po_id).first()
            if not po:
                return

            s_name = session.query(Setting).filter_by(key='shop_name').first()
            s_contact = session.query(Setting).filter_by(key='shop_contact').first()
            s_address = session.query(Setting).filter_by(key='shop_address').first()
            s_gst = session.query(Setting).filter_by(key='shop_gst').first()

            items_list = []
            for it in po.items:
                items_list.append({
                    "product_code": it.product_code or "-",
                    "name": it.item_name,
                    "brand_model": it.brand_model or "-",
                    "qty": it.qty,
                    "unit": it.unit or "Pcs",
                    "rate": it.rate,
                    "total": it.total_amount
                })

            po_pdf_data = {
                "shop_name": s_name.value if s_name else "I TECH MOBILES,",
                "shop_contact": s_contact.value if s_contact else "N/A",
                "shop_address": s_address.value if s_address else "N/A",
                "shop_gst": s_gst.value if s_gst else "N/A",
                "po_number": po.po_number,
                "date": po.date.strftime("%Y-%m-%d") if po.date else "-",
                "expected_date": po.expected_date.strftime("%Y-%m-%d") if po.expected_date else "Immediate",
                "status": po.status,
                "notes": po.notes or "",
                "supplier_name": po.supplier_name or "N/A",
                "supplier_mobile": po.supplier_mobile or "N/A",
                "supplier_address": po.supplier_address or "N/A",
                "supplier_gst": po.supplier_gst or "N/A",
                "items": items_list,
                "total_items": po.total_items,
                "total_qty": po.total_qty,
                "total_amount": po.total_amount
            }

            os.makedirs("statements", exist_ok=True)
            safe_po = po.po_number.replace("/", "_").replace("\\", "_")
            pdf_path = os.path.abspath(f"statements/purchase_order_{safe_po}.pdf")
            generate_purchase_order_pdf(po_pdf_data, pdf_path)

            try:
                os.startfile(pdf_path)
            except Exception as e:
                print(f"Could not auto-open PDF: {e}")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate PO PDF: {e}")
        finally:
            session.close()

    def delete_po_from_history(self, po_id):
        reply = QMessageBox.question(
            self, "Confirm Delete",
            "Are you sure you want to delete this Purchase Order?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            session = Session()
            try:
                po = session.query(PurchaseOrderMaster).filter_by(id=po_id).first()
                if po:
                    session.delete(po)
                    session.commit()
                    QMessageBox.information(self, "Deleted", "Purchase order deleted.")
                    self.load_history_data()
            except Exception as e:
                session.rollback()
                QMessageBox.critical(self, "Error", f"Failed to delete PO: {e}")
            finally:
                session.close()
