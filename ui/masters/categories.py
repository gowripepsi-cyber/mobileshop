from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, 
                             QPushButton, QLineEdit, QLabel, QDialog, QFormLayout, QMessageBox, QHeaderView)
from PySide6.QtCore import Qt
from sqlalchemy import func
from database import Session
from models import Category, Product

class CategoryDialog(QDialog):
    def __init__(self, category=None, initial_name="", parent=None):
        super().__init__(parent)
        self.category = category
        self.initial_name = initial_name
        self.saved_category_id = None
        self.saved_category_name = None
        self.setWindowTitle("Edit Item Category" if category else "Add Item Category")
        self.setFixedSize(400, 210)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        form_layout = QFormLayout()
        form_layout.setSpacing(12)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g. Accessories, Spares, Sellables...")
        self.name_input.setFixedHeight(36)

        self.description_input = QLineEdit()
        self.description_input.setPlaceholderText("e.g. Mobile covers, chargers, spare parts...")
        self.description_input.setFixedHeight(36)

        form_layout.addRow("Category Name *:", self.name_input)
        form_layout.addRow("Description:", self.description_input)

        layout.addLayout(form_layout)

        # Buttons
        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("Save")
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
        if self.category:
            self.name_input.setText(self.category.name)
            self.description_input.setText(getattr(self.category, 'description', '') or "")
        elif self.initial_name:
            self.name_input.setText(self.initial_name)

    def handle_save(self):
        name = self.name_input.text().strip()
        description = self.description_input.text().strip() or None

        if not name:
            QMessageBox.warning(self, "Validation Error", "Category Name is required.")
            self.name_input.setFocus()
            return

        session = Session()
        try:
            # Check unique constraint (case-insensitive)
            existing = session.query(Category).filter(Category.name.ilike(name)).first()
            if existing and (not self.category or existing.id != self.category.id):
                QMessageBox.warning(self, "Validation Error", f"A category with name '{name}' already exists.")
                self.name_input.setFocus()
                return

            if self.category:
                cat_obj = session.query(Category).get(self.category.id)
                old_name = cat_obj.name
                cat_obj.name = name
                cat_obj.description = description

                # Cascade rename to existing products
                if old_name != name:
                    session.query(Product).filter(Product.category == old_name).update(
                        {Product.category: name}, synchronize_session='fetch'
                    )

                self.saved_category_id = cat_obj.id
                self.saved_category_name = cat_obj.name
            else:
                new_cat = Category(name=name, description=description)
                session.add(new_cat)
                session.flush()
                self.saved_category_id = new_cat.id
                self.saved_category_name = new_cat.name

            session.commit()
            self.accept()
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", f"Failed to save category: {e}")
        finally:
            session.close()


class CategoriesView(QWidget):
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
        self.search_input.setPlaceholderText("Search categories by name or description...")
        self.search_input.setFixedHeight(38)
        self.search_input.textChanged.connect(self.refresh_data)
        top_bar.addWidget(self.search_input, 4)

        self.add_btn = QPushButton("Add Category (Ctrl+N)")
        self.add_btn.setToolTip("Add new category (Ctrl+N)")
        self.add_btn.setFixedHeight(38)
        self.add_btn.clicked.connect(self.add_category)
        top_bar.addWidget(self.add_btn, 1)

        self.edit_btn = QPushButton("Edit Category")
        self.edit_btn.setProperty("class", "btn-secondary")
        self.edit_btn.setFixedHeight(38)
        self.edit_btn.clicked.connect(self.edit_category)
        top_bar.addWidget(self.edit_btn, 1)

        self.delete_btn = QPushButton("Delete")
        self.delete_btn.setProperty("class", "btn-danger")
        self.delete_btn.setFixedHeight(38)
        self.delete_btn.clicked.connect(self.delete_category)
        top_bar.addWidget(self.delete_btn, 1)

        layout.addLayout(top_bar)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["ID", "Category Name", "Description", "Products Using Category"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.doubleClicked.connect(self.edit_category)
        layout.addWidget(self.table)

    def refresh_data(self):
        search_txt = self.search_input.text().strip()
        session = Session()
        try:
            query = session.query(Category)
            if search_txt:
                query = query.filter(
                    Category.name.ilike(f"%{search_txt}%") |
                    Category.description.ilike(f"%{search_txt}%")
                )
            categories = query.order_by(Category.id.asc()).all()

            # Product counts grouped by category
            prod_counts = dict(
                session.query(Product.category, func.count(Product.id))
                .group_by(Product.category)
                .all()
            )

            self.table.setRowCount(len(categories))
            for i, c in enumerate(categories):
                self.table.setItem(i, 0, QTableWidgetItem(str(c.id)))

                name_item = QTableWidgetItem(c.name)
                name_item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
                self.table.setItem(i, 1, name_item)

                desc_item = QTableWidgetItem(getattr(c, 'description', '') or "-")
                desc_item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
                self.table.setItem(i, 2, desc_item)

                count = prod_counts.get(c.name, 0)
                usage_item = QTableWidgetItem(f"{count} products")
                usage_item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(i, 3, usage_item)

        except Exception as e:
            print(f"Error loading categories: {e}")
        finally:
            session.close()

    def get_selected_category_id(self):
        selected = self.table.selectedItems()
        if not selected:
            return None
        return int(self.table.item(selected[0].row(), 0).text())

    def add_category(self):
        dlg = CategoryDialog(parent=self)
        if dlg.exec() == QDialog.Accepted:
            self.refresh_data()

    def edit_category(self):
        cat_id = self.get_selected_category_id()
        if cat_id is None:
            QMessageBox.information(self, "No Selection", "Please select a category from the table to edit.")
            return

        session = Session()
        try:
            cat_obj = session.query(Category).get(cat_id)
            if cat_obj:
                dlg = CategoryDialog(category=cat_obj, parent=self)
                if dlg.exec() == QDialog.Accepted:
                    self.refresh_data()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not load category details: {e}")
        finally:
            session.close()

    def delete_category(self):
        cat_id = self.get_selected_category_id()
        if cat_id is None:
            QMessageBox.information(self, "No Selection", "Please select a category from the table to delete.")
            return

        session = Session()
        try:
            cat_obj = session.query(Category).get(cat_id)
            if not cat_obj:
                return

            # Check if any products use this category
            prod_count = session.query(Product).filter(Product.category == cat_obj.name).count()
            if prod_count > 0:
                confirm = QMessageBox.question(
                    self,
                    "Confirm Delete",
                    f"Category '{cat_obj.name}' is currently used by {prod_count} product(s).\n\n"
                    "If you delete this category, these products will be reassigned to 'General'.\n\n"
                    "Do you want to proceed?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                if confirm != QMessageBox.Yes:
                    return

                session.query(Product).filter(Product.category == cat_obj.name).update(
                    {Product.category: 'General'}, synchronize_session='fetch'
                )
            else:
                confirm = QMessageBox.question(
                    self,
                    "Confirm Delete",
                    f"Are you sure you want to delete category '{cat_obj.name}'?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                if confirm != QMessageBox.Yes:
                    return

            session.delete(cat_obj)
            session.commit()
            self.refresh_data()
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", f"Failed to delete category: {e}")
        finally:
            session.close()


class CategoryManagerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Manage Item Categories")
        self.resize(750, 520)
        self.setMinimumSize(650, 420)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)

        title_lbl = QLabel("Item Categories")
        title_lbl.setStyleSheet("font-size: 16px; font-weight: bold; color: #6366f1; border-bottom: 1px solid #28284e; padding-bottom: 8px;")
        layout.addWidget(title_lbl)

        self.categories_view = CategoriesView(self)
        layout.addWidget(self.categories_view)

        btn_box = QHBoxLayout()
        btn_box.addStretch()
        self.close_btn = QPushButton("Close")
        self.close_btn.setProperty("class", "btn-secondary")
        self.close_btn.clicked.connect(self.accept)
        btn_box.addWidget(self.close_btn)
        layout.addLayout(btn_box)

