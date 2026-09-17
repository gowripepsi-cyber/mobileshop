from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, 
                             QPushButton, QLineEdit, QLabel, QDialog, QFormLayout, QMessageBox, QHeaderView)
from PySide6.QtCore import Qt
from database import Session
from models import Unit, Product

class UnitDialog(QDialog):
    def __init__(self, unit=None, parent=None):
        super().__init__(parent)
        self.unit = unit
        self.saved_unit_id = None
        self.setWindowTitle("Edit Unit" if unit else "Add Unit")
        self.setFixedSize(380, 200)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        form_layout = QFormLayout()
        form_layout.setSpacing(12)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g. Pcs, Box, Kg, Doz...")
        self.name_input.setFixedHeight(36)

        self.description_input = QLineEdit()
        self.description_input.setPlaceholderText("e.g. Pieces, Boxes, Kilograms...")
        self.description_input.setFixedHeight(36)

        form_layout.addRow("Unit Name *:", self.name_input)
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

        # Populate if editing
        if self.unit:
            self.name_input.setText(self.unit.name)
            self.description_input.setText(self.unit.description or "")

    def handle_save(self):
        name = self.name_input.text().strip()
        description = self.description_input.text().strip() or None

        if not name:
            QMessageBox.warning(self, "Validation Error", "Unit Name is required.")
            self.name_input.setFocus()
            return

        session = Session()
        try:
            # Check unique constraint (case-insensitive)
            existing = session.query(Unit).filter(Unit.name.ilike(name)).first()
            if existing and (not self.unit or existing.id != self.unit.id):
                QMessageBox.warning(self, "Validation Error", f"A unit with name '{name}' already exists.")
                self.name_input.setFocus()
                return

            if self.unit:
                unit_obj = session.query(Unit).get(self.unit.id)
                unit_obj.name = name
                unit_obj.description = description
                self.saved_unit_id = unit_obj.id
            else:
                new_unit = Unit(name=name, description=description)
                session.add(new_unit)
                session.flush()
                self.saved_unit_id = new_unit.id

            session.commit()
            self.accept()
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", f"Failed to save unit: {e}")
        finally:
            session.close()


class UnitsView(QWidget):
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
        self.search_input.setPlaceholderText("Search units by name or description...")
        self.search_input.setFixedHeight(38)
        self.search_input.textChanged.connect(self.refresh_data)
        top_bar.addWidget(self.search_input, 4)

        self.add_btn = QPushButton("Add Unit (Ctrl+N)")
        self.add_btn.setToolTip("Add new unit (Ctrl+N)")
        self.add_btn.setFixedHeight(38)
        self.add_btn.clicked.connect(self.add_unit)
        top_bar.addWidget(self.add_btn, 1)

        self.edit_btn = QPushButton("Edit Unit")
        self.edit_btn.setProperty("class", "btn-secondary")
        self.edit_btn.setFixedHeight(38)
        self.edit_btn.clicked.connect(self.edit_unit)
        top_bar.addWidget(self.edit_btn, 1)

        self.delete_btn = QPushButton("Delete")
        self.delete_btn.setProperty("class", "btn-danger")
        self.delete_btn.setFixedHeight(38)
        self.delete_btn.clicked.connect(self.delete_unit)
        top_bar.addWidget(self.delete_btn, 1)

        layout.addLayout(top_bar)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["ID", "Unit Name", "Description", "Products Using Unit"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.doubleClicked.connect(self.edit_unit)
        layout.addWidget(self.table)

    def refresh_data(self):
        search_txt = self.search_input.text().strip()
        session = Session()
        try:
            query = session.query(Unit)
            if search_txt:
                query = query.filter(
                    Unit.name.ilike(f"%{search_txt}%") |
                    Unit.description.ilike(f"%{search_txt}%")
                )
            units = query.order_by(Unit.id.asc()).all()

            # Cache product count per unit for insight
            all_prods = session.query(Product.unit).all()
            unit_usage = {}
            for (p_unit,) in all_prods:
                if p_unit:
                    u_key = p_unit.strip().lower()
                    unit_usage[u_key] = unit_usage.get(u_key, 0) + 1

            self.table.setRowCount(len(units))
            for i, u in enumerate(units):
                self.table.setItem(i, 0, QTableWidgetItem(str(u.id)))
                
                name_item = QTableWidgetItem(u.name)
                name_item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
                self.table.setItem(i, 1, name_item)

                desc_item = QTableWidgetItem(u.description or "-")
                desc_item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
                self.table.setItem(i, 2, desc_item)

                usage_count = unit_usage.get(u.name.strip().lower(), 0)
                usage_item = QTableWidgetItem(f"{usage_count} products")
                usage_item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(i, 3, usage_item)

        except Exception as e:
            print(f"Error loading units: {e}")
        finally:
            session.close()

    def get_selected_unit_id(self):
        selected = self.table.selectedItems()
        if not selected:
            return None
        return int(self.table.item(selected[0].row(), 0).text())

    def add_unit(self):
        dlg = UnitDialog(parent=self)
        if dlg.exec() == QDialog.Accepted:
            self.refresh_data()

    def edit_unit(self):
        unit_id = self.get_selected_unit_id()
        if unit_id is None:
            QMessageBox.information(self, "No Selection", "Please select a unit from the table to edit.")
            return

        session = Session()
        try:
            unit_obj = session.query(Unit).get(unit_id)
            if unit_obj:
                dlg = UnitDialog(unit=unit_obj, parent=self)
                if dlg.exec() == QDialog.Accepted:
                    self.refresh_data()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not load unit details: {e}")
        finally:
            session.close()

    def delete_unit(self):
        unit_id = self.get_selected_unit_id()
        if unit_id is None:
            QMessageBox.information(self, "No Selection", "Please select a unit from the table to delete.")
            return

        session = Session()
        try:
            unit_obj = session.query(Unit).get(unit_id)
            if not unit_obj:
                return

            # Check if any products use this unit
            prod_count = session.query(Product).filter(Product.unit == unit_obj.name).count()
            warning_extra = ""
            if prod_count > 0:
                warning_extra = f"\n\nWARNING: {prod_count} product(s) are currently using this unit!"

            confirm = QMessageBox.question(
                self,
                "Confirm Delete",
                f"Are you sure you want to delete unit '{unit_obj.name}'?{warning_extra}",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if confirm == QMessageBox.Yes:
                session.delete(unit_obj)
                session.commit()
                self.refresh_data()
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", f"Failed to delete unit: {e}")
        finally:
            session.close()
