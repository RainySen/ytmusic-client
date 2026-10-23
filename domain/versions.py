import re


def version_label(tag: str) -> str:
    return re.sub(r"^v\.?", "", (tag or "").strip())


# trailing zeros dropped so 1.4 == 1.4.0
def _parts(version: str) -> tuple[int, ...]:
    parts = [int(n) for n in re.findall(r"\d+", version_label(version))]
    while parts and parts[-1] == 0:
        parts.pop()
    return tuple(parts)


def is_newer(latest: str, current: str) -> bool:
    return bool(_parts(latest)) and bool(_parts(current)) and _parts(latest) > _parts(current)
