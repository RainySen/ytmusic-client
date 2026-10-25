from core.i18n import t

GREETING_KEYS = ("buen día", "buenos días", "buenas tardes", "buenas noches",
                 "good morning", "good afternoon", "good evening", "good night",
                 "bom dia", "boa tarde", "boa noite")

CARDS_LAYOUT = "cards"
_CARD_ROW_KEYS = ("descubrimiento diario", "descubrimientos diarios", "daily discover",
                  "lanzamientos", "new releases", "descobertas diárias", "lançamentos")


def is_greeting(title: str) -> bool:
    text = title.lower()
    return any(key in text for key in GREETING_KEYS)


def shelf_layout(title: str) -> str | None:
    text = title.lower()
    return CARDS_LAYOUT if any(key in text for key in _CARD_ROW_KEYS) else None


# (id sent to youtube as the search term, label key)
MOODS = (
    ("Todos", "mood.all"),
    ("Relajación", "mood.relax"),
    ("Actívate", "mood.energize"),
    ("Fiesta", "mood.party"),
    ("Entrenamiento", "mood.workout"),
    ("Romance", "mood.romance"),
    ("Concentración", "mood.focus"),
    ("Tristeza", "mood.sadness"),
)


def mood_label(mood_id: str) -> str:
    return next((t(key) for mid, key in MOODS if mid == mood_id), mood_id)
