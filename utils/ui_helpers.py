import os
from utils.formatters import format_inr
from PySide6.QtCore import QObject, QEvent, QTimer, Qt, QByteArray, QSize, QItemSelectionModel
from PySide6.QtWidgets import (QApplication, QLineEdit, QComboBox, QAbstractSpinBox, 
                             QDateTimeEdit, QTextEdit, QPlainTextEdit, QAbstractButton, QCompleter,
                             QPushButton, QToolButton, QSpinBox, QDoubleSpinBox,
                             QProxyStyle, QStyle, QDialog, QFrame, QGraphicsDropShadowEffect, QScrollArea, QWidget, QVBoxLayout, QHBoxLayout, QLabel)
from PySide6.QtGui import QColor, QIcon, QPixmap, QPainter, QAction, QDoubleValidator, QIntValidator
from PySide6.QtSvg import QSvgRenderer

EYE_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#e2e8f0" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
  <path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z"></path>
  <circle cx="12" cy="12" r="3" fill="#cbd5e1" stroke="#cbd5e1"></circle>
</svg>"""

EYE_OFF_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#818cf8" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
  <path d="M9.88 9.88a3 3 0 1 0 4.24 4.24"></path>
  <path d="M10.73 5.08A10.43 10.43 0 0 1 12 5c7 0 10 7 10 7a13.16 13.16 0 0 1-1.67 2.68"></path>
  <path d="M6.61 6.61A13.526 13.526 0 0 0 2 12s3 7 10 7a9.74 9.74 0 0 0 5.39-1.61"></path>
  <line x1="2" y1="2" x2="22" y2="22"></line>
</svg>"""

def _svg_to_icon(svg_str, size=22):
    renderer = QSvgRenderer(QByteArray(svg_str.encode('utf-8')))
    icon = QIcon()
    for s in [16, 20, 24, 32, 48, 64]:
        pixmap = QPixmap(s, s)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
        renderer.render(painter)
        painter.end()
        icon.addPixmap(pixmap)
    return icon

def setup_password_toggle(line_edit: QLineEdit):
    """
    Attaches a clickable eye icon to a password QLineEdit to toggle password visibility.
    The icon is perfectly centered vertically (middle between top and bottom) on the right side.
    """
    icon_hidden = _svg_to_icon(EYE_SVG)
    icon_visible = _svg_to_icon(EYE_OFF_SVG)

    btn = QToolButton(line_edit)
    btn.setIcon(icon_hidden)
    btn.setIconSize(QSize(20, 20))
    btn.setCursor(Qt.PointingHandCursor)
    btn.setFocusPolicy(Qt.NoFocus)
    btn.setToolTip("Show Password")
    btn.setStyleSheet("""
        QToolButton {
            border: none;
            background: transparent;
            padding: 0px;
            margin: 0px;
            min-height: 24px;
            max-height: 24px;
            min-width: 24px;
            max-width: 24px;
        }
        QToolButton:hover {
            background-color: rgba(255, 255, 255, 0.08);
            border-radius: 4px;
        }
    """)

    def toggle():
        if line_edit.echoMode() == QLineEdit.Password:
            line_edit.setEchoMode(QLineEdit.Normal)
            btn.setIcon(icon_visible)
            btn.setToolTip("Hide Password")
        else:
            line_edit.setEchoMode(QLineEdit.Password)
            btn.setIcon(icon_hidden)
            btn.setToolTip("Show Password")

    btn.clicked.connect(toggle)

    class TogglePositionFilter(QObject):
        def __init__(self, target_edit, target_btn):
            super().__init__(target_edit)
            self.target_edit = target_edit
            self.target_btn = target_btn

        def update_geom(self):
            btn_w, btn_h = 24, 24
            # 8px from right edge, exactly centered vertically
            x = max(0, self.target_edit.width() - btn_w - 8)
            y = max(0, (self.target_edit.height() - btn_h) // 2)
            self.target_btn.setGeometry(x, y, btn_w, btn_h)

        def eventFilter(self, obj, event):
            if event.type() in (QEvent.Resize, QEvent.Show, QEvent.Polish):
                self.update_geom()
            return super().eventFilter(obj, event)

    filter_obj = TogglePositionFilter(line_edit, btn)
    line_edit.installEventFilter(filter_obj)
    line_edit._pwd_toggle_btn = btn
    line_edit._pwd_toggle_filter = filter_obj

    # Add text margin on right so typed text doesn't slide underneath the eye button
    margins = line_edit.textMargins()
    line_edit.setTextMargins(margins.left(), margins.top(), max(margins.right(), 34), margins.bottom())

    filter_obj.update_geom()
    return btn


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


def enable_auto_clear_and_expand(combo: QComboBox):
    """
    Installs an event filter on an editable QComboBox lineEdit so that
    whenever it receives focus or is clicked, its previous text is cleared and
    the dropdown list expands immediately.
    If left empty on focus out, it restores the default index (0).
    """
    class AutoClearExpandFilter(QObject):
        def __init__(self, target_combo):
            super().__init__(target_combo)
            self.combo = target_combo
            self._just_cleared = False

        def eventFilter(self, obj, event):
            if obj == self.combo.lineEdit():
                if event.type() == QEvent.FocusIn:
                    self._just_cleared = True
                    QTimer.singleShot(0, self._handle_focus_in)
                elif event.type() == QEvent.MouseButtonRelease:
                    if self._just_cleared:
                        self._just_cleared = False
                        QTimer.singleShot(0, self._show_popup)
                elif event.type() == QEvent.FocusOut:
                    if self.combo.view() and self.combo.view().isVisible():
                        return super().eventFilter(obj, event)
                    from PySide6.QtWidgets import QApplication
                    focus_w = QApplication.focusWidget()
                    if focus_w in (self.combo, self.combo.lineEdit(), self.combo.view()):
                        return super().eventFilter(obj, event)
                    
                    txt = self.combo.currentText().strip()
                    if not txt and self.combo.count() > 0:
                        self.combo.setCurrentIndex(0)
            return super().eventFilter(obj, event)

        def _handle_focus_in(self):
            line_edit = self.combo.lineEdit()
            if line_edit:
                line_edit.clear()
                self._show_popup()

        def _show_popup(self):
            if not self.combo.view().isVisible():
                self.combo.showPopup()

    filter_obj = AutoClearExpandFilter(combo)
    line_edit = combo.lineEdit()
    if line_edit:
        line_edit.installEventFilter(filter_obj)
        line_edit._auto_clear_expand_filter = filter_obj
    combo._auto_clear_expand_filter = filter_obj


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

        # Universal smart amount & numeric entry behavior
        target_line = self._get_amount_line_edit(obj)
        if target_line:
            self._handle_amount_event(target_line, event)

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

    def _get_amount_line_edit(self, obj):
        if isinstance(obj, QAbstractSpinBox):
            return obj.lineEdit()
        if isinstance(obj, QLineEdit):
            return obj
        return None

    def _is_amount_or_numeric_field(self, line_edit):
        if not isinstance(line_edit, QLineEdit):
            return False
        if line_edit.echoMode() != QLineEdit.Normal or line_edit.isReadOnly():
            return False
        parent = getattr(line_edit, 'parent', lambda: None)()
        if isinstance(parent, QComboBox):
            return False
        if isinstance(parent, QAbstractSpinBox):
            return True
        if type(line_edit).__name__ == 'AmountLineEdit':
            return True
        val = line_edit.validator()
        if val is not None and isinstance(val, (QDoubleValidator, QIntValidator)):
            return True
        if line_edit.property('is_amount') or (parent and parent.property('is_amount')):
            return True
        if getattr(line_edit, '_is_amount', False) or (parent and getattr(parent, '_is_amount', False)):
            return True
        ph = (line_edit.placeholderText() or '').strip()
        if ph in ('0.00', '0.0', '0'):
            return True
        raw = line_edit.text().strip()
        clean = raw.replace('₹', '').replace('$', '').replace(',', '').strip()
        if clean in ('0', '0.0', '0.00', '0.01'):
            return True
        if '₹' in raw:
            return True
        obj_name = (line_edit.objectName() or '').lower()
        if any(k in obj_name for k in ['amount', 'price', 'rate', 'cost', 'charge', 'balance', 'discount', 'paid', 'refund']):
            return True
        if clean != '' and clean.replace('.', '', 1).isdigit() and not any(ch.isalpha() for ch in raw):
            return True
        return False

    def _handle_amount_event(self, target, event):
        if not self._is_amount_or_numeric_field(target):
            return

        parent = getattr(target, 'parent', lambda: None)()
        is_spin = isinstance(parent, QAbstractSpinBox)
        raw = target.text().strip()
        clean = raw.replace('₹', '').replace('$', '').replace(',', '').strip()

        if event.type() == QEvent.FocusIn:
            target._focus_by_mouse = False
            if clean in ('0', '0.0', '0.00', '0.01'):
                if is_spin and hasattr(parent, 'setMinimum') and parent.minimum() > 0:
                    parent.setMinimum(0.0)
                QTimer.singleShot(0, target.clear)
            elif clean != '':
                QTimer.singleShot(0, target.selectAll)

        elif event.type() == QEvent.MouseButtonPress:
            if not target.hasFocus():
                target._focus_by_mouse = True

        elif event.type() == QEvent.MouseButtonRelease:
            if clean in ('0', '0.0', '0.00', '0.01'):
                if is_spin and hasattr(parent, 'setMinimum') and parent.minimum() > 0:
                    parent.setMinimum(0.0)
                QTimer.singleShot(0, target.clear)
            elif getattr(target, '_focus_by_mouse', False):
                target._focus_by_mouse = False
                if clean != '':
                    QTimer.singleShot(0, target.selectAll)

        elif event.type() == QEvent.FocusOut:
            if target.text().strip() == '':
                if is_spin:
                    parent.setValue(0.0)
                    dec = parent.decimals() if hasattr(parent, 'decimals') else (0 if isinstance(parent, QSpinBox) else 2)
                    target.setText(f'{0.0:.{dec}f}' if dec > 0 else '0')
                elif target.placeholderText() != '0.00':
                    target.setText('0.00')

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
        self._suppress_popup = False
        
        if self.lineEdit():
            self.lineEdit().installEventFilter(self)
            self.lineEdit().textChanged.connect(self.on_text_changed)
        
    def update_completer(self):
        completer = QCompleter(self.model(), self)
        completer.setFilterMode(Qt.MatchContains)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.activated[str].connect(self._on_completer_activated)
        self.setCompleter(completer)

    def showPopup(self):
        completer = self.completer()
        if completer:
            if self.lineEdit():
                self.lineEdit().setFocus()
                if isinstance(self.lineEdit(), AutoClearLineEdit):
                    self.lineEdit().clear()
                    self.lineEdit()._cleared_on_focus = True
            completer.setCompletionPrefix("")
            completer.complete()
        else:
            super().showPopup()

    def _on_completer_activated(self, text):
        self._suppress_popup = True
        le = self.lineEdit()
        if le:
            le._suppress_clear = True
            le.setText(text)
        idx = self.findText(text)
        if idx >= 0:
            if self.currentIndex() != idx:
                self.setCurrentIndex(idx)
            else:
                self.currentIndexChanged.emit(idx)
                self.currentTextChanged.emit(text)
            self.activated.emit(idx)
        if self.completer() and self.completer().popup():
            self.completer().popup().hide()
        if le:
            le._suppress_clear = False
            le._cleared_on_focus = False
        self._suppress_popup = False

    def on_text_changed(self, text):
        if getattr(self, '_suppress_popup', False):
            return
        if not (self.hasFocus() or (self.lineEdit() and self.lineEdit().hasFocus())):
            return
        completer = self.completer()
        if completer:
            completer.setCompletionPrefix(text)
            if (self.hasFocus() or (self.lineEdit() and self.lineEdit().hasFocus())) and self.isVisible():
                completer.complete()

    def hideEvent(self, event):
        if self.completer() and self.completer().popup():
            self.completer().popup().hide()
        super().hideEvent(event)

    def changeEvent(self, event):
        if event.type() in (QEvent.ActivationChange, QEvent.Hide):
            if self.completer() and self.completer().popup():
                self.completer().popup().hide()
        super().changeEvent(event)

    def eventFilter(self, obj, event):
        if obj == self.lineEdit():
            if event.type() == QEvent.KeyPress:
                if event.key() in (Qt.Key_Return, Qt.Key_Enter):
                    if self._handle_enter_key():
                        return True
                elif event.key() == Qt.Key_Down:
                    if self._handle_arrow_key(1):
                        return True
                elif event.key() == Qt.Key_Up:
                    if self._handle_arrow_key(-1):
                        return True
            elif event.type() == QEvent.FocusOut:
                if self.completer() and self.completer().popup():
                    self.completer().popup().hide()
                    
                from PySide6.QtWidgets import QApplication
                focus_widget = QApplication.focusWidget()
                if focus_widget in (self, self.lineEdit(), self.view()):
                    return False
                    
                self._suppress_popup = True
                self._sync_index_from_text()
                self._suppress_popup = False
                self.on_focus_out_validation()
        return super().eventFilter(obj, event)

    def _handle_arrow_key(self, delta):
        completer = self.completer()
        if completer and completer.popup() and completer.popup().isVisible():
            popup = completer.popup()
            m = popup.model()
            if m and m.rowCount() > 0:
                count = m.rowCount()
                curr = popup.currentIndex().row()
                if curr < 0:
                    nxt = 0 if delta > 0 else count - 1
                else:
                    nxt = curr + delta
                    if nxt >= count:
                        nxt = 0
                    elif nxt < 0:
                        nxt = count - 1
                idx = m.index(nxt, 0)
                self._suppress_popup = True
                if self.lineEdit():
                    self.lineEdit().blockSignals(True)
                if popup.selectionModel():
                    popup.selectionModel().select(idx, QItemSelectionModel.ClearAndSelect)
                popup.setCurrentIndex(idx)
                popup.scrollTo(idx)
                if self.lineEdit():
                    self.lineEdit().blockSignals(False)
                self._suppress_popup = False
                return True
        return False

    def _handle_enter_key(self):
        completer = self.completer()
        le = self.lineEdit()
        if completer and completer.popup() and completer.popup().isVisible():
            popup = completer.popup()
            selected_text = None
            if popup.currentIndex().isValid():
                selected_text = popup.currentIndex().data()
            elif popup.model() and popup.model().rowCount() > 0:
                selected_text = popup.model().index(0, 0).data()
            
            self._suppress_popup = True
            if le:
                le._suppress_clear = True
            if selected_text:
                if le:
                    le.setText(selected_text)
                idx = self.findText(selected_text)
                if idx >= 0:
                    if self.currentIndex() != idx:
                        self.setCurrentIndex(idx)
                    else:
                        self.currentIndexChanged.emit(idx)
                        self.currentTextChanged.emit(selected_text)
                    self.activated.emit(idx)
            popup.hide()
            if le:
                le._suppress_clear = False
                le._cleared_on_focus = False
            self._suppress_popup = False
            self.focusNextChild()
            return True
        else:
            self._suppress_popup = True
            if le:
                le._suppress_clear = True
            self._sync_index_from_text()
            if completer and completer.popup():
                completer.popup().hide()
            if le:
                le._suppress_clear = False
                le._cleared_on_focus = False
            self._suppress_popup = False
            self.focusNextChild()
            return True

    def _sync_index_from_text(self):
        current_text = self.currentText().strip()
        if not current_text:
            if self.count() > 0:
                self.blockSignals(True)
                self.setCurrentIndex(0)
                self.blockSignals(False)
            return

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
                if self.lineEdit():
                    self.lineEdit().setText(self.itemText(match_idx))
        
        if match_idx >= 0:
            if self.currentIndex() != match_idx:
                self.setCurrentIndex(match_idx)
            else:
                self.currentIndexChanged.emit(match_idx)
                self.currentTextChanged.emit(self.itemText(match_idx))
            self.activated.emit(match_idx)
        else:
            if self.currentIndex() != -1:
                self.setCurrentIndex(-1)

    def on_focus_out_validation(self):
        pass


class AutoClearLineEdit(QLineEdit):
    def __init__(self, combo, parent=None):
        super().__init__(parent)
        self.combo = combo
        self._cleared_on_focus = False
        self._suppress_clear = False

    def focusInEvent(self, event):
        super().focusInEvent(event)
        if getattr(self, '_suppress_clear', False) or getattr(self.combo, '_suppress_popup', False):
            return
        if self._cleared_on_focus:
            return
        self.clear()
        self._cleared_on_focus = True
        QTimer.singleShot(0, self._open_dropdown)

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        if getattr(self, '_suppress_clear', False) or getattr(self.combo, '_suppress_popup', False):
            return
        if not self._cleared_on_focus:
            self.clear()
            self._cleared_on_focus = True
        QTimer.singleShot(0, self._open_dropdown)

    def _open_dropdown(self):
        if not self.isVisible():
            return
        if getattr(self, '_suppress_clear', False) or getattr(self.combo, '_suppress_popup', False):
            return
        if not self.hasFocus():
            self.setFocus()
        completer = self.combo.completer()
        if completer:
            completer.setCompletionPrefix("")
            completer.complete()
        else:
            self.combo.showPopup()

    def focusOutEvent(self, event):
        self._cleared_on_focus = False
        super().focusOutEvent(event)
        if self.combo.completer() and self.combo.completer().popup():
            self.combo.completer().popup().hide()


class AutoClearSearchableComboBox(SearchableComboBox):
    """
    Searchable QComboBox that automatically clears previous text and expands
    the dropdown list whenever the user places the cursor or clicks inside the text box,
    while leaving the cursor blinking and ready for direct typing.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        custom_line_edit = AutoClearLineEdit(self)
        self.setLineEdit(custom_line_edit)
        self.lineEdit().installEventFilter(self)
        self.lineEdit().textChanged.connect(self.on_text_changed)


class SearchableProductComboBox(AutoClearSearchableComboBox):
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
            bm = getattr(p, 'brand_model', None) or getattr(p, 'brand', '') or ''
            if bm:
                display_txt = f"{p.name} ({bm}) [Stock: {p.stock_qty}]"
            else:
                display_txt = f"{p.name} [Stock: {p.stock_qty}]"
            self.addItem(display_txt, p.id)
            
        self.setCurrentIndex(-1)
        if self.lineEdit():
            self.lineEdit().clear()
            self.lineEdit().setPlaceholderText("Select Product")
        self.setEditText("")
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


def get_circular_pixmap(src, size=44):
    """
    Returns an anti-aliased circular-cropped QPixmap from a file path or existing QPixmap.
    """
    if isinstance(src, str):
        if not src or not os.path.exists(src):
            return None
        pix = QPixmap(src)
    elif isinstance(src, QPixmap):
        pix = src
    else:
        return None

    if pix.isNull():
        return None

    scaled = pix.scaled(size, size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
    out = QPixmap(size, size)
    out.fill(Qt.transparent)

    painter = QPainter(out)
    painter.setRenderHint(QPainter.Antialiasing, True)
    painter.setRenderHint(QPainter.SmoothPixmapTransform, True)

    from PySide6.QtGui import QPainterPath
    path = QPainterPath()
    path.addEllipse(0, 0, size, size)
    painter.setClipPath(path)

    x = (size - scaled.width()) // 2
    y = (size - scaled.height()) // 2
    painter.drawPixmap(x, y, scaled)
    painter.end()

    return out


class ModernAlertDialog(QDialog):
    """
    Modern frameless alert dialog with true rounded corners, floating drop shadow,
    draggable header, and dynamic theme styling.
    """
    def __init__(self, title, message, icon_type="warning", parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMinimumWidth(460)
        self.setMaximumWidth(560)
        self._drag_pos = None
        self.init_ui(title, message, icon_type)

    def get_theme_color(self):
        try:
            from database import Session, Setting
            session = Session()
            t = session.query(Setting).filter_by(key='theme_color').first()
            val = t.value if t and t.value else "#8fd53b"
            session.close()
            return val
        except Exception:
            return "#8fd53b"

    def init_ui(self, title, message, icon_type):
        theme_hex = self.get_theme_color()
        c = QColor(theme_hex)
        if not c.isValid():
            c = QColor("#8fd53b")
        theme_hex = c.name()
        hover_hex = c.darker(110).name()
        lum = (0.299 * c.red() + 0.587 * c.green() + 0.114 * c.blue()) / 255.0
        btn_text_color = "#0f172a" if lum > 0.55 else "#ffffff"

        # Outer Layout with margins for shadow and smooth anti-aliased rounded corners
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(12, 12, 12, 12)

        # Card container with rounded corners and theme border
        self.card = QFrame(self)
        self.card.setObjectName("alert_card")
        self.card.setStyleSheet(f"""
            QFrame#alert_card {{
                background-color: #ffffff;
                border: 2px solid {theme_hex};
                border-radius: 24px;
            }}
        """)

        # Drop shadow effect
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 45))
        shadow.setOffset(0, 4)
        self.card.setGraphicsEffect(shadow)

        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(24, 16, 24, 20)
        card_layout.setSpacing(12)

        # Top Bar: Title & Close Button
        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(0, 0, 0, 0)

        lbl_title = QLabel(title)
        lbl_title.setStyleSheet("font-size: 15px; font-weight: 800; color: #0f172a; letter-spacing: 0.3px;")
        top_bar.addWidget(lbl_title)

        top_bar.addStretch()

        self.close_btn = QPushButton("✕")
        self.close_btn.setFixedSize(28, 28)
        self.close_btn.setCursor(Qt.PointingHandCursor)
        self.close_btn.setToolTip("Close / மூடு (Esc)")
        self.close_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #94a3b8;
                font-size: 14px;
                font-weight: bold;
                border: none;
                border-radius: 14px;
                padding: 0px;
            }
            QPushButton:hover {
                background-color: #fee2e2;
                color: #ef4444;
            }
        """)
        self.close_btn.clicked.connect(self.reject)
        top_bar.addWidget(self.close_btn)
        card_layout.addLayout(top_bar)

        # Content Row: Icon + Message
        content_row = QHBoxLayout()
        content_row.setContentsMargins(0, 4, 0, 4)
        content_row.setSpacing(16)
        content_row.setAlignment(Qt.AlignTop)

        # Icon Badge
        icon_badge = QLabel("⚠️" if icon_type == "warning" else ("✅" if icon_type == "success" else "ℹ️"))
        icon_badge.setFixedSize(44, 44)
        icon_badge.setAlignment(Qt.AlignCenter)
        if icon_type == "warning":
            badge_bg = "#fffbeb"
            badge_border = "#f59e0b"
        elif icon_type == "success":
            badge_bg = "#f0fdf4"
            badge_border = "#22c55e"
        else:
            badge_bg = "#eff6ff"
            badge_border = "#3b82f6"

        icon_badge.setStyleSheet(f"""
            QLabel {{
                background-color: {badge_bg};
                border: 1.5px solid {badge_border};
                border-radius: 22px;
                font-size: 24px;
            }}
        """)
        content_row.addWidget(icon_badge)

        # Message Text
        msg_layout = QVBoxLayout()
        msg_layout.setSpacing(6)

        # Parse message lines to highlight OUT OF STOCK
        lines = message.strip().split("\n")
        header_text = lines[0] if lines else ""
        lbl_msg_head = QLabel(header_text)
        lbl_msg_head.setStyleSheet("font-size: 13px; font-weight: 700; color: #1e293b;")
        msg_layout.addWidget(lbl_msg_head)

        if len(lines) > 1:
            items_container = QWidget()
            items_layout = QVBoxLayout(items_container)
            items_layout.setContentsMargins(0, 0, 0, 0)
            items_layout.setSpacing(4)

            for line in lines[1:]:
                line_str = line.strip()
                if not line_str:
                    continue
                lbl_item = QLabel()
                lbl_item.setWordWrap(True)
                lbl_item.setTextInteractionFlags(Qt.TextSelectableByMouse)
                if "OUT OF STOCK" in line_str:
                    parts = line_str.split("OUT OF STOCK")
                    lbl_item.setText(f"{parts[0]}<span style='color: #ef4444; font-weight: bold;'>OUT OF STOCK</span>{parts[1]}")
                elif "Qty:" in line_str:
                    parts = line_str.split(" - ")
                    if len(parts) == 2:
                        lbl_item.setText(f"{parts[0]} - <span style='color: #f59e0b; font-weight: 600;'>{parts[1]}</span>")
                    else:
                        lbl_item.setText(line_str)
                else:
                    lbl_item.setText(line_str)
                lbl_item.setStyleSheet("font-size: 12px; color: #334155; line-height: 1.4;")
                items_layout.addWidget(lbl_item)

            # If many lines, wrap in scroll area
            if len(lines) > 8:
                scroll = QScrollArea()
                scroll.setWidget(items_container)
                scroll.setWidgetResizable(True)
                scroll.setMaximumHeight(160)
                scroll.setFrameShape(QFrame.NoFrame)
                scroll.setStyleSheet("background: transparent;")
                msg_layout.addWidget(scroll)
            else:
                msg_layout.addWidget(items_container)

        content_row.addLayout(msg_layout)
        card_layout.addLayout(content_row)

        # Bottom Row: OK Button
        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(0, 6, 0, 0)
        btn_row.addStretch()

        self.ok_btn = QPushButton("OK")
        self.ok_btn.setFixedSize(92, 36)
        self.ok_btn.setCursor(Qt.PointingHandCursor)
        self.ok_btn.setDefault(True)
        self.ok_btn.setAutoDefault(True)
        self.ok_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme_hex};
                color: {btn_text_color};
                font-weight: bold;
                font-size: 13px;
                border: none;
                border-radius: 10px;
            }}
            QPushButton:hover {{
                background-color: {hover_hex};
            }}
        """)
        self.ok_btn.clicked.connect(self.accept)
        btn_row.addWidget(self.ok_btn)
        card_layout.addLayout(btn_row)

        outer_layout.addWidget(self.card)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self._drag_pos is not None:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        event.accept()


def show_modern_alert(parent, title, message, icon_type="warning"):
    """
    Displays a frameless rounded modal alert matching the application theme.
    """
    dlg = ModernAlertDialog(title, message, icon_type=icon_type, parent=parent)
    return dlg.exec()
