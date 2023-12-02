from dataclasses import dataclass
from typing import Dict, List

from .dateutils import last_day_of_month


class WorklogReport:
    def __init__(self, title: str, time_in_seconds: int):
        self.title = title
        spent_time = round(time_in_seconds / 60 / 60, 3)
        self.spent_time = f"{spent_time}h"
        self.hours = spent_time
        self.time_in_seconds = time_in_seconds
        self.summary = f"{title}. {self.spent_time}"

    def __repr__(self):
        return self.summary


@dataclass
class UserReport:
    user: str
    reports: Dict[str, List[WorklogReport]]
    not_working_days: List[int]
    month: int
    year: int

    def get_expected_working_hours(self) -> int:
        last_day = last_day_of_month(self.month, self.year).day
        days = [
            day for day in range(last_day) if day not in self.not_working_days
        ]
        return len(days) * 8
