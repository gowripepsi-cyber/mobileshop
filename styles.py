GLOBAL_STYLE = """
/* Global Stylesheet for Inventory & Accounting Management System */

QMainWindow {
    background-color: #0f0f1b;
}

QWidget {
    font-family: 'Segoe UI', -apple-system, Roboto, Helvetica, sans-serif;
    font-size: 13px;
    color: #e2e8f0;
}

/* Sidebar Styling */
#sidebar {
    background-color: #151528;
    border-right: 1px solid #20203e;
    min-width: 250px;
    max-width: 250px;
}

#sidebar QLabel {
    color: #ffffff;
    font-weight: bold;
    font-size: 16px;
    padding: 15px 10px;
}

#sidebar QPushButton {
    background-color: transparent;
    border: none;
    padding: 12px 20px;
    border-radius: 6px;
    margin: 4px 10px;
}

#sidebar QPushButton:hover {
    background-color: rgba(99, 102, 241, 0.1);
}

#sidebar QPushButton:checked {
    background-color: #6366f1;
}

#sidebar QPushButton QLabel {
    background: transparent;
}

#sidebar QPushButton QLabel#btn_label {
    color: #94a3b8;
    font-size: 14px;
}

#sidebar QPushButton:hover QLabel#btn_label {
    color: #ffffff;
}

#sidebar QPushButton:checked QLabel#btn_label {
    color: #ffffff;
    font-weight: bold;
}

#sidebar QPushButton QLabel#shortcut_label {
    color: #475569;
    font-size: 11px;
    font-weight: normal;
    background: transparent;
    border: none;
    padding: 0px;
}

#sidebar QPushButton:hover QLabel#shortcut_label {
    color: #64748b;
    background: transparent;
    border: none;
}

#sidebar QPushButton:checked QLabel#shortcut_label {
    color: #94a3b8;
    background: transparent;
    border: none;
}

/* Header Area */
#header {
    background-color: #151528;
    border-bottom: 1px solid #20203e;
    min-height: 60px;
    max-height: 60px;
    padding: 0px 20px;
}

#header QLabel {
    font-size: 18px;
    font-weight: bold;
    color: #ffffff;
}

/* Main Content Area */
#content_area {
    background-color: #0f0f1b;
}

/* Card / Frame Container */
.CardFrame {
    background-color: #1b1b32;
    border: 1px solid #28284e;
    border-radius: 12px;
}

.CardFrame QLabel {
    background: transparent;
}

/* Metrics Cards on Dashboard */
.MetricCard {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1e1e38, stop:1 #15152a);
    border: 1px solid #2c2c54;
    border-radius: 12px;
    padding: 15px;
}

.ClickableMetricCard {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1e1e38, stop:1 #15152a);
    border: 1px solid #2c2c54;
    border-radius: 12px;
    padding: 15px;
}

.ClickableMetricCard:hover {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #252547, stop:1 #1b1b36);
    border: 1px solid #434380;
}

.MetricTitle {
    color: #94a3b8;
    font-size: 12px;
    font-weight: bold;
    text-transform: uppercase;
}

.MetricValue {
    color: #ffffff;
    font-size: 22px;
    font-weight: bold;
    margin-top: 5px;
}

/* Form inputs & buttons */
QLineEdit, QPlainTextEdit, QTextEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit {
    background-color: #141426;
    border: 1px solid #2c2c54;
    border-radius: 6px;
    padding: 6px 12px;
    min-height: 28px;
    color: #ffffff;
    selection-background-color: #6366f1;
}

QLineEdit:hover, QPlainTextEdit:hover, QTextEdit:hover, QComboBox:hover, QSpinBox:hover, QDoubleSpinBox:hover, QDateEdit:hover {
    border: 1px solid #434380;
}

QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus, QComboBox:focus, QComboBox:on, QComboBox:editable:focus, QSpinBox:focus, QDoubleSpinBox:focus, QDateEdit:focus {
    border: 1px solid #6366f1;
}

QComboBox QLineEdit {
    border: none;
    background: transparent;
    padding: 0px;
}

QComboBox QLineEdit:focus {
    border: none;
    background: transparent;
}

QComboBox::drop-down {
    border: none;
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 25px;
}

QComboBox QAbstractItemView, QListView {
    background-color: #2b2b3c;
    border: 1px solid #4a6cf7;
    color: #ffffff;
    selection-background-color: #4a6cf7;
    selection-color: #ffffff;
}

QComboBox QAbstractItemView::item, QListView::item {
    background-color: #2b2b3c;
    color: #ffffff;
    padding: 6px 12px;
}

QComboBox QAbstractItemView::item:selected, QListView::item:selected {
    background-color: #4a6cf7;
    color: #ffffff;
}

QComboBox QAbstractItemView::item:hover, QListView::item:hover {
    background-color: #3b3b52;
    color: #ffffff;
}

QComboBox QAbstractItemView::item:disabled, QListView::item:disabled {
    color: #64748b;
    background-color: #2b2b3c;
}


/* Standard Buttons */
QPushButton {
    background-color: #6366f1;
    border: none;
    color: #ffffff;
    padding: 9px 18px;
    font-weight: bold;
    border-radius: 6px;
}

QPushButton:hover {
    background-color: #4f46e5;
}

QPushButton:pressed {
    background-color: #4338ca;
}

/* Secondary Button style */
.btn-secondary {
    background-color: #334155;
    color: #f8fafc;
}

.btn-secondary:hover {
    background-color: #475569;
}

/* Action Alert/Danger button */
.btn-danger {
    background-color: #ef4444;
}

.btn-danger:hover {
    background-color: #dc2626;
}

/* Success Button */
.btn-success {
    background-color: #10b981;
}

.btn-success:hover {
    background-color: #059669;
}

/* Warning Button */
.btn-warning {
    background-color: #f59e0b;
}

/* Quick-Add Plus Button */
.btn-quick-add {
    background-color: #6366f1;
    color: #ffffff;
    padding: 0px;
    font-size: 18px;
    font-weight: bold;
    text-align: center;
    border-radius: 6px;
    min-width: 40px;
    max-width: 40px;
}

.btn-quick-add:hover {
    background-color: #4f46e5;
}

.btn-warning:hover {
    background-color: #d97706;
}


/* Tables */
QTableWidget, QTableView {
    background-color: #151528;
    border: 1px solid #20203e;
    border-radius: 8px;
    gridline-color: #20203e;
    selection-background-color: rgba(99, 102, 241, 0.2);
    selection-color: #ffffff;
}

QTableWidget::item, QTableView::item {
    padding: 10px;
    border-bottom: 1px solid #20203e;
}

QHeaderView::section {
    background-color: #1c1c36;
    color: #94a3b8;
    padding: 8px;
    font-weight: bold;
    border: none;
    border-bottom: 2px solid #2c2c54;
}

QHeaderView {
    background-color: transparent;
}

QScrollBar:vertical {
    border: none;
    background-color: #0f0f1b;
    width: 10px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background-color: #2c2c54;
    min-height: 20px;
    border-radius: 5px;
}

QScrollBar::handle:vertical:hover {
    background-color: #434380;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    border: none;
    background: none;
}

QScrollBar:horizontal {
    border: none;
    background-color: #0f0f1b;
    height: 10px;
    margin: 0px;
}

QScrollBar::handle:horizontal {
    background-color: #2c2c54;
    min-width: 20px;
    border-radius: 5px;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    border: none;
    background: none;
}

/* Dialog Box */
QDialog {
    background-color: #151528;
    border: 1px solid #28284e;
}

QDialog QLabel {
    color: #ffffff;
}

QTabWidget::pane {
    border: 1px solid #28284e;
    background-color: #151528;
    border-radius: 8px;
    padding: 10px;
}

QTabBar::tab {
    background-color: #1b1b32;
    color: #94a3b8;
    padding: 10px 20px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    margin-right: 4px;
}

QTabBar::tab:selected {
    background-color: #151528;
    color: #ffffff;
    font-weight: bold;
    border-bottom: 2px solid #6366f1;
}

QTabBar::tab:hover {
    background-color: #28284e;
    color: #ffffff;
}

/* List Widget styling */
QListWidget {
    background-color: #151528;
    border: 1px solid #20203e;
    border-radius: 6px;
    color: #ffffff;
}

QListWidget::item {
    padding: 8px;
    border-bottom: 1px solid #20203e;
}

QListWidget::item:hover {
    background-color: rgba(99, 102, 241, 0.1);
}

QListWidget::item:selected {
    background-color: #6366f1;
    color: #ffffff;
}

/* Calendar Widget Styling */
QCalendarWidget {
    background-color: #151528;
    border: 1px solid #2c2c54;
    border-radius: 8px;
}

QCalendarWidget QWidget {
    alternate-background-color: #1b1b32;
    background-color: #151528;
    color: #e2e8f0;
}

/* Navigation bar at the top */
QCalendarWidget QWidget#qt_calendar_navigationbar {
    background-color: #1b1b32;
    border-bottom: 1px solid #2c2c54;
}

/* Tool buttons in navigation bar (Month, Year, Prev, Next) */
QCalendarWidget QToolButton {
    color: #ffffff;
    background-color: transparent;
    border: none;
    border-radius: 4px;
    margin: 3px;
    padding: 4px 8px;
    font-weight: bold;
}

QCalendarWidget QToolButton:hover {
    background-color: rgba(99, 102, 241, 0.2);
}

QCalendarWidget QToolButton:pressed {
    background-color: #6366f1;
}

/* The month/year drop down menus */
QCalendarWidget QMenu {
    background-color: #141426;
    border: 1px solid #2c2c54;
    color: #ffffff;
}

QCalendarWidget QMenu::item:selected {
    background-color: #6366f1;
    color: #ffffff;
}

/* Year SpinBox */
QCalendarWidget QSpinBox {
    background-color: #141426;
    border: 1px solid #2c2c54;
    border-radius: 4px;
    color: #ffffff;
    selection-background-color: #6366f1;
}

/* Grid view (the days table) */
QCalendarWidget QAbstractItemView {
    background-color: #151528;
    color: #e2e8f0;
    selection-background-color: #6366f1;
    selection-color: #ffffff;
}

QCalendarWidget QAbstractItemView::item {
    padding: 0px;
    border: none;
}

QCalendarWidget QAbstractItemView:enabled {
    color: #e2e8f0;
}

QCalendarWidget QAbstractItemView:disabled {
    color: #475569;
}

/* Tooltip styling */
QToolTip {
    background-color: #1e1e38;
    color: #ffffff;
    border: 1px solid #2c2c54;
    border-radius: 4px;
    padding: 5px;
    font-size: 12px;
}

/* Table Action Buttons - Modern ERP/CRM styling */
QPushButton[class="btn-action-view"] {
    background-color: #3b82f6;
    color: #ffffff;
    font-size: 11px;
    font-weight: bold;
    border-radius: 6px;
    padding: 2px 10px !important;
    min-height: 24px !important;
    max-height: 24px !important;
    min-width: 65px !important;
    border: none;
}
QPushButton[class="btn-action-view"]:hover {
    background-color: #2563eb;
}
QPushButton[class="btn-action-view"]:pressed {
    background-color: #1d4ed8;
}

QPushButton[class="btn-action-print"] {
    background-color: #64748b;
    color: #ffffff;
    font-size: 11px;
    font-weight: bold;
    border-radius: 6px;
    padding: 2px 10px !important;
    min-height: 24px !important;
    max-height: 24px !important;
    min-width: 65px !important;
    border: none;
}
QPushButton[class="btn-action-print"]:hover {
    background-color: #475569;
}
QPushButton[class="btn-action-print"]:pressed {
    background-color: #334155;
}

QPushButton[class="btn-action-edit"] {
    background-color: #f59e0b;
    color: #ffffff;
    font-size: 11px;
    font-weight: bold;
    border-radius: 6px;
    padding: 2px 10px !important;
    min-height: 24px !important;
    max-height: 24px !important;
    min-width: 65px !important;
    border: none;
}
QPushButton[class="btn-action-edit"]:hover {
    background-color: #d97706;
}
QPushButton[class="btn-action-edit"]:pressed {
    background-color: #b45309;
}

QPushButton[class="btn-action-delete"] {
    background-color: #ef4444;
    color: #ffffff;
    font-size: 11px;
    font-weight: bold;
    border-radius: 6px;
    padding: 2px 10px !important;
    min-height: 24px !important;
    max-height: 24px !important;
    min-width: 75px !important;
    border: none;
}
QPushButton[class="btn-action-delete"]:hover {
    background-color: #dc2626;
}
QPushButton[class="btn-action-delete"]:pressed {
    background-color: #b91c1c;
}

QPushButton[class="btn-action-success"] {
    background-color: #10b981;
    color: #ffffff;
    font-size: 11px;
    font-weight: bold;
    border-radius: 6px;
    padding: 2px 10px !important;
    min-height: 24px !important;
    max-height: 24px !important;
    min-width: 65px !important;
    border: none;
}
QPushButton[class="btn-action-success"]:hover {
    background-color: #059669;
}
QPushButton[class="btn-action-success"]:pressed {
    background-color: #047857;
}

/* GroupBox Styling */
QGroupBox {
    font-weight: bold;
    font-size: 13px;
    border: 1px solid #28284e;
    border-radius: 8px;
    margin-top: 15px;
    padding-top: 15px;
    background-color: #151528;
    color: #ffffff;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 15px;
    padding: 0 8px;
    background-color: #151528;
    color: #818cf8;
    font-weight: bold;
}

/* TreeWidget and TreeView Styling */
QTreeWidget, QTreeView {
    background-color: #141426;
    alternate-background-color: #191930;
    border: 1px solid #28284e;
    border-radius: 6px;
    color: #f1f5f9;
    outline: none;
}

QTreeWidget:disabled, QTreeView:disabled {
    background-color: #141426;
    color: #cbd5e1;
}

QTreeWidget::item, QTreeView::item {
    padding: 8px 6px;
    color: #f1f5f9;
    border-bottom: 1px solid #1e1e38;
}

QTreeWidget::item:hover, QTreeView::item:hover {
    background-color: #222244;
    color: #ffffff;
}

QTreeWidget::item:selected, QTreeView::item:selected {
    background-color: #4f46e5;
    color: #ffffff;
}

QTreeWidget::item:disabled, QTreeView::item:disabled {
    color: #cbd5e1;
    background-color: #141426;
}

/* Branch / Arrow styling */
QTreeWidget::branch, QTreeView::branch {
    background-color: #141426;
}

QTreeWidget::branch:selected, QTreeView::branch:selected {
    background-color: #4f46e5;
}

QTreeWidget::branch:hover, QTreeView::branch:hover {
    background-color: #222244;
}

/* Checkbox / Indicator styling in TreeWidget and standalone QCheckBox */
QTreeWidget::indicator, QCheckBox::indicator {
    width: 18px;
    height: 18px;
    background-color: #1e1e38;
    border: 2px solid #475569;
    border-radius: 4px;
}

QTreeWidget::indicator:hover, QCheckBox::indicator:hover {
    border: 2px solid #818cf8;
    background-color: #28284e;
}

QTreeWidget::indicator:checked, QCheckBox::indicator:checked {
    background-color: #6366f1;
    border: 2px solid #818cf8;
}

QTreeWidget::indicator:unchecked, QCheckBox::indicator:unchecked {
    background-color: #141426;
    border: 2px solid #475569;
}

QTreeWidget::indicator:disabled, QCheckBox::indicator:disabled {
    background-color: #18182e;
    border: 2px solid #334155;
}

QTreeWidget::indicator:checked:disabled, QCheckBox::indicator:checked:disabled {
    background-color: #3730a3;
    border: 2px solid #818cf8;
}
"""
