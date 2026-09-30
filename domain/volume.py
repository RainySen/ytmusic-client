from __future__ import annotations


def gain(level: int) -> int:
    return max(0, min(100, int(level)))
