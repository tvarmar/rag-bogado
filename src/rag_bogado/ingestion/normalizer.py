import re


def normalize_text(text: str) -> str:
    lines = []

    for line in text.splitlines():
        normalized_line = re.sub(r"[ \t]+", " ", line).strip()
        lines.append(normalized_line)

    normalized_text = "\n".join(lines)

    return re.sub(r"\n{3,}", "\n\n", normalized_text).strip()
