BG = "#0f0f0f"
SURFACE = "#212121"
SURFACE_RAISED = "#282828"
BORDER = "#3a3a3a"
TEXT = "#f1f1f1"
TEXT_SECONDARY = "#aaaaaa"
TEXT_MUTED = "#717171"
ACCENT = "#ff0033"
LINK = "#3ea6ff"
DANGER = "#ff4e45"

SCRIM = "rgba(0, 0, 0, 0.6)"


# tema botones
def button_qss(kind: str = "primary", height: int = 40) -> str:
    palette = {
        "primary": ("#ffffff", "#0f0f0f", "#e6e6e6", "#cccccc"),
        "tonal": ("rgba(255,255,255,0.12)", "#ffffff", "rgba(255,255,255,0.20)", "rgba(255,255,255,0.26)"),
        "text": ("transparent", LINK, "rgba(62,166,255,0.12)", "rgba(62,166,255,0.20)"),
    }[kind]
    background, color, hover, pressed = palette
    return f"""
        QPushButton {{ background: {background}; color: {color}; border: none; border-radius: {height // 2}px;
                       padding: 0 22px; min-height: {height}px; font-size: 14px; font-weight: 600; }}
        QPushButton:hover {{ background: {hover}; }}
        QPushButton:pressed {{ background: {pressed}; }}
        QPushButton:disabled {{ background: rgba(255,255,255,0.08); color: rgba(255,255,255,0.35); }}
        QPushButton:focus {{ outline: none; }}
    """


def input_qss(selector: str) -> str:
    return f"""
        {selector} {{ background: transparent; color: {TEXT}; border: 2px solid rgba(255,255,255,0.22);
                      border-radius: 10px; padding: 11px 14px; font-size: 15px;
                      selection-background-color: {LINK}; selection-color: #0f0f0f; }}
        {selector}:focus {{ border: 2px solid {LINK}; background: transparent; }}
    """


def chip_qss(selected: bool) -> str:
    if selected:
        return """
            QPushButton { background: #ffffff; color: #0f0f0f; border: none; border-radius: 8px;
                          padding: 8px 16px; font-size: 14px; font-weight: 600; }
        """
    return """
        QPushButton { background: rgba(255,255,255,0.10); color: #f1f1f1; border: none; border-radius: 8px;
                      padding: 8px 16px; font-size: 14px; font-weight: 500; }
        QPushButton:hover { background: rgba(255,255,255,0.18); }
    """
