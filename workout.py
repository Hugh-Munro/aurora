# training_plan_today.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pandas as pd


DEFAULT_PLAN_PATH = Path(
    r"C:\Users\hugom\OneDrive\Desktop\Root\Personal\Fitness\Sports\Exercise\Training Plan.xlsx"
)

@dataclass(frozen=True)
class Workout:
    dt: date
    week: str
    day: str
    run_km: str
    session: str
    gym: str
    checklist: str


def _load_plan(path: Path) -> pd.DataFrame:
    df = pd.read_excel(path, sheet_name=0)
    df.columns = [str(c).strip() for c in df.columns]

    if "Date" not in df.columns:
        raise ValueError(f"Couldn't find a 'Date' column. Found columns: {list(df.columns)}")

    # Your dates are dd/mm/yyyy
    df["Date"] = pd.to_datetime(df["Date"], dayfirst=True, errors="coerce").dt.date
    df = df.dropna(subset=["Date"]).copy()
    return df


def _to_workout(row: pd.Series) -> Workout:
    def g(col: str) -> str:
        if col not in row.index:
            return ""
        v = row[col]
        return "" if pd.isna(v) else str(v).strip()

    return Workout(
        dt=row["Date"],
        week=g("Week"),
        day=g("Day"),
        run_km=g("Run_km"),
        session=g("Session"),
        gym=g("Gym"),
        checklist=g("Checklist"),
    )


def find_workout_for_date(target: date, plan_path: Path = DEFAULT_PLAN_PATH) -> tuple[str, Workout | None]:
    """
    Returns (status, workout):
      - status = "today" if exact match
      - status = "next" if no match, returns next future workout
      - status = "past" if no match and no future, returns most recent past workout
      - status = "none" if sheet has no usable rows
    """
    if not plan_path.exists():
        raise FileNotFoundError(f"Training plan not found: {plan_path}")

    df = _load_plan(plan_path)

    today_rows = df.loc[df["Date"] == target]
    if not today_rows.empty:
        return "today", _to_workout(today_rows.iloc[0])

    future = df.loc[df["Date"] > target].sort_values("Date")
    if not future.empty:
        return "next", _to_workout(future.iloc[0])

    past = df.loc[df["Date"] < target].sort_values("Date")
    if not past.empty:
        return "past", _to_workout(past.iloc[-1])

    return "none", None


def format_workout(w: Workout) -> str:
    lines = [
        f"Date: {w.dt:%d/%m/%Y} ({w.day})",
        f"Week: {w.week}" if w.week else None,
        f"Run_km: {w.run_km}" if w.run_km else None,
        f"Session: {w.session}" if w.session else None,
        f"Gym: {w.gym}" if w.gym else None,
        f"Checklist: {w.checklist}" if w.checklist else None,
    ]
    return "\n".join([ln for ln in lines if ln])


def format_workout_single_line(w: Workout) -> str:
    # Example: Mon 29/12/2025 — Week 1 — Run: 0 km — Rest + mobility (10–15 min) — Gym: Upper gym
    parts = [
        f"{w.day} {w.dt:%d/%m/%Y}",
        f"Week {w.week}" if w.week else None,
        f"Run: {w.run_km.rstrip('0').rstrip('.') if w.run_km else w.run_km} km" if w.run_km != "" else None,
        w.session if w.session else None,
        f"Gym: {w.gym}" if w.gym else None,
        f"Checklist: {w.checklist}" if w.checklist else None,
    ]
    return " — ".join([p for p in parts if p])


def get_workout_of_the_day(plan_path: Path = DEFAULT_PLAN_PATH) -> str:
    status, w = find_workout_for_date(date.today(), plan_path=plan_path)

    if status == "none" or w is None:
        return "No workout found in the training plan."

    prefix = {
        "today": "TODAY",
        "next": "NEXT",
        "past": "MOST RECENT",
    }[status]

    return f"{prefix}: {format_workout_single_line(w)}"