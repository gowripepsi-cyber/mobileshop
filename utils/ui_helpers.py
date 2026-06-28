from PySide6.QtCore import QObject, QEvent, QTimer, Qt
from PySide6.QtWidgets import (QApplication, QLineEdit, QComboBox, QAbstractSpinBox, 
                             QDateTimeEdit, QTextEdit, QPlainTextEdit, QAbstractButton)

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
