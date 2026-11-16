from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, 
                             QPushButton, QLineEdit, QLabel, QDialog, QFormLayout, QMessageBox, QHeaderView)
from PySide6.QtCore import Qt
from sqlalchemy import func
from database import Session
from models import Brand, Product, ProductModel

class BrandDialog(QDialog):
    def __init__(self, brand=None, initial_name="", parent=None):
        super().__init__(parent)
        self.brand = brand
        self.initial_name = initial_name
        self.saved_brand_id = None
        self.saved_brand_name = None
        self.setWindowTitle("Edit Brand" if brand else "Add Brand")
        self.setFixedSize(420, 220)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        form_layout = QFormLayout()
        form_layout.setSpacing(12)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g. Apple, Samsung, Boat, NOA...")
        self.name_input.setFixedHeight(36)

        self.description_input = QLineEdit()
        self.description_input.setPlaceholderText("e.g. Mobile phones, audio, accessories...")
        self.description_input.setFixedHeight(36)

        form_layout.addRow("Brand Name *:", self.name_input)
        form_layout.addRow("Description:", self.description_input)

        layout.addLayout(form_layout)

        # Buttons
        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("Save")
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

        # Populate if editing or initial name provided
        if self.brand:
            self.name_input.setText(self.brand.name)
            self.description_input.setText(getattr(self.brand, 'description', '') or "")
        elif self.initial_name:
            self.name_input.setText(self.initial_name)

    def handle_save(self):
        name = self.name_input.text().strip()
        description = self.description_input.text().strip() or None

        if not name:
            QMessageBox.warning(self, "Validation Error", "Brand Name is required.")
            self.name_input.setFocus()
            return

        session = Session()
        try:
            # Check unique constraint (case-insensitive)
            existing = session.query(Brand).filter(Brand.name.ilike(name)).first()
            if existing and (not self.brand or existing.id != self.brand.id):
                QMessageBox.warning(self, "Validation Error", f"A brand with name '{name}' already exists.")
                self.name_input.setFocus()
                return

            if self.brand:
                brand_obj = session.query(Brand).get(self.brand.id)
                old_name = brand_obj.name
                brand_obj.name = name
                brand_obj.description = description

                # Cascade rename to existing products and models
                if old_name != name:
                    session.query(Product).filter(Product.brand == old_name).update(
                        {Product.brand: name}, synchronize_session='fetch'
                    )
                    session.query(ProductModel).filter(ProductModel.brand_name == old_name).update(
                        {ProductModel.brand_name: name}, synchronize_session='fetch'
                    )

                session.commit()
                self.saved_brand_id = brand_obj.id
                self.saved_brand_name = brand_obj.name
            else:
                new_brand = Brand(name=name, description=description)
                session.add(new_brand)
                session.commit()
                self.saved_brand_id = new_brand.id
                self.saved_brand_name = new_brand.name

            self.accept()
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", f"Failed to save brand: {e}")
        finally:
            session.close()


class BrandsView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)

        # Top Bar (Search & Action Buttons)
        top_bar = QHBoxLayout()
        top_bar.setSpacing(10)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search brands by name or description...")
        self.search_input.setFixedHeight(38)
        self.search_input.textChanged.connect(self.refresh_data)
        top_bar.addWidget(self.search_input, 4)

        self.add_btn = QPushButton("Add Brand (Ctrl+N)")
        self.add_btn.setToolTip("Add new brand (Ctrl+N)")
        self.add_btn.setFixedHeight(38)
        self.add_btn.clicked.connect(self.add_brand)
        top_bar.addWidget(self.add_btn, 1)

        self.edit_btn = QPushButton("Edit Brand")
        self.edit_btn.setProperty("class", "btn-secondary")
        self.edit_btn.setFixedHeight(38)
        self.edit_btn.clicked.connect(self.edit_brand)
        top_bar.addWidget(self.edit_btn, 1)

        self.delete_btn = QPushButton("Delete")
        self.delete_btn.setProperty("class", "btn-danger")
        self.delete_btn.setFixedHeight(38)
        self.delete_btn.clicked.connect(self.delete_brand)
        top_bar.addWidget(self.delete_btn, 1)

        layout.addLayout(top_bar)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["ID", "Brand Name", "Description", "Products Using Brand"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.doubleClicked.connect(self.edit_brand)
        layout.addWidget(self.table)

    def refresh_data(self):
        search_txt = self.search_input.text().strip()
        session = Session()
        try:
            query = session.query(Brand)
            if search_txt:
                query = query.filter(
                    Brand.name.ilike(f"%{search_txt}%") |
                    Brand.description.ilike(f"%{search_txt}%")
                )
            brands = query.order_by(Brand.name.asc()).all()

            # Product counts grouped by brand
            prod_counts = dict(
                session.query(Product.brand, func.count(Product.id))
                .group_by(Product.brand)
                .all()
            )

            self.table.setRowCount(len(brands))
            for i, b in enumerate(brands):
                self.table.setItem(i, 0, QTableWidgetItem(str(b.id)))

                name_item = QTableWidgetItem(b.name)
                name_item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
                self.table.setItem(i, 1, name_item)

                desc_item = QTableWidgetItem(getattr(b, 'description', '') or "-")
                desc_item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
                self.table.setItem(i, 2, desc_item)

                count = prod_counts.get(b.name, 0)
                usage_item = QTableWidgetItem(f"{count} products")
                usage_item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(i, 3, usage_item)

        except Exception as e:
            print(f"Error loading brands: {e}")
        finally:
            session.close()

    def get_selected_brand_id(self):
        selected = self.table.selectedItems()
        if not selected:
            return None
        return int(self.table.item(selected[0].row(), 0).text())

    def add_brand(self, initial_name=""):
        dlg = BrandDialog(initial_name=initial_name, parent=self)
        if dlg.exec() == QDialog.Accepted:
            self.refresh_data()

    def edit_brand(self):
        brand_id = self.get_selected_brand_id()
        if brand_id is None:
            QMessageBox.information(self, "No Selection", "Please select a brand from the table to edit.")
            return

        session = Session()
        try:
            brand_obj = session.query(Brand).get(brand_id)
            if brand_obj:
                dlg = BrandDialog(brand=brand_obj, parent=self)
                if dlg.exec() == QDialog.Accepted:
                    self.refresh_data()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not load brand details: {e}")
        finally:
            session.close()

    def delete_brand(self):
        brand_id = self.get_selected_brand_id()
        if brand_id is None:
            QMessageBox.information(self, "No Selection", "Please select a brand to delete.")
            return

        session = Session()
        try:
            brand_obj = session.query(Brand).get(brand_id)
            if not brand_obj:
                return

            brand_name = brand_obj.name
            prod_count = session.query(Product).filter(Product.brand == brand_name).count()
            model_count = session.query(ProductModel).filter(ProductModel.brand_name == brand_name).count()

            if prod_count > 0 or model_count > 0:
                confirm = QMessageBox.question(
                    self, "Confirm Delete",
                    f"Brand '{brand_name}' is referenced by {prod_count} product(s) and {model_count} model(s).\n"
                    "If you proceed, referencing products will have their brand cleared.\n\n"
                    "Do you still want to delete this brand?",
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No
                )
                if confirm != QMessageBox.Yes:
                    return

                # Clear brand reference from products and models
                session.query(Product).filter(Product.brand == brand_name).update(
                    {Product.brand: ''}, synchronize_session='fetch'
                )
                session.query(ProductModel).filter(ProductModel.brand_name == brand_name).update(
                    {ProductModel.brand_id: None, ProductModel.brand_name: None}, synchronize_session='fetch'
                )
            else:
                confirm = QMessageBox.question(
                    self, "Confirm Delete",
                    f"Are you sure you want to delete brand '{brand_name}'?",
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No
                )
                if confirm != QMessageBox.Yes:
                    return

            session.delete(brand_obj)
            session.commit()
            self.refresh_data()
            QMessageBox.information(self, "Success", f"Brand '{brand_name}' has been deleted.")

        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", f"Could not delete brand: {e}")
        finally:
            session.close()

    def retranslate_ui(self):
        from utils.translator import tr
        self.search_input.setPlaceholderText(f"{tr('Search')} {tr('Brands').lower()}...")
        self.add_btn.setText(f"{tr('Add Brand')} (Ctrl+N)")
        self.edit_btn.setText(tr("Edit Brand"))
        self.delete_btn.setText(tr("Delete"))
        self.table.setHorizontalHeaderLabels([
            "ID", tr("Brand Name"), tr("Description"), tr("Products Using Brand")
        ])

