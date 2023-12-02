from typing import List

from requests import Session

from .dateutils import get_current_year, last_day_of_month


class WorkingDaysApi:
    def __init__(self, token: str):
        self.base_url = "https://working-days.p.rapidapi.com/1.3"
        self.session = Session()
        self.session.headers.update(
            {
                "X-RapidAPI-Key": token,
                "X-RapidAPI-Host": "working-days.p.rapidapi.com",
            }
        )

    def get_not_working_days(
        self, month: int, country_code: str, year: int = None
    ) -> List[int]:
        url = f"{self.base_url}/list_non_working_days"
        if not year:
            year = get_current_year()
        last_day = last_day_of_month(month, year).day
        month = f"{month:02d}"
        query = {
            "country_code": country_code,
            "start_date": f"{year}-{month}-01",
            "end_date": f"{year}-{month}-{last_day}",
        }

        response = self.session.get(url, params=query)
        if not response.ok:
            raise ValueError(response.content)
        not_working = response.json()["non_working_days"]
        return [int(data["date"].split("-")[-1]) for data in not_working]
