from math import floor
import pandas as pd
import numpy as np

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

def badge(text: str, score: float = None):
    """
    Render a colored HTML badge for momentum/volume signals.
    Supports Strong/Weak Buy/Sell, Neutral, plain Buy/Sell, and optional score.
    """
    t = (text or "").upper()
    base = (
        "display:inline-block;padding:2px 8px;"
        "border-radius:12px;font-size:12px;font-weight:600;color:#fff"
    )

    # default gray
    color = "#6b7280"

    # --- Volume-style ---
    if "STRONG BUY" in t:
        color = "#0e7a3b"
    elif "WEAK BUY" in t:
        color = "#1e9e57"
    elif "STRONG SELL" in t:
        color = "#b11226"
    elif "WEAK SELL" in t:
        color = "#d9343a"
    elif "CAUTION" in t:
        color = "#b26a00"

    # --- Momentum composite ---
    elif t == "BUY":
        color = "#16a34a"  # green
    elif t == "SELL":
        color = "#dc2626"  # red
    elif t == "NEUTRAL":
        color = "#6b7280"  # gray

    # Build label text
    label = text
    if score is not None and pd.notna(score):
        try:
            label = f"{text} ({score:.1f})"
        except Exception:
            pass

    return f'<span style="{base};background:{color}">{label}</span>'


def momentum_badge(text: str):
    """
    Wrap 'Buy'/'Sell'/'Neutral' substrings in a colored HTML badge style.
    Works even when text has multiple signals joined by '|'.
    """
    if not text or text.strip() == "—":
        return "—"

    parts = [p.strip() for p in text.split("|")]
    styled = []

    base = (
        "display:inline-block;padding:2px 6px;"
        "border-radius:10px;font-size:12px;font-weight:600;color:#fff;margin-right:2px"
    )

    for p in parts:
        t = p.upper()
        color = "#6b7280"  # default gray

        if "BUY" in t:
            color = "#16a34a"   # green
        if "SELL" in t:
            color = "#dc2626"   # red
        if "NEUTRAL" in t:
            color = "#6b7280"   # gray

        styled.append(f'<span style="{base};background:{color}">{p}</span>')

    return " ".join(styled)



def highlight_vol(num, avg5, strong_mult=2.0, weak_mult=1.5):
    """Format volume compactly, highlight vs 5d avg."""
    import pandas as pd
    if num is None or pd.isna(num):
        return "N/A"

    val_str = dollar_format(num)

    if avg5 is None or pd.isna(avg5) or avg5 <= 0:
        return val_str

    if num >= strong_mult * avg5:
        return f'<span style="color:#0e7a3b;font-weight:600">{val_str}</span>'  # dark green bold
    elif num >= weak_mult * avg5:
        return f'<span style="color:#22c55e">{val_str}</span>'  # green
    elif num <= 0.5 * avg5:
        return f'<span style="color:#b26a00">{val_str}</span>'  # orange
    return val_str

# Map numeric 1/-1 signals to words/symbols
def _buy_sell_from_num(x):
    if pd.isna(x) or x == 0: return None
    return "Buy" if x > 0 else "Sell"

def _present(val):
    """True if val represents a real signal."""
    if isinstance(val, (int, float, np.number)):
        return not pd.isna(val) and val != 0
    if isinstance(val, str):
        return val != "" and not pd.isna(val)
    return val is not None


def format_signal_row(row):
    """Return a list of pretty signal strings for one row, skipping NaN/0."""
    out = []

    def present(v):
        if v is None: 
            return False
        if isinstance(v, (int, float, np.number)):
            return not pd.isna(v) and v != 0
        if isinstance(v, str):
            return v.strip() != "" and v.lower() != "nan"
        return True

    # --- Bollinger ---
    if present(row.get('BB_Buy_Signal')):
        out.append("BB: Buy")
    if present(row.get('BB_Sell_Signal')):
        out.append("BB: Sell")

    # --- KD ---
    if present(row.get('MA_Signal')):
        out.append(f"KD: {row['MA_Signal']}")
    if present(row.get('Solid_Buy')):
        out.append("KD: Solid Buy")
    if present(row.get('Solid_Sell')):
        out.append("KD: Solid Sell")
    if present(row.get('Overbought')):
        out.append("KD: Overbought")
    if present(row.get('Oversold')):
        out.append("KD: Oversold")
    if present(row.get('Divergence')):
        out.append(f"KD: {row['Divergence']}")

    # --- RSI ---
    if present(row.get('RSI_State')):
        out.append(f"RSI: {row['RSI_State']}")
    if present(row.get('RSI_Buy_Signal')):
        out.append("RSI: Buy")
    if present(row.get('RSI_Sell_Signal')):
        out.append("RSI: Sell")
    if present(row.get('RSI_Mid_Cross_Up')):
        out.append("RSI: Mid ↑")
    if present(row.get('RSI_Mid_Cross_Down')):
        out.append("RSI: Mid ↓")

    # --- MACD ---
    if present(row.get('MACD_Signal')):
        out.append("MACD: " + ("Buy" if row['MACD_Signal'] > 0 else "Sell"))

    # --- Composite ---
    if present(row.get('Composite_Signal')):
        if present(row.get('Composite_Score')):
            out.append(f"Composite: {row['Composite_Signal']} ({row['Composite_Score']:.1f})")
        else:
            out.append(f"Composite: {row['Composite_Signal']}")

    return out


pretty_map = {
    'BB_Buy_Signal':    lambda v: "BB: Buy" if v==1 else None,
    'BB_Sell_Signal':   lambda v: "BB: Sell" if v==-1 else None,
    'MA_Signal':        lambda v: f"KD: {v}" if isinstance(v,str) and v else None,
    'Solid_Buy':        lambda v: "KD: Solid Buy" if isinstance(v,str) and v else None,
    'Solid_Sell':       lambda v: "KD: Solid Sell" if isinstance(v,str) and v else None,
    'Overbought':       lambda v: "KD: Overbought" if isinstance(v,str) and v else None,
    'Oversold':         lambda v: "KD: Oversold" if isinstance(v,str) and v else None,
    'Divergence':       lambda v: f"KD: {v}" if isinstance(v,str) and v else None,
    'RSI_State':        lambda v: f"RSI: {v}" if isinstance(v,str) and v else None,
    'RSI_Buy_Signal':   lambda v: "RSI: Buy (exit OS)" if v==1 else None,
    'RSI_Sell_Signal':  lambda v: "RSI: Sell (exit OB)" if v==-1 else None,
    'RSI_Mid_Cross_Up':   lambda v: "RSI: Mid ↑" if v==1 else None,
    'RSI_Mid_Cross_Down': lambda v: "RSI: Mid ↓" if v==-1 else None,
    'KD_Score':         None,  # keep scores out of the text line, or render below table
    'RSI_Score':        None,
    'BB_Score':         None,
    'MACD_Score':       None,
    'Composite_Score':  lambda v: f"Composite Score {v:.1f}" if pd.notna(v) else None,
    'Composite_Signal': lambda v: f"Composite: {v}" if isinstance(v,str) and v else None,
}


if __name__ == "__main__":
    pass

