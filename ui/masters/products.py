from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, 
                             QPushButton, QLineEdit, QLabel, QDialog, QFormLayout, QMessageBox, QHeaderView, QComboBox, QCompleter, QTabWidget)
from PySide6.QtCore import Qt
from database import Session
from models import Product, Category, Brand, ProductModel
from utils.ui_helpers import enable_quick_add_auto_select

class ModelEditDialog(QDialog):
    def __init__(self, model_obj=None, initial_name="", default_brand=None, parent=None):
        super().__init__(parent)
        self.model_obj = model_obj
        self.setWindowTitle("Edit Model" if model_obj else "Add New Model")
        self.setFixedSize(380, 200)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        form = QFormLayout()
        
        self.name_input = QLineEdit()
        if model_obj:
            self.name_input.setText(model_obj.name)
        elif initial_name:
            self.name_input.setText(initial_name)
            
        self.brand_combo = QComboBox()
        self.brand_combo.setEditable(True)
        self.brand_combo.addItem("-- None / General --")
        
        session = Session()
        try:
            brands = session.query(Brand).order_by(Brand.name.asc()).all()
            for b in brands:
                self.brand_combo.addItem(b.name)
        finally:
            session.close()
            
        if model_obj and model_obj.brand_name:
            idx = self.brand_combo.findText(model_obj.brand_name)
            if idx >= 0:
                self.brand_combo.setCurrentIndex(idx)
            else:
                self.brand_combo.setEditText(model_obj.brand_name)
        elif default_brand:
            idx = self.brand_combo.findText(default_brand)
            if idx >= 0:
                self.brand_combo.setCurrentIndex(idx)
            else:
                self.brand_combo.setEditText(default_brand)
                
        form.addRow("Model Name *:", self.name_input)
        form.addRow("Brand:", self.brand_combo)
        layout.addLayout(form)
        
        btn_box = QHBoxLayout()
        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self.accept)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setProperty("class", "btn-secondary")
        self.cancel_btn.clicked.connect(self.reject)
        
        btn_box.addWidget(self.save_btn)
        btn_box.addWidget(self.cancel_btn)
        layout.addLayout(btn_box)
        
    def get_data(self):
        name = self.name_input.text().strip()
        brand = self.brand_combo.currentText().strip()
        if brand == "-- None / General --":
            brand = ""
        return name, brand

class ItemAttributesManagerDialog(QDialog):
    def __init__(self, initial_tab=0, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Manage Categories, Brands & Models")
        self.resize(740, 540)
        self.setMinimumSize(680, 480)
        self.init_ui()
        self.tabs.setCurrentIndex(initial_tab)
        self.refresh_all()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(12)

        # Header Title
        title_lbl = QLabel("Item Attributes Master (Category, Brand & Model)")
        title_lbl.setStyleSheet("font-size: 16px; font-weight: bold; color: #6366f1; border-bottom: 1px solid #28284e; padding-bottom: 8px;")
        main_layout.addWidget(title_lbl)

        # Tabs
        self.tabs = QTabWidget()
        
        # 1. Categories Tab
        self.cat_widget = QWidget()
        self.init_cat_tab(self.cat_widget)
        self.tabs.addTab(self.cat_widget, "📁 Categories")

        # 2. Brands Tab
        self.brand_widget = QWidget()
        self.init_brand_tab(self.brand_widget)
        self.tabs.addTab(self.brand_widget, "🏷️ Brands")

        # 3. Models Tab
        self.model_widget = QWidget()
        self.init_model_tab(self.model_widget)
        self.tabs.addTab(self.model_widget, "📱 Models")

        main_layout.addWidget(self.tabs)

        # Close Button at bottom
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.close_btn = QPushButton("Close")
        self.close_btn.setProperty("class", "btn-secondary")
        self.close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self.close_btn)
        main_layout.addLayout(btn_layout)

        self.tabs.currentChanged.connect(self.on_tab_changed)

    def on_tab_changed(self, index):
        if index == 0:
            self.refresh_categories()
        elif index == 1:
            self.refresh_brands()
        elif index == 2:
            self.refresh_models()

    def refresh_all(self):
        self.refresh_categories()
        self.refresh_brands()
        self.refresh_models()

    # ------------------ Categories Tab ------------------
    def init_cat_tab(self, parent):
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        top_bar = QHBoxLayout()
        self.cat_search = QLineEdit()
        self.cat_search.setPlaceholderText("🔍 Search category...")
        self.cat_search.textChanged.connect(self.filter_categories)
        top_bar.addWidget(self.cat_search, 1)

        self.add_cat_btn = QPushButton("Add Category")
        self.add_cat_btn.clicked.connect(self.add_category)
        top_bar.addWidget(self.add_cat_btn)

        self.edit_cat_btn = QPushButton("Rename")
        self.edit_cat_btn.setProperty("class", "btn-secondary")
        self.edit_cat_btn.clicked.connect(self.edit_category)
        top_bar.addWidget(self.edit_cat_btn)

        self.del_cat_btn = QPushButton("Delete")
        self.del_cat_btn.setProperty("class", "btn-danger")
        self.del_cat_btn.clicked.connect(self.delete_category)
        top_bar.addWidget(self.del_cat_btn)

        layout.addLayout(top_bar)

        self.cat_table = QTableWidget()
        self.cat_table.setColumnCount(3)
        self.cat_table.setHorizontalHeaderLabels(["ID", "Category Name", "Products Count"])
        self.cat_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.cat_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.cat_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.cat_table.verticalHeader().setVisible(False)
        self.cat_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.cat_table.setSelectionMode(QTableWidget.SingleSelection)
        self.cat_table.itemDoubleClicked.connect(lambda: self.edit_category())
        layout.addWidget(self.cat_table)

    def refresh_categories(self):
        session = Session()
        try:
            from sqlalchemy import func
            cats = session.query(Category).order_by(Category.name.asc()).all()
            prod_counts = dict(session.query(Product.category, func.count(Product.id)).group_by(Product.category).all())
            self.cats_data = []
            for c in cats:
                cnt = prod_counts.get(c.name, 0)
                self.cats_data.append((c.id, c.name, cnt))
            self.filter_categories()
        except Exception as e:
            print(f"Error loading categories: {e}")
        finally:
            session.close()

    def filter_categories(self):
        query = self.cat_search.text().strip().lower()
        filtered = [c for c in getattr(self, 'cats_data', []) if query in c[1].lower()]
        self.cat_table.setRowCount(len(filtered))
        for row, (c_id, c_name, count) in enumerate(filtered):
            self.cat_table.setItem(row, 0, QTableWidgetItem(str(c_id)))
            self.cat_table.setItem(row, 1, QTableWidgetItem(c_name))
            cnt_item = QTableWidgetItem(str(count))
            cnt_item.setTextAlignment(Qt.AlignCenter)
            self.cat_table.setItem(row, 2, cnt_item)

    def get_selected_cat(self):
        selected = self.cat_table.selectedItems()
        if not selected:
            return None, None
        row = selected[0].row()
        cat_id = int(self.cat_table.item(row, 0).text())
        cat_name = self.cat_table.item(row, 1).text()
        return cat_id, cat_name

    def add_category(self, initial_name=""):
        from PySide6.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(self, "Add Category", "New Category Name:", QLineEdit.Normal, initial_name)
        if ok and name.strip():
            name = name.strip()
            session = Session()
            try:
                existing = session.query(Category).filter(Category.name.ilike(name)).first()
                if existing:
                    QMessageBox.warning(self, "Error", f"Category '{name}' already exists.")
                    return existing.name
                new_cat = Category(name=name)
                session.add(new_cat)
                session.commit()
                self.refresh_categories()
                return name
            except Exception as e:
                session.rollback()
                QMessageBox.critical(self, "Error", f"Could not save category: {e}")
                return None
            finally:
                session.close()
        return None

    def edit_category(self):
        cat_id, cat_name = self.get_selected_cat()
        if cat_id is None:
            QMessageBox.information(self, "No Selection", "Please select a category to edit.")
            return
        from PySide6.QtWidgets import QInputDialog
        new_name, ok = QInputDialog.getText(self, "Rename Category", "New Category Name:", QLineEdit.Normal, cat_name)
        if ok and new_name.strip() and new_name.strip() != cat_name:
            new_name = new_name.strip()
            session = Session()
            try:
                existing = session.query(Category).filter(Category.name.ilike(new_name), Category.id != cat_id).first()
                if existing:
                    QMessageBox.warning(self, "Error", f"Category '{new_name}' already exists.")
                    return
                cat = session.query(Category).get(cat_id)
                if cat:
                    cat.name = new_name
                session.query(Product).filter_by(category=cat_name).update({Product.category: new_name})
                session.commit()
                self.refresh_categories()
            except Exception as e:
                session.rollback()
                QMessageBox.critical(self, "Error", f"Could not rename category: {e}")
            finally:
                session.close()

    def delete_category(self):
        cat_id, cat_name = self.get_selected_cat()
        if cat_id is None:
            QMessageBox.information(self, "No Selection", "Please select a category to delete.")
            return
        session = Session()
        try:
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
            self.refresh_categories()
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", f"Could not delete category: {e}")
        finally:
            session.close()

    # ------------------ Brands Tab ------------------
    def init_brand_tab(self, parent):
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        top_bar = QHBoxLayout()
        self.brand_search = QLineEdit()
        self.brand_search.setPlaceholderText("🔍 Search brand...")
        self.brand_search.textChanged.connect(self.filter_brands)
        top_bar.addWidget(self.brand_search, 1)

        self.add_brand_btn = QPushButton("Add Brand")
        self.add_brand_btn.clicked.connect(self.add_brand)
        top_bar.addWidget(self.add_brand_btn)

        self.edit_brand_btn = QPushButton("Rename")
        self.edit_brand_btn.setProperty("class", "btn-secondary")
        self.edit_brand_btn.clicked.connect(self.edit_brand)
        top_bar.addWidget(self.edit_brand_btn)

        self.del_brand_btn = QPushButton("Delete")
        self.del_brand_btn.setProperty("class", "btn-danger")
        self.del_brand_btn.clicked.connect(self.delete_brand)
        top_bar.addWidget(self.del_brand_btn)

        layout.addLayout(top_bar)

        self.brand_table = QTableWidget()
        self.brand_table.setColumnCount(4)
        self.brand_table.setHorizontalHeaderLabels(["ID", "Brand Name", "Products Count", "Models Count"])
        self.brand_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.brand_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.brand_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.brand_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.brand_table.verticalHeader().setVisible(False)
        self.brand_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.brand_table.setSelectionMode(QTableWidget.SingleSelection)
        self.brand_table.itemDoubleClicked.connect(lambda: self.edit_brand())
        layout.addWidget(self.brand_table)

    def refresh_brands(self):
        session = Session()
        try:
            from sqlalchemy import func
            brands = session.query(Brand).order_by(Brand.name.asc()).all()
            prod_counts = dict(session.query(Product.brand, func.count(Product.id)).group_by(Product.brand).all())
            model_counts = dict(session.query(ProductModel.brand_name, func.count(ProductModel.id)).group_by(ProductModel.brand_name).all())
            
            self.brands_data = []
            for b in brands:
                p_cnt = prod_counts.get(b.name, 0)
                m_cnt = model_counts.get(b.name, 0)
                self.brands_data.append((b.id, b.name, p_cnt, m_cnt))
            self.filter_brands()
        except Exception as e:
            print(f"Error loading brands: {e}")
        finally:
            session.close()

    def filter_brands(self):
        query = self.brand_search.text().strip().lower()
        filtered = [b for b in getattr(self, 'brands_data', []) if query in b[1].lower()]
        self.brand_table.setRowCount(len(filtered))
        for row, (b_id, b_name, p_cnt, m_cnt) in enumerate(filtered):
            self.brand_table.setItem(row, 0, QTableWidgetItem(str(b_id)))
            self.brand_table.setItem(row, 1, QTableWidgetItem(b_name))
            p_item = QTableWidgetItem(str(p_cnt))
            p_item.setTextAlignment(Qt.AlignCenter)
            self.brand_table.setItem(row, 2, p_item)
            m_item = QTableWidgetItem(str(m_cnt))
            m_item.setTextAlignment(Qt.AlignCenter)
            self.brand_table.setItem(row, 3, m_item)

    def get_selected_brand(self):
        selected = self.brand_table.selectedItems()
        if not selected:
            return None, None
        row = selected[0].row()
        b_id = int(self.brand_table.item(row, 0).text())
        b_name = self.brand_table.item(row, 1).text()
        return b_id, b_name

    def add_brand(self, initial_name=""):
        from PySide6.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(self, "Add Brand", "New Brand Name:", QLineEdit.Normal, initial_name)
        if ok and name.strip():
            name = name.strip()
            session = Session()
            try:
                existing = session.query(Brand).filter(Brand.name.ilike(name)).first()
                if existing:
                    QMessageBox.warning(self, "Error", f"Brand '{name}' already exists.")
                    return existing.name
                new_brand = Brand(name=name)
                session.add(new_brand)
                session.commit()
                self.refresh_brands()
                return name
            except Exception as e:
                session.rollback()
                QMessageBox.critical(self, "Error", f"Could not save brand: {e}")
                return None
            finally:
                session.close()
        return None

    def edit_brand(self):
        b_id, b_name = self.get_selected_brand()
        if b_id is None:
            QMessageBox.information(self, "No Selection", "Please select a brand to edit.")
            return
        from PySide6.QtWidgets import QInputDialog
        new_name, ok = QInputDialog.getText(self, "Rename Brand", "New Brand Name:", QLineEdit.Normal, b_name)
        if ok and new_name.strip() and new_name.strip() != b_name:
            new_name = new_name.strip()
            session = Session()
            try:
                existing = session.query(Brand).filter(Brand.name.ilike(new_name), Brand.id != b_id).first()
                if existing:
                    QMessageBox.warning(self, "Error", f"Brand '{new_name}' already exists.")
                    return
                brand = session.query(Brand).get(b_id)
                if brand:
                    brand.name = new_name
                session.query(Product).filter_by(brand=b_name).update({Product.brand: new_name})
                session.query(ProductModel).filter_by(brand_name=b_name).update({ProductModel.brand_name: new_name})
                session.commit()
                self.refresh_brands()
                self.refresh_models()
            except Exception as e:
                session.rollback()
                QMessageBox.critical(self, "Error", f"Could not rename brand: {e}")
            finally:
                session.close()

    def delete_brand(self):
        b_id, b_name = self.get_selected_brand()
        if b_id is None:
            QMessageBox.information(self, "No Selection", "Please select a brand to delete.")
            return
        session = Session()
        try:
            prod_count = session.query(Product).filter_by(brand=b_name).count()
            model_count = session.query(ProductModel).filter_by(brand_name=b_name).count()
            if prod_count > 0 or model_count > 0:
                confirm = QMessageBox.question(
                    self, "Confirm Delete",
                    f"Brand '{b_name}' is referenced by {prod_count} product(s) and {model_count} model(s).\n"
                    "Are you sure you want to delete this brand?",
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No
                )
                if confirm != QMessageBox.Yes:
                    return
            else:
                confirm = QMessageBox.question(
                    self, "Confirm Delete",
                    f"Are you sure you want to delete brand '{b_name}'?",
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No
                )
                if confirm != QMessageBox.Yes:
                    return
            brand = session.query(Brand).get(b_id)
            if brand:
                session.delete(brand)
            session.commit()
            self.refresh_brands()
            self.refresh_models()
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", f"Could not delete brand: {e}")
        finally:
            session.close()

    # ------------------ Models Tab ------------------
    def init_model_tab(self, parent):
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        filter_bar = QHBoxLayout()
        filter_bar.setSpacing(8)

        lbl_brand = QLabel("Brand:")
        filter_bar.addWidget(lbl_brand)

        self.model_brand_filter = QComboBox()
        self.model_brand_filter.setMinimumWidth(150)
        self.model_brand_filter.currentIndexChanged.connect(self.filter_models)
        filter_bar.addWidget(self.model_brand_filter)

        self.model_search = QLineEdit()
        self.model_search.setPlaceholderText("🔍 Search model name...")
        self.model_search.textChanged.connect(self.filter_models)
        filter_bar.addWidget(self.model_search, 1)

        self.add_model_btn = QPushButton("Add Model")
        self.add_model_btn.clicked.connect(self.add_model)
        filter_bar.addWidget(self.add_model_btn)

        self.edit_model_btn = QPushButton("Edit Model")
        self.edit_model_btn.setProperty("class", "btn-secondary")
        self.edit_model_btn.clicked.connect(self.edit_model)
        filter_bar.addWidget(self.edit_model_btn)

        self.del_model_btn = QPushButton("Delete")
        self.del_model_btn.setProperty("class", "btn-danger")
        self.del_model_btn.clicked.connect(self.delete_model)
        filter_bar.addWidget(self.del_model_btn)

        layout.addLayout(filter_bar)

        self.model_table = QTableWidget()
        self.model_table.setColumnCount(4)
        self.model_table.setHorizontalHeaderLabels(["ID", "Model Name", "Brand", "Products Count"])
        self.model_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.model_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.model_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.model_table.verticalHeader().setVisible(False)
        self.model_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.model_table.setSelectionMode(QTableWidget.SingleSelection)
        self.model_table.itemDoubleClicked.connect(lambda: self.edit_model())
        layout.addWidget(self.model_table)

    def refresh_models(self):
        session = Session()
        try:
            from sqlalchemy import func
            curr_brand = self.model_brand_filter.currentText()
            self.model_brand_filter.blockSignals(True)
            self.model_brand_filter.clear()
            self.model_brand_filter.addItem("-- All Brands --")
            brands = session.query(Brand).order_by(Brand.name.asc()).all()
            for b in brands:
                self.model_brand_filter.addItem(b.name)
            idx = self.model_brand_filter.findText(curr_brand)
            if idx >= 0:
                self.model_brand_filter.setCurrentIndex(idx)
            self.model_brand_filter.blockSignals(False)

            models = session.query(ProductModel).order_by(ProductModel.name.asc()).all()
            prod_counts = dict(session.query(Product.model, func.count(Product.id)).group_by(Product.model).all())

            self.models_data = []
            for m in models:
                cnt = prod_counts.get(m.name, 0)
                self.models_data.append((m.id, m.name, m.brand_name or "General", cnt))
            self.filter_models()
        except Exception as e:
            print(f"Error loading models: {e}")
        finally:
            session.close()

    def filter_models(self):
        brand_sel = self.model_brand_filter.currentText()
        query = self.model_search.text().strip().lower()

        filtered = []
        for m_id, m_name, b_name, cnt in getattr(self, 'models_data', []):
            if brand_sel != "-- All Brands --" and b_name != brand_sel:
                continue
            if query and query not in m_name.lower() and query not in b_name.lower():
                continue
            filtered.append((m_id, m_name, b_name, cnt))

        self.model_table.setRowCount(len(filtered))
        for row, (m_id, m_name, b_name, cnt) in enumerate(filtered):
            self.model_table.setItem(row, 0, QTableWidgetItem(str(m_id)))
            self.model_table.setItem(row, 1, QTableWidgetItem(m_name))
            self.model_table.setItem(row, 2, QTableWidgetItem(b_name))
            cnt_item = QTableWidgetItem(str(cnt))
            cnt_item.setTextAlignment(Qt.AlignCenter)
            self.model_table.setItem(row, 3, cnt_item)

    def get_selected_model(self):
        selected = self.model_table.selectedItems()
        if not selected:
            return None, None, None
        row = selected[0].row()
        m_id = int(self.model_table.item(row, 0).text())
        m_name = self.model_table.item(row, 1).text()
        b_name = self.model_table.item(row, 2).text()
        return m_id, m_name, b_name

    def add_model(self, initial_name="", default_brand=""):
        brand_hint = default_brand or (self.model_brand_filter.currentText() if self.model_brand_filter.currentText() != "-- All Brands --" else "")
        dlg = ModelEditDialog(initial_name=initial_name, default_brand=brand_hint, parent=self)
        if dlg.exec() == QDialog.Accepted:
            name, brand_name = dlg.get_data()
            if not name:
                QMessageBox.warning(self, "Error", "Model name cannot be empty.")
                return None
            session = Session()
            try:
                existing = session.query(ProductModel).filter(ProductModel.name.ilike(name)).first()
                if existing:
                    QMessageBox.warning(self, "Error", f"Model '{name}' already exists.")
                    return existing.name
                
                brand_id = None
                if brand_name:
                    b_obj = session.query(Brand).filter(Brand.name.ilike(brand_name)).first()
                    if not b_obj:
                        b_obj = Brand(name=brand_name)
                        session.add(b_obj)
                        session.flush()
                    brand_id = b_obj.id
                    brand_name = b_obj.name

                new_model = ProductModel(name=name, brand_id=brand_id, brand_name=brand_name)
                session.add(new_model)
                session.commit()
                self.refresh_models()
                self.refresh_brands()
                return name
            except Exception as e:
                session.rollback()
                QMessageBox.critical(self, "Error", f"Could not save model: {e}")
                return None
            finally:
                session.close()
        return None

    def edit_model(self):
        m_id, m_name, b_name = self.get_selected_model()
        if m_id is None:
            QMessageBox.information(self, "No Selection", "Please select a model to edit.")
            return
        session = Session()
        try:
            model_obj = session.query(ProductModel).get(m_id)
            if not model_obj:
                return
            dlg = ModelEditDialog(model_obj=model_obj, parent=self)
            if dlg.exec() == QDialog.Accepted:
                new_name, new_brand = dlg.get_data()
                if not new_name:
                    QMessageBox.warning(self, "Error", "Model name cannot be empty.")
                    return
                dup = session.query(ProductModel).filter(ProductModel.name.ilike(new_name), ProductModel.id != m_id).first()
                if dup:
                    QMessageBox.warning(self, "Error", f"Model '{new_name}' already exists.")
                    return
                
                brand_id = None
                if new_brand:
                    b_obj = session.query(Brand).filter(Brand.name.ilike(new_brand)).first()
                    if not b_obj:
                        b_obj = Brand(name=new_brand)
                        session.add(b_obj)
                        session.flush()
                    brand_id = b_obj.id
                    new_brand = b_obj.name

                model_obj.name = new_name
                model_obj.brand_id = brand_id
                model_obj.brand_name = new_brand

                session.query(Product).filter_by(model=m_name).update({Product.model: new_name})
                session.commit()
                self.refresh_models()
                self.refresh_brands()
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", f"Could not update model: {e}")
        finally:
            session.close()

    def delete_model(self):
        m_id, m_name, b_name = self.get_selected_model()
        if m_id is None:
            QMessageBox.information(self, "No Selection", "Please select a model to delete.")
            return
        session = Session()
        try:
            prod_count = session.query(Product).filter_by(model=m_name).count()
            if prod_count > 0:
                confirm = QMessageBox.question(
                    self, "Confirm Delete",
                    f"Model '{m_name}' is currently used by {prod_count} product(s).\n"
                    "Are you sure you want to delete this model?",
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No
                )
                if confirm != QMessageBox.Yes:
                    return
            else:
                confirm = QMessageBox.question(
                    self, "Confirm Delete",
                    f"Are you sure you want to delete model '{m_name}'?",
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No
                )
                if confirm != QMessageBox.Yes:
                    return
            model_obj = session.query(ProductModel).get(m_id)
            if model_obj:
                session.delete(model_obj)
            session.commit()
            self.refresh_models()
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", f"Could not delete model: {e}")
        finally:
            session.close()

class CategoryManagerDialog(ItemAttributesManagerDialog):
    def __init__(self, parent=None):
        super().__init__(initial_tab=0, parent=parent)


class ProductDialog(QDialog):
    def __init__(self, product=None, initial_name="", parent=None):
        super().__init__(parent)
        self.product = product
        self.initial_name = initial_name
        self.setWindowTitle("Edit Product" if product else "Add New Product")
        
        # Check settings for IMEI visibility
        from database import Setting
        session = Session()
        self.show_imei = True
        try:
            val = session.query(Setting).filter_by(key='enable_imei_tracking').first()
            if val and val.value == 'false':
                self.show_imei = False
        except Exception:
            pass
        finally:
            session.close()

        if self.show_imei:
            self.setFixedSize(450, 520)
        else:
            self.setFixedSize(450, 490)
            
        self.init_ui()

    def suggest_product_code(self):
        if self.product is None:
            category_name = self.category_combo.currentText().strip()
            if category_name:
                session = Session()
                try:
                    from database import generate_next_product_code
                    code = generate_next_product_code(session, category_name)
                    self.product_code_input.setText(code)
                except Exception as e:
                    print(f"Error generating code: {e}")
                finally:
                    session.close()

    def load_categories(self, select_category=None):
        current_txt = select_category if select_category else (self.category_combo.currentText() if hasattr(self, 'category_combo') else "")
        self.category_combo.blockSignals(True)
        self.category_combo.clear()
        session = Session()
        try:
            cats = session.query(Category).order_by(Category.name.asc()).all()
            for c in cats:
                self.category_combo.addItem(c.name)
        except Exception as e:
            print(f"Error loading categories in dialog: {e}")
        finally:
            session.close()
        self.category_combo.blockSignals(False)

        # Autocomplete configuration
        completer = QCompleter(self.category_combo.model(), self.category_combo)
        completer.setFilterMode(Qt.MatchContains)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.setCompletionMode(QCompleter.PopupCompletion)
        self.category_combo.setCompleter(completer)
        completer.activated[str].connect(self._on_completer_activated)
        
        if current_txt:
            idx = self.category_combo.findText(current_txt)
            if idx >= 0:
                self.category_combo.setCurrentIndex(idx)
            else:
                self.category_combo.setEditText(current_txt)
        elif self.category_combo.count() > 0:
            self.category_combo.setCurrentIndex(0)

        if hasattr(self, 'add_category_btn'):
            self.check_category_match()

    def load_brands(self, select_brand=None):
        current_txt = select_brand if select_brand else (self.brand_combo.currentText() if hasattr(self, 'brand_combo') else "")
        self.brand_combo.blockSignals(True)
        self.brand_combo.clear()
        session = Session()
        try:
            brands = session.query(Brand).order_by(Brand.name.asc()).all()
            for b in brands:
                self.brand_combo.addItem(b.name)
        except Exception as e:
            print(f"Error loading brands in dialog: {e}")
        finally:
            session.close()
        self.brand_combo.blockSignals(False)

        completer = QCompleter(self.brand_combo.model(), self.brand_combo)
        completer.setFilterMode(Qt.MatchContains)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.setCompletionMode(QCompleter.PopupCompletion)
        self.brand_combo.setCompleter(completer)

        if current_txt:
            idx = self.brand_combo.findText(current_txt)
            if idx >= 0:
                self.brand_combo.setCurrentIndex(idx)
            else:
                self.brand_combo.setEditText(current_txt)
        elif self.brand_combo.count() > 0:
            self.brand_combo.setCurrentIndex(0)

    def load_models(self, select_model=None, for_brand=None):
        current_txt = select_model if select_model else (self.model_combo.currentText() if hasattr(self, 'model_combo') else "")
        self.model_combo.blockSignals(True)
        self.model_combo.clear()
        session = Session()
        try:
            q = session.query(ProductModel)
            if for_brand and for_brand.strip():
                b_name = for_brand.strip()
                q = q.filter((ProductModel.brand_name.ilike(b_name)) | (ProductModel.brand_name == None) | (ProductModel.brand_name == ""))
            models = q.order_by(ProductModel.name.asc()).all()
            for m in models:
                self.model_combo.addItem(m.name)
        except Exception as e:
            print(f"Error loading models in dialog: {e}")
        finally:
            session.close()
        self.model_combo.blockSignals(False)

        completer = QCompleter(self.model_combo.model(), self.model_combo)
        completer.setFilterMode(Qt.MatchContains)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.setCompletionMode(QCompleter.PopupCompletion)
        self.model_combo.setCompleter(completer)

        if current_txt:
            idx = self.model_combo.findText(current_txt)
            if idx >= 0:
                self.model_combo.setCurrentIndex(idx)
            else:
                self.model_combo.setEditText(current_txt)

    def on_brand_changed(self, text):
        brand_name = self.brand_combo.currentText().strip()
        curr_model = self.model_combo.currentText().strip()
        self.load_models(select_model=curr_model, for_brand=brand_name)

    def _on_completer_activated(self, text):
        self.category_combo.setCurrentText(text)
        self.suggest_product_code()
        self.check_category_match()

    def check_category_match(self):
        text = self.category_combo.currentText().strip()
        if not text:
            self.add_category_btn.hide()
            return
        
        matched = False
        for i in range(self.category_combo.count()):
            if self.category_combo.itemText(i).strip().lower() == text.lower():
                matched = True
                break
        
        if not matched:
            self.add_category_btn.show()
        else:
            self.add_category_btn.hide()

    def on_category_text_changed(self, text):
        self.check_category_match()
        if self.category_combo.hasFocus() and text:
            completer = self.category_combo.completer()
            if completer:
                completer.setCompletionPrefix(text)
                completer.complete()

    def handle_add_category_click(self):
        typed_text = self.category_combo.currentText().strip()
        mgr = ItemAttributesManagerDialog(initial_tab=0, parent=self)
        new_cat = mgr.add_category(initial_name=typed_text)
        if new_cat:
            self.load_categories(select_category=new_cat)
            self.suggest_product_code()

    def handle_add_brand_click(self):
        typed_text = self.brand_combo.currentText().strip()
        mgr = ItemAttributesManagerDialog(initial_tab=1, parent=self)
        new_brand = mgr.add_brand(initial_name=typed_text)
        if new_brand:
            self.load_brands(select_brand=new_brand)
            self.load_models(for_brand=new_brand)

    def handle_add_model_click(self):
        typed_text = self.model_combo.currentText().strip()
        brand_name = self.brand_combo.currentText().strip()
        mgr = ItemAttributesManagerDialog(initial_tab=2, parent=self)
        new_model = mgr.add_model(initial_name=typed_text, default_brand=brand_name)
        if new_model:
            self.load_models(select_model=new_model, for_brand=brand_name)

    def init_ui(self):
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        
        self.product_code_input = QLineEdit()
        self.product_code_input.setPlaceholderText("Auto-generated")
        
        self.name_input = QLineEdit()
        self.category_combo = QComboBox()
        self.category_combo.setEditable(True)
        self.category_combo.setInsertPolicy(QComboBox.NoInsert)
        enable_quick_add_auto_select(self.category_combo)
        
        self.load_categories()

        self.brand_combo = QComboBox()
        self.brand_combo.setEditable(True)
        self.brand_combo.setInsertPolicy(QComboBox.NoInsert)
        enable_quick_add_auto_select(self.brand_combo)
        self.load_brands()

        self.model_combo = QComboBox()
        self.model_combo.setEditable(True)
        self.model_combo.setInsertPolicy(QComboBox.NoInsert)
        enable_quick_add_auto_select(self.model_combo)
        self.load_models()

        # Backward compatibility properties
        self.brand_input = self.brand_combo.lineEdit()
        self.model_input = self.model_combo.lineEdit()

        # Check if user is Admin, otherwise set read-only for manual code editing
        self.is_authorized = True
        try:
            curr = self
            while curr is not None:
                if hasattr(curr, "user_data"):
                    self.is_authorized = curr.user_data.get("role") == "Admin"
                    break
                curr = curr.parent()
        except Exception:
            pass
            
        if not self.is_authorized:
            self.product_code_input.setReadOnly(True)
            self.product_code_input.setToolTip("Only administrators can edit product codes manually.")

        # Connect category changes
        self.category_combo.currentTextChanged.connect(self.suggest_product_code)
        self.category_combo.currentTextChanged.connect(self.check_category_match)
        if self.category_combo.lineEdit():
            self.category_combo.lineEdit().textChanged.connect(self.on_category_text_changed)

        # Connect brand changes to filter model suggestions
        self.brand_combo.currentTextChanged.connect(self.on_brand_changed)

        # Layout for category combo and Add Category (+) button
        cat_layout = QHBoxLayout()
        cat_layout.setContentsMargins(0, 0, 0, 0)
        cat_layout.setSpacing(6)
        cat_layout.addWidget(self.category_combo, 1)
        
        self.add_category_btn = QPushButton("+")
        self.add_category_btn.setToolTip("Add / Manage Categories")
        self.add_category_btn.setProperty("class", "btn-quick-add")
        self.add_category_btn.setFixedWidth(40)
        self.add_category_btn.setStyleSheet("padding: 0px; font-size: 18px; font-weight: bold; text-align: center;")
        self.add_category_btn.setCursor(Qt.PointingHandCursor)
        self.add_category_btn.clicked.connect(self.handle_add_category_click)
        cat_layout.addWidget(self.add_category_btn)
        
        # Layout for brand combo and Add Brand (+) button
        brand_layout = QHBoxLayout()
        brand_layout.setContentsMargins(0, 0, 0, 0)
        brand_layout.setSpacing(6)
        brand_layout.addWidget(self.brand_combo, 1)

        self.add_brand_btn = QPushButton("+")
        self.add_brand_btn.setToolTip("Add / Manage Brands")
        self.add_brand_btn.setProperty("class", "btn-quick-add")
        self.add_brand_btn.setFixedWidth(40)
        self.add_brand_btn.setStyleSheet("padding: 0px; font-size: 18px; font-weight: bold; text-align: center;")
        self.add_brand_btn.setCursor(Qt.PointingHandCursor)
        self.add_brand_btn.clicked.connect(self.handle_add_brand_click)
        brand_layout.addWidget(self.add_brand_btn)

        # Layout for model combo and Add Model (+) button
        model_layout = QHBoxLayout()
        model_layout.setContentsMargins(0, 0, 0, 0)
        model_layout.setSpacing(6)
        model_layout.addWidget(self.model_combo, 1)

        self.add_model_btn = QPushButton("+")
        self.add_model_btn.setToolTip("Add / Manage Models")
        self.add_model_btn.setProperty("class", "btn-quick-add")
        self.add_model_btn.setFixedWidth(40)
        self.add_model_btn.setStyleSheet("padding: 0px; font-size: 18px; font-weight: bold; text-align: center;")
        self.add_model_btn.setCursor(Qt.PointingHandCursor)
        self.add_model_btn.clicked.connect(self.handle_add_model_click)
        model_layout.addWidget(self.add_model_btn)

        self.unit_combo = QComboBox()
        self.unit_combo.addItems(["Pcs", "Box", "Kg", "Grams", "Ltr", "Mtr", "Nos", "Pack", "Set"])

        self.imei_input = QLineEdit()
        self.purchase_price_input = QLineEdit()
        self.purchase_price_input.setText("0.00")
        self.selling_price_input = QLineEdit()
        self.selling_price_input.setText("0.00")
        self.stock_qty_input = QLineEdit()
        self.stock_qty_input.setText("0")
        self.low_stock_limit_input = QLineEdit()
        self.low_stock_limit_input.setText("5")

        if not self.product and self.initial_name:
            self.name_input.setText(self.initial_name)

        form_layout.addRow("Product Code *:", self.product_code_input)
        form_layout.addRow("Product Name *:", self.name_input)
        form_layout.addRow("Category *:", cat_layout)
        form_layout.addRow("Unit *:", self.unit_combo)
        form_layout.addRow("Brand *:", brand_layout)
        form_layout.addRow("Model *:", model_layout)
        if self.show_imei:
            form_layout.addRow("IMEI Number:", self.imei_input)
        form_layout.addRow("Purchase Price (₹) *:", self.purchase_price_input)
        form_layout.addRow("Selling Price (₹) *:", self.selling_price_input)
        form_layout.addRow("Initial Stock Qty *:", self.stock_qty_input)
        form_layout.addRow("Low Stock Limit *:", self.low_stock_limit_input)
        
        layout.addLayout(form_layout)

        # Trigger initial code suggestion
        if self.product is None:
            self.suggest_product_code()

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
            self.product_code_input.setText(self.product.product_code or "")
            self.name_input.setText(self.product.name)
            
            cat = self.product.category or "Phones"
            idx = self.category_combo.findText(cat)
            if idx >= 0:
                self.category_combo.setCurrentIndex(idx)
            else:
                self.category_combo.addItem(cat)
                self.category_combo.setCurrentText(cat)

            unit_val = getattr(self.product, 'unit', 'Pcs') or 'Pcs'
            u_idx = self.unit_combo.findText(unit_val)
            if u_idx >= 0:
                self.unit_combo.setCurrentIndex(u_idx)

            if self.product.brand:
                b_idx = self.brand_combo.findText(self.product.brand)
                if b_idx >= 0:
                    self.brand_combo.setCurrentIndex(b_idx)
                else:
                    self.brand_combo.setEditText(self.product.brand)
                self.load_models(for_brand=self.product.brand)

            if self.product.model:
                m_idx = self.model_combo.findText(self.product.model)
                if m_idx >= 0:
                    self.model_combo.setCurrentIndex(m_idx)
                else:
                    self.model_combo.setEditText(self.product.model)

            self.imei_input.setText(self.product.imei or "")
            self.purchase_price_input.setText(str(self.product.purchase_price))
            self.selling_price_input.setText(str(self.product.selling_price))
            self.stock_qty_input.setText(str(self.product.stock_qty))
            self.low_stock_limit_input.setText(str(self.product.low_stock_limit))

    def handle_save(self):
        name = self.name_input.text().strip()
        category = self.category_combo.currentText().strip() or "Phones"
        brand = self.brand_input.text().strip()
        model = self.model_input.text().strip()
        imei = self.imei_input.text().strip() or None
        product_code = self.product_code_input.text().strip()
        
        if not product_code:
            QMessageBox.warning(self, "Validation Error", "Product Code is required.")
            return
            
        if len(product_code) != 4 or not product_code.isdigit():
            QMessageBox.warning(self, "Validation Error", "Product Code must be exactly 4 numeric digits.")
            return

        if not name or not brand or not model:
            QMessageBox.warning(self, "Validation Error", "Please fill in all mandatory fields (*)")
            return

        unit = self.unit_combo.currentText().strip() or "Pcs"

        try:
            purchase_price = float(self.purchase_price_input.text())
            selling_price = float(self.selling_price_input.text())
            stock_qty = int(self.stock_qty_input.text())
            low_stock_limit = int(self.low_stock_limit_input.text())
            if purchase_price < 0 or selling_price < 0 or stock_qty < 0 or low_stock_limit < 0:
                raise ValueError
        except ValueError:
            QMessageBox.warning(self, "Validation Error", "Please enter valid non-negative numbers for prices, stock, and low stock limit.")
            return

        session = Session()
        try:
            from database import get_category_code
            cat_code = get_category_code(session, category)
            if not product_code.startswith(cat_code):
                QMessageBox.warning(self, "Validation Error", f"Product Code for category '{category}' must start with category code '{cat_code}'.")
                session.close()
                return

            # Check product_code uniqueness
            existing_code = session.query(Product).filter_by(product_code=product_code).first()
            if existing_code and (not self.product or existing_code.id != self.product.id):
                QMessageBox.warning(self, "Validation Error", f"Product Code '{product_code}' is already assigned to another product.")
                session.close()
                return

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
                prod.product_code = product_code
                prod.name = name
                prod.category = category
                prod.brand = brand
                prod.model = model
                prod.imei = imei
                prod.purchase_price = purchase_price
                prod.selling_price = selling_price
                prod.stock_qty = stock_qty
                prod.low_stock_limit = low_stock_limit
                prod.unit = unit
                self.saved_product_id = prod.id
                self.saved_product_name = prod.name
            else:
                # Add
                new_prod = Product(
                    product_code=product_code,
                    name=name, category=category, brand=brand, model=model, imei=imei,
                    purchase_price=purchase_price, selling_price=selling_price, stock_qty=stock_qty,
                    low_stock_limit=low_stock_limit,
                    unit=unit
                )
                session.add(new_prod)
                session.flush()
                self.saved_product_id = new_prod.id
                self.saved_product_name = new_prod.name

            # Auto-register brand and model into master catalog if newly typed
            if brand:
                b_obj = session.query(Brand).filter(Brand.name.ilike(brand)).first()
                if not b_obj:
                    b_obj = Brand(name=brand)
                    session.add(b_obj)
                    session.flush()
                if model:
                    m_obj = session.query(ProductModel).filter(ProductModel.name.ilike(model)).first()
                    if not m_obj:
                        session.add(ProductModel(name=model, brand_id=b_obj.id, brand_name=b_obj.name))

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

        self.add_btn = QPushButton("Add Product (Ctrl+N)")
        self.add_btn.setToolTip("Add new product (Ctrl+N)")
        self.add_btn.clicked.connect(self.add_product)
        top_bar.addWidget(self.add_btn, 1)

        self.manage_cats_btn = QPushButton("Manage Category / Brand / Model")
        self.manage_cats_btn.setToolTip("Manage Categories, Brands, and Models Master")
        self.manage_cats_btn.clicked.connect(self.manage_attributes)
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
        self.table.setColumnCount(11)
        self.table.setHorizontalHeaderLabels([
            "ID", "Product Code", "Product Name", "Category", "Brand", "Model", "IMEI Number", 
            "Purchase Price", "Selling Price", "Stock Qty", "Low Limit"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.doubleClicked.connect(self.edit_product)
        layout.addWidget(self.table)

    def refresh_data(self):
        from database import Setting
        session = Session()
        show_imei = True
        try:
            val = session.query(Setting).filter_by(key='enable_imei_tracking').first()
            if val and val.value == 'false':
                show_imei = False
        except Exception:
            pass
        finally:
            session.close()

        self.table.setColumnHidden(6, not show_imei)
        if show_imei:
            self.search_input.setPlaceholderText("Search products by code, name, brand, model or IMEI...")
        else:
            self.search_input.setPlaceholderText("Search products by code, name, brand, or model...")

        search_txt = self.search_input.text().strip()
        session = Session()
        try:
            query = session.query(Product)
            if search_txt:
                if show_imei:
                    query = query.filter(
                        Product.product_code.like(f"%{search_txt}%") |
                        Product.name.like(f"%{search_txt}%") |
                        Product.brand.like(f"%{search_txt}%") |
                        Product.model.like(f"%{search_txt}%") |
                        Product.imei.like(f"%{search_txt}%")
                    )
                else:
                    query = query.filter(
                        Product.product_code.like(f"%{search_txt}%") |
                        Product.name.like(f"%{search_txt}%") |
                        Product.brand.like(f"%{search_txt}%") |
                        Product.model.like(f"%{search_txt}%")
                    )
            products = query.all()
            
            self.table.setRowCount(len(products))
            for i, p in enumerate(products):
                self.table.setItem(i, 0, QTableWidgetItem(str(p.id)))
                self.table.setItem(i, 1, QTableWidgetItem(p.product_code or "-"))
                self.table.setItem(i, 2, QTableWidgetItem(p.name))
                self.table.setItem(i, 3, QTableWidgetItem(p.category or "Phones"))
                self.table.setItem(i, 4, QTableWidgetItem(p.brand))
                self.table.setItem(i, 5, QTableWidgetItem(p.model))
                self.table.setItem(i, 6, QTableWidgetItem(p.imei or "-"))
                self.table.setItem(i, 7, QTableWidgetItem(f"₹{p.purchase_price:,.2f}"))
                self.table.setItem(i, 8, QTableWidgetItem(f"₹{p.selling_price:,.2f}"))
                
                stock_item = QTableWidgetItem(str(p.stock_qty))
                if p.stock_qty <= 0:
                    stock_item.setForeground(Qt.red)
                elif p.stock_qty <= p.low_stock_limit:
                    stock_item.setForeground(Qt.yellow)
                self.table.setItem(i, 9, stock_item)
                
                self.table.setItem(i, 10, QTableWidgetItem(str(p.low_stock_limit)))
                
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

    def manage_attributes(self, initial_tab=0):
        dlg = ItemAttributesManagerDialog(initial_tab=initial_tab, parent=self)
        dlg.exec()
        self.refresh_data()

    def manage_categories(self):
        self.manage_attributes(0)
