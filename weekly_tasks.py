from __future__ import annotations

import shutil
from dataclasses import dataclass
from datetime import date
from pathlib import Path


@dataclass(frozen=True)
class WeeklyTasksResult:
    created: bool
    path: Path
    message: str


# Python's weekday(): Monday=0 ... Saturday=5 ... Sunday=6
SATURDAY = 5


def create_weekly_tasks_file(template_path: Path) -> WeeklyTasksResult:
    """
    Copies template_path into the same folder and names it:
      Weekly_Tasks_YYYYMMDD.xlsx

    Only runs on Saturdays. Does not overwrite if today's file already exists.
    """
    today = date.today()

    if today.weekday() != SATURDAY:
        return WeeklyTasksResult(
            created=False,
            path=template_path,
            message="Not Saturday — no Weekly Tasks file created.",
        )

    if not template_path.exists():
        return WeeklyTasksResult(
            created=False,
            path=template_path,
            message=f"(Weekly Tasks template not found: {template_path})",
        )

    folder = template_path.parent
    today_str = today.strftime("%Y%m%d")
    new_file_path = folder / f"Weekly_Tasks_{today_str}.xlsx"

    if new_file_path.exists():
        return WeeklyTasksResult(
            created=False,
            path=new_file_path,
            message=f"Weekly Tasks file already exists: {new_file_path.name}",
        )

    shutil.copy2(template_path, new_file_path)
    return WeeklyTasksResult(
        created=True,
        path=new_file_path,
        message=f"Created Weekly Tasks file: {new_file_path.name}",
    )
