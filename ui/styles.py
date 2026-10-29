from ui import theme


def app_stylesheet() -> str:
    family = f"font-family: {theme.font_family()};" if theme.font_family() else ""
    return f"""
QWidget {{
    background-color: {theme.BG};
    color: {theme.TEXT};
    {family}
    font-size: 13px;
}}
QLabel {{ background: transparent; }}
QLabel#card_title {{ font-size: 13px; font-weight: 600; color: {theme.TEXT}; }}
QLabel#card_subtitle {{ font-size: 11px; color: {theme.TEXT_SECONDARY}; }}
QLabel#compact_title {{ font-size: 13px; font-weight: 600; color: {theme.TEXT}; }}
QLabel#compact_subtitle {{ font-size: 11px; color: {theme.TEXT_MUTED}; }}

#top_bar {{
    background: {theme.glass(theme.SURFACE)};
}}
#logo_label {{
    color: {theme.TEXT};
    font-weight: 700;
    font-size: 17px;
    letter-spacing: -0.3px;
}}

QLineEdit {{
    background: {theme.BG};
    border: 1px solid {theme.BORDER};
    border-radius: {theme.radius(20)}px;
    padding: 8px 20px;
    color: {theme.TEXT};
    font-size: 14px;
}}
QLineEdit:focus {{
    border: 1px solid {theme.overlay(0.5)};
    background: {theme.SURFACE};
}}
QLineEdit::placeholder {{ color: {theme.TEXT_MUTED}; }}

#sidebar {{
    background: {theme.SURFACE};
}}
#right_panel {{
    background: {theme.SURFACE};
}}

#player_widget {{
    background: {theme.glass(theme.SURFACE_RAISED)};
    border-top: 1px solid {theme.BORDER};
}}
#player_widget QWidget {{ background: transparent; }}
#song_label {{
    font-weight: 600;
    font-size: 14px;
    color: {theme.TEXT};
}}

QPushButton#play_button {{
    background: {theme.BUTTON_BG};
    border-radius: {theme.radius(20)}px;
    border: none;
}}
QPushButton#play_button:hover  {{ background: {theme.HOVER}; }}
QPushButton#play_button:pressed {{ background: {theme.PRESSED}; }}

QPushButton {{
    background: transparent;
    border: none;
    border-radius: {theme.radius(4)}px;
}}
QPushButton:hover   {{ background: {theme.overlay(0.08)}; }}
QPushButton:pressed {{ background: {theme.overlay(0.14)}; }}

QSlider::groove:horizontal {{
    border: none;
    height: 4px;
    background: {theme.BORDER};
    border-radius: {theme.radius(2)}px;
}}
QSlider::sub-page:horizontal {{
    background: {theme.ACCENT};
    border-radius: {theme.radius(2)}px;
}}
QSlider::handle:horizontal {{
    background: {theme.BUTTON_BG};
    width: 12px;
    height: 12px;
    margin: -4px 0;
    border-radius: {theme.radius(6)}px;
}}
QSlider::handle:horizontal:hover {{ background: {theme.ACCENT}; }}

QScrollArea {{ border: none; background: transparent; }}

QScrollBar:vertical {{ background: transparent; width: 8px; margin: 0; }}
QScrollBar::handle:vertical {{
    background: {theme.overlay(0.15)};
    border-radius: {theme.radius(4)}px;
    min-height: 40px;
    margin: 2px;
}}
QScrollBar::handle:vertical:hover {{ background: {theme.overlay(0.30)}; }}
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {{ height: 0; background: transparent; }}
QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical {{ background: transparent; }}

QScrollBar:horizontal {{ background: transparent; height: 8px; margin: 0; }}
QScrollBar::handle:horizontal {{
    background: {theme.overlay(0.15)};
    border-radius: {theme.radius(4)}px;
    min-width: 40px;
    margin: 2px;
}}
QScrollBar::handle:horizontal:hover {{ background: {theme.overlay(0.30)}; }}
QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal {{ width: 0; background: transparent; }}
QScrollBar::add-page:horizontal,
QScrollBar::sub-page:horizontal {{ background: transparent; }}

#lyrics_list {{
    background: transparent;
    border: none;
    font-size: 17px;
    font-weight: 700;
    outline: none;
}}
#lyrics_list::item {{
    border: none;
    padding: 6px 8px;
    background: transparent;
    color: {theme.TEXT_MUTED};
}}
#lyrics_list::item:selected {{
    background: transparent;
    color: {theme.CHIP_CHECKED};
    font-weight: 700;
    font-size: 19px;
}}

QMenu {{
    background: {theme.SURFACE_RAISED};
    border: 1px solid {theme.BORDER};
    border-radius: {theme.radius(8)}px;
    padding: 6px;
}}
QMenu::item {{
    padding: 9px 20px;
    border-radius: {theme.radius(4)}px;
    color: {theme.TEXT};
}}
QMenu::item:selected {{ background: {theme.overlay(0.10)}; }}
QMenu::separator {{
    height: 1px;
    background: {theme.BORDER};
    margin: 4px 8px;
}}

QSplitter::handle {{ background: transparent; width: 1px; height: 1px; }}
""" + _THEME_EXTRAS.get(theme.current(), lambda: "")()


# vista/7 glass: translucent panes, shine lines, gel handles
def _aero_qss() -> str:
    shine = (f"qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {theme.overlay(0.26)}, stop:0.49 {theme.overlay(0.10)}, "
             f"stop:0.5 {theme.overlay(0.03)}, stop:1 {theme.overlay(0.12)})")
    return f"""
#top_bar {{ border-bottom: 1px solid {theme.overlay(0.30)}; }}
#player_widget {{ border-top: 1px solid {theme.overlay(0.40)}; }}
#sidebar, #right_panel {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {theme.overlay(0.12)}, stop:1 {theme.overlay(0.03)});
    border: 1px solid {theme.overlay(0.18)};
    border-radius: {theme.radius(8)}px;
}}
QLineEdit {{ background: {theme.shade(0.45)}; border: 1px solid {theme.overlay(0.35)}; }}
QLineEdit:focus {{ border: 1px solid {theme.LINK}; background: {theme.shade(0.55)}; }}
QPushButton:hover {{ background: {shine}; border: 1px solid {theme.overlay(0.35)}; }}
QPushButton:pressed {{ background: {theme.shade(0.35)}; border: 1px solid {theme.overlay(0.25)}; }}
QSlider::groove:horizontal {{ height: 6px; border-radius: {theme.radius(3)}px; background: {theme.shade(0.55)};
                             border: 1px solid {theme.overlay(0.20)}; }}
QSlider::sub-page:horizontal {{ background: {theme.gel()}; border-radius: {theme.radius(3)}px; }}
QSlider::handle:horizontal {{
    background: qradialgradient(cx:0.4, cy:0.3, radius:0.8, fx:0.4, fy:0.3, stop:0 {theme.TEXT}, stop:1 {theme.BUTTON_BG});
    border: 1px solid {theme.overlay(0.70)};
    width: 14px; height: 14px; margin: -5px 0; border-radius: {theme.radius(7)}px;
}}
QSlider::handle:horizontal:hover {{ background: {theme.gel()}; }}
QScrollBar::handle:vertical, QScrollBar::handle:horizontal {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {theme.overlay(0.40)}, stop:0.5 {theme.overlay(0.22)},
                                stop:0.51 {theme.overlay(0.10)}, stop:1 {theme.overlay(0.20)});
    border: 1px solid {theme.overlay(0.30)};
}}
QMenu {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {theme.PANEL_TOP}, stop:1 {theme.SURFACE});
    border: 1px solid {theme.overlay(0.40)};
}}
QMenu::item:selected {{ background: {shine}; border: 1px solid {theme.overlay(0.45)}; }}
"""


# pixel terminal: hard corners, neon edges
def _cyberpunk_qss() -> str:
    return f"""
#top_bar {{ border-bottom: 1px solid {theme.ACCENT}; }}
#player_widget {{ border-top: 1px solid {theme.LINK}; }}
#sidebar {{ border-right: 1px solid {theme.BORDER}; }}
#logo_label {{ color: {theme.LINK}; letter-spacing: 2px; }}
QLineEdit {{ border-radius: 0; border: 1px solid {theme.BORDER}; }}
QLineEdit:focus {{ border: 1px solid {theme.LINK}; }}
QPushButton {{ border-radius: 0; }}
QPushButton:hover {{ border: 1px solid {theme.LINK}; }}
QPushButton#play_button {{ border-radius: 0; border: 1px solid {theme.LINK}; }}
QSlider::groove:horizontal, QSlider::sub-page:horizontal {{ border-radius: 0; }}
QSlider::handle:horizontal {{ background: {theme.LINK}; width: 8px; height: 12px; margin: -4px 0; border-radius: 0; }}
QScrollBar::handle:vertical, QScrollBar::handle:horizontal {{ border-radius: 0; background: {theme.SELECTION}; }}
QMenu {{ border-radius: 0; border: 1px solid {theme.LINK}; }}
QMenu::item {{ border-radius: 0; }}
QMenu::item:selected {{ background: {theme.SELECTION}; border-left: 2px solid {theme.ACCENT}; }}
"""


_THEME_EXTRAS = {"aero": _aero_qss, "cyberpunk": _cyberpunk_qss}
