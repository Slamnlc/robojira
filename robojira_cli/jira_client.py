from datetime import datetime, timedelta
from functools import partial
from multiprocessing import Pool
from typing import Optional, Dict, List

from requests import Session

try:
    from robojira_cli.helpers.classes import WorklogReport
    from robojira_cli.helpers.dateutils import (
        last_day_of_month,
        get_current_year,
    )
    from robojira_cli.helpers.text_decoration import color_text
except ImportError:
    from helpers.classes import WorklogReport
    from helpers.dateutils import last_day_of_month, get_current_year
    from helpers.text_decoration import color_text


class JiraApi:
    def __init__(self, domain: str, login: str, token: str):
        self.base_url = f"https://{domain}.atlassian.net/rest/api/3"
        self.session = Session()
        self.session.auth = (login, token)
        self.session.headers.update({"Content-Type": "application/json"})
        self.myself = self.get_myself()
        self.user_id = self.myself["accountId"]

    def get_myself(self) -> dict:
        return self.session.get(f"{self.base_url}/myself").json()

    def get_user_by_username(self, username: str) -> Optional[dict]:
        url = f"{self.base_url}/user/search"
        params = {"query": username}
        response = self.session.get(url, params=params)
        if not response.ok:
            raise ValueError(response.content)
        data = response.json()
        if data:
            return data[0]

    def get_report(
        self,
        date: datetime,
        user_id: Optional[str] = None,
    ) -> Dict[str, WorklogReport]:
        if not user_id:
            user_id = self.user_id
        issue_date = date.strftime("%Y-%m-%d")
        query = f"worklogDate = {issue_date} AND worklogAuthor = {user_id}"
        params = {"jql": query, "maxResults": 100, "fields": "summary,worklog"}
        url = self.base_url + "/search"
        response = self.session.get(url, params=params)
        if not response.ok:
            raise ValueError(response.content)
        issues = []
        for issue in response.json()["issues"]:
            total_time = 0

            fields = issue["fields"]

            if "worklog" in fields:
                for worklog in fields["worklog"]["worklogs"]:
                    if worklog["updateAuthor"]["accountId"] != user_id:
                        continue
                    worklog_date = datetime.fromisoformat(worklog["started"])
                    if worklog_date.strftime("%Y-%m-%d") == issue_date:
                        total_time += worklog["timeSpentSeconds"]
                if total_time == 0:
                    total_time = self.get_worklog_time(
                        issue["key"], date, user_id
                    )
            title = f'{issue["key"]}: {fields["summary"]}'

            issues.append(WorklogReport(title, total_time))

        return {issue_date: issues}

    def get_worklog_time(
        self, issue_key: str, date: datetime, user_id: str
    ) -> int:
        url = f"{self.base_url}/issue/{issue_key}/worklog"
        start = date.replace(hour=0, minute=0, second=0)
        end = date.replace(hour=23, minute=59, second=59)
        params = {
            "startedAfter": int(start.timestamp() * 1000),
            "startedBefore": int(end.timestamp() * 1000),
        }

        response = self.session.get(url, params=params).json()
        total_time = 0
        for worklog in response["worklogs"]:
            if worklog["updateAuthor"]["accountId"] != user_id:
                continue
            total_time += worklog["timeSpentSeconds"]

        return total_time

    def get_month_report(
        self,
        month_number: int,
        year: int = None,
        user: Optional[str] = None,
        print_report: bool = False,
        short_report: bool = False,
    ) -> Dict[str, List[WorklogReport]]:
        if user:
            user_data = self.get_user_by_username(user)
            if not user_data:
                print(f"Can't find user with username {user}")
            user_id = user_data["accountId"]
        else:
            user_id = self.user_id

        if not year:
            year = get_current_year()

        start_date = datetime(year, month_number, 1)
        end_date = last_day_of_month(month_number, year)

        delta = timedelta(days=1)

        issues: Dict[str, List[WorklogReport]] = {}
        dates = []
        func = partial(self.get_report, user_id=user_id)

        while start_date <= end_date:
            dates.append(start_date)
            start_date += delta

        with Pool() as pool:
            reports = pool.map(func, dates)

        for report in reports:
            for key, value in report.items():
                if value:
                    issues[key] = value

        if print_report:
            print("📄 User work 📄")
            for key, value in issues.items():
                print(color_text(f"{key}:", "bold"))
                for report in value:
                    if short_report:
                        print(f"\t{report.title}")
                    else:
                        print(f"\t{report.summary}")
                print("")
        return issues
