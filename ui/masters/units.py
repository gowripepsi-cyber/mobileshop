from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, 
                             QPushButton, QLineEdit, QLabel, QDialog, QFormLayout, QMessageBox, 
                             QHeaderView, QCheckBox, QComboBox, QDoubleSpinBox, QGroupBox)
from PySide6.QtCore import Qt
from database import Session
from models import Unit, Product
from utils.unit_converter import check_circular_unit_reference

class UnitDialog(QDialog):
    def __init__(self, unit=None, parent=None):
        super().__init__(parent)
        self.unit = unit
        self.saved_unit_id = None
        self.setWindowTitle("Edit Unit" if unit else "Add Unit")
        self.setFixedSize(460, 420)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        form_layout = QFormLayout()
        form_layout.setSpacing(10)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g. Coil, Box, Kg, Meter, Pcs...")
        self.name_input.setFixedHeight(36)
        self.name_input.textChanged.connect(self.update_preview)

        self.description_input = QLineEdit()
        self.description_input.setPlaceholderText("e.g. Cable coil, Packaging box, Pieces...")
        self.description_input.setFixedHeight(36)

        form_layout.addRow("Unit Name *:", self.name_input)
        form_layout.addRow("Description:", self.description_input)
        layout.addLayout(form_layout)

        # Sub-unit section
        self.sub_unit_group = QGroupBox("Sub-Unit & Conversion Configuration")
        self.sub_unit_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #dcdfe6;
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 5px;
                color: #2c3e50;
            }
        """)
        group_layout = QVBoxLayout(self.sub_unit_group)
        group_layout.setSpacing(10)

        self.enable_sub_unit_check = QCheckBox("Enable Sub-Unit Conversion (Parent -> Sub-Unit)")
        self.enable_sub_unit_check.setStyleSheet("font-weight: 600; color: #2c3e50;")
        self.enable_sub_unit_check.toggled.connect(self.toggle_sub_unit_fields)
        group_layout.addWidget(self.enable_sub_unit_check)

        self.sub_unit_fields_widget = QWidget()
        fields_form = QFormLayout(self.sub_unit_fields_widget)
        fields_form.setContentsMargins(5, 5, 5, 5)
        fields_form.setSpacing(10)

        self.sub_unit_combo = QComboBox()
        self.sub_unit_combo.setFixedHeight(34)
        self.sub_unit_combo.currentIndexChanged.connect(self.update_preview)

        self.conversion_qty_spin = QDoubleSpinBox()
        self.conversion_qty_spin.setFixedHeight(34)
        self.conversion_qty_spin.setRange(0.0001, 1000000.0)
        self.conversion_qty_spin.setDecimals(2)
        self.conversion_qty_spin.setValue(100.0)
        self.conversion_qty_spin.setSuffix(" sub-units per main unit")
        self.conversion_qty_spin.valueChanged.connect(self.update_preview)

        fields_form.addRow("Sub-Unit Name *:", self.sub_unit_combo)
        fields_form.addRow("Conversion Qty *:", self.conversion_qty_spin)

        self.preview_label = QLabel("Rule: -")
        self.preview_label.setStyleSheet("""
            QLabel {
                background-color: #e8f4fd;
                color: #0d6efd;
                border: 1px solid #b6d4fe;
                border-radius: 4px;
                padding: 6px 10px;
                font-weight: 600;
                font-size: 12px;
            }
        """)
        fields_form.addRow("Conversion Rule:", self.preview_label)

        group_layout.addWidget(self.sub_unit_fields_widget)
        layout.addWidget(self.sub_unit_group)

        # Load available sub-units
        self.load_sub_unit_options()

        # Buttons
        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("Save Unit")
        self.save_btn.setFixedHeight(38)
        self.save_btn.clicked.connect(self.handle_save)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setProperty("class", "btn-secondary")
        self.cancel_btn.setFixedHeight(38)
        self.cancel_btn.clicked.connect(self.reject)

        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)

        # Populate if editing
        if self.unit:
            self.name_input.setText(self.unit.name)
            self.description_input.setText(self.unit.description or "")
            if self.unit.has_sub_unit:
                self.enable_sub_unit_check.setChecked(True)
                # Find sub-unit in combo
                idx = -1
                for i in range(self.sub_unit_combo.count()):
                    if self.sub_unit_combo.itemData(i) == self.unit.sub_unit_id:
                        idx = i
                        break
                    if self.sub_unit_combo.itemText(i) == self.unit.sub_unit_name:
                        idx = i
                        break
                if idx >= 0:
                    self.sub_unit_combo.setCurrentIndex(idx)
                if self.unit.conversion_rate:
                    self.conversion_qty_spin.setValue(float(self.unit.conversion_rate))
            else:
                self.enable_sub_unit_check.setChecked(False)
        else:
            self.enable_sub_unit_check.setChecked(False)

        self.toggle_sub_unit_fields(self.enable_sub_unit_check.isChecked())
        self.update_preview()

    def load_sub_unit_options(self):
        self.sub_unit_combo.clear()
        self.sub_unit_combo.addItem("-- Select Sub-Unit --", None)
        session = Session()
        try:
            query = session.query(Unit)
            if self.unit and self.unit.id:
                # Exclude self to avoid immediate self-referencing
                query = query.filter(Unit.id != self.unit.id)
            units = query.order_by(Unit.name.asc()).all()
            for u in units:
                self.sub_unit_combo.addItem(u.name, u.id)
        finally:
            session.close()

    def toggle_sub_unit_fields(self, enabled: bool):
        self.sub_unit_fields_widget.setVisible(enabled)
        self.update_preview()

    def update_preview(self):
        if not self.enable_sub_unit_check.isChecked():
            self.preview_label.setText("No sub-unit configured (Standard individual unit)")
            return

        main_name = self.name_input.text().strip() or "[Main Unit]"
        sub_name = self.sub_unit_combo.currentText().strip()
        if not sub_name or self.sub_unit_combo.currentData() is None:
            sub_name = "[Sub Unit]"
        rate = self.conversion_qty_spin.value()
        rate_str = f"{rate:g}" if rate > 0 else "0"
        self.preview_label.setText(f"Rule: 1 {main_name} = {rate_str} {sub_name}")

    def handle_save(self):
        name = self.name_input.text().strip()
        description = self.description_input.text().strip() or None
        is_sub_enabled = self.enable_sub_unit_check.isChecked()

        if not name:
            QMessageBox.warning(self, "Validation Error", "Unit Name is required.")
            self.name_input.setFocus()
            return

        sub_unit_id = None
        sub_unit_name = None
        conversion_rate = 1.0

        if is_sub_enabled:
            sub_unit_id = self.sub_unit_combo.currentData()
            if not sub_unit_id:
                QMessageBox.warning(self, "Validation Error", "Please select a valid Sub-Unit from the dropdown.")
                self.sub_unit_combo.setFocus()
                return

            sub_unit_name = self.sub_unit_combo.currentText().strip()
            conversion_rate = self.conversion_qty_spin.value()
            if conversion_rate <= 0:
                QMessageBox.warning(self, "Validation Error", "Conversion Quantity must be greater than zero.")
                self.conversion_qty_spin.setFocus()
                return

            # Check for self-reference
            if self.unit and sub_unit_id == self.unit.id:
                QMessageBox.warning(self, "Validation Error", "A unit cannot be its own sub-unit.")
                return

            if name.lower() == sub_unit_name.lower():
                QMessageBox.warning(self, "Validation Error", "Main Unit and Sub-Unit cannot have the same name.")
                return

        session = Session()
        try:
            # Check unique constraint (case-insensitive)
            existing = session.query(Unit).filter(Unit.name.ilike(name)).first()
            if existing and (not self.unit or existing.id != self.unit.id):
                QMessageBox.warning(self, "Validation Error", f"A unit with name '{name}' already exists.")
                self.name_input.setFocus()
                return

            # Circular reference validation
            if is_sub_enabled and self.unit and self.unit.id:
                if check_circular_unit_reference(self.unit.id, sub_unit_id, session):
                    QMessageBox.warning(
                        self,
                        "Circular Unit Reference Error",
                        f"Cannot set '{sub_unit_name}' as sub-unit for '{name}'.\n"
                        f"This creates a circular unit reference loop."
                    )
                    return

            if self.unit:
                unit_obj = session.query(Unit).get(self.unit.id)
                unit_obj.name = name
                unit_obj.description = description
                unit_obj.has_sub_unit = is_sub_enabled
                unit_obj.sub_unit_id = sub_unit_id if is_sub_enabled else None
                unit_obj.sub_unit_name = sub_unit_name if is_sub_enabled else None
                unit_obj.conversion_rate = conversion_rate if is_sub_enabled else 1.0
                self.saved_unit_id = unit_obj.id
            else:
                new_unit = Unit(
                    name=name,
                    description=description,
                    has_sub_unit=is_sub_enabled,
                    sub_unit_id=sub_unit_id if is_sub_enabled else None,
                    sub_unit_name=sub_unit_name if is_sub_enabled else None,
                    conversion_rate=conversion_rate if is_sub_enabled else 1.0
                )
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
        self.search_input.setPlaceholderText("Search units by name, sub-unit or description...")
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

        # Table: 6 columns: ID, Main Unit, Sub Unit, Conversion Rule, Description, Products Using Unit
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "ID", "Main Unit", "Sub Unit", "Conversion Rule", "Description", "Products Using Unit"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
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
                    Unit.description.ilike(f"%{search_txt}%") |
                    Unit.sub_unit_name.ilike(f"%{search_txt}%")
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
                # ID
                self.table.setItem(i, 0, QTableWidgetItem(str(u.id)))
                
                # Main Unit
                name_item = QTableWidgetItem(u.name)
                name_item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
                self.table.setItem(i, 1, name_item)

                # Sub Unit
                sub_item = QTableWidgetItem(u.sub_unit_name if u.has_sub_unit and u.sub_unit_name else "-")
                sub_item.setTextAlignment(Qt.AlignVCenter | Qt.AlignCenter)
                self.table.setItem(i, 2, sub_item)

                # Conversion Rule
                rule_str = u.conversion_rule_display
                rule_item = QTableWidgetItem(rule_str)
                rule_item.setTextAlignment(Qt.AlignVCenter | Qt.AlignCenter)
                if u.has_sub_unit and u.sub_unit_name:
                    rule_item.setForeground(Qt.darkGreen)
                self.table.setItem(i, 3, rule_item)

                # Description
                desc_item = QTableWidgetItem(u.description or "-")
                desc_item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
                self.table.setItem(i, 4, desc_item)

                # Products Using Unit
                usage_count = unit_usage.get(u.name.strip().lower(), 0)
                usage_item = QTableWidgetItem(f"{usage_count} products")
                usage_item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(i, 5, usage_item)

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

            # Check if any other unit uses this unit as its sub-unit
            parent_units = session.query(Unit).filter(Unit.sub_unit_id == unit_obj.id).all()
            if parent_units:
                parent_names = ", ".join([p.name for p in parent_units])
                QMessageBox.warning(
                    self,
                    "Cannot Delete Unit",
                    f"Unit '{unit_obj.name}' is currently configured as the Sub-Unit for: {parent_names}.\n\n"
                    f"Please reconfigure or remove the sub-unit relationship from those units before deleting."
                )
                return

            # Check if any products use this unit
            prod_count = session.query(Product).filter(
                (Product.unit == unit_obj.name) | (Product.sub_unit == unit_obj.name)
            ).count()
            warning_extra = ""
            if prod_count > 0:
                warning_extra = f"\n\nWARNING: {prod_count} product(s) are currently referencing this unit!"

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
