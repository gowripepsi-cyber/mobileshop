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
        self.setFixedSize(420, 180)
        self.init_ui()

    def load_brands(self, select_brand=None):
        current_txt = select_brand if select_brand else (self.brand_combo.currentText() if hasattr(self, 'brand_combo') else "")
        self.brand_combo.blockSignals(True)
        self.brand_combo.clear()
        session = Session()
        try:
            # Load unique brands/models from Product and Brand tables
            brand_set = set()
            for b in session.query(Brand.name).all():
                if b[0] and b[0].strip():
                    brand_set.add(b[0].strip())
            for p in session.query(Product.brand).distinct().all():
                if p[0] and p[0].strip():
                    brand_set.add(p[0].strip())
            for bm in sorted(list(brand_set)):
                self.brand_combo.addItem(bm)
        except Exception as e:
            print(f"Error loading brands: {e}")
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

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        form_layout = QFormLayout()
        form_layout.setSpacing(10)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Enter product name")

        self.brand_combo = QComboBox()
        self.brand_combo.setEditable(True)
        self.brand_combo.setInsertPolicy(QComboBox.NoInsert)
        self.brand_combo.setPlaceholderText("Enter or select brand / model")
        enable_quick_add_auto_select(self.brand_combo)
        self.load_brands()

        self.brand_input = self.brand_combo.lineEdit()

        if not self.product and self.initial_name:
            self.name_input.setText(self.initial_name)

        form_layout.addRow("Product Name *:", self.name_input)
        form_layout.addRow("Brand / Model *:", self.brand_combo)

        layout.addLayout(form_layout)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
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
            brand_val = self.product.brand_model or self.product.brand or ""
            if brand_val:
                b_idx = self.brand_combo.findText(brand_val)
                if b_idx >= 0:
                    self.brand_combo.setCurrentIndex(b_idx)
                else:
                    self.brand_combo.setEditText(brand_val)

    def handle_save(self):
        name = self.name_input.text().strip()
        brand_model = self.brand_combo.currentText().strip()

        if not name:
            QMessageBox.warning(self, "Validation Error", "Product Name is required.")
            self.name_input.setFocus()
            return

        if not brand_model:
            QMessageBox.warning(self, "Validation Error", "Brand / Model is required.")
            self.brand_combo.setFocus()
            return

        session = Session()
        try:
            if self.product:
                # Update
                prod = session.query(Product).get(self.product.id)
                prod.name = name
                prod.brand = brand_model
                prod.model = brand_model
                self.saved_product_id = prod.id
                self.saved_product_name = prod.name
            else:
                # Add
                new_prod = Product(
                    name=name,
                    brand=brand_model,
                    model=brand_model,
                    category='General',
                    unit='Pcs',
                    purchase_price=0.0,
                    selling_price=0.0,
                    stock_qty=0,
                    low_stock_limit=5
                )
                session.add(new_prod)
                session.flush()
                self.saved_product_id = new_prod.id
                self.saved_product_name = new_prod.name

            # Auto-save brand into Brand table if new
            if brand_model:
                b_obj = session.query(Brand).filter(Brand.name.ilike(brand_model)).first()
                if not b_obj:
                    session.add(Brand(name=brand_model))

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
        self.search_input.setPlaceholderText("Search products by name or brand/model...")
        self.search_input.textChanged.connect(self.refresh_data)
        top_bar.addWidget(self.search_input, 4)

        self.add_btn = QPushButton("Add Product (Ctrl+N)")
        self.add_btn.setToolTip("Add new product (Ctrl+N)")
        self.add_btn.clicked.connect(self.add_product)
        top_bar.addWidget(self.add_btn, 1)

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
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels([
            "ID", "Product Name", "Brand / Model", "Current Stock"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
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
                    Product.model.like(f"%{search_txt}%")
                )
            products = query.order_by(Product.name.asc()).all()

            self.table.setRowCount(len(products))
            for i, p in enumerate(products):
                self.table.setItem(i, 0, QTableWidgetItem(str(p.id)))
                self.table.setItem(i, 1, QTableWidgetItem(p.name))
                self.table.setItem(i, 2, QTableWidgetItem(p.brand_model or p.brand or "-"))

                stock_item = QTableWidgetItem(str(p.stock_qty))
                stock_item.setTextAlignment(Qt.AlignCenter)
                if p.stock_qty <= 0:
                    stock_item.setForeground(Qt.red)
                elif p.stock_qty <= p.low_stock_limit:
                    stock_item.setForeground(Qt.yellow)
                self.table.setItem(i, 3, stock_item)

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
