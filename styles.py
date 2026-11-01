import os
from PySide6.QtGui import QColor

def get_theme_palette(primary_hex="#8fd53b"):
    """
    Computes a cohesive UI color palette from a single primary hex color.
    """
    if not primary_hex or not isinstance(primary_hex, str):
        primary_hex = "#8fd53b"
    primary_hex = primary_hex.strip()
    if not primary_hex.startswith("#"):
        primary_hex = "#" + primary_hex
    
    c = QColor(primary_hex)
    if not c.isValid():
        c = QColor("#8fd53b")

    primary = c.name()
    hover = c.darker(110).name()
    pressed = c.darker(122).name()
    border = c.darker(118).name()
    grad_start = c.lighter(106).name()
    grad_end = c.darker(108).name()

    # Relative luminance formula for WCAG contrast
    lum = (0.299 * c.red() + 0.587 * c.green() + 0.114 * c.blue()) / 255.0
    text_primary = "#0f172a" if lum > 0.55 else "#ffffff"
    sidebar_text = "#142b05" if lum > 0.55 else "#ffffff"
    sidebar_subtext = "rgba(20, 43, 5, 0.65)" if lum > 0.55 else "rgba(255, 255, 255, 0.70)"

    light_bg = f"rgba({c.red()}, {c.green()}, {c.blue()}, 0.08)"
    light_hover = f"rgba({c.red()}, {c.green()}, {c.blue()}, 0.15)"
    dropdown_hover = f"rgba({c.red()}, {c.green()}, {c.blue()}, 0.24)"

    return {
        "primary": primary,
        "hover": hover,
        "pressed": pressed,
        "border": border,
        "grad_start": grad_start,
        "grad_end": grad_end,
        "text_primary": text_primary,
        "sidebar_text": sidebar_text,
        "sidebar_subtext": sidebar_subtext,
        "light_bg": light_bg,
        "light_hover": light_hover,
        "dropdown_hover": dropdown_hover,
    }

THEME_STYLESHEET_TEMPLATE = """
/* =========================================================================
   Global Theme: Modern Fresh Lime & Sunny Ivory
   Inspired by clean, organic, rounded capsule design:
   - Soft porcelain canvas (#f6f8fa)
   - Encapsulated floating lime pill sidebar (__THEME_GRAD_START__ -> __THEME_GRAD_END__)
   - Warm sunny golden-amber accents (#f6c944 / #f59e0b)
   - Deep rich slate typography (#0f172a) for high readability
   ========================================================================= */

QMainWindow {
    background-color: #f6f8fa;
}

QWidget {
    font-family: 'Segoe UI', -apple-system, Roboto, Helvetica, sans-serif;
    font-size: 13px;
    color: #0f172a;
    outline: none;
}

/* =========================================================================
   Sidebar Styling (Floating Lime Capsule Dock)
   ========================================================================= */
#sidebar {
    background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 __THEME_GRAD_START__, stop:1 __THEME_GRAD_END__);
    border: none;
    border-radius: 24px;
    min-width: 250px;
    max-width: 250px;
    padding: 10px 6px;
}

#shop_emblem {
    background-color: #f59e0b;
    color: #ffffff;
    font-size: 22px;
    font-weight: bold;
    border-radius: 24px;
    min-width: 48px;
    max-width: 48px;
    min-height: 48px;
    max-height: 48px;
    border: 2px solid #ffffff;
    qproperty-alignment: AlignCenter;
}

#shop_title {
    color: __THEME_SIDEBAR_TEXT__;
    font-size: 15px;
    font-weight: 800;
    margin-top: 4px;
    margin-bottom: 8px;
    letter-spacing: 0.5px;
    qproperty-alignment: AlignCenter;
    text-align: center;
}

#sidebar QPushButton {
    background-color: transparent;
    border: none;
    padding: 10px 14px;
    border-radius: 18px;
    margin: 3px 6px;
}

#sidebar QPushButton:hover {
    background-color: rgba(255, 255, 255, 0.45);
}

#sidebar QPushButton:checked {
    background-color: #ffffff;
    border: none;
}

#sidebar QPushButton QLabel {
    background: transparent;
}

#sidebar QPushButton QLabel#btn_label {
    color: __THEME_SIDEBAR_TEXT__;
    font-size: 13px;
    font-weight: 600;
}

#sidebar QPushButton:hover QLabel#btn_label {
    color: #0f172a;
}

#sidebar QPushButton:checked QLabel#btn_label {
    color: #0f172a;
    font-weight: 800;
}

#sidebar QPushButton QLabel#shortcut_label {
    color: #1b3808;
    font-size: 11px;
    font-weight: 700;
    background: transparent;
    border: none;
    padding: 0px;
}

#sidebar QPushButton:hover QLabel#shortcut_label {
    color: #0f172a;
}

#sidebar QPushButton:checked QLabel#shortcut_label {
    color: #475569;
}

#logout_btn {
    background-color: rgba(255, 255, 255, 0.9);
    color: #dc2626;
    border: 1px solid rgba(220, 38, 38, 0.25);
    border-radius: 18px;
    padding: 10px 16px;
    font-weight: bold;
    margin: 10px 12px 14px 12px;
}

#logout_btn:hover {
    background-color: #fee2e2;
    color: #b91c1c;
}

/* =========================================================================
   Header Area
   ========================================================================= */
#header {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 18px;
    min-height: 56px;
    max-height: 56px;
    padding: 0px 20px;
}

#header QLabel {
    font-size: 18px;
    font-weight: 800;
    color: #0f172a;
}

/* =========================================================================
   Main Content Area
   ========================================================================= */
#content_area {
    background-color: transparent;
}

/* =========================================================================
   Card / Frame Container
   ========================================================================= */
.CardFrame {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 18px;
}

.CardFrame QLabel {
    background: transparent;
}

/* =========================================================================
   Metrics Cards on Dashboard
   ========================================================================= */
.MetricCard {
    background-color: #ffffff;
    border: 1.5px solid #e2e8f0;
    border-radius: 16px;
    padding: 15px;
}

.ClickableMetricCard {
    background-color: #ffffff;
    border: 1.5px solid #e2e8f0;
    border-radius: 16px;
    padding: 15px;
}

.ClickableMetricCard:hover {
    background-color: __THEME_LIGHT_BG__;
    border: 1.5px solid __THEME_PRIMARY__;
}

.MetricTitle {
    color: #64748b;
    font-size: 12px;
    font-weight: bold;
    text-transform: uppercase;
}

.MetricValue {
    color: #0f172a;
    font-size: 22px;
    font-weight: 800;
    margin-top: 5px;
}

/* =========================================================================
   Form Inputs & Controls
   ========================================================================= */
QLineEdit, QPlainTextEdit, QTextEdit, QSpinBox, QDoubleSpinBox {
    background-color: #ffffff;
    border: 1.5px solid #cbd5e1;
    border-radius: 10px;
    padding: 6px 12px;
    min-height: 28px;
    color: #0f172a;
    selection-background-color: __THEME_PRIMARY__;
    selection-color: #0f172a;
}

QLineEdit:hover, QPlainTextEdit:hover, QTextEdit:hover, QSpinBox:hover, QDoubleSpinBox:hover {
    border: 1.5px solid __THEME_HOVER__;
}

QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {
    border: 2px solid __THEME_PRIMARY__;
    background-color: __THEME_LIGHT_BG__;
}

QLineEdit:disabled, QPlainTextEdit:disabled, QTextEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled {
    background-color: #f1f5f9;
    border: 1px solid #e2e8f0;
    color: #94a3b8;
}

/* ComboBox Explicit Styling */
QComboBox {
    background-color: #ffffff;
    border: 1.5px solid #cbd5e1;
    border-radius: 10px;
    padding: 4px 10px;
    min-height: 28px;
    color: #0f172a;
    selection-background-color: __THEME_PRIMARY__;
    selection-color: #0f172a;
}

QComboBox:editable {
    background-color: #ffffff;
    border: 1.5px solid #cbd5e1;
    border-radius: 10px;
    padding: 2px 6px;
}

QComboBox:hover, QComboBox:editable:hover {
    border: 1.5px solid __THEME_PRIMARY__;
}

QComboBox:focus, QComboBox:on, QComboBox:editable:focus {
    border: 2px solid __THEME_PRIMARY__;
    background-color: __THEME_LIGHT_BG__;
}

QComboBox:disabled {
    background-color: #f1f5f9;
    border: 1px solid #e2e8f0;
    color: #94a3b8;
}

QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 26px;
    border-left: 1px solid #e2e8f0;
    border-top-right-radius: 9px;
    border-bottom-right-radius: 9px;
    background-color: #f8fafc;
}

QComboBox::drop-down:hover {
    background-color: __THEME_LIGHT_HOVER__;
}

QComboBox::down-arrow {
    width: 0;
    height: 0;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid #475569;
}

QComboBox QLineEdit {
    border: none;
    background: transparent;
    padding: 0px;
    color: #0f172a;
}

QComboBox QLineEdit:focus {
    border: none;
    background: transparent;
}

QComboBox QAbstractItemView, QListView {
    background-color: #ffffff;
    border: 2px solid __THEME_PRIMARY__;
    border-radius: 10px;
    color: #0f172a;
    selection-background-color: __THEME_PRIMARY__;
    selection-color: __THEME_TEXT_PRIMARY__;
    padding: 5px;
}

QComboBox QAbstractItemView::item, QListView::item {
    background-color: #ffffff;
    color: #0f172a;
    padding: 8px 12px;
    border-radius: 6px;
    border: 1.5px solid transparent;
    margin: 1px 0px;
}

QComboBox QAbstractItemView::item:selected, QListView::item:selected {
    background-color: __THEME_PRIMARY__;
    color: __THEME_TEXT_PRIMARY__;
    font-weight: bold;
    border: 1.5px solid __THEME_HOVER__;
}

QComboBox QAbstractItemView::item:hover, QListView::item:hover {
    background-color: __THEME_DROPDOWN_HOVER__;
    color: #0f172a;
    font-weight: bold;
    border: 1.5px solid __THEME_PRIMARY__;
}

QComboBox QAbstractItemView::item:selected:hover, QListView::item:selected:hover {
    background-color: __THEME_HOVER__;
    color: __THEME_TEXT_PRIMARY__;
    font-weight: bold;
    border: 1.5px solid __THEME_HOVER__;
}

QComboBox QAbstractItemView::item:disabled, QListView::item:disabled {
    color: #94a3b8;
    background-color: #ffffff;
}

/* =========================================================================
   Date & Time Inputs with Styled Calendar Drop-Down
   ========================================================================= */
QDateEdit, QDateTimeEdit {
    background-color: #ffffff;
    border: 1.5px solid #cbd5e1;
    border-radius: 10px;
    padding: 4px 10px;
    min-height: 28px;
    color: #0f172a;
    selection-background-color: __THEME_PRIMARY__;
    selection-color: #0f172a;
}

QDateEdit:hover, QDateTimeEdit:hover {
    border: 1.5px solid __THEME_PRIMARY__;
}

QDateEdit:focus, QDateTimeEdit:focus {
    border: 2px solid __THEME_PRIMARY__;
    background-color: __THEME_LIGHT_BG__;
}

QDateEdit:disabled, QDateTimeEdit:disabled {
    background-color: #f1f5f9;
    border: 1px solid #e2e8f0;
    color: #94a3b8;
}

QDateEdit::drop-down, QDateTimeEdit::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 28px;
    border-left: 1px solid #e2e8f0;
    border-top-right-radius: 9px;
    border-bottom-right-radius: 9px;
    background-color: #f8fafc;
}

QDateEdit::drop-down:hover, QDateTimeEdit::drop-down:hover {
    background-color: __THEME_LIGHT_HOVER__;
}

QDateEdit::down-arrow, QDateTimeEdit::down-arrow {
    image: url("__CALENDAR_ICON__");
    width: 16px;
    height: 16px;
}

QDateEdit::down-arrow:disabled, QDateTimeEdit::down-arrow:disabled {
    image: none;
}

/* Remove spin up/down arrows from numeric spin boxes */
QSpinBox::up-button, QSpinBox::down-button,
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {
    subcontrol-origin: border;
    subcontrol-position: none;
    width: 0px;
    height: 0px;
    border: none;
    background: transparent;
    margin: 0px;
    padding: 0px;
}

QSpinBox::up-arrow, QSpinBox::down-arrow,
QDoubleSpinBox::up-arrow, QDoubleSpinBox::down-arrow {
    image: none;
    width: 0px;
    height: 0px;
    border: none;
    background: none;
}

/* =========================================================================
   Standard Buttons
   ========================================================================= */
QPushButton, QToolButton {
    background-color: __THEME_PRIMARY__;
    border: none;
    color: __THEME_TEXT_PRIMARY__;
    padding: 6px 18px;
    min-height: 28px;
    font-weight: bold;
    border-radius: 12px;
    outline: none;
}

QPushButton:hover, QToolButton:hover {
    background-color: __THEME_HOVER__;
}

QPushButton:focus, QToolButton:focus {
    background-color: __THEME_HOVER__;
    border: 1.5px solid __THEME_BORDER__;
    outline: none;
}

QPushButton:pressed, QToolButton:pressed {
    background-color: __THEME_PRESSED__;
}

/* Secondary Button style */
.btn-secondary, QPushButton[class="btn-secondary"] {
    background-color: #f1f5f9;
    color: #1e293b;
    font-weight: 600;
    border: 1.5px solid #cbd5e1;
    border-radius: 10px;
    padding: 6px 14px;
}

.btn-secondary:hover, QPushButton[class="btn-secondary"]:hover {
    background-color: #e2e8f0;
    color: #0f172a;
    border-color: #94a3b8;
}

/* Action Alert/Danger button */
.btn-danger, QPushButton[class="btn-danger"] {
    background-color: #fef2f2;
    color: #ef4444;
    font-weight: 600;
    border: 1.5px solid #fecaca;
    border-radius: 10px;
    padding: 6px 14px;
}

.btn-danger:hover, QPushButton[class="btn-danger"]:hover {
    background-color: #fee2e2;
    border-color: #f87171;
}

/* Success Button */
.btn-success, QPushButton[class="btn-success"], #btn_theme_primary {
    background-color: __THEME_PRIMARY__;
    color: __THEME_TEXT_PRIMARY__;
    font-weight: bold;
    border: none;
    border-radius: 10px;
    padding: 6px 16px;
}

.btn-success:hover, QPushButton[class="btn-success"]:hover, #btn_theme_primary:hover {
    background-color: __THEME_HOVER__;
}

.btn-success:pressed, QPushButton[class="btn-success"]:pressed, #btn_theme_primary:pressed {
    background-color: __THEME_PRESSED__;
}

/* Warning Button (Warm Honey Amber) */
.btn-warning {
    background-color: #f6c944;
    color: #0f172a;
    font-weight: bold;
}

.btn-warning:hover {
    background-color: #eab308;
}

/* Quick-Add Plus Button */
.btn-quick-add {
    background-color: __THEME_PRIMARY__;
    color: __THEME_TEXT_PRIMARY__;
    padding: 0px;
    font-size: 18px;
    font-weight: bold;
    text-align: center;
    border-radius: 10px;
    min-width: 40px;
    max-width: 40px;
}

.btn-quick-add:hover {
    background-color: __THEME_HOVER__;
}

/* =========================================================================
   Tables & Grids
   ========================================================================= */
QTableWidget, QTableView {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 14px;
    gridline-color: #f1f5f9;
    selection-background-color: #dcfce7;
    selection-color: #0f172a;
    color: #0f172a;
    outline: none;
}

QTableWidget::item, QTableView::item {
    padding: 9px;
    border-bottom: 1px solid #f1f5f9;
    outline: none;
    color: #0f172a;
}

QTableWidget::item:focus, QTableView::item:focus {
    outline: none;
    border: none;
}

QHeaderView::section {
    background-color: __THEME_LIGHT_HOVER__;
    color: #334155;
    padding: 8px 6px;
    font-weight: bold;
    border: none;
    border-bottom: 2px solid #e2e8f0;
}

QHeaderView {
    background-color: transparent;
}

QScrollBar:vertical {
    border: none;
    background-color: #f8fafc;
    width: 10px;
    margin: 0px;
    border-radius: 5px;
}

QScrollBar::handle:vertical {
    background-color: #cbd5e1;
    min-height: 20px;
    border-radius: 5px;
}

QScrollBar::handle:vertical:hover {
    background-color: #94a3b8;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    border: none;
    background: none;
}

QScrollBar:horizontal {
    border: none;
    background-color: #f8fafc;
    height: 10px;
    margin: 0px;
    border-radius: 5px;
}

QScrollBar::handle:horizontal {
    background-color: #cbd5e1;
    min-width: 20px;
    border-radius: 5px;
}

QScrollBar::handle:horizontal:hover {
    background-color: #94a3b8;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    border: none;
    background: none;
}

/* =========================================================================
   Dialog Boxes & Tabs
   ========================================================================= */
LoginWindow, ModernAlertDialog {
    background-color: transparent;
    border: none;
}

QDialog {
    background-color: #ffffff;
    border: 1.5px solid __THEME_PRIMARY__;
    border-radius: 18px;
}

QDialog QLabel {
    color: #0f172a;
}

QTabWidget::pane {
    border: 1px solid #e2e8f0;
    background-color: #ffffff;
    border-radius: 16px;
    padding: 12px;
}

QTabBar::tab {
    background-color: #e2e8f0;
    color: #475569;
    padding: 9px 20px;
    border-radius: 12px;
    margin-right: 6px;
    outline: none;
    font-weight: 600;
}

QTabBar::tab:focus {
    outline: none;
}

QTabBar::tab:selected {
    background-color: __THEME_PRIMARY__;
    color: __THEME_TEXT_PRIMARY__;
    font-weight: bold;
}

QTabBar::tab:hover {
    background-color: #cbd5e1;
    color: #0f172a;
}

QTabBar QToolButton {
    background-color: #e2e8f0;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    margin: 1px;
}

QTabBar QToolButton:hover {
    background-color: __THEME_PRIMARY__;
}

/* =========================================================================
   List Widget
   ========================================================================= */
QListWidget {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    color: #0f172a;
}

QListWidget::item {
    padding: 8px 12px;
    border-bottom: 1px solid #f1f5f9;
}

QListWidget::item:hover {
    background-color: __THEME_LIGHT_HOVER__;
    color: #0f172a;
}

QListWidget::item:selected {
    background-color: __THEME_PRIMARY__;
    color: __THEME_TEXT_PRIMARY__;
    font-weight: bold;
}

/* =========================================================================
   Calendar Widget
   ========================================================================= */
QCalendarWidget {
    background-color: #ffffff;
    border: 1.5px solid #cbd5e1;
    border-radius: 14px;
}

QCalendarWidget QWidget {
    alternate-background-color: #f8fafc;
    background-color: #ffffff;
    color: #0f172a;
}

QCalendarWidget QWidget#qt_calendar_navigationbar {
    background-color: __THEME_LIGHT_HOVER__;
    border-bottom: 1px solid #e2e8f0;
}

QCalendarWidget QToolButton {
    color: #0f172a;
    background-color: transparent;
    border: none;
    border-radius: 6px;
    margin: 3px;
    padding: 4px 8px;
    font-weight: bold;
}

QCalendarWidget QToolButton:hover {
    background-color: #e2e8f0;
}

QCalendarWidget QToolButton:pressed {
    background-color: __THEME_PRIMARY__;
}

QCalendarWidget QMenu {
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    color: #0f172a;
}

QCalendarWidget QMenu::item:selected {
    background-color: __THEME_PRIMARY__;
    color: #0f172a;
}

QCalendarWidget QSpinBox {
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    color: #0f172a;
    selection-background-color: __THEME_PRIMARY__;
}

QCalendarWidget QAbstractItemView {
    background-color: #ffffff;
    color: #0f172a;
    selection-background-color: __THEME_PRIMARY__;
    selection-color: #0f172a;
}

QCalendarWidget QAbstractItemView::item {
    padding: 0px;
    border: none;
}

QCalendarWidget QAbstractItemView:enabled {
    color: #0f172a;
}

QCalendarWidget QAbstractItemView:disabled {
    color: #94a3b8;
}

/* Tooltip */
QToolTip {
    background-color: #0f172a;
    color: #ffffff;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 6px 10px;
    font-size: 12px;
}

/* =========================================================================
   Table Action Buttons (Harmonized with Dynamic Theme Palette)
   ========================================================================= */
QPushButton[class="btn-action-view"] {
    background-color: __THEME_PRIMARY__;
    color: __THEME_TEXT_PRIMARY__;
    font-size: 11px;
    font-weight: bold;
    border-radius: 6px;
    padding: 2px 8px !important;
    min-height: 24px !important;
    max-height: 24px !important;
    min-width: 55px !important;
    border: none;
}
QPushButton[class="btn-action-view"]:hover {
    background-color: __THEME_HOVER__;
}
QPushButton[class="btn-action-view"]:pressed {
    background-color: __THEME_PRESSED__;
}

QPushButton[class="btn-action-print"] {
    background-color: #f1f5f9;
    color: #334155;
    font-size: 11px;
    font-weight: bold;
    border-radius: 6px;
    padding: 2px 8px !important;
    min-height: 24px !important;
    max-height: 24px !important;
    min-width: 55px !important;
    border: 1px solid #cbd5e1;
}
QPushButton[class="btn-action-print"]:hover {
    background-color: #e2e8f0;
    color: #0f172a;
}

QPushButton[class="btn-action-edit"] {
    background-color: #fef3c7;
    color: #b45309;
    font-size: 11px;
    font-weight: bold;
    border-radius: 6px;
    padding: 2px 8px !important;
    min-height: 24px !important;
    max-height: 24px !important;
    min-width: 55px !important;
    border: 1px solid #fde68a;
}
QPushButton[class="btn-action-edit"]:hover {
    background-color: #f59e0b;
    color: #ffffff;
    border: 1px solid #f59e0b;
}

QPushButton[class="btn-action-delete"] {
    background-color: #fee2e2;
    color: #dc2626;
    font-size: 11px;
    font-weight: bold;
    border-radius: 6px;
    padding: 2px 8px !important;
    min-height: 24px !important;
    max-height: 24px !important;
    min-width: 58px !important;
    border: 1px solid #fecaca;
}
QPushButton[class="btn-action-delete"]:hover {
    background-color: #ef4444;
    color: #ffffff;
    border: 1px solid #ef4444;
}
QPushButton[class="btn-action-delete"]:pressed {
    background-color: #dc2626;
    color: #ffffff;
}

QPushButton[class="btn-action-success"] {
    background-color: __THEME_PRIMARY__;
    color: __THEME_TEXT_PRIMARY__;
    font-size: 11px;
    font-weight: bold;
    border-radius: 6px;
    padding: 2px 8px !important;
    min-height: 24px !important;
    max-height: 24px !important;
    min-width: 55px !important;
    border: none;
}
QPushButton[class="btn-action-success"]:hover {
    background-color: __THEME_HOVER__;
}
QPushButton[class="btn-action-success"]:pressed {
    background-color: __THEME_PRESSED__;
}

/* Compact Table Action Icon Buttons */
QPushButton[class="btn-action-icon-view"] {
    background-color: __THEME_PRIMARY__;
    color: __THEME_TEXT_PRIMARY__;
    font-size: 13px;
    font-weight: bold;
    border-radius: 8px;
    min-height: 28px !important;
    max-height: 28px !important;
    min-width: 34px !important;
    max-width: 34px !important;
    border: none;
    padding: 0px !important;
}
QPushButton[class="btn-action-icon-view"]:hover {
    background-color: __THEME_HOVER__;
}
QPushButton[class="btn-action-icon-view"]:pressed {
    background-color: __THEME_PRESSED__;
}

QPushButton[class="btn-action-icon-success"] {
    background-color: __THEME_PRIMARY__;
    color: __THEME_TEXT_PRIMARY__;
    font-size: 13px;
    font-weight: bold;
    border-radius: 8px;
    min-height: 28px !important;
    max-height: 28px !important;
    min-width: 34px !important;
    max-width: 34px !important;
    border: none;
    padding: 0px !important;
}
QPushButton[class="btn-action-icon-success"]:hover {
    background-color: __THEME_HOVER__;
}
QPushButton[class="btn-action-icon-success"]:pressed {
    background-color: __THEME_PRESSED__;
}

QPushButton[class="btn-action-icon-edit"] {
    background-color: #fef3c7;
    color: #b45309;
    font-size: 13px;
    font-weight: bold;
    border-radius: 8px;
    min-height: 28px !important;
    max-height: 28px !important;
    min-width: 34px !important;
    max-width: 34px !important;
    border: 1px solid #fde68a;
    padding: 0px !important;
}
QPushButton[class="btn-action-icon-edit"]:hover {
    background-color: #f59e0b;
    color: #ffffff;
    border: 1px solid #f59e0b;
}

QPushButton[class="btn-action-icon-delete"] {
    background-color: #fee2e2;
    color: #dc2626;
    font-size: 13px;
    font-weight: bold;
    border-radius: 8px;
    min-height: 28px !important;
    max-height: 28px !important;
    min-width: 34px !important;
    max-width: 34px !important;
    border: 1px solid #fecaca;
    padding: 0px !important;
}
QPushButton[class="btn-action-icon-delete"]:hover {
    background-color: #ef4444;
    color: #ffffff;
    border: 1px solid #ef4444;
}
QPushButton[class="btn-action-icon-delete"]:pressed {
    background-color: #dc2626;
    color: #ffffff;
}

/* =========================================================================
   GroupBox
   ========================================================================= */
QGroupBox {
    font-weight: bold;
    font-size: 13px;
    border: 1px solid #e2e8f0;
    border-radius: 14px;
    margin-top: 15px;
    padding-top: 15px;
    background-color: #ffffff;
    color: #0f172a;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 15px;
    padding: 0 8px;
    background-color: #ffffff;
    color: #475569;
    font-weight: bold;
}

/* =========================================================================
   TreeWidget and TreeView
   ========================================================================= */
QTreeWidget, QTreeView {
    background-color: #ffffff;
    alternate-background-color: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    color: #0f172a;
    outline: none;
}

QTreeWidget:disabled, QTreeView:disabled {
    background-color: #f1f5f9;
    color: #94a3b8;
}

QTreeWidget::item, QTreeView::item {
    padding: 8px 6px;
    color: #0f172a;
    border-bottom: 1px solid #f1f5f9;
}

QTreeWidget::item:hover, QTreeView::item:hover {
    background-color: __THEME_LIGHT_HOVER__;
    color: #0f172a;
}

QTreeWidget::item:selected, QTreeView::item:selected {
    background-color: __THEME_PRIMARY__;
    color: __THEME_TEXT_PRIMARY__;
    font-weight: bold;
}

QTreeWidget::branch, QTreeView::branch {
    background-color: #ffffff;
}

QTreeWidget::branch:selected, QTreeView::branch:selected {
    background-color: __THEME_PRIMARY__;
}

QTreeWidget::branch:hover, QTreeView::branch:hover {
    background-color: __THEME_LIGHT_HOVER__;
}

/* Checkbox / Indicator */
QTreeWidget::indicator, QCheckBox::indicator {
    width: 18px;
    height: 18px;
    background-color: #ffffff;
    border: 1.5px solid #cbd5e1;
    border-radius: 5px;
}

QTreeWidget::indicator:hover, QCheckBox::indicator:hover {
    border: 1.5px solid __THEME_PRIMARY__;
    background-color: __THEME_LIGHT_HOVER__;
}

QTreeWidget::indicator:checked, QCheckBox::indicator:checked {
    background-color: __THEME_PRIMARY__;
    border: 1.5px solid __THEME_HOVER__;
}

QTreeWidget::indicator:unchecked, QCheckBox::indicator:unchecked {
    background-color: #ffffff;
    border: 1.5px solid #cbd5e1;
}

QTreeWidget::indicator:disabled, QCheckBox::indicator:disabled {
    background-color: #f1f5f9;
    border: 1px solid #e2e8f0;
}

/* =========================================================================
   Top Bar Language Toggle Button
   ========================================================================= */
#lang_btn {
    background-color: __THEME_PRIMARY__;
    color: __THEME_TEXT_PRIMARY__;
    border: none;
    border-radius: 17px;
    padding: 4px 18px;
    font-weight: bold;
    font-size: 12px;
}
#lang_btn:hover {
    background-color: __THEME_HOVER__;
}
"""

def get_theme_stylesheet(primary_hex="#8fd53b"):
    """
    Generates the complete application stylesheet customized for the specified theme color.
    """
    palette = get_theme_palette(primary_hex)
    css = THEME_STYLESHEET_TEMPLATE
    cal_icon = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "calendar.png").replace("\\", "/")
    replacements = {
        "__CALENDAR_ICON__": cal_icon,
        "__THEME_PRIMARY__": palette["primary"],
        "__THEME_HOVER__": palette["hover"],
        "__THEME_PRESSED__": palette["pressed"],
        "__THEME_BORDER__": palette["border"],
        "__THEME_GRAD_START__": palette["grad_start"],
        "__THEME_GRAD_END__": palette["grad_end"],
        "__THEME_TEXT_PRIMARY__": palette["text_primary"],
        "__THEME_SIDEBAR_TEXT__": palette["sidebar_text"],
        "__THEME_SIDEBAR_SUBTEXT__": palette["sidebar_subtext"],
        "__THEME_LIGHT_BG__": palette["light_bg"],
        "__THEME_LIGHT_HOVER__": palette["light_hover"],
        "__THEME_DROPDOWN_HOVER__": palette["dropdown_hover"],
    }
    for token, val in replacements.items():
        css = css.replace(token, val)
    return css

# Default global style for backwards-compatibility
GLOBAL_STYLE = get_theme_stylesheet("#8fd53b")
