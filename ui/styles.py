APP_STYLESHEET = """
QWidget {
    background-color: #0f0f0f;
    color: #e6e6e6;
    font-family: "YouTube Sans", "Roboto", "Google Sans", "Segoe UI", system-ui;
    font-size: 13px;
}
QLabel { background: transparent; }

#top_bar {
    background: #212121;
    border-bottom: 1px solid #333;
}
#logo_label {
    color: white;
    font-weight: 700;
    font-size: 17px;
    letter-spacing: -0.3px;
}

QLineEdit {
    background: #121212;
    border: 1px solid #383838;
    border-radius: 20px;
    padding: 8px 20px;
    color: white;
    font-size: 14px;
}
QLineEdit:focus {
    border: 1px solid rgba(255,255,255,0.5);
    background: #1a1a1a;
}
QLineEdit::placeholder { color: #717171; }

#sidebar {
    background: #212121;
    border-right: 1px solid #333;
}
#right_panel {
    background: #212121;
    border-left: 1px solid #333;
}

#player_widget {
    background: #282828;
    border-top: 1px solid #3a3a3a;
}
#player_widget QWidget { background: transparent; }
#song_label {
    font-weight: 600;
    font-size: 14px;
    color: #ffffff;
}

QPushButton#play_button {
    background: #ffffff;
    border-radius: 20px;
    border: none;
}
QPushButton#play_button:hover  { background: #e0e0e0; }
QPushButton#play_button:pressed { background: #c8c8c8; }

QPushButton {
    background: transparent;
    border: none;
    border-radius: 4px;
}
QPushButton:hover   { background: rgba(255,255,255,0.08); }
QPushButton:pressed { background: rgba(255,255,255,0.14); }

QSlider::groove:horizontal {
    border: none;
    height: 4px;
    background: #3a3a3a;
    border-radius: 2px;
}
QSlider::sub-page:horizontal {
    background: #FF0033;
    border-radius: 2px;
}
QSlider::handle:horizontal {
    background: white;
    width: 12px;
    height: 12px;
    margin: -4px 0;
    border-radius: 6px;
}
QSlider::handle:horizontal:hover { background: #FF0033; }

QScrollArea { border: none; background: transparent; }

QScrollBar:vertical { background: transparent; width: 8px; margin: 0; }
QScrollBar::handle:vertical {
    background: rgba(255,255,255,0.15);
    border-radius: 4px;
    min-height: 40px;
    margin: 2px;
}
QScrollBar::handle:vertical:hover { background: rgba(255,255,255,0.30); }
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical { height: 0; background: transparent; }
QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical { background: transparent; }

QScrollBar:horizontal { background: transparent; height: 8px; margin: 0; }
QScrollBar::handle:horizontal {
    background: rgba(255,255,255,0.15);
    border-radius: 4px;
    min-width: 40px;
    margin: 2px;
}
QScrollBar::handle:horizontal:hover { background: rgba(255,255,255,0.30); }
QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal { width: 0; background: transparent; }
QScrollBar::add-page:horizontal,
QScrollBar::sub-page:horizontal { background: transparent; }

#lyrics_list {
    background: transparent;
    border: none;
    font-size: 15px;
    outline: none;
}
#lyrics_list::item {
    border: none;
    padding: 6px 8px;
    background: transparent;
    color: #888;
}
#lyrics_list::item:selected {
    background: transparent;
    color: white;
    font-weight: 700;
    font-size: 16px;
}

QMenu {
    background: #282828;
    border: 1px solid #383838;
    border-radius: 8px;
    padding: 6px;
}
QMenu::item {
    padding: 9px 20px;
    border-radius: 4px;
    color: #e0e0e0;
}
QMenu::item:selected { background: rgba(255,255,255,0.10); }
QMenu::separator {
    height: 1px;
    background: #383838;
    margin: 4px 8px;
}

QSplitter::handle { background: #333; width: 1px; height: 1px; }
"""
