"""German/English strings for the Python side (overlay, tray). The UI has its own table."""
import ctypes

DE = {
    "Pick a model first": "Erst ein Modell wählen",
    "Mic problem": "Mikrofon-Problem",
    "Recording error": "Aufnahmefehler",
    "Saved audio, retry later": "Audio gesichert, später erneut",
    "Heard nothing": "Nichts gehört",
    "Pasted!": "Eingefügt!",
    "Done": "Fertig",
    "Paste failed, see History": "Einfügen fehlgeschlagen, siehe Verlauf",
    "Open Murmur": "Murmur öffnen",
    "Pause dictation": "Diktat pausieren",
    "Open recordings folder": "Aufnahmen-Ordner öffnen",
    "Quit": "Beenden",
    "Murmur: ready": "Murmur: bereit",
    "Murmur: listening…": "Murmur: hört zu…",
    "Murmur: transcribing…": "Murmur: transkribiert…",
    "Murmur: paused": "Murmur: pausiert",
    "Murmur is already running. Look for the little bird in your system tray (bottom right).":
        "Murmur läuft bereits. Such den kleinen Vogel im Infobereich (unten rechts).",
}


def system_lang() -> str:
    try:
        lid = ctypes.windll.kernel32.GetUserDefaultUILanguage()
        return "de" if (lid & 0x3FF) == 0x07 else "en"
    except Exception:
        return "en"


def resolve(setting) -> str:
    return setting if setting in ("de", "en") else system_lang()


def t(msg: str, lang: str) -> str:
    return DE.get(msg, msg) if lang == "de" else msg
