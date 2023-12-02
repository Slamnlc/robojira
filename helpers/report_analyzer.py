from datetime import datetime, timedelta
from typing import Dict, List

from .classes import WorklogReport
from .text_decoration import color_text


def analyze_reports(
    reports: Dict[str, List[WorklogReport]],
    not_working_days: List[int],
    start_date: datetime,
    end_date: datetime,
    user: str,
    print_output: bool = True,
) -> Dict[str, List[str]]:
    delta = timedelta(days=1)
    missing_dates, extra_time, not_enough_time, ok_days = [], [], [], []
    while start_date <= end_date:
        date = start_date.strftime("%Y-%m-%d")
        day = start_date.day
        if date not in reports:
            if day not in not_working_days:
                missing_dates.append(str(day))
        else:
            report = reports[date]
            spent_time = round(
                sum(worklog.time_in_seconds for worklog in report), 2
            )

            spent_hours = round(spent_time / 60 / 60, 2)
            if spent_hours > 8:
                extra_time.append(f"{day}. {spent_hours}h")
            elif spent_hours < 8:
                not_enough_time.append(f"{day}. {spent_hours}h")
            else:
                ok_days.append(str(day))
        start_date += delta

    if print_output:
        print(f"👀Report for {user}👀")
        if ok_days:
            print("Ok days:👌")
            print("\t" + ",".join(ok_days))
        else:
            print(f"❌{color_text('!!!NO OK DAYS!!!', 'red')}❌")

        if missing_dates:
            print("⚠️Missing days:⚠️")
            print("\t" + ",".join(missing_dates))
        else:
            print("👌No missing days👌")

        if extra_time:
            print("🐱‍💻Days with extra time (> 8h)🐱‍💻")
            print("\n".join(extra_time))
        else:
            print(color_text("No days with extra time (> 8h)", "green"))

        if not_enough_time:
            print("🦥Days with not enough time (< 8h)🦥")
            print("\n".join(not_enough_time))
        else:
            print(color_text("No days with not enough time (< 8h)", "green"))

    return {
        "ok_days": ok_days,
        "missing_dates": missing_dates,
        "extra_time": extra_time,
        "not_enough_time": not_enough_time,
    }
