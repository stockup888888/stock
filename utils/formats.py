from math import floor
import pandas as pd

def dollar_format(num):
    import pandas as pd
    # Handles None or NaN
    if num is None or pd.isna(num):
        return "N/A"
    # Compact formatting
    for unit in ['', 'k', 'M', 'B', 'T']:
        if abs(num) < 1000:
            return f"{num:.0f}{unit}"
        num /= 1000
    return f"{num:.0f}P"  # Very large fallback


def colorize(value, is_percent=False):
    """Return HTML span with green for positive, red for negative."""
    if value in ("N/A", None) or pd.isna(value):
        return value
    try:
        num = float(value.strip('%')) if is_percent else float(value)
    except ValueError:
        return value
    color = "green" if num > 0 else "red" if num < 0 else "black"
    return f"<span style='color:{color}'>{value}</span>"
