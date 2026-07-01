from PySide6.QtCore import QObject, QEvent, QTimer, Qt
from PySide6.QtWidgets import (QApplication, QLineEdit, QComboBox, QAbstractSpinBox, 
                             QDateTimeEdit, QTextEdit, QPlainTextEdit, QAbstractButton, QCompleter)

class AutoSelectFilter(QObject):
    """
    Event filter attached to editable QComboBox widgets and their inner QLineEdits.
    Automatically clears existing text on focus (FocusIn) or mouse click (MouseButtonPress / MouseButtonRelease)
    so users can immediately type new values without manually deleting existing text.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self._clearing = False

    def eventFilter(self, obj, event):
        if event.type() in (QEvent.FocusIn, QEvent.MouseButtonPress, QEvent.MouseButtonRelease):
            if not self._clearing:
                self._clearing = True
                QTimer.singleShot(0, lambda: self._do_clear(obj))
        return super().eventFilter(obj, event)

    def _do_clear(self, obj):
        self._clearing = False
        try:
            if isinstance(obj, QLineEdit):
                obj.clear()
            elif hasattr(obj, 'lineEdit') and obj.lineEdit():
                obj.lineEdit().clear()
            elif hasattr(obj, 'clearEditText'):
                obj.clearEditText()
        except Exception:
            pass

def enable_quick_add_auto_select(combo):
    """
    Enables automatic text clearing on click and focus for an editable QComboBox.
    """
    filter_obj = AutoSelectFilter(combo)
    combo.installEventFilter(filter_obj)
    line_edit = combo.lineEdit()
    if line_edit:
        line_edit.installEventFilter(filter_obj)
        line_edit._auto_select_filter = filter_obj
    combo._auto_select_filter = filter_obj


class EnterNavigationFilter(QObject):
    """
    Global event filter installed on QApplication.
    Intercepts Return / Enter key presses on input fields (QLineEdit, QComboBox, QSpinBox, QDateEdit)
    and moves focus to the next child in the tab order (acting like the Tab key).
    """
    def eventFilter(self, obj, event):
        if event.type() == QEvent.KeyPress and event.key() in (Qt.Key_Return, Qt.Key_Enter):
            # Do not intercept if a popup (like QComboBox popup or QCompleter popup) is active
            if QApplication.activePopupWidget() is not None:
                return super().eventFilter(obj, event)

            focus_widget = QApplication.focusWidget()
            if focus_widget and self._is_input_widget(focus_widget):
                # Check if widget or its parent combobox is marked to skip enter navigation
                if getattr(focus_widget, '_skip_enter_nav', False):
                    return super().eventFilter(obj, event)

                parent_combo = focus_widget.parent() if isinstance(focus_widget.parent(), QComboBox) else None
                if parent_combo and getattr(parent_combo, '_skip_enter_nav', False):
                    return super().eventFilter(obj, event)

                nav_widget = parent_combo if parent_combo else focus_widget
                nav_widget.focusNextChild()
                return True

        return super().eventFilter(obj, event)

    def _is_input_widget(self, widget):
        if isinstance(widget, (QTextEdit, QPlainTextEdit, QAbstractButton)):
            return False
        if isinstance(widget, (QLineEdit, QComboBox, QAbstractSpinBox, QDateTimeEdit)):
            return True
        return False

def setup_global_enter_navigation(app):
    """
    Installs global Enter key navigation filter on the QApplication instance.
    """
    filter_obj = EnterNavigationFilter(app)
    app.installEventFilter(filter_obj)
    app._enter_nav_filter = filter_obj


class SearchableComboBox(QComboBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setEditable(True)
        self.setInsertPolicy(QComboBox.NoInsert)
        
        self.lineEdit().installEventFilter(self)
        self.lineEdit().textChanged.connect(self.on_text_changed)
        
    def update_completer(self):
        completer = QCompleter(self.model(), self)
        completer.setFilterMode(Qt.MatchContains)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.setCompleter(completer)

    def on_text_changed(self, text):
        if self.hasFocus() and text:
            completer = self.completer()
            if completer:
                completer.setCompletionPrefix(text)
                completer.complete()

    def eventFilter(self, obj, event):
        if obj == self.lineEdit():
            if event.type() == QEvent.FocusOut:
                # If the dropdown popup is currently visible, do not validate/restore yet
                if (self.completer() and self.completer().popup() and self.completer().popup().isVisible()) or self.view().isVisible():
                    return False
                    
                from PySide6.QtWidgets import QApplication
                focus_widget = QApplication.focusWidget()
                if focus_widget in (self, self.lineEdit(), self.view()):
                    return False
                    
                current_text = self.currentText().strip()
                
                # Check for exact display text match
                match_idx = self.findText(current_text)
                
                # If not an exact match, try to find a unique substring match
                if match_idx < 0 and current_text:
                    query = current_text.lower()
                    matched_indices = []
                    for i in range(self.count()):
                        item_text = self.itemText(i).lower()
                        if query in item_text:
                            matched_indices.append(i)
                            
                    if len(matched_indices) == 1:
                        match_idx = matched_indices[0]
                
                self.blockSignals(True)
                if match_idx >= 0:
                    self.setCurrentIndex(match_idx)
                else:
                    self.setCurrentIndex(-1)
                self.blockSignals(False)
                
                self.on_focus_out_validation()
        return super().eventFilter(obj, event)

    def on_focus_out_validation(self):
        pass


class SearchableProductComboBox(SearchableComboBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.currentIndexChanged.connect(self.on_index_changed)

    def on_index_changed(self, idx):
        # Save previous valid ID on selection change
        data = self.currentData()
        if data is not None:
            self._previous_id = data

    def set_products(self, products):
        self.blockSignals(True)
        self.clear()
        
        # Add Select Product placeholder at index 0
        self.addItem("Select Product", None)
        
        for p in products:
            display_txt = f"{p.product_code} | {p.name} ({p.brand} - {p.model}) [Stock: {p.stock_qty}]"
            if p.imei:
                display_txt += f" | IMEI: {p.imei}"
            self.addItem(display_txt, p.id)
            
        self.setCurrentIndex(-1)
        self.blockSignals(False)
        self.update_completer()

    def reset_items(self):
        self.blockSignals(True)
        self.setCurrentIndex(-1)
        self.blockSignals(False)

    def select_product_id(self, product_id):
        self.blockSignals(True)
        idx = self.findData(product_id)
        if idx >= 0:
            self.setCurrentIndex(idx)
        else:
            self.setCurrentIndex(-1)
        self.blockSignals(False)

    def on_focus_out_validation(self):
        # Trigger rate update in parent
        parent_view = self.parent()
        while parent_view and not hasattr(parent_view, 'update_rate_on_product_change'):
            parent_view = parent_view.parent()
        if parent_view:
            parent_view.update_rate_on_product_change()
        return super().eventFilter(obj, event)
