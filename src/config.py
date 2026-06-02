"""
src/config.py
-------------
Single source of truth for all constants and environment-derived settings.
Call load_config() once in main.py; pass the returned Config object around.
"""
from __future__ import annotations
import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# ── Paths ───────────────────────────────────────────────────────────────────
PASSAGES_FOLDER    = ROOT / "data" / "passages"
PORTFOLIO_PATH     = ROOT / "data" / "portfolio.csv"
TRAINING_PLAN_PATH = ROOT / "data" / "training_plan.csv"

# ── Quote extraction ─────────────────────────────────────────────────────────
PDF_PATTERN    = "Passages - *.pdf"
RECURSIVE      = False
GAP_MULTIPLIER = 1.8

# ── Portfolio ────────────────────────────────────────────────────────────────
INCEPTION_DATE   = "2025-09-15"
HISTORY_START    = "2025-08-01"
TRADING_DAYS     = 252
RISK_FREE_ANNUAL = 0.0
BASE_CCY         = "EUR"

# ── Colours (shared across portfolio + email) ────────────────────────────────
GREEN   = "#0F6E56"
RED     = "#993C1D"
INK     = "#1a1a1a"
MUTE    = "#888888"
CARD_BG = "#f7f7f5"
ASSET_CLASS_COLOURS = {
    "Equities":     "#5DCAA5",
    "Alternatives": "#0F6E56",
    "Fixed Income": "#B0C4B1",
}


@dataclass(frozen=True)
class Config:
    smtp_host: str
    smtp_port: int
    smtp_user: str
    smtp_pass: str
    mail_from: str
    mail_to:   str


def _load_dotenv(dotenv_path: Path) -> None:
    if not dotenv_path.exists():
        return
    for line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        if k and k not in os.environ:
            os.environ[k] = v


def load_config() -> Config:
    """Load .env then read SMTP/mail settings from environment."""
    _load_dotenv(ROOT / ".env")
    missing = [
        k for k in ["SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASS", "MAIL_FROM", "MAIL_TO"]
        if not os.environ.get(k)
    ]
    if missing:
        raise SystemExit(f"Missing settings in .env: {', '.join(missing)}")
    return Config(
        smtp_host = os.environ["SMTP_HOST"],
        smtp_port = int(os.environ["SMTP_PORT"]),
        smtp_user = os.environ["SMTP_USER"],
        smtp_pass = os.environ["SMTP_PASS"],
        mail_from = os.environ.get("MAIL_FROM", os.environ["SMTP_USER"]),
        mail_to   = os.environ["MAIL_TO"],
    )