from __future__ import annotations
import shutil
from dataclasses import dataclass
from datetime import date
from pathlib import Path


@dataclass(frozen=True)
class DailyTasksResult:
    created: bool
    path: Path
    message: str


def create_daily_tasks_file(template_path: Path) -> DailyTasksResult:
    """
    Copies template_path into the same folder and names it:
      Daily_Tasks_YYYYMMDD.xlsx

    Does not overwrite if today's file already exists.
    """
    if not template_path.exists():
        return DailyTasksResult(
            created=False,
            path=template_path,
            message=f"(Daily Tasks template not found: {template_path})",
        )

    folder = template_path.parent
    today_str = date.today().strftime("%Y%m%d")
    new_file_path = folder / f"Daily_Tasks_{today_str}.xlsx"

    if new_file_path.exists():
        return DailyTasksResult(
            created=False,
            path=new_file_path,
            message=f"Daily Tasks file already exists: {new_file_path.name}",
        )

    shutil.copy2(template_path, new_file_path)
    return DailyTasksResult(
        created=True,
        path=new_file_path,
        message=f"Created Daily Tasks file: {new_file_path.name}",
    )
