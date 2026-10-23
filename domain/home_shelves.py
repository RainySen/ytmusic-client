GREETING_KEYS = ("buen día", "buenos días", "buenas tardes", "buenas noches",
                 "good morning", "good afternoon", "good evening", "good night")

CARDS_LAYOUT = "cards"
_CARD_ROW_KEYS = ("descubrimiento diario", "descubrimientos diarios", "daily discover",
                  "lanzamientos", "new releases")


def is_greeting(title: str) -> bool:
    text = title.lower()
    return any(key in text for key in GREETING_KEYS)


def shelf_layout(title: str) -> str | None:
    text = title.lower()
    return CARDS_LAYOUT if any(key in text for key in _CARD_ROW_KEYS) else None
