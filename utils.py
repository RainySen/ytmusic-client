import re

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QColor


def parse_curl_headers(text: str) -> str:
    unwrapped = re.sub(r'[\^\\]\s*\n', ' ', text).replace('\n', ' ')
    headers = [m[1] for m in re.findall(r"-H\s+(['\"])(.*?)\1", unwrapped)]
    cookie = re.search(r"(--cookie|-b)\s+(['\"])(.*?)\2", unwrapped)
    if cookie:
        headers.append(f"Cookie: {cookie.group(3)}")
    return "\n".join(headers)


def get_thumbnail_url(song: dict) -> str:
    thumbnails = song.get('thumbnails', [])
    if thumbnails:
        return sorted(thumbnails, key=lambda x: x.get('width', 0))[-1]['url']
    video_id = song.get('videoId', '')
    if video_id:
        return f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"
    return ''


def scale_cover(pixmap: QPixmap, size: int) -> QPixmap:
    scaled = pixmap.scaled(size, size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
    x = (scaled.width() - size) // 2
    y = (scaled.height() - size) // 2
    return scaled.copy(x, y, size, size)


def extract_dominant_color(pixmap: QPixmap, alpha: int = 90) -> QColor:
    """Sample a downscaled version of pixmap to find an average vivid color."""
    if not pixmap or pixmap.isNull():
        return QColor(0, 0, 0, alpha)

    tiny = pixmap.scaled(24, 24, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    img = tiny.toImage()
    w, h = img.width(), img.height()

    r_sum = g_sum = b_sum = sat_w = 0.0

    for y in range(h):
        for x in range(w):
            c = QColor(img.pixel(x, y))
            lightness = c.lightnessF()
            saturation = c.hsvSaturationF()
            # skip near-black, near-white, and grey pixels
            if lightness < 0.10 or lightness > 0.90 or saturation < 0.15:
                continue
            weight = saturation  # vivid colors weigh more
            r_sum += c.redF() * weight
            g_sum += c.greenF() * weight
            b_sum += c.blueF() * weight
            sat_w += weight

    if sat_w > 0:
        r = int((r_sum / sat_w) * 255)
        g = int((g_sum / sat_w) * 255)
        b = int((b_sum / sat_w) * 255)
        # Darken so it works as a tint overlay (not too bright)
        return QColor(r // 2, g // 2, b // 2, alpha)

    return QColor(0, 0, 0, alpha)
