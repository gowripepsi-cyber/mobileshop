"""
Unit & Sub-Unit Conversion Helper Utilities
Handles conversion between main units and sub-units for products and transactions.
"""
from typing import Tuple, Optional, Any
from sqlalchemy.orm import Session as SASession


def get_product_unit_info(product: Any, session: SASession) -> Tuple[str, Optional[str], float]:
    """
    Returns (main_unit, sub_unit, conversion_rate).
    If no sub-unit is configured, returns (main_unit, None, 1.0).
    """
    if not product:
        return ("Pcs", None, 1.0)

    main_unit = getattr(product, 'unit', 'Pcs') or 'Pcs'
    sub_unit = getattr(product, 'sub_unit', None)
    conversion_rate = getattr(product, 'unit_conversion_qty', None)

    # If product doesn't have an explicit sub-unit override, look up its Unit in Master
    if not sub_unit or not conversion_rate or conversion_rate <= 0:
        from models import Unit
        u_obj = session.query(Unit).filter(Unit.name.ilike(main_unit.strip())).first()
        if u_obj and u_obj.has_sub_unit and u_obj.sub_unit_name and u_obj.conversion_rate and u_obj.conversion_rate > 0:
            sub_unit = u_obj.sub_unit_name
            conversion_rate = u_obj.conversion_rate

    if sub_unit and conversion_rate and conversion_rate > 0:
        return (main_unit, sub_unit, float(conversion_rate))
    return (main_unit, None, 1.0)


def calculate_base_qty(product: Any, qty: float, selected_unit: str, session: SASession) -> float:
    """
    Converts a transaction quantity in selected_unit to base (sub-unit) quantity.
    Example: 5 Coils (rate 100) -> 500 Meters.
             20 Meters -> 20 Meters.
    """
    if qty is None:
        return 0.0

    qty_val = float(qty)
    main_unit, sub_unit, rate = get_product_unit_info(product, session)

    if not sub_unit or rate <= 1.0:
        return round(qty_val, 4)

    sel_u = (selected_unit or "").strip().lower()
    main_u = main_unit.strip().lower()
    sub_u = sub_unit.strip().lower()

    if sel_u == main_u:
        return round(qty_val * rate, 4)
    elif sel_u == sub_u:
        return round(qty_val, 4)
    return round(qty_val, 4)


def convert_from_base_qty(product: Any, base_qty: float, target_unit: str, session: SASession) -> float:
    """
    Converts a base (sub-unit) quantity to target_unit.
    Example: 480 Meters -> 4.8 Coils (if target_unit is Coil).
    """
    if base_qty is None:
        return 0.0

    b_qty = float(base_qty)
    main_unit, sub_unit, rate = get_product_unit_info(product, session)

    if not sub_unit or rate <= 1.0:
        return round(b_qty, 4)

    tgt_u = (target_unit or "").strip().lower()
    main_u = main_unit.strip().lower()

    if tgt_u == main_u:
        return round(b_qty / rate, 4)
    return round(b_qty, 4)


def format_stock_display(stock_qty: float, main_unit: str, sub_unit: Optional[str] = None, conversion_rate: float = 1.0) -> str:
    """
    Formats stock quantity displaying both base unit and main unit equivalent if applicable.
    Example: 480 Meter (4.8 Coil)
             500 Meter (5 Coil)
             10 Pcs
    """
    if stock_qty is None:
        stock_qty = 0.0
    stock_val = float(stock_qty)
    m_unit = main_unit or "Pcs"

    if sub_unit and conversion_rate > 1.0:
        # stock_qty is stored in base unit (sub_unit)
        main_eq = round(stock_val / conversion_rate, 4)
        stock_str = f"{stock_val:g}"
        main_str = f"{main_eq:g}"
        return f"{stock_str} {sub_unit} ({main_str} {m_unit})"
    else:
        stock_str = f"{stock_val:g}"
        return f"{stock_str} {m_unit}"


def format_product_stock(product: Any, session: SASession) -> str:
    """
    Helper to format a product's current stock based on its unit setup.
    """
    if not product:
        return "0 Pcs"
    main_unit, sub_unit, rate = get_product_unit_info(product, session)
    return format_stock_display(product.stock_qty, main_unit, sub_unit, rate)


def check_circular_unit_reference(unit_id: Optional[int], target_sub_unit_id: Optional[int], session: SASession) -> bool:
    """
    Checks if setting target_sub_unit_id as a sub-unit of unit_id creates a circular loop.
    Returns True if a circular reference is detected, False otherwise.
    """
    if not unit_id or not target_sub_unit_id:
        return False
    if unit_id == target_sub_unit_id:
        return True

    from models import Unit
    visited = {unit_id}
    curr_id = target_sub_unit_id

    while curr_id:
        if curr_id in visited:
            return True
        visited.add(curr_id)
        u_obj = session.query(Unit).get(curr_id)
        if u_obj and u_obj.has_sub_unit and u_obj.sub_unit_id:
            curr_id = u_obj.sub_unit_id
        else:
            break

    return False


def get_available_product_units(product: Any, session: SASession) -> list:
    """
    Returns the list of selectable unit names for a product:
    e.g. ['Coil', 'Meter'] if sub-unit configured, else ['Pcs'].
    """
    main_unit, sub_unit, _ = get_product_unit_info(product, session)
    if sub_unit and sub_unit.strip().lower() != main_unit.strip().lower():
        return [main_unit, sub_unit]
    return [main_unit]


def convert_rate_between_units(rate: float, from_unit: str, to_unit: str, product_or_rate: Any, session: Optional[SASession] = None) -> float:
    """
    Suggests converted rate when user changes unit dropdown.
    Accepts either (rate, from_unit, to_unit, product, session) or (rate, from_unit, to_unit, float_conversion_rate).
    Example: Rate is 6000 per Coil -> switching to Meter yields 60.0 per Meter.
             Rate is 60 per Meter -> switching to Coil yields 6000.0 per Coil.
    """
    if not rate or rate <= 0:
        return rate

    f_u = (from_unit or "").strip().lower()
    t_u = (to_unit or "").strip().lower()

    if f_u == t_u:
        return rate

    if isinstance(product_or_rate, (int, float)):
        conv_rate = float(product_or_rate)
    elif product_or_rate is not None and session is not None:
        _, _, conv_rate = get_product_unit_info(product_or_rate, session)
    else:
        conv_rate = 1.0

    if conv_rate <= 1.0:
        return rate

    if session and hasattr(product_or_rate, 'unit'):
        main_u, sub_u, _ = get_product_unit_info(product_or_rate, session)
        if f_u == (main_u or "").strip().lower():
            return round(rate / conv_rate, 4)
        elif f_u == (sub_u or "").strip().lower():
            return round(rate * conv_rate, 4)

    if "meter" in t_u or "pcs" in t_u or "gram" in t_u:
        return round(rate / conv_rate, 4)
    else:
        return round(rate * conv_rate, 4)
