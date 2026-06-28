from PySide6.QtCore import QObject, QEvent, QTimer
from PySide6.QtWidgets import QLineEdit

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
