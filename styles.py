GLOBAL_STYLE = """
/* =========================================================================
   Global Theme: Modern Fresh Lime & Sunny Ivory
   Inspired by clean, organic, rounded capsule design:
   - Soft porcelain canvas (#f6f8fa)
   - Encapsulated floating lime pill sidebar (#95da4c -> #84cc34)
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
    background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #95da4c, stop:1 #84cc34);
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
    border-radius: 22px;
    min-width: 44px;
    max-width: 44px;
    min-height: 44px;
    max-height: 44px;
    border: 2px solid #ffffff;
}

#shop_title {
    color: #142b05;
    font-size: 15px;
    font-weight: 800;
    margin-top: 4px;
    margin-bottom: 8px;
    letter-spacing: 0.5px;
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
    color: #142b05;
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
    background-color: #fbfdf9;
    border: 1.5px solid #8fd53b;
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
QLineEdit, QPlainTextEdit, QTextEdit, QSpinBox, QDoubleSpinBox, QDateEdit {
    background-color: #ffffff;
    border: 1.5px solid #cbd5e1;
    border-radius: 10px;
    padding: 6px 12px;
    min-height: 28px;
    color: #0f172a;
    selection-background-color: #8fd53b;
    selection-color: #0f172a;
}

QLineEdit:hover, QPlainTextEdit:hover, QTextEdit:hover, QSpinBox:hover, QDoubleSpinBox:hover, QDateEdit:hover {
    border: 1.5px solid #94d743;
}

QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QDateEdit:focus {
    border: 2px solid #8fd53b;
    background-color: #fbfdf9;
}

QLineEdit:disabled, QPlainTextEdit:disabled, QTextEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled, QDateEdit:disabled {
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
    selection-background-color: #8fd53b;
    selection-color: #0f172a;
}

QComboBox:editable {
    background-color: #ffffff;
    border: 1.5px solid #cbd5e1;
    border-radius: 10px;
    padding: 2px 6px;
}

QComboBox:hover, QComboBox:editable:hover {
    border: 1.5px solid #8fd53b;
}

QComboBox:focus, QComboBox:on, QComboBox:editable:focus {
    border: 2px solid #8fd53b;
    background-color: #fbfdf9;
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
    background-color: #f4faee;
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
    border: 1.5px solid #8fd53b;
    border-radius: 8px;
    color: #0f172a;
    selection-background-color: #8fd53b;
    selection-color: #0f172a;
    padding: 4px;
}

QComboBox QAbstractItemView::item, QListView::item {
    background-color: #ffffff;
    color: #0f172a;
    padding: 7px 12px;
    border-radius: 6px;
}

QComboBox QAbstractItemView::item:selected, QListView::item:selected {
    background-color: #8fd53b;
    color: #0f172a;
    font-weight: bold;
}

QComboBox QAbstractItemView::item:hover, QListView::item:hover {
    background-color: #f4faee;
    color: #0f172a;
}

QComboBox QAbstractItemView::item:disabled, QListView::item:disabled {
    color: #94a3b8;
    background-color: #ffffff;
}

/* Remove spin up/down arrows from text boxes */
QSpinBox::up-button, QSpinBox::down-button,
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button,
QAbstractSpinBox::up-button, QAbstractSpinBox::down-button {
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
QDoubleSpinBox::up-arrow, QDoubleSpinBox::down-arrow,
QAbstractSpinBox::up-arrow, QAbstractSpinBox::down-arrow {
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
    background-color: #8fd53b;
    border: none;
    color: #0f172a;
    padding: 6px 18px;
    min-height: 28px;
    font-weight: bold;
    border-radius: 12px;
    outline: none;
}

QPushButton:hover, QToolButton:hover {
    background-color: #7ec72e;
}

QPushButton:focus, QToolButton:focus {
    background-color: #7ec72e;
    border: 1.5px solid #63a820;
    outline: none;
}

QPushButton:pressed, QToolButton:pressed {
    background-color: #6eb520;
}

/* Secondary Button style */
.btn-secondary {
    background-color: #e2e8f0;
    color: #1e293b;
    border: 1px solid #cbd5e1;
}

.btn-secondary:hover {
    background-color: #cbd5e1;
    color: #0f172a;
}

/* Action Alert/Danger button */
.btn-danger {
    background-color: #ef4444;
    color: #ffffff;
}

.btn-danger:hover {
    background-color: #dc2626;
}

/* Success Button */
.btn-success {
    background-color: #10b981;
    color: #ffffff;
    font-weight: bold;
}

.btn-success:hover {
    background-color: #059669;
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
    background-color: #8fd53b;
    color: #0f172a;
    padding: 0px;
    font-size: 18px;
    font-weight: bold;
    text-align: center;
    border-radius: 10px;
    min-width: 40px;
    max-width: 40px;
}

.btn-quick-add:hover {
    background-color: #7ec72e;
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
    background-color: #f4faee;
    color: #334155;
    padding: 9px;
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
QDialog {
    background-color: #ffffff;
    border: 1.5px solid #8fd53b;
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
    background-color: #8fd53b;
    color: #0f172a;
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
    background-color: #8fd53b;
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
    background-color: #f4faee;
    color: #0f172a;
}

QListWidget::item:selected {
    background-color: #8fd53b;
    color: #0f172a;
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
    background-color: #f4faee;
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
    background-color: #8fd53b;
}

QCalendarWidget QMenu {
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    color: #0f172a;
}

QCalendarWidget QMenu::item:selected {
    background-color: #8fd53b;
    color: #0f172a;
}

QCalendarWidget QSpinBox {
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    color: #0f172a;
    selection-background-color: #8fd53b;
}

QCalendarWidget QAbstractItemView {
    background-color: #ffffff;
    color: #0f172a;
    selection-background-color: #8fd53b;
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
   Table Action Buttons
   ========================================================================= */
QPushButton[class="btn-action-view"] {
    background-color: #3b82f6;
    color: #ffffff;
    font-size: 11px;
    font-weight: bold;
    border-radius: 8px;
    padding: 2px 10px !important;
    min-height: 24px !important;
    max-height: 24px !important;
    min-width: 65px !important;
    border: none;
}
QPushButton[class="btn-action-view"]:hover {
    background-color: #2563eb;
}

QPushButton[class="btn-action-print"] {
    background-color: #64748b;
    color: #ffffff;
    font-size: 11px;
    font-weight: bold;
    border-radius: 8px;
    padding: 2px 10px !important;
    min-height: 24px !important;
    max-height: 24px !important;
    min-width: 65px !important;
    border: none;
}
QPushButton[class="btn-action-print"]:hover {
    background-color: #475569;
}

QPushButton[class="btn-action-edit"] {
    background-color: #f59e0b;
    color: #ffffff;
    font-size: 11px;
    font-weight: bold;
    border-radius: 8px;
    padding: 2px 10px !important;
    min-height: 24px !important;
    max-height: 24px !important;
    min-width: 65px !important;
    border: none;
}
QPushButton[class="btn-action-edit"]:hover {
    background-color: #d97706;
}

QPushButton[class="btn-action-delete"] {
    background-color: #ef4444;
    color: #ffffff;
    font-size: 11px;
    font-weight: bold;
    border-radius: 8px;
    padding: 2px 10px !important;
    min-height: 24px !important;
    max-height: 24px !important;
    min-width: 75px !important;
    border: none;
}
QPushButton[class="btn-action-delete"]:hover {
    background-color: #dc2626;
}

QPushButton[class="btn-action-success"] {
    background-color: #10b981;
    color: #ffffff;
    font-size: 11px;
    font-weight: bold;
    border-radius: 8px;
    padding: 2px 10px !important;
    min-height: 24px !important;
    max-height: 24px !important;
    min-width: 65px !important;
    border: none;
}
QPushButton[class="btn-action-success"]:hover {
    background-color: #059669;
}

/* Compact Table Action Icon Buttons */
QPushButton[class="btn-action-icon-view"] {
    background-color: #3b82f6;
    color: #ffffff;
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
    background-color: #2563eb;
}

QPushButton[class="btn-action-icon-success"] {
    background-color: #10b981;
    color: #ffffff;
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
    background-color: #059669;
}

QPushButton[class="btn-action-icon-edit"] {
    background-color: #f59e0b;
    color: #ffffff;
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
QPushButton[class="btn-action-icon-edit"]:hover {
    background-color: #d97706;
}

QPushButton[class="btn-action-icon-delete"] {
    background-color: #ef4444;
    color: #ffffff;
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
QPushButton[class="btn-action-icon-delete"]:hover {
    background-color: #dc2626;
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
    background-color: #f4faee;
    color: #0f172a;
}

QTreeWidget::item:selected, QTreeView::item:selected {
    background-color: #8fd53b;
    color: #0f172a;
    font-weight: bold;
}

QTreeWidget::branch, QTreeView::branch {
    background-color: #ffffff;
}

QTreeWidget::branch:selected, QTreeView::branch:selected {
    background-color: #8fd53b;
}

QTreeWidget::branch:hover, QTreeView::branch:hover {
    background-color: #f4faee;
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
    border: 1.5px solid #8fd53b;
    background-color: #f4faee;
}

QTreeWidget::indicator:checked, QCheckBox::indicator:checked {
    background-color: #8fd53b;
    border: 1.5px solid #7ec72e;
}

QTreeWidget::indicator:unchecked, QCheckBox::indicator:unchecked {
    background-color: #ffffff;
    border: 1.5px solid #cbd5e1;
}

QTreeWidget::indicator:disabled, QCheckBox::indicator:disabled {
    background-color: #f1f5f9;
    border: 1px solid #e2e8f0;
}
"""
