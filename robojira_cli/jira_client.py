import time
from datetime import datetime, timedelta
from functools import partial
from multiprocessing import Pool
from typing import Optional, Dict, List

import httpx

from robojira_cli.helpers.constants import DATE_FORMAT

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
        self.auth = httpx.BasicAuth(login or "", token or "")
        self._user_id = None

    async def get_user_id(self) -> str:
        if not self._user_id:
            myself = (await self.get_myself())["accountId"]
            self._user_id = myself

        return self._user_id

    async def get_myself(self) -> Dict[str, str]:
        response = await self.request("get", "/myself")
        return response.json()

    async def request(self, method: str, url: str, **kwargs) -> httpx.Response:
        async with httpx.AsyncClient(auth=self.auth, base_url=self.base_url) as client:
            response = await client.request(method, url, **kwargs)
            return response

    async def get_user_by_username(self, username: str) -> Optional[dict]:
        url = f"{self.base_url}/user/search"
        params = {"query": username}
        response = await self.request("GET", url, params=params)

        if not response.is_success:
            raise ValueError(response.content)
        data = response.json()
        if data:
            return data[0]

    async def get_report(
        self,
        date: datetime,
        user_id: Optional[str] = None,
    ) -> Dict[str, List[WorklogReport]]:
        if not user_id:
            user_id = await self.get_user_id()
        issue_date = date.strftime(DATE_FORMAT)
        query = f"worklogDate = {issue_date} AND worklogAuthor = {user_id}"
        params = {"jql": query, "maxResults": 100, "fields": "summary,worklog"}
        url = self.base_url + "/search/jql"

        response = await self.request("GET", url, params=params)
        if not response.is_success:
            raise ValueError(response.content)
        issues = []
        for issue in response.json()["issues"]:
            total_time = 0

            fields = issue["fields"]

            if "worklog" in fields:
                for worklog in fields["worklog"]["worklogs"]:
                    if worklog["updateAuthor"]["accountId"] != user_id:
                        continue
                    started = worklog["started"]
                    try:
                        worklog_date = datetime.fromisoformat(started)
                    except ValueError:
                        started = started.split("T")[0]
                        worklog_date = datetime.strptime(started, "%Y-%m-%d")
                    if worklog_date.strftime(DATE_FORMAT) == issue_date:
                        total_time += worklog["timeSpentSeconds"]
            if total_time == 0:
                total_time = await self.get_worklog_time(issue["key"], date, user_id)
            title = f"{issue['key']}: {fields['summary']}"

            issues.append(WorklogReport(title, total_time))

        return {issue_date: issues}

    async def get_worklog_time(
        self, issue_key: str, date: datetime, user_id: str
    ) -> int:
        url = f"{self.base_url}/issue/{issue_key}/worklog"
        start = date.replace(hour=0, minute=0, second=0)
        end = date.replace(hour=23, minute=59, second=59)
        params = {
            "startedAfter": int(start.timestamp() * 1000),
            "startedBefore": int(end.timestamp() * 1000),
        }

        response = await self.request("GET", url, params=params)
        data = response.json()

        total_time = 0
        for worklog in data["worklogs"]:
            if worklog["updateAuthor"]["accountId"] != user_id:
                continue
            total_time += worklog["timeSpentSeconds"]

        return total_time

    async def get_month_report(
        self,
        month_number: int,
        year: int = None,
        user: Optional[str] = None,
        print_report: bool = False,
        short_report: bool = False,
    ) -> Dict[str, List[WorklogReport]]:
        if user:
            user_data = await self.get_user_by_username(user)
            if not user_data:
                print(f"Can't find user with username {user}")
            user_id = user_data["accountId"]
        else:
            user_id = await self.get_user_id()

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
