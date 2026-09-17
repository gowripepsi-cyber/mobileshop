from PySide6.QtCore import QObject, QEvent, QTimer, Qt, QByteArray
from PySide6.QtWidgets import (QApplication, QLineEdit, QComboBox, QAbstractSpinBox, 
                             QDateTimeEdit, QTextEdit, QPlainTextEdit, QAbstractButton, QCompleter,
                             QPushButton, QToolButton, QSpinBox, QDoubleSpinBox,
                             QProxyStyle, QStyle)
from PySide6.QtGui import QIcon, QPixmap, QPainter, QAction
from PySide6.QtSvg import QSvgRenderer

EYE_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#94a3b8" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
  <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8z"></path>
  <circle cx="12" cy="12" r="3"></circle>
</svg>"""

EYE_OFF_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#38bdf8" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
  <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path>
  <line x1="1" y1="1" x2="23" y2="23"></line>
</svg>"""

def _svg_to_icon(svg_str, size=18):
    renderer = QSvgRenderer(QByteArray(svg_str.encode('utf-8')))
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return QIcon(pixmap)

def setup_password_toggle(line_edit: QLineEdit):
    """
    Attaches a clickable eye icon to a password QLineEdit to toggle password visibility.
    """
    icon_hidden = _svg_to_icon(EYE_SVG)
    icon_visible = _svg_to_icon(EYE_OFF_SVG)

    action = line_edit.addAction(icon_hidden, QLineEdit.TrailingPosition)
    action.setToolTip("Show Password")

    def toggle():
        if line_edit.echoMode() == QLineEdit.Password:
            line_edit.setEchoMode(QLineEdit.Normal)
            action.setIcon(icon_visible)
            action.setToolTip("Hide Password")
        else:
            line_edit.setEchoMode(QLineEdit.Password)
            action.setIcon(icon_hidden)
            action.setToolTip("Show Password")

    action.triggered.connect(toggle)
    return action


def enable_quick_add_auto_select(combo: QComboBox):
    """
    Installs an event filter on the editable QComboBox lineEdit so that
    whenever it receives focus, its text is automatically selected.
    """
    class AutoSelectFilter(QObject):
        def eventFilter(self, obj, event):
            if event.type() == QEvent.FocusIn:
                QTimer.singleShot(0, obj.selectAll)
            return super().eventFilter(obj, event)

    filter_obj = AutoSelectFilter(combo)
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
    Also triggers click when focus is on a QPushButton or QToolButton.
    """
    def eventFilter(self, obj, event):
        # Automatically remove spin up/down arrow buttons on all spin boxes
        if event.type() in (QEvent.Show, QEvent.Polish) and isinstance(obj, (QSpinBox, QDoubleSpinBox)):
            if obj.buttonSymbols() != QAbstractSpinBox.ButtonSymbols.NoButtons:
                obj.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)

        # Disable mouse wheel scrolling on all spin box / numeric text boxes
        if event.type() == QEvent.Wheel:
            parent = getattr(obj, 'parent', lambda: None)()
            if isinstance(obj, QAbstractSpinBox) or isinstance(parent, QAbstractSpinBox):
                event.ignore()
                return True

        if event.type() == QEvent.KeyPress and event.key() in (Qt.Key_Return, Qt.Key_Enter):
            # Do not intercept if a popup (like QComboBox popup or QCompleter popup) is active
            if QApplication.activePopupWidget() is not None:
                return super().eventFilter(obj, event)

            target = QApplication.focusWidget() or obj
            button = target if isinstance(target, (QPushButton, QToolButton)) else None
            if not button and target and isinstance(getattr(target, 'parent', lambda: None)(), (QPushButton, QToolButton)):
                button = target.parent()

            if button:
                if button.isEnabled():
                    button.click()
                return True

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

class NoFocusProxyStyle(QProxyStyle):
    """
    Suppresses native dotted focus rectangles (PE_FrameFocusRect) drawn on buttons,
    tabs, and table cells across the application.
    """
    def drawPrimitive(self, element, option, painter, widget=None):
        if element == QStyle.PrimitiveElement.PE_FrameFocusRect:
            return
        super().drawPrimitive(element, option, painter, widget)

def setup_global_enter_navigation(app):
    """
    Installs global Enter key navigation filter on the QApplication instance
    and suppresses native dotted focus outlines on all controls.
    """
    app.setStyle(NoFocusProxyStyle(app.style()))
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
