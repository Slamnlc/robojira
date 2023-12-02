import calendar
from datetime import datetime, timedelta
from typing import List

import xlsxwriter
from xlsxwriter.utility import xl_rowcol_to_cell

from helpers.classes import UserReport
from helpers.dateutils import last_day_of_month
from helpers.report_analyzer import analyze_reports


class ExcelExporter:
    def __init__(self, user_reports: List[UserReport], month: int, year: int):
        key = datetime.now().strftime("%H_%M")
        self.month_name = calendar.month_name[month]
        self.month = month
        self.year = year
        self.wb = xlsxwriter.Workbook(
            f"Jira_report_{self.month_name}_{key}.xlsx"
        )
        self.summary_ws = self.wb.add_worksheet("Summary")
        self.reports = user_reports
        self._formats = {}
        self.create_formats()
        self.fill_summary_page()
        self.wb.close()

    def create_formats(self):
        center = {"align": "center", "valign": "vcenter"}
        border = {"border": 1}
        self._formats["bold"] = self.wb.add_format({"bold": True})
        self._formats["bold_center"] = self.wb.add_format(
            {**center, "bold": True}
        )
        self._formats["center"] = self.wb.add_format(center)
        self._formats["center_border"] = self.wb.add_format(
            {**center, **border}
        )
        self._formats["center_border_bold"] = self.wb.add_format(
            {**center, **border, "bold": True}
        )
        self._formats["green_bg"] = self.wb.add_format(
            {**center, **border, "bg_color": "#008000"}
        )
        self._formats["red_bg"] = self.wb.add_format(
            {**center, **border, "bg_color": "#D2042D"}
        )
        self._formats["overtime_bg"] = self.wb.add_format(
            {**center, **border, "bg_color": "#355E3B"}
        )
        self._formats["not_enough_bg"] = self.wb.add_format(
            {**center, **border, "bg_color": "#90EE90"}
        )
        self._formats["holiday_bg"] = self.wb.add_format(
            {**center, **border, "bg_color": "#7DF9FF"}
        )
        self._formats["border"] = self.wb.add_format({"border": 1})

    def format(self, name: str):
        return self._formats[name]

    def fill_summary_page(self):
        ws = self.summary_ws
        ws.merge_range(1, 0, 2, 0, "Employees", self.format("bold_center"))

        delta = timedelta(days=1)
        start_date = datetime(self.year, self.month, 1)
        end_date = last_day_of_month(self.month, self.year)
        column = 1
        user_added = False

        while start_date <= end_date:
            self.create_header(column, start_date)

            date = start_date.strftime("%Y-%m-%d")
            row = 3
            for user_report in self.reports:
                self.fill_user_row(user_report, row, column, user_added, date)
                row += 1

            column += 1
            user_added = True
            start_date += delta

        self.populate_total_info(column)

        ws.autofit()
        self.write_report_header(end_date)

    def create_user_page(self, user_report: UserReport) -> str:
        ws = self.wb.add_worksheet(user_report.user)
        ws.write(0, 0, "Not working days", self.format("bold"))
        days = [str(dt) for dt in user_report.not_working_days]
        ws.write(0, 1, ",".join(days))

        row = 1
        bold = self.format("bold")
        center = self.format("center")
        for date, reports in user_report.reports.items():
            ws.write(row, 0, date, bold)
            row += 1
            for report in reports:
                ws.write(row, 1, report.title)
                ws.write(row, 2, report.spent_time, center)
                row += 1

        start_date = datetime(self.year, self.month, 1)
        end_date = last_day_of_month(self.month, self.year)

        analyze = analyze_reports(
            user_report.reports,
            user_report.not_working_days,
            start_date,
            end_date,
            user_report.user,
            False,
        )

        for key, value in analyze.items():
            ws.write(row, 0, key.replace("_", " ").capitalize(), bold)
            if key in ["missing_dates", "ok_days"]:
                ws.write(row, 1, ", ".join(value))
            else:
                for val in value:
                    ws.write(row + 1, 1, val)
                    row += 1
            row += 1

        ws.autofit()
        return f"internal:{ws.name}!A1"

    def create_header(self, column: int, date: datetime):
        self.summary_ws.write(1, column, date.day, self.format("center_border"))
        self.summary_ws.write(
            2, column, date.strftime("%a"), self.format("center_border")
        )

    def fill_user_row(
        self,
        user_report: UserReport,
        row: int,
        column: int,
        user_added: bool,
        date: str,
    ) -> int:
        ws = self.summary_ws
        if not user_added:
            ws.write_url(
                row,
                0,
                self.create_user_page(user_report),
                string=user_report.user,
            )
        if date in user_report.reports:
            reports = user_report.reports[date]
            spent_time = round(
                sum(worklog.time_in_seconds for worklog in reports), 2
            )
            spent_hours = round(spent_time / 60 / 60, 2)

            if spent_hours > 8:
                cell_format = self.format("overtime_bg")
            elif spent_hours < 8:
                cell_format = self.format("not_enough_bg")
            else:
                cell_format = self.format("green_bg")
            ws.write(row, column, spent_hours, cell_format)
            return spent_time

        else:
            day = int(date.split("-")[-1])
            if day in user_report.not_working_days:
                cell_format = self.format("holiday_bg")
            else:
                cell_format = self.format("red_bg")
            ws.write(row, column, "", cell_format)

            return 0

    def populate_total_info(self, column):
        ws = self.summary_ws
        row = 3
        center_border = self.format("center_border")
        center_border_bold = self.format("center_border_bold")
        ws.write(row - 1, column, "Total WH", center_border_bold)
        ws.write(row - 1, column + 1, "Expected WH", center_border_bold)
        ws.write(row - 1, column + 2, "Difference", center_border_bold)
        for user_report in self.reports:
            start_cell = xl_rowcol_to_cell(row, 1)
            end_cell = xl_rowcol_to_cell(row, column - 1)
            ws.write_formula(
                row, column, f"=SUM({start_cell}:{end_cell})", center_border
            )
            ws.write(
                row,
                column + 1,
                user_report.get_expected_working_hours(),
                center_border,
            )
            diff_real = xl_rowcol_to_cell(row, column + 1)
            diff_expected = xl_rowcol_to_cell(row, column)
            ws.write_formula(
                row, column + 2, f"={diff_expected}-{diff_real}", center_border
            )
            row += 1

    def write_report_header(self, end_date: datetime):
        last_day = end_date.day
        text = (
            f"Report period from 01 {self.month_name} {self.year} "
            f"to {last_day} {self.month_name} {self.year}"
        )
        self.summary_ws.merge_range(
            0, 1, 0, last_day + 3, text, self.format("bold_center")
        )
