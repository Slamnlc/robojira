import calendar
from datetime import datetime


def last_day_of_month(month: int, year: int) -> datetime:
    _, last_day = calendar.monthrange(year, month)
    return datetime(year, month, last_day)


def get_current_year() -> int:
    return datetime.now().year
