from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, 
                             QPushButton, QLineEdit, QLabel, QDialog, QFormLayout, QMessageBox, QHeaderView, QComboBox)
from PySide6.QtCore import Qt
from database import Session
from models import Product, Category

class CategoryManagerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Manage Categories")
        self.setFixedSize(450, 400)
        self.init_ui()
        self.refresh_data()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)
        
        # Title
        title_lbl = QLabel("Product Categories Master")
        title_lbl.setStyleSheet("font-size: 15px; font-weight: bold; color: #6366f1; border-bottom: 1px solid #28284e; padding-bottom: 6px;")
        layout.addWidget(title_lbl)
        
        # Top layout for buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        
        self.add_btn = QPushButton("Add Category")
        self.add_btn.clicked.connect(self.add_category)
        
        self.edit_btn = QPushButton("Rename")
        self.edit_btn.setProperty("class", "btn-secondary")
        self.edit_btn.clicked.connect(self.edit_category)
        
        self.delete_btn = QPushButton("Delete")
        self.delete_btn.setProperty("class", "btn-danger")
        self.delete_btn.clicked.connect(self.delete_category)
        
        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.edit_btn)
        btn_layout.addWidget(self.delete_btn)
        layout.addLayout(btn_layout)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["ID", "Category Name"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        layout.addWidget(self.table)
        
        # Close button
        self.close_btn = QPushButton("Close")
        self.close_btn.setProperty("class", "btn-secondary")
        self.close_btn.clicked.connect(self.accept)
        layout.addWidget(self.close_btn)
        
    def refresh_data(self):
        session = Session()
        try:
            cats = session.query(Category).all()
            self.table.setRowCount(len(cats))
            for i, c in enumerate(cats):
                self.table.setItem(i, 0, QTableWidgetItem(str(c.id)))
                self.table.setItem(i, 1, QTableWidgetItem(c.name))
        except Exception as e:
            print(f"Error loading categories: {e}")
        finally:
            session.close()
            
    def get_selected_cat_id_name(self):
        selected = self.table.selectedItems()
        if not selected:
            return None, None
        row = selected[0].row()
        cat_id = int(self.table.item(row, 0).text())
        cat_name = self.table.item(row, 1).text()
        return cat_id, cat_name
        
    def add_category(self):
        from PySide6.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(self, "Add Category", "New Category Name:")
        if ok and name.strip():
            name = name.strip()
            session = Session()
            try:
                existing = session.query(Category).filter_by(name=name).first()
                if existing:
                    QMessageBox.warning(self, "Error", f"Category '{name}' already exists.")
                    return
                new_cat = Category(name=name)
                session.add(new_cat)
                session.commit()
                self.refresh_data()
            except Exception as e:
                session.rollback()
                QMessageBox.critical(self, "Error", f"Could not save category: {e}")
            finally:
                session.close()
                
    def edit_category(self):
        cat_id, cat_name = self.get_selected_cat_id_name()
        if cat_id is None:
            QMessageBox.information(self, "No Selection", "Please select a category to edit.")
            return
        from PySide6.QtWidgets import QInputDialog
        new_name, ok = QInputDialog.getText(self, "Rename Category", "New Category Name:", QLineEdit.Normal, cat_name)
        if ok and new_name.strip() and new_name.strip() != cat_name:
            new_name = new_name.strip()
            session = Session()
            try:
                existing = session.query(Category).filter_by(name=new_name).first()
                if existing:
                    QMessageBox.warning(self, "Error", f"Category '{new_name}' already exists.")
                    return
                
                # Update Category record
                cat = session.query(Category).get(cat_id)
                if cat:
                    cat.name = new_name
                
                # Cascade rename on all Products
                session.query(Product).filter_by(category=cat_name).update({Product.category: new_name})
                
                session.commit()
                self.refresh_data()
            except Exception as e:
                session.rollback()
                QMessageBox.critical(self, "Error", f"Could not rename category: {e}")
            finally:
                session.close()
                
    def delete_category(self):
        cat_id, cat_name = self.get_selected_cat_id_name()
        if cat_id is None:
            QMessageBox.information(self, "No Selection", "Please select a category to delete.")
            return
            
        session = Session()
        try:
            # Check if any products are using it
            prod_count = session.query(Product).filter_by(category=cat_name).count()
            if prod_count > 0:
                confirm = QMessageBox.question(
                    self, "Confirm Delete",
                    f"Category '{cat_name}' is currently used by {prod_count} products.\n"
                    "If you delete this category, these products will be reset to 'Phones'.\n"
                    "Do you want to proceed?",
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No
                )
                if confirm != QMessageBox.Yes:
                    return
                
                # Reset products
                session.query(Product).filter_by(category=cat_name).update({Product.category: 'Phones'})
            else:
                confirm = QMessageBox.question(
                    self, "Confirm Delete",
                    f"Are you sure you want to delete category '{cat_name}'?",
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No
                )
                if confirm != QMessageBox.Yes:
                    return
            
            cat = session.query(Category).get(cat_id)
            if cat:
                session.delete(cat)
            session.commit()
            self.refresh_data()
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", f"Could not delete category: {e}")
        finally:
            session.close()

class ProductDialog(QDialog):
    def __init__(self, product=None, parent=None):
        super().__init__(parent)
        self.product = product
        self.setWindowTitle("Edit Product" if product else "Add New Product")
        self.setFixedSize(400, 350)
        self.init_ui()

    def load_categories(self):
        self.category_combo.clear()
        session = Session()
        try:
            cats = session.query(Category).all()
            for c in cats:
                self.category_combo.addItem(c.name)
        except Exception as e:
            print(f"Error loading categories in dialog: {e}")
        finally:
            session.close()

    def init_ui(self):
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        
        self.name_input = QLineEdit()
        self.category_combo = QComboBox()
        self.category_combo.setEditable(False)
        self.load_categories()
        
        self.brand_input = QLineEdit()
        self.model_input = QLineEdit()
        self.imei_input = QLineEdit()
        self.purchase_price_input = QLineEdit()
        self.purchase_price_input.setText("0.00")
        self.selling_price_input = QLineEdit()
        self.selling_price_input.setText("0.00")
        self.stock_qty_input = QLineEdit()
        self.stock_qty_input.setText("0")

        form_layout.addRow("Product Name *:", self.name_input)
        form_layout.addRow("Category *:", self.category_combo)
        form_layout.addRow("Brand *:", self.brand_input)
        form_layout.addRow("Model *:", self.model_input)
        form_layout.addRow("IMEI Number:", self.imei_input)
        form_layout.addRow("Purchase Price (₹) *:", self.purchase_price_input)
        form_layout.addRow("Selling Price (₹) *:", self.selling_price_input)
        form_layout.addRow("Initial Stock Qty *:", self.stock_qty_input)
        
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
        if self.product:
            self.name_input.setText(self.product.name)
            
            cat = self.product.category or "Phones"
            idx = self.category_combo.findText(cat)
            if idx >= 0:
                self.category_combo.setCurrentIndex(idx)
            else:
                self.category_combo.addItem(cat)
                self.category_combo.setCurrentText(cat)

            self.brand_input.setText(self.product.brand)
            self.model_input.setText(self.product.model)
            self.imei_input.setText(self.product.imei or "")
            self.purchase_price_input.setText(str(self.product.purchase_price))
            self.selling_price_input.setText(str(self.product.selling_price))
            self.stock_qty_input.setText(str(self.product.stock_qty))
            # If editing, stock is usually adjusted via Purchase/Sales, but let's allow it in master
            # Or make it read-only/editable as standard. Let's keep it editable for manual adjustments.

    def handle_save(self):
        name = self.name_input.text().strip()
        category = self.category_combo.currentText().strip() or "Phones"
        brand = self.brand_input.text().strip()
        model = self.model_input.text().strip()
        imei = self.imei_input.text().strip() or None
        
        if not name or not brand or not model:
            QMessageBox.warning(self, "Validation Error", "Please fill in all mandatory fields (*)")
            return

        try:
            purchase_price = float(self.purchase_price_input.text())
            selling_price = float(self.selling_price_input.text())
            stock_qty = int(self.stock_qty_input.text())
            if purchase_price < 0 or selling_price < 0 or stock_qty < 0:
                raise ValueError
        except ValueError:
            QMessageBox.warning(self, "Validation Error", "Please enter valid non-negative numbers for prices and stock.")
            return

        session = Session()
        try:
            # Check IMEI uniqueness if provided
            if imei:
                existing = session.query(Product).filter_by(imei=imei).first()
                if existing and (not self.product or existing.id != self.product.id):
                    QMessageBox.warning(self, "Validation Error", f"A product with IMEI {imei} already exists.")
                    session.close()
                    return

            if self.product:
                # Update
                prod = session.query(Product).get(self.product.id)
                prod.name = name
                prod.category = category
                prod.brand = brand
                prod.model = model
                prod.imei = imei
                prod.purchase_price = purchase_price
                prod.selling_price = selling_price
                prod.stock_qty = stock_qty
            else:
                # Add
                new_prod = Product(
                    name=name, category=category, brand=brand, model=model, imei=imei,
                    purchase_price=purchase_price, selling_price=selling_price, stock_qty=stock_qty
                )
                session.add(new_prod)

            session.commit()
            self.accept()
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", f"Could not save product: {e}")
        finally:
            session.close()


class ProductsView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Top bar: Search and Buttons
        top_bar = QHBoxLayout()
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search products by name, brand, model or IMEI...")
        self.search_input.textChanged.connect(self.refresh_data)
        top_bar.addWidget(self.search_input, 4)

        self.add_btn = QPushButton("Add Product")
        self.add_btn.clicked.connect(self.add_product)
        top_bar.addWidget(self.add_btn, 1)

        self.manage_cats_btn = QPushButton("Manage Categories")
        self.manage_cats_btn.clicked.connect(self.manage_categories)
        top_bar.addWidget(self.manage_cats_btn, 1)

        self.edit_btn = QPushButton("Edit Product")
        self.edit_btn.setProperty("class", "btn-secondary")
        self.edit_btn.clicked.connect(self.edit_product)
        top_bar.addWidget(self.edit_btn, 1)

        self.delete_btn = QPushButton("Delete")
        self.delete_btn.setProperty("class", "btn-danger")
        self.delete_btn.clicked.connect(self.delete_product)
        top_bar.addWidget(self.delete_btn, 1)

        layout.addLayout(top_bar)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels([
            "ID", "Product Name", "Category", "Brand", "Model", "IMEI Number", 
            "Purchase Price", "Selling Price", "Stock Qty"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.doubleClicked.connect(self.edit_product)
        layout.addWidget(self.table)

    def refresh_data(self):
        search_txt = self.search_input.text().strip()
        session = Session()
        try:
            query = session.query(Product)
            if search_txt:
                query = query.filter(
                    Product.name.like(f"%{search_txt}%") |
                    Product.brand.like(f"%{search_txt}%") |
                    Product.model.like(f"%{search_txt}%") |
                    Product.imei.like(f"%{search_txt}%")
                )
            products = query.all()
            
            self.table.setRowCount(len(products))
            for i, p in enumerate(products):
                self.table.setItem(i, 0, QTableWidgetItem(str(p.id)))
                self.table.setItem(i, 1, QTableWidgetItem(p.name))
                self.table.setItem(i, 2, QTableWidgetItem(p.category or "Phones"))
                self.table.setItem(i, 3, QTableWidgetItem(p.brand))
                self.table.setItem(i, 4, QTableWidgetItem(p.model))
                self.table.setItem(i, 5, QTableWidgetItem(p.imei or "-"))
                self.table.setItem(i, 6, QTableWidgetItem(f"₹{p.purchase_price:,.2f}"))
                self.table.setItem(i, 7, QTableWidgetItem(f"₹{p.selling_price:,.2f}"))
                
                stock_item = QTableWidgetItem(str(p.stock_qty))
                if p.stock_qty <= 0:
                    stock_item.setForeground(Qt.red)
                elif p.stock_qty <= 5:
                    stock_item.setForeground(Qt.yellow)
                self.table.setItem(i, 8, stock_item)
                
        except Exception as e:
            print(f"Error loading products: {e}")
        finally:
            session.close()

    def get_selected_product_id(self):
        selected = self.table.selectedItems()
        if not selected:
            return None
        # The first column is ID
        return int(self.table.item(selected[0].row(), 0).text())

    def add_product(self):
        dlg = ProductDialog(parent=self)
        if dlg.exec() == QDialog.Accepted:
            self.refresh_data()

    def edit_product(self):
        prod_id = self.get_selected_product_id()
        if prod_id is None:
            QMessageBox.information(self, "No Selection", "Please select a product to edit.")
            return

        session = Session()
        try:
            prod = session.query(Product).get(prod_id)
            if prod:
                dlg = ProductDialog(product=prod, parent=self)
                if dlg.exec() == QDialog.Accepted:
                    self.refresh_data()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not load product details: {e}")
        finally:
            session.close()

    def delete_product(self):
        prod_id = self.get_selected_product_id()
        if prod_id is None:
            QMessageBox.information(self, "No Selection", "Please select a product to delete.")
            return

        confirm = QMessageBox.question(
            self, "Confirm Delete", "Are you sure you want to delete this product? All stock entries for this will be lost.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if confirm == QMessageBox.Yes:
            session = Session()
            try:
                prod = session.query(Product).get(prod_id)
                if prod:
                    session.delete(prod)
                    session.commit()
                    self.refresh_data()
            except Exception as e:
                session.rollback()
                QMessageBox.critical(self, "Error", f"Could not delete product (it may be linked to purchases or sales): {e}")
            finally:
                session.close()

    def manage_categories(self):
        dlg = CategoryManagerDialog(parent=self)
        dlg.exec()
        self.refresh_data()
