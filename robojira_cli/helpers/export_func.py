import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from robojira_cli.helpers.classes import WorklogReport


def json_export(data: Dict[str, List[WorklogReport]], folder: Path) -> Path:
    result = {}
    for date, reports in data.items():
        result[date] = "\n".join([report.title for report in reports])
    current_date = datetime.now().strftime("%H_%M")
    file = folder.joinpath(f"robojira_output_{current_date}.json")
    file.write_text(json.dumps(result, indent=4))

    return file
