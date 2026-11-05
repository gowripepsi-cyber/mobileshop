"""
Indian Numbering System (Lakhs & Crores) Formatting Utility.
Formats numbers according to the Indian grouping convention:
- Last 3 digits grouped (hundreds)
- Followed by groups of 2 digits (thousands, lakhs, crores)
Example:
  2000000.00   -> 20,00,000.00  (Twenty Lakhs)
  2040150.00   -> 20,40,150.00
  -2040150.00  -> -20,40,150.00 (or -₹20,40,150.00 with symbol=True)
  10000000.00  -> 1,00,00,000.00 (One Crore)
"""

def format_inr(val, decimals=2, symbol=False):
    """
    Formats a number or numeric string into Indian numbering format (Lakhs and Crores).
    :param val: float, int, Decimal, or str representing an amount
    :param decimals: number of decimal digits (default 2)
    :param symbol: whether to include the currency symbol ('₹')
    :return: formatted string
    """
    if val is None or val == "" or val == "-":
        return "-" if not symbol else "₹0.00"
    
    if isinstance(val, str):
        clean_str = val.replace("₹", "").replace(",", "").replace("Rs.", "").replace("Rs", "").strip()
        try:
            fval = float(clean_str)
        except ValueError:
            return val
    else:
        try:
            fval = float(val)
        except (ValueError, TypeError):
            return str(val)

    if abs(fval) < 1e-9:
        is_negative = False
        fval = 0.0
    else:
        is_negative = fval < 0
        fval = abs(fval)

    if decimals > 0:
        s = f"{fval:.{decimals}f}"
        int_part, dec_part = s.split(".")
    else:
        int_part = f"{int(round(fval))}"
        dec_part = ""

    if len(int_part) <= 3:
        formatted_int = int_part
    else:
        last_three = int_part[-3:]
        rem = int_part[:-3]
        groups = []
        while len(rem) > 2:
            groups.append(rem[-2:])
            rem = rem[:-2]
        if rem:
            groups.append(rem)
        groups.reverse()
        formatted_int = ",".join(groups) + "," + last_three

    res = f"{formatted_int}.{dec_part}" if dec_part else formatted_int
    if symbol:
        return f"-₹{res}" if is_negative else f"₹{res}"
    else:
        return f"-{res}" if is_negative else res

