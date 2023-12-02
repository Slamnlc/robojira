import json
import re
from pathlib import Path


def get_config_file() -> Path:
    return Path.home().joinpath(".robojira.json")


def create_config_file() -> Path:
    file = get_config_file()
    file.unlink(missing_ok=True)
    home_dir = str(Path.home().absolute())
    data = f"""
{
    "jira_username": "", # Your Jira username (email)
    "jira_api_token": "", # Your Jira token (https://id.atlassian.com/manage-profile/security/api-tokens)
    "jira_domain": "", # Your Jira domain
    "working_day_api_token": "", # Your working day api token (https://rapidapi.com/joursouvres-api/api/working-days)"
    "my_country_code": "UA", # Change to your country code
    "users": {{}}, # Fill for manager mode
    "excel_folder": "{home_dir}" # Update if needed
}"""

    file.write_text(data)

    return file


def is_config_file_exists() -> bool:
    return get_config_file().is_file()


def read_config_file() -> dict:
    text = get_config_file().read_text()
    return json.loads(re.sub(r"\s*#\s*.+", "", text))


def validate_config_data(data: dict) -> bool:
    errors = []
    for key in [
        "jira_username",
        "jira_api_token",
        "jira_domain",
        "working_day_api_token",
        "my_country_code",
    ]:
        if key in data:
            if not data[key]:
                errors.append(f"Empty value for '{key}'")
        else:
            errors.append(f"Missing key '{key}'")

    if errors:
        print("\n".join(errors))
        return False
    return True
