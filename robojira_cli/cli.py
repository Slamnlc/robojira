from __future__ import annotations

import argparse
import calendar
import json
from datetime import datetime

from .config_helper import (
    is_config_file_exists,
    create_config_file,
    read_config_file,
    validate_config_data, get_config_file,
)
from .excel_export import ExcelExporter
from .helpers.classes import UserReport
from .helpers.dateutils import get_current_year, last_day_of_month
from .helpers.report_analyzer import analyze_reports
from .helpers.working_days import WorkingDaysApi
from .jira_client import JiraApi

current_year = get_current_year()

robojira_parser = argparse.ArgumentParser(
    description="Script to work with Jira worklog"
)

robojira_parser.add_argument(
    "-m", "--month", help="Month number", type=int, required=True
)

robojira_parser.add_argument(
    "-y",
    "--year",
    help=f"Report year. Default: {current_year}",
    type=int,
    default=current_year,
)

__execution_modes = ["manager", "self"]

robojira_parser.add_argument(
    "--mode",
    help=f"Script execution mode: {__execution_modes}",
    type=str,
    default="self",
)

robojira_parser.add_argument(
    "-c",
    "--show-config",
    help="Display config file path and its content",
    type=bool,
    action="store_true",
    default=False,
)


def main():
    if not is_config_file_exists():
        file = create_config_file()
        print("Config file created, please, fill it")
        print(str(file.absolute()))
        return

    config_data = read_config_file()
    if not validate_config_data(config_data):
        return

    args = robojira_parser.parse_args()
    if args.mode not in __execution_modes:
        print(f"--mode should be on of {__execution_modes}")
        return

    if args.show_config:
        print(str(get_config_file().absolute()))
        print(json.dumps(config_data, indent=4))
        return

    user = config_data["jira_username"]
    token = config_data["jira_api_token"]
    jira_domain = config_data["jira_domain"]
    user_country_code = config_data["my_country_code"]

    working_day_token = config_data["working_day_api_token"]

    month = args.month
    year = args.year

    month_name = calendar.month_name[month]

    working_day_api = WorkingDaysApi(working_day_token)
    jira_api = JiraApi(jira_domain, user, token)

    if args.mode == "self":
        print("🤓 Running in self-check mode 🤓")
        not_working_days = working_day_api.get_not_working_days(
            month, user_country_code, year
        )
        print(f"Not working day for {month_name} ({month})")
        print("\t" + ", ".join([str(dt) for dt in not_working_days]))
        reports = jira_api.get_month_report(month, year, print_report=True)
        start_date = datetime(year, month, 1)
        end_date = last_day_of_month(month, year)
        analyze_reports(
            reports,
            not_working_days,
            start_date,
            end_date,
            user,
            print_output=True,
        )
    elif args.mode == "manager":
        if "users" not in config_data:
            print("'users' key is missing in config file")
            return
        users = config_data["users"]
        if not isinstance(users, dict):
            print("'users' should be a dict")
            return
        user_reports = []

        for code, users in users.items():
            not_working_days = working_day_api.get_not_working_days(month, code)

            print(f"Not working day for {month_name} ({month})")
            print("\t" + ", ".join([str(dt) for dt in not_working_days]))

            for user in users:
                reports = jira_api.get_month_report(month, user=user)
                start_date = datetime(year, month, 1)
                end_date = last_day_of_month(month, year)
                analyze_reports(
                    reports,
                    not_working_days,
                    start_date,
                    end_date,
                    user,
                    print_output=False,
                )

                user_reports.append(
                    UserReport(user, reports, not_working_days, month, year)
                )

        ExcelExporter(user_reports, month, year)


if __name__ == "__main__":
    main()
