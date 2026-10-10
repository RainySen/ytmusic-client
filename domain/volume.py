from __future__ import annotations

# slider feel like the windows mixer: amplitude = level^1.5
TARGET_EXPONENT = 1.5
# vlc's windows outputs (mmdevice, directsound) cube the volume they get
VLC_CUBE = 3


def gain(level: int) -> int:
    level = max(0, min(100, int(level)))
    return round(100 * (level / 100) ** (TARGET_EXPONENT / VLC_CUBE))
