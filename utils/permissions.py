# utils/permissions.py

MODULE_CATEGORIES = {
    "Dashboard": [
        ("dashboard", "Dashboard Overview", ["view"])
    ],
    "Master Data": [
        ("products", "Products Master", ["view", "add", "edit", "delete"]),
        ("customers", "Customers Master", ["view", "add", "edit", "delete"]),
        ("suppliers", "Suppliers Master", ["view", "add", "edit", "delete"]),
        ("bank_accounts", "Bank Accounts Master", ["view", "add", "edit", "delete"])
    ],
    "Operations & Billing": [
        ("purchase", "Purchase Entry", ["view", "add", "edit", "delete"]),
        ("sales", "Sales Invoice", ["view", "add", "edit", "delete"]),
        ("services", "Service Cards (Repair Center)", ["view", "add", "edit", "delete"]),
        ("payments", "Payments Ledger", ["view", "add", "edit", "delete"])
    ],
    "Analytics": [
        ("reports", "Reports & Financial Analysis", ["view"])
    ],
    "System Administration": [
        ("settings", "Access Settings Page", ["view"]),
        ("system_configuration", "Shop Profile & Configuration", ["view", "edit"]),
        ("user_management", "User Management & Roles", ["view", "add", "edit", "delete"]),
        ("backup_restore", "Database Backup & Restore", ["view", "edit"]),
        ("database_maintenance", "System Maintenance & Factory Reset", ["view", "edit"])
    ]
}

def get_all_module_keys():
    keys = []
    for cat, modules in MODULE_CATEGORIES.items():
        for mod_key, label, actions in modules:
            keys.append(mod_key)
    return keys

def get_default_admin_permissions():
    perms = {}
    for cat, modules in MODULE_CATEGORIES.items():
        for mod_key, label, actions in modules:
            perms[mod_key] = {act: True for act in actions}
    return perms

def has_permission(user_data, module_key, action='view'):
    if not user_data:
        return False
    role = user_data.get('role', '')
    if role in ['Administrator', 'Admin']:
        return True
    
    perms = user_data.get('permissions', {})
    if isinstance(perms, str):
        import json
        try:
            perms = json.loads(perms)
        except Exception:
            perms = {}
            
    mod_perms = perms.get(module_key, {})
    return bool(mod_perms.get(action, False))

def enforce_ui_permissions(main_window):
    """
    Enforces UI permissions on the main window by hiding/disabling navigation buttons,
    sub-tabs, and operational buttons according to user_data permissions.
    """
    if not hasattr(main_window, 'user_data') or not main_window.user_data:
        return

    user = main_window.user_data
    role = user.get('role', '')
    is_admin = role in ['Administrator', 'Admin']

    # 1. Sidebar Navigation Buttons Mapping
    # Nav indices: 0: Dashboard, 1: Masters, 2: Purchase, 3: Sales, 4: Services, 5: Payments, 6: Reports, 7: Settings, 8: Money Transfer
    nav_permission_map = {
        0: [("dashboard", "view")],
        1: [("products", "view"), ("customers", "view"), ("suppliers", "view"), ("bank_accounts", "view")],
        2: [("purchase", "view")],
        3: [("sales", "view")],
        4: [("services", "view")],
        5: [("payments", "view")],
        6: [("reports", "view")],
        7: [("settings", "view"), ("system_configuration", "view"), ("user_management", "view"), ("backup_restore", "view"), ("database_maintenance", "view")],
        8: [("bank_accounts", "view"), ("payments", "view")]
    }

    if hasattr(main_window, 'nav_buttons'):
        for idx, btn in main_window.nav_buttons.items():
            if is_admin:
                pass
            else:
                reqs = nav_permission_map.get(idx, [])
                can_access = any(has_permission(user, mod, act) for mod, act in reqs)
                btn.setVisible(can_access)

    # 2. Masters Sub-tabs
    if hasattr(main_window, 'masters_view'):
        mv = main_window.masters_view
        if hasattr(mv, 'tabs'):
            mv.tabs.setTabVisible(0, is_admin or has_permission(user, "products", "view"))
            mv.tabs.setTabVisible(1, is_admin or has_permission(user, "customers", "view"))
            mv.tabs.setTabVisible(2, is_admin or has_permission(user, "suppliers", "view"))
            mv.tabs.setTabVisible(3, is_admin or has_permission(user, "bank_accounts", "view"))

    # 3. Settings Sub-tabs
    if hasattr(main_window, 'settings_view'):
        sv = main_window.settings_view
        if hasattr(sv, 'tabs'):
            if hasattr(sv, 'shop_tab'):
                idx = sv.tabs.indexOf(sv.shop_tab)
                if idx >= 0:
                    sv.tabs.setTabVisible(idx, is_admin or has_permission(user, "system_configuration", "view"))
            if hasattr(sv, 'user_mgmt_tab'):
                idx = sv.tabs.indexOf(sv.user_mgmt_tab)
                if idx >= 0:
                    sv.tabs.setTabVisible(idx, is_admin or has_permission(user, "user_management", "view"))
            if hasattr(sv, 'db_tab'):
                idx = sv.tabs.indexOf(sv.db_tab)
                if idx >= 0:
                    sv.tabs.setTabVisible(idx, is_admin or has_permission(user, "backup_restore", "view"))
            if hasattr(sv, 'feature_tab'):
                idx = sv.tabs.indexOf(sv.feature_tab)
                if idx >= 0:
                    sv.tabs.setTabVisible(idx, is_admin or has_permission(user, "database_maintenance", "view"))

    # 4. Action Buttons inside Master Views
    def enforce_crud_buttons(view, module_key):
        if not view: return
        can_add = is_admin or has_permission(user, module_key, "add")
        can_edit = is_admin or has_permission(user, module_key, "edit")
        can_del = is_admin or has_permission(user, module_key, "delete")

        if hasattr(view, 'add_btn'): view.add_btn.setEnabled(can_add)
        if hasattr(view, 'edit_btn'): view.edit_btn.setEnabled(can_edit)
        if hasattr(view, 'delete_btn'): view.delete_btn.setEnabled(can_del)

    if hasattr(main_window, 'masters_view'):
        mv = main_window.masters_view
        enforce_crud_buttons(getattr(mv, 'products_view', None), "products")
        enforce_crud_buttons(getattr(mv, 'customers_view', None), "customers")
        enforce_crud_buttons(getattr(mv, 'suppliers_view', None), "suppliers")
        enforce_crud_buttons(getattr(mv, 'bank_accounts_view', None), "bank_accounts")
