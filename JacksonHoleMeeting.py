import pandas as pd
import numpy as np
import yfinance as yf
from scipy import stats
import datetime as dt
import io, base64
import matplotlib.pyplot as plt
from utils import *
from credential import *

# Load historical data for each ticker
def load_data(startdate, enddate, tickers, col=None):
    
    start_ts = pd.to_datetime(startdate)
    end_ts = pd.to_datetime(enddate)

    data = {}

    for t in tickers:
        csv_path = os.path.join(data_path, f"{t}.csv")
        if not os.path.exists(csv_path):
            print(f"[MISSING] {t}: CSV not found at {csv_path}")
            continue
        try:
            df = pd.read_csv(csv_path, parse_dates=["Date"])
            mask = (df["Date"] >= start_ts) & (df["Date"] <= end_ts)
            df = df.loc[mask].copy()
            if col:
                df = df.set_index("Date")
                df = df[col]
                df = df.rename(columns = {df.columns[0]: t})
            data[t] = df
            print(f"[LOADED] {t}: {len(df)} rows")
        except Exception as e:
            print(f"[ERR] {t}: failed to read {csv_path} ({e})")

    return data

# -----------------------------
# 1) Jackson Hole speech dates
# -----------------------------
JH_SPEECH_DATES = pd.to_datetime([
#     "2009-08-21", "2010-08-27", "2011-08-26", "2012-08-31",
#     "2014-08-22", "2016-08-26",
#     "2018-08-24", "2019-08-23", 
    "2020-08-27",
    "2021-08-27", "2022-08-26", "2023-08-25", "2024-08-23",
    "2025-08-22",  
])

# -----------------------------
# 2) Parameters 
# -----------------------------
tickers = ["AAPL","MSFT","AMZN"]   
mkt = "SPY"                        # market proxy for abnormal returns
pre_days = 6                       # window size for CARs
post_days = 6

# -----------------------------
# 3) Download prices
# -----------------------------
start = (JH_SPEECH_DATES.min() - pd.Timedelta(days=60)).strftime("%Y-%m-%d")
end   = (JH_SPEECH_DATES.max() + pd.Timedelta(days=60)).strftime("%Y-%m-%d")
all_tickers = list(set(tickers + [mkt]))

# px = yf.download(all_tickers, start=start, end=end, auto_adjust=True, progress=False)["Close"]
px_dict = load_data(start, end, all_tickers, ['Close'])
px_df = pd.concat(px_dict.values(), axis=1)
rets = px_df.pct_change().dropna()

# -----------------------------
# 4) Build event windows
# -----------------------------
def get_window(df, event_date, pre=pre_days, post=post_days):
    # Use nearest trading day on/after the given date for event day (E0)
    if event_date not in df.index:
        # find the next available trading day
        try:
            event_date = df.index[df.index.get_indexer([event_date], method="bfill")[0]]
        except Exception:
            return None, None
    e0_loc = df.index.get_loc(event_date)
    start_loc = max(0, e0_loc - pre)
    end_loc   = min(len(df.index)-1, e0_loc + post)
    window = df.iloc[start_loc:end_loc+1].copy()
    rel_days = np.arange(start_loc - e0_loc, end_loc - e0_loc + 1)
    window["rel_day"] = rel_days
    return window, event_date

# -----------------------------
# 5) Compute abnormal returns (AR) and CARs
# -----------------------------
def event_study(rets, tickers, mkt, dates, pre=pre_days, post=post_days):
    rows = []
    curves = {}  # for plotting mean CAR curves later
    for d in dates:
        win, e0 = get_window(rets, d, pre, post)
        if win is None: 
            continue

        # market “signal” proxy: SPY event-day return
        mkt_e0_ret = win.loc[win["rel_day"]==0, mkt].values[0]

        for t in tickers:
            w = win[[t, mkt, "rel_day"]].dropna()
            # Abnormal return = stock - market
            w["AR"] = w[t] - w[mkt]
            # CAR by relative day
            w["CAR"] = w["AR"].cumsum()

            # summaries for common windows
            def car_window(lo, hi):
                return w.loc[(w["rel_day"]>=lo)&(w["rel_day"]<=hi), "AR"].sum()

            # t-test of ARs in [-1,+1] around event
            mask_3d = (w["rel_day"]>=-1)&(w["rel_day"]<=1)
            tstat, pval = stats.ttest_1samp(w.loc[mask_3d,"AR"], 0.0, nan_policy="omit")
            

            rows.append({
                "ticker": t,
                "event_date": pd.to_datetime(e0).date(),
                "mkt_event_ret": mkt_e0_ret,
                "AR_E0": w.loc[w["rel_day"]==0, "AR"].values[0],
                "CAR_-1_to_+1": car_window(-1, +1),
                "CAR_-3_to_+3": car_window(-3, +3),
                "CAR_-5_to_+5": car_window(-5, +5),
                "AR_tstat_-1_to_+1": tstat,
                "AR_pval_-1_to_+1": pval,
                "signal": np.sign(mkt_e0_ret)  # +1 dovish (stocks up), -1 hawkish
            })

            # store per-event CAR curve (for later plotting of means)
            key = (t, str(e0.date()))
            curves[key] = w[["rel_day","CAR"]].set_index("rel_day")["CAR"]

    out = pd.DataFrame(rows).sort_values(["ticker","event_date"])
    # cross-event avg sensitivity to the "signal"
    sig_beta = (out.groupby("ticker")
                  .apply(lambda g: np.nan if g["signal"].abs().sum()==0
                         else np.cov(g["AR_E0"], g["signal"], bias=True)[0,1] /
                              np.var(g["signal"]))
                  .rename("beta_to_signal")).reset_index()

    # build mean CAR curve per ticker
    mean_curves = {}
    for t in tickers:
        # align all curves on rel_day and average
        t_curves = [c for (tick, _), c in curves.items() if tick==t]
        if not t_curves: 
            continue
        dfc = pd.concat(t_curves, axis=1).mean(axis=1)
        mean_curves[t] = dfc  # index = rel_day, values = mean CAR

    return out, sig_beta, mean_curves

results, signal_betas, mean_cars = event_study(rets, tickers, mkt, JH_SPEECH_DATES)

# -----------------------------
# 6) Display summary tables
# -----------------------------
summary = (results.groupby("ticker")[["CAR_-1_to_+1","CAR_-3_to_+3","CAR_-5_to_+5"]]
           .mean().rename(columns=lambda c: c+"_avg"))
sig = (results.groupby("ticker")["AR_pval_-1_to_+1"]
       .apply(lambda s: (s<0.05).mean())
       .rename("share_of_events_sig(±1d)"))
final_summary = summary.join(sig).merge(signal_betas, on="ticker", how="left")
final_summary.round(4)

# 1) Map numeric signal to text
signal_map = {-1: "Hawkish (SELL bias)", 0: "Neutral", 1: "Dovish (BUY bias)"}
results["signal_text"] = results["signal"].map(signal_map)

# 2) Counts of events by signal_text (per ticker)
sig_counts = (results
              .groupby(["ticker","signal_text"])
              .size()
              .unstack(fill_value=0)
              .add_prefix("n_"))  # columns like n_Dovish..., n_Hawkish..., n_Neutral

# 3) Mean event-day AR by signal_text (per ticker)
sig_ar_means = (results
                .pivot_table(index="ticker",
                             columns="signal_text",
                             values="AR_E0",
                             aggfunc="mean")
                .add_prefix("AR_E0_mean_"))

# 4) “Alignment” with the signal:
#     +1 events → want AR_E0 > 0 ;  -1 events → want AR_E0 < 0 ; ignore 0 (neutral)
tmp = results[results["signal"]!=0].copy()
alignment = (np.sign(tmp["AR_E0"]) == tmp["signal"])
signal_alignment = alignment.groupby(tmp["ticker"]).mean().rename("signal_alignment_share")

# 5) Net tilt: mean AR_E0 on dovish minus hawkish days (where available)
dov = sig_ar_means.filter(like="Dovish", axis=1).copy()
haw = sig_ar_means.filter(like="Hawkish", axis=1).copy()
# align column names if your signal_text labels differ; using current prefixes:
dov_col = [c for c in dov.columns if "Dovish" in c]
haw_col = [c for c in haw.columns if "Hawkish" in c]
net_tilt = None
if dov_col and haw_col:
    net_tilt = (dov[dov_col[0]] - haw[haw_col[0]]).rename("AR_E0_mean_dovish_minus_hawkish")

# 6) Merge everything into final_summary
augmented = final_summary.copy()
augmented = (augmented
             .merge(sig_counts, left_on="ticker", right_index=True, how="left")
             .merge(sig_ar_means, left_on="ticker", right_index=True, how="left")
             .merge(signal_alignment, left_on="ticker", right_index=True, how="left"))

# Add net tilt if available
if net_tilt is not None:
    augmented = augmented.merge(net_tilt, left_on="ticker", right_index=True, how="left")

# Finally merge in beta_to_signal ONCE
if "beta_to_signal" not in augmented.columns:
    augmented = augmented.merge(signal_betas, on="ticker", how="left")

# 7) (Optional) tidy column order
preferred_cols = [
    "ticker",
    "CAR_-1_to_+1_avg","CAR_-3_to_+3_avg","CAR_-5_to_+5_avg",
    "share_of_events_sig(±1d)",
    "beta_to_signal","signal_alignment_share","AR_E0_mean_dovish_minus_hawkish",
    # Counts:
    *[c for c in augmented.columns if c.startswith("n_")],
    # Means by signal:
    *[c for c in augmented.columns if c.startswith("AR_E0_mean_")],
]
# keep any others at the end
other_cols = [c for c in augmented.columns if c not in preferred_cols]
augmented = augmented[[c for c in preferred_cols if c in augmented.columns] + other_cols]

# This is your enriched summary table:
final_summary = augmented


# -----------------------------
# 8) Per-event detail (optional)
# -----------------------------
print("\nPer-event detail (first few rows):")
results.head(10).round(4)

# Paste this into your notebook/script after you've computed:
# - final_summary (DataFrame)
# - mean_cars (dict: {ticker: Series rel_day->mean CAR})

def aggregate_event_windows(rets, ticker, mkt, dates, pre=5, post=5):
    """
    Aggregate returns across multiple Jackson Hole dates.
    Returns dataframe with mean raw, AR, CAR by rel_day.
    """
    dfs = []
    for d in dates:
        # Assume get_window is available in user's environment; for demo we'll simulate
        try:
            win, e0 = get_window(rets[[ticker,mkt]], pd.to_datetime(d), pre, post)  # type: ignore
        except Exception:
            win, e0 = None, None
        if win is None:
            continue
        win = win.copy()
        win["AR"] = win[ticker] - win[mkt]
        win["CAR"] = win["AR"].cumsum()
        win["event"] = str(e0.date())
        dfs.append(win)
    if not dfs:
        return None
    all_df = pd.concat(dfs)
    mean_df = all_df.groupby("rel_day")[[ticker,"AR","CAR"]].mean()
    return mean_df

def _plot_mean_car(series, title_suffix):
    s = pd.Series(series).sort_index()
    fig = plt.figure(figsize=(5,3.2))
    ax = fig.add_subplot(111)
    ax.plot(s.index, s.values, marker="o")     # no explicit colors per instructions
    ax.axvline(0, linestyle="--")              # E0 marker
    ax.set_title(f"Mean CAR vs. rel_day — {title_suffix}")
    ax.set_xlabel("Relative day (E0 = speech)")
    ax.set_ylabel("Mean CAR")
    return _fig_to_base64(fig)


def _plot_aggregate_barline(ticker, df):
    """
    df: index=rel_day, columns=[ticker, 'AR', 'CAR']
    Bars = mean raw return (%), Lines = mean AR (%) and mean CAR (%)
    """
    df = df.sort_index()
    fig, ax1 = plt.subplots(figsize=(5,3.2))
    ax1.bar(df.index, df[ticker]*100, alpha=0.4, label=f"{ticker} mean return (%)")
    ax1.axvline(0, linestyle="--")  # E0 marker
    ax1.set_xlabel("Relative day (E0 = speech)")
    ax1.set_ylabel(f"{ticker} mean raw return (%)")
    ax2 = ax1.twinx()
    # No explicit colors specified
    ax2.plot(df.index, df["AR"]*100, marker="o", label="Mean AR (%)")
    ax2.plot(df.index, df["CAR"]*100, marker="s", label="Mean CAR (%)")
    # Merge legends
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1+lines2, labels1+labels2, loc="upper left")
    ax1.set_title(f"{ticker}: Average across events (Bar+Line)")
    return _fig_to_base64(fig)


def _fig_to_base64(fig):
    buf = io.BytesIO(); fig.savefig(buf, format="png", bbox_inches="tight", dpi=160); plt.close(fig)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")

def build_jh_email_with_agg(final_summary: pd.DataFrame,
                            mean_cars: dict,
                            mean_agg: dict,
                            title="Jackson Hole Event Study — Email Report (With Aggregate Charts)"):
    css = """
    <style>
      body { font-family: -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif; color:#111; }
      h1 { font-size: 20px; margin: 0 0 12px; }
      h2 { font-size: 16px; margin: 18px 0 8px; }
      p  { line-height: 1.4; margin: 8px 0; }
      .defs { background:#f8f9fb; border:1px solid #e5e7eb; padding:12px; border-radius:8px; }
      table { border-collapse: collapse; width: 100%; font-size: 13px; }
      th, td { border: 1px solid #e5e7eb; padding: 6px 8px; text-align: right; }
      th { background: #f3f4f6; text-align: right; }
      td:first-child, th:first-child { text-align: left; }
      .row { display: table; width: 100%; table-layout: fixed; }
      .col { display: table-cell; vertical-align: top; width: 50%; padding-right: 10px; }
      .chart img { max-width: 300px; height: auto; }
      .caption { color:#555; font-size:12px; margin-top:4px; }
      .hr { height:1px; background:#e5e7eb; border:0; margin:16px 0; }
    </style>
    """
    defs_html = """
    <div class="defs">
    <p><b>AR = Abnormal Return</b><br/>
    where the part of a stock’s return that is not explained by the market (or benchmark)<br/>
    It’s the “excess move” the stock makes, after stripping out general market drift.<br/>
    If Apple is +2% on speech day and SPY is +1%, then AR = +1%.<br/>
    That +1% is plausibly linked to the Jackson Hole signal rather than broad market news.</p>
    <p><b>CAR = Cumulative Abnormal Return</b>, which is the sum (or cumulative product if using log returns) of abnormal returns over an event window.<br/>
    CAR tells you whether the stock systematically drifts up or down across the days before/after the speech.</p>
    <p>AR pinpoints the instantaneous shock (e.g., the market’s reaction exactly at Powell’s speech).<br/>
    CAR shows the persistence of that shock over several days (does it fade, reverse, or compound?).</p>
    </div>
    """
    # Prepare summary table
    fs = final_summary.copy()
    for c in fs.columns:
        if pd.api.types.is_float_dtype(fs[c]):
            fs[c] = fs[c].astype(float).round(4)
    table_html = fs.to_html(index=False, border=0, escape=False)

    # Build per-ticker side-by-side charts
    blocks = []
    tickers = sorted(set(mean_cars.keys()) | set(mean_agg.keys()))
    for t in tickers:
        left_img = _fig_to_base64(plt.figure())  # fallback empty
        right_img = _fig_to_base64(plt.figure())
        if t in mean_cars and mean_cars[t] is not None:
            left_img = _plot_mean_car(mean_cars[t], t)
        if t in mean_agg and mean_agg[t] is not None:
            right_img = _plot_aggregate_barline(t, mean_agg[t])
        block = f"""
        <div class="row">
          <div class="col chart">
            <img src="{left_img}" alt="Mean CAR vs. rel_day — {t}" />
            <div class="caption">Mean CAR vs. rel_day — {t} (dashed line = E0)</div>
          </div>
          <div class="col chart">
            <img src="{right_img}" alt="{t}: Average across events (Bar+Line)" />
            <div class="caption">{t}: Bars = mean raw return; Lines = mean AR & CAR (%, dashed line = E0)</div>
          </div>
        </div>
        """
        blocks.append(block)
    charts_html = "\n".join(blocks) if blocks else "<p>(No charts provided.)</p>"

    html = f"""<!doctype html>
<html>
<head><meta charset="utf-8">{css}</head>
<body>
  <h1>{title}</h1>
  {defs_html}
  <h2>Final Summary</h2>
  <div class="defs">
  <p><b>Column explanations:</b></p>
  <ul>
    <li><b>CAR_-1_to_+1_avg / CAR_-3_to_+3_avg / CAR_-5_to_+5_avg</b>: 
        Avg cumulative abnormal return across events in the given window. 
        Positive = outperformance vs market, Negative = underperformance.</li>
    <li><b>share_of_events_sig(±1d)</b>: Share of events with statistically significant AR in [−1,+1].</li>
    <li><b>beta_to_signal</b>: Sensitivity of AR to event-day “signal” 
        (+1 = dovish/SPY up, −1 = hawkish/SPY down).</li>
    <li><b>n_Dovish / n_Hawkish / n_Neutral</b>: Counts of event types for this stock.</li>
    <li><b>AR_E0_mean_Dovish / AR_E0_mean_Hawkish</b>: Mean event-day AR conditional on signal.</li>
    <li><b>signal_alignment_share</b>: Share of events where AR matched the signal direction.</li>
    <li><b>AR_E0_mean_dovish_minus_hawkish</b>: Net tilt of AR between dovish vs hawkish events.</li>
  </ul>
</div>
  {table_html}
  <hr class="hr"/>
  <h2>Plots</h2>
  {charts_html}
</body>
</html>"""
    return html

# aggregate for 2022–2025
dates_subset = [d for d in JH_SPEECH_DATES if d.year >= 2022]
mean_agg = {}
for t in tickers:
    mean_df = aggregate_event_windows(rets, t, mkt, dates_subset)
    if mean_df is not None:
        # plot_mean_event(t, mean_df)
        mean_agg[t] = mean_df

html_path = os.path.join(report_path , "JacksonHole_Email_With_Aggregates.html")
report_html = build_jh_email_with_agg(final_summary, mean_cars, mean_agg)
email_subject="Jackson Hole Event Study — Report on " + str(datetime.datetime.now())
email_body="<p>Hi, please see attached HTML report.</p>"
send_email(
    email_subject,
    email_body,
    attach_html_str=report_html,                # attaches as JacksonHole_Report.html
    attach_filename="JacksonHoleEventStudy.html",         # optional custom name
)
with open(html_path, "w", encoding="utf-8") as f:
    f.write(report_html)

