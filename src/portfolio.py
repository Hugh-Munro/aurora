"""
src/portfolio.py
----------------
Builds the portfolio block for the daily email.
Public entry point: build_portfolio_html() -> str
  Returns an email-safe HTML fragment for injection into email_builder.py.

Design notes:
  - One batched yf.download call (rate-limit safe), with retry/backoff.
  - Currency is read per-instrument from yfinance, NOT inferred from the
    ticker suffix. '.L' covers USD (IGLN), GBp (SGLN/VWRL) and EUR (EGLN)
    lines simultaneously, so suffix-guessing is unsafe.
  - LSE pence ('GBp') is detected case-sensitively and divided by 100.
  - NAV is built from a per-position EUR value matrix that is forward-filled
    and date-aligned, so missing prints never distort the series.
  - All HTML is <table> + inline styles only: Gmail strips SVG and ignores
    flex / gap / CSS variables.
"""
from __future__ import annotations

import csv
import math
import time
import traceback
from datetime import datetime
from pathlib import Path

import pandas as pd
import yfinance as yf

from src.config import (
    PORTFOLIO_PATH,
    HISTORY_START,
    TRADING_DAYS,
    RISK_FREE_ANNUAL,
    BASE_CCY,
    GREEN,
    RED,
    INK,
    MUTE,
    CARD_BG,
    ASSET_CLASS_COLOURS,
)

# =============================================================================
# CSV
# =============================================================================

def read_portfolio() -> list[dict]:
    """Read the portfolio CSV. Tolerates tab/comma/semicolon delimiters and
    a range of encodings; strips whitespace from keys and values."""
    encodings = ["utf-8-sig", "utf-8", "latin-1", "cp1252"]
    last_err: Exception | None = None
    for enc in encodings:
        try:
            with open(PORTFOLIO_PATH, newline="", encoding=enc) as f:
                sample = f.read(2048)
                f.seek(0)
                try:
                    dialect = csv.Sniffer().sniff(sample, delimiters="\t,;")
                except csv.Error:
                    dialect = csv.excel_tab
                rows = list(csv.DictReader(f, dialect=dialect))
            cleaned = [
                {(k or "").strip(): (v or "").strip() for k, v in r.items()}
                for r in rows
            ]
            if not cleaned:
                raise RuntimeError("Portfolio CSV is empty")
            return cleaned
        except UnicodeDecodeError as e:
            last_err = e
            continue
    raise RuntimeError(f"Could not read portfolio CSV: {last_err}")


# =============================================================================
# CURRENCY
# =============================================================================

def get_instrument_currencies(tickers: list[str]) -> dict[str, str]:
    """Ask yfinance for each instrument's quote currency, preserving exact
    case ('GBp' = pence vs 'GBP' = pounds)."""
    currencies: dict[str, str] = {}
    for t in tickers:
        ccy = None
        try:
            fi  = yf.Ticker(t).fast_info
            ccy = getattr(fi, "currency", None)
            if ccy is None and hasattr(fi, "get"):
                ccy = fi.get("currency")
        except Exception:
            ccy = None
        currencies[t] = ccy if ccy else _fallback_currency(t)
    return currencies


def _fallback_currency(ticker: str) -> str:
    """Last-resort guess ONLY if yfinance fast_info fails.
    A '.L' suffix does NOT reliably mean pence (IGLN.L is USD, SGLN.L is GBp,
    EGLN.L is EUR), so the safe fallback for an unknown .L ticker is plain
    GBP with no divisor -- better to be off by an FX rate than by 100x.
    """
    if ticker.endswith(".L"):
        return "GBP"
    if ticker.endswith((".MU", ".DE", ".F", ".AS", ".PA")):
        return "EUR"
    return "USD"


def normalise_currency(raw_ccy: str) -> tuple[str, float]:
    """Map a yfinance quote currency to (major_currency, divisor).
    CASE-SENSITIVE by design: 'GBp' = pence -> ('GBP', 100.0);
    'GBP' = pounds -> ('GBP', 1.0). yfinance uses exactly this convention.
    """
    c = (raw_ccy or "USD").strip()
    minor = {
        "GBp": ("GBP", 100.0),
        "GBX": ("GBP", 100.0),
        "ZAc": ("ZAR", 100.0),
        "ILA": ("ILS", 100.0),
    }
    return minor.get(c, (c.upper(), 1.0))


# =============================================================================
# MARKET DATA
# =============================================================================

def _download_with_retry(
    tickers: list[str],
    start:   str,
    end:     str,
    retries: int   = 3,
    pause:   float = 2.0,
) -> pd.DataFrame:
    """One batched yf.download call with linear backoff on transient failure.
    Batching ALL tickers into a single call is the key to not getting rate
    limited -- it is one HTTP round-trip, not one per ticker.
    """
    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            raw = yf.download(
                tickers,
                start=start,
                end=end,
                auto_adjust=True,
                actions=False,
                progress=False,
                threads=True,
                group_by="column",
            )
            if raw is not None and not raw.empty:
                return raw
        except Exception as e:
            last_err = e
        time.sleep(pause * (attempt + 1))
    raise RuntimeError(
        f"yfinance download failed after {retries} attempts: {last_err}"
    )


def _extract_close(raw: pd.DataFrame, tickers: list[str]) -> pd.DataFrame:
    """Return a Date-indexed DataFrame of close prices, one column per ticker.
    Handles every column shape yfinance currently emits.
    """
    if isinstance(raw.columns, pd.MultiIndex):
        lvl0 = set(raw.columns.get_level_values(0))
        if "Close" in lvl0:
            close = raw["Close"].copy()
        else:
            close = raw.xs("Close", axis=1, level=1).copy()
    else:
        close = raw[["Close"]].copy()
        close.columns = [tickers[0]]
    close = close[[c for c in tickers if c in close.columns]]
    return close.sort_index()


# =============================================================================
# FX
# =============================================================================

def build_fx_table(
    close:       pd.DataFrame,
    needed_ccys: set[str],
    index:       pd.DatetimeIndex,
) -> pd.DataFrame:
    """DataFrame indexed like `index`, one column per currency, giving units
    of BASE_CCY per 1 unit of that currency. BASE_CCY itself -> 1.0.
    Uses Yahoo's liquid EUR{CCY}=X pairs (CCY per EUR) and inverts them.
    """
    fx = pd.DataFrame(index=index)
    fx[BASE_CCY] = 1.0
    for ccy in needed_ccys:
        if ccy == BASE_CCY:
            continue
        pair = f"{BASE_CCY}{ccy}=X"
        if pair in close.columns:
            series  = close[pair].reindex(index).ffill().bfill()
            fx[ccy] = 1.0 / series
        else:
            fallback = {"GBP": 1.17, "USD": 0.92}.get(ccy, 1.0)
            fx[ccy]  = fallback
    return fx


# =============================================================================
# VALUE MATRIX
# =============================================================================

def build_value_matrix(
    positions:  list[dict],
    close:      pd.DataFrame,
    currencies: dict[str, str],
    fx:         pd.DataFrame,
) -> tuple[pd.DataFrame, list[dict]]:
    """Return (value_df, ok_positions).

    value_df: Date-indexed, one column per ticker, holding the EUR market
    value of that position on each date. Forward-filled then NA-dropped, so
    NAV is never distorted by a missing print on a given day.
    """
    per_position: dict[str, pd.Series] = {}
    ok_positions: list[dict] = []

    for pos in positions:
        t = pos["yf_ticker"]
        if t not in close.columns:
            continue
        price = close[t].dropna()
        if len(price) < 2:
            continue
        shares      = float(pos["shares"])
        major_ccy, divisor = normalise_currency(currencies.get(t, "USD"))
        price_major = price / divisor
        rate        = fx[major_ccy].reindex(price.index).ffill().bfill()
        per_position[t] = price_major * shares * rate
        pos["_major_ccy"] = major_ccy
        ok_positions.append(pos)

    if not per_position:
        raise RuntimeError("No positions had usable price data")

    value_df = pd.DataFrame(per_position).ffill().dropna(how="any")
    return value_df, ok_positions


# =============================================================================
# HTML HELPERS  (Gmail target: table layout, no SVG, no flex)
# =============================================================================

def _sign(v: float) -> str:
    return "+" if v >= 0 else ""


def _pc(v: float) -> str:
    return GREEN if v >= 0 else RED


def _metric_cell(label: str, value: str, colour: str = INK) -> str:
    """One stat box, as a table cell. Used in a 2x2 grid."""
    return (
        f"<td style='width:50%;padding:3px;'>"
        f"<div style='background:{CARD_BG};border-radius:8px;padding:10px;'>"
        f"<p style='font-family:Arial,sans-serif;font-size:10px;color:{MUTE};"
        f"margin:0 0 3px 0;letter-spacing:0.04em;'>{label}</p>"
        f"<p style='font-family:Arial,sans-serif;font-size:16px;font-weight:bold;"
        f"margin:0;color:{colour};'>{value}</p>"
        f"</div></td>"
    )


def attribution_bars(attribution: dict) -> str:
    if not attribution:
        return ""

    max_abs = max(
        max(abs(d["pnl_pct"]) for d in attribution.values()),
        0.5,
    )
    max_h              = 90
    MIN_BAR_FOR_LABEL  = 20
    pos_cells:   list[str] = []
    neg_cells:   list[str] = []
    label_cells: list[str] = []

    for ac, d in attribution.items():
        pct     = d["pnl_pct"]
        pnl_eur = d["pnl_eur"]
        colour  = RED if pct < 0 else ASSET_CLASS_COLOURS.get(ac, GREEN)
        h       = max(3, round(abs(pct) / max_abs * max_h))

        sign_pct = "+" if pct     >= 0 else "-"
        sign_eur = "+" if pnl_eur >= 0 else "-"
        pct_str  = f"{sign_pct}{abs(pct):.2f}%"
        eur_str  = f"{sign_eur}&euro;{abs(pnl_eur):,.2f}"

        text_colour = "#E1F5EE" if colour == GREEN else "#085041"
        eur_inside  = h >= MIN_BAR_FOR_LABEL

        label_cells.append(
            f"<td style='text-align:center;padding:6px 6px 0 6px;width:33%;'>"
            f"<p style='font-family:Arial,sans-serif;font-size:11px;color:{MUTE};"
            f"margin:0;'>{ac}</p>"
            f"</td>"
        )

        if pct >= 0:
            pos_cells.append(
                f"<td style='vertical-align:bottom;text-align:center;"
                f"padding:0 6px;width:33%;'>"
                f"<p style='font-family:Arial,sans-serif;font-size:11px;"
                f"font-weight:bold;color:{colour};margin:0 0 4px 0;'>{pct_str}</p>"
                + (
                    f"<p style='font-family:Arial,sans-serif;font-size:10px;"
                    f"font-weight:bold;color:{colour};margin:0 0 4px 0;'>{eur_str}</p>"
                    if not eur_inside else ""
                )
                + f"<div style='height:{h}px;background:{colour};"
                f"border-radius:3px 3px 0 0;font-size:10px;font-weight:bold;"
                f"color:{text_colour};text-align:center;padding-top:4px;'>"
                + (eur_str if eur_inside else "&nbsp;")
                + f"</div>"
                f"</td>"
            )
            neg_cells.append(
                f"<td style='width:33%;padding:0 6px;height:1px;'>&nbsp;</td>"
            )
        else:
            pos_cells.append(
                f"<td style='width:33%;padding:0 6px;vertical-align:bottom;'>"
                f"<div style='height:{max_h}px;font-size:1px;line-height:1px;'>"
                f"&nbsp;</div>"
                f"</td>"
            )
            neg_cells.append(
                f"<td style='vertical-align:top;text-align:center;"
                f"padding:0 6px;width:33%;'>"
                f"<div style='height:{h}px;background:{colour};"
                f"border-radius:0 0 3px 3px;font-size:1px;line-height:1px;'>"
                f"&nbsp;</div>"
                f"<p style='font-family:Arial,sans-serif;font-size:11px;"
                f"font-weight:bold;color:{colour};margin:4px 0 0 0;'>{pct_str}</p>"
                f"<p style='font-family:Arial,sans-serif;font-size:10px;"
                f"font-weight:bold;color:{colour};margin:2px 0 0 0;'>{eur_str}</p>"
                f"</td>"
            )

    zero = (
        f"<tr><td colspan='3' style='height:1px;background:#e0e0e0;"
        f"font-size:1px;line-height:1px;padding:0;'></td></tr>"
    )

    return (
        f"<table role='presentation' cellpadding='0' cellspacing='0' border='0' "
        f"style='width:100%;border-collapse:collapse;'>"
        f"<tr style='vertical-align:bottom;height:{max_h}px;'>"
        f"{''.join(pos_cells)}</tr>"
        f"{zero}"
        f"<tr style='vertical-align:top;'>{''.join(neg_cells)}</tr>"
        f"<tr>{''.join(label_cells)}</tr>"
        f"</table>"
    )


# =============================================================================
# PUBLIC ENTRY POINT
# =============================================================================

def build_portfolio_html() -> str:
    try:
        # -- Data pipeline ----------------------------------------------------
        positions     = read_portfolio()
        asset_tickers = [p["yf_ticker"] for p in positions]
        currencies    = get_instrument_currencies(asset_tickers)
        needed_ccys   = {normalise_currency(c)[0] for c in currencies.values()}
        fx_tickers    = [f"{BASE_CCY}{c}=X" for c in needed_ccys if c != BASE_CCY]
        all_tickers   = asset_tickers + fx_tickers

        end = datetime.today().strftime("%Y-%m-%d")
        raw = _download_with_retry(all_tickers, start=HISTORY_START, end=end)
        close   = _extract_close(raw, all_tickers)
        missing = [t for t in asset_tickers if t not in close.columns]
        fx      = build_fx_table(close, needed_ccys, close.index)
        value_df, positions = build_value_matrix(positions, close, currencies, fx)
        nav = value_df.sum(axis=1)

        if len(nav) < 2:
            raise RuntimeError("Not enough overlapping price history to build NAV")

        # -- Metrics ----------------------------------------------------------
        nav_today = float(nav.iloc[-1])
        nav_prev  = float(nav.iloc[-2])
        daily_pnl = nav_today - nav_prev
        daily_pct = daily_pnl / nav_prev * 100 if nav_prev else 0.0

        cost = 0.0
        for p in positions:
            pay_ccy = (p.get("purchase_currency") or "EUR").strip().upper()
            rate    = float(fx[pay_ccy].iloc[-1]) if pay_ccy in fx.columns else 1.0
            cost   += float(p["purchase_price"]) * float(p["shares"]) * rate
        itd_pct = (nav_today - cost) / cost * 100 if cost else 0.0

        yr_start = pd.Timestamp(f"{datetime.today().year}-01-01")
        ytd      = nav[nav.index >= yr_start]
        ytd_pct  = (
            (float(ytd.iloc[-1]) - float(ytd.iloc[0])) / float(ytd.iloc[0]) * 100
            if len(ytd) >= 2 else 0.0
        )

        returns = nav.pct_change().dropna()
        if len(returns) > 1 and returns.std() > 0:
            vol    = float(returns.std() * math.sqrt(TRADING_DAYS) * 100)
            rf_daily = RISK_FREE_ANNUAL / TRADING_DAYS
            sharpe = float(
                (returns - rf_daily).mean() / returns.std() * math.sqrt(TRADING_DAYS)
            )
        else:
            vol, sharpe = 0.0, 0.0

        cummax   = nav.cummax()
        drawdown = float(((nav - cummax) / cummax).iloc[-1] * 100)

        # -- Attribution by asset class (today) -------------------------------
        attribution: dict = {}
        prev_row, now_row = value_df.iloc[-2], value_df.iloc[-1]
        for p in positions:
            t  = p["yf_ticker"]
            ac = p.get("asset_class", "Other")
            if t not in value_df.columns:
                continue
            attribution.setdefault(ac, {"pnl_eur": 0.0, "prev_nav": 0.0})
            attribution[ac]["pnl_eur"]  += float(now_row[t] - prev_row[t])
            attribution[ac]["prev_nav"] += float(prev_row[t])
        for ac in attribution:
            prev = attribution[ac]["prev_nav"]
            attribution[ac]["pnl_pct"] = (
                attribution[ac]["pnl_eur"] / prev * 100 if prev else 0.0
            )

        # -- HTML -------------------------------------------------------------
        pnl_bg = "#E1F5EE" if daily_pnl >= 0 else "#FAECE7"
        attrib = attribution_bars(attribution)
        warn   = ""
        if missing:
            warn = (
                f"<p style='font-family:Arial,sans-serif;font-size:10px;"
                f"color:{RED};margin:0 0 8px 0;'>"
                f"\u26a0 No data for: {', '.join(missing)}</p>"
            )

        return f"""{warn}<table role="presentation" cellpadding="0" cellspacing="0" border="0" style="width:100%;border-collapse:collapse;margin-bottom:16px;">
<tr><td>
<div style="background:#ffffff;border:1px solid #e0e0e0;border-radius:12px;padding:20px;">
  <!-- NAV header row -->
  <table role="presentation" cellpadding="0" cellspacing="0" border="0" style="width:100%;border-collapse:collapse;margin-bottom:18px;">
    <tr>
      <td style="vertical-align:top;">
        <p style="font-family:Arial,sans-serif;font-size:10px;color:{MUTE};margin:0 0 2px 0;letter-spacing:0.08em;text-transform:uppercase;">Portfolio NAV</p>
        <p style="font-family:Arial,sans-serif;font-size:24px;font-weight:bold;color:{INK};margin:0 0 4px 0;">&euro;{nav_today:,.2f}</p>
        <span style="font-family:Arial,sans-serif;font-size:12px;font-weight:bold;color:{_pc(daily_pnl)};background:{pnl_bg};padding:2px 8px;border-radius:20px;">{_sign(daily_pnl)}&euro;{daily_pnl:,.2f} ({_sign(daily_pct)}{daily_pct:.2f}%) yesterday</span>
      </td>
      <td style="vertical-align:top;text-align:right;width:120px;">
        <p style="font-family:Arial,sans-serif;font-size:10px;color:{MUTE};margin:0 0 2px 0;letter-spacing:0.04em;text-transform:uppercase;">Drawdown</p>
        <p style="font-family:Arial,sans-serif;font-size:15px;font-weight:bold;color:{_pc(drawdown)};margin:0;">{drawdown:.2f}%</p>
      </td>
    </tr>
  </table>
  <!-- metric boxes: 2x2 grid -->
  <table role="presentation" cellpadding="0" cellspacing="0" border="0" style="width:100%;border-collapse:collapse;margin-bottom:18px;">
    <tr>
      {_metric_cell("ITD RETURN", f"{_sign(itd_pct)}{itd_pct:.2f}%", _pc(itd_pct))}
      {_metric_cell("YTD", f"{_sign(ytd_pct)}{ytd_pct:.2f}%", _pc(ytd_pct))}
    </tr>
    <tr>
      {_metric_cell("REALISED VOL", f"{vol:.2f}%")}
      {_metric_cell("SHARPE 252d", f"{sharpe:.2f}")}
    </tr>
  </table>
  <!-- attribution -->
  <table role="presentation" cellpadding="0" cellspacing="0" border="0" style="width:100%;border-collapse:collapse;border-top:1px solid #f0f0f0;">
    <tr><td style="padding-top:14px;">
        <p style="font-family:Arial,sans-serif;font-size:10px;color:{MUTE};margin:0 0 12px 0;letter-spacing:0.08em;text-transform:uppercase;">Asset Class Attribution</p>
      {attrib}
    </td></tr>
  </table>
</div>
</td></tr>
</table>"""

    except Exception as e:
        traceback.print_exc()
        return (
            f"<p style='font-family:Arial,sans-serif;font-size:13px;"
            f"color:#888888;padding:16px;'>(Portfolio unavailable: {e})</p>"
        )


if __name__ == "__main__":
    print(build_portfolio_html())
