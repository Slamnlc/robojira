colors = {
    "bold": "\033[1m",
    "red": "\033[91m",
    "green": "\033[92m",
}


def color_text(text: str, color: str) -> str:
    return f"{colors[color]}{text}\033[0m"
