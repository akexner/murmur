# 🪶 Murmur

**English** · [Deutsch](#deutsch)

Free voice typing for Windows. Hold a key, speak, let go. Your words appear wherever your cursor is.
Speech recognition runs **locally on your PC** with open-source Whisper ([faster-whisper](https://github.com/SYSTRAN/faster-whisper)). No account, no cloud, no subscription.

## Features
- Push-to-talk (default `Ctrl`+`Win`) or press-to-toggle, pastes into any app
- Floating status pill and tray icon with an animated mascot, Murmi
- English and German interface; dictation language auto-detected (many more languages supported)
- Custom dictionary (names, jargon) and replacements; voice commands ("new line", "new paragraph" / "neue Zeile", "neuer Absatz"); filler-word removal
- **Audio is never lost:** recordings stream to disk while you speak; interrupted ones are recovered on next launch; failed transcriptions keep their audio with a retry button; deleting moves clips to "Recently deleted" for 14 days; starred clips never expire
- **Offline / office mode:** the app itself refuses every non-local network connection, model downloads are disabled, models are imported from a folder, USB stick or network drive
- **Optional text polish with a local [Ollama](https://ollama.com) model** (off by default): tidies punctuation and wording, keeps your line breaks, talks only to `127.0.0.1`, and falls back to your original text on any problem
- Models: Tiny, Base, Small (default), Medium, Turbo, downloaded once

## Install (Windows 10/11)
1. Download `Murmur-Windows.zip` from [Releases](../../releases/latest), unzip anywhere.
2. Run `Murmur.exe` (Windows SmartScreen may warn because the app is not code-signed: *More info → Run anyway*).
3. Pick a model (Small is a good start), click into any text box, hold `Ctrl`+`Win`, speak.

Data lives in `%APPDATA%\Murmur` (recordings, history, settings).

## Offline / office use
Download a model once on any PC, copy `%APPDATA%\Murmur\models` to a USB stick or share, then in *Settings → Offline / office mode* import it (or point Murmur at the folder) and switch offline mode on.

## Build from source
```powershell
python -m venv C:\mvenv
C:\mvenv\Scripts\pip install -r requirements.txt
C:\mvenv\Scripts\python -m murmur --show      # run
powershell -ExecutionPolicy Bypass -File build.ps1   # build Murmur-Windows.zip
```

## Notes
CPU only (int8). Murmur sends no audio or text anywhere; the only network access is the optional one-time model download from huggingface.co. Whether a given setup meets professional-secrecy or data-protection rules is for you to assess.

---

<a name="deutsch"></a>
# 🪶 Murmur (Deutsch)

Kostenloses Diktieren für Windows. Taste halten, sprechen, loslassen, und der Text erscheint dort, wo dein Cursor steht.
Die Spracherkennung läuft **lokal auf deinem PC** mit Open-Source-Whisper (faster-whisper). Kein Konto, keine Cloud, kein Abo.

## Funktionen
- Push-to-talk (Standard `Strg`+`Win`) oder Umschalten, Einfügen in jedes Programm
- Schwebende Statusanzeige und Tray-Symbol mit animiertem Maskottchen Murmi
- Deutsche und englische Oberfläche; Diktiersprache wird automatisch erkannt
- Eigenes Wörterbuch (Namen, Fachbegriffe), Ersetzungen, Sprachbefehle („neue Zeile“, „neuer Absatz“), Füllwörter entfernen
- **Audio geht nicht verloren:** Aufnahmen werden schon beim Sprechen auf die Platte geschrieben; unterbrochene werden beim nächsten Start wiederhergestellt; bei fehlgeschlagener Transkription bleibt das Audio mit „Neu transkribieren“-Knopf erhalten; Löschen verschiebt Clips 14 Tage nach „Zuletzt gelöscht“; mit Stern markierte Clips laufen nie ab
- **Offline-/Kanzlei-Modus:** Die App verweigert selbst jede nicht-lokale Netzwerkverbindung, Modell-Downloads sind aus, Modelle kommen per Import aus Ordner, USB-Stick oder Netzlaufwerk
- **Optionale Textglättung mit einem lokalen [Ollama](https://ollama.com)-Modell** (standardmäßig aus): glättet Zeichensetzung und Formulierung, behält deine Zeilenumbrüche, spricht nur mit `127.0.0.1` und nutzt bei jedem Problem deinen Originaltext
- Modelle: Tiny, Base, Small (Standard), Medium, Turbo, einmalig geladen

## Installation (Windows 10/11)
1. `Murmur-Windows.zip` von den [Releases](../../releases/latest) laden und entpacken.
2. `Murmur.exe` starten (SmartScreen warnt evtl., weil die App nicht signiert ist: *Weitere Informationen → Trotzdem ausführen*).
3. Modell wählen (Small ist ein guter Start), in ein Textfeld klicken, `Strg`+`Win` halten, sprechen.

Daten liegen in `%APPDATA%\Murmur` (Aufnahmen, Verlauf, Einstellungen).

## Offline-/Kanzlei-Betrieb
Modell einmal auf einem beliebigen PC laden, den Ordner `%APPDATA%\Murmur\models` auf USB-Stick oder Freigabe kopieren, dann unter *Einstellungen → Offline-/Kanzlei-Modus* importieren (oder Ordner direkt verwenden) und den Offline-Modus einschalten.

## Hinweis
Nur CPU (int8). Murmur sendet weder Audio noch Text irgendwohin; einziger Netzzugriff ist der optionale, einmalige Modell-Download von huggingface.co. Ob ein Einsatz berufs- oder datenschutzrechtlichen Vorgaben genügt, musst du selbst beurteilen.

## License / Lizenz
MIT. Whisper models © OpenAI (MIT), faster-whisper © SYSTRAN (MIT).
