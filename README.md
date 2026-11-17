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
- **Optional text polish with a local [Ollama](https://ollama.com) model** (off by default): tidies punctuation and wording, keeps your line breaks, talks only to `127.0.0.1`, and falls back to your original text on any problem, including when the model changes a long word (names, tax terms) or a number
- **Hotkeys:** any key or combination, left/right-specific keys, mouse side buttons. Default mode is *smart*: hold to talk, or tap once for hands-free and tap again to stop
- **German tax vocabulary pack** (about 130 terms) for recognition and correct spelling; your own dictionary words always come first
- **Snippets:** say a trigger phrase (or "insert" plus the trigger) and a saved text block is pasted exactly as written
- **Undo last dictation:** say "scratch that" / "streich das" (or use the tray menu). Safe by design: only right after pasting, in the same window, and only if you haven't typed since
- **Per-app behaviour:** choose a writing style (formal, friendly, concise, or none) and the paste key per program, for example Ctrl+Shift+V for terminals
- **Microphone check** with a live level meter and a plain-language verdict
- **Signed updates from a USB stick or folder** (no internet): see below
- Models: Tiny, Base, Small (default), Medium, Turbo, downloaded once

## Install (Windows 10/11)
1. Download `Murmur-Windows.zip` from [Releases](../../releases/latest), unzip anywhere.
2. Run `Murmur.exe` (Windows SmartScreen may warn because the app is not code-signed: *More info → Run anyway*).
3. Pick a model (Small is a good start), click into any text box, hold `Ctrl`+`Win`, speak.

Data lives in `%APPDATA%\Murmur` (recordings, history, settings).

## Offline / office use
Download a model once on any PC, copy `%APPDATA%\Murmur\models` to a USB stick or share, then in *Settings → Offline / office mode* import it (or point Murmur at the folder) and switch offline mode on.

## Updates by USB stick (no internet)
Murmur never updates itself over the internet. Instead:
1. Download `Murmur-Update-x.y.z.murmurupdate` from [Releases](../../releases/latest) (or build one yourself) and copy it to a USB stick or a network share.
2. Plug the stick in. Murmur notices the file, checks its **digital signature**, and offers to install it with one click (or automatically, if you enable that). It restarts, and your recordings, history and settings stay untouched. If anything fails, the previous version is restored.

Only updates signed with the owner's private key are accepted; forged, edited or damaged files are refused. The matching public key is built into every Murmur. This is a separate mechanism from Windows code signing and does not remove the SmartScreen warning.

**For the maintainer:** run `python tools/keygen.py` once. The private key stays on your PC (`%USERPROFILE%\.murmur-signing\update-private.pem`), is git-ignored and **must be backed up**: if it is lost, installed copies can no longer accept your updates and need a manual reinstall. Create a package with `python tools/make_update.py --payload <built Murmur folder> --version x.y.z --out <folder>`. Murmur 1.2.0 is the first version that can install updates this way.

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
- **Hotkeys:** beliebige Taste oder Kombination, links/rechts-spezifische Tasten, Maus-Seitentasten. Standardmodus *smart*: halten zum Sprechen, oder einmal antippen für Freisprechen und erneut antippen zum Stoppen
- **Deutsches Steuer-Vokabular** (ca. 130 Begriffe) für Erkennung und richtige Schreibweise; deine eigenen Wörter haben Vorrang
- **Textbausteine:** Auslösewort sagen (oder „einfügen“ plus Auslösewort), und der gespeicherte Text wird exakt so eingefügt
- **Letztes Diktat rückgängig:** „streich das“ / „scratch that“ sagen (oder Tray-Menü). Bewusst sicher: nur direkt nach dem Einfügen, im selben Fenster und nur, wenn du seitdem nichts getippt hast
- **Verhalten je Programm:** Schreibstil (förmlich, freundlich, knapp oder keiner) und Einfüge-Taste pro Programm, z. B. Strg+Umschalt+V für Terminals
- **Mikrofon-Check** mit Pegelanzeige und verständlichem Ergebnis
- **Signierte Updates per USB-Stick oder Ordner** (ohne Internet): siehe unten
- Modelle: Tiny, Base, Small (Standard), Medium, Turbo, einmalig geladen

## Installation (Windows 10/11)
1. `Murmur-Windows.zip` von den [Releases](../../releases/latest) laden und entpacken.
2. `Murmur.exe` starten (SmartScreen warnt evtl., weil die App nicht signiert ist: *Weitere Informationen → Trotzdem ausführen*).
3. Modell wählen (Small ist ein guter Start), in ein Textfeld klicken, `Strg`+`Win` halten, sprechen.

Daten liegen in `%APPDATA%\Murmur` (Aufnahmen, Verlauf, Einstellungen).

## Offline-/Kanzlei-Betrieb
Modell einmal auf einem beliebigen PC laden, den Ordner `%APPDATA%\Murmur\models` auf USB-Stick oder Freigabe kopieren, dann unter *Einstellungen → Offline-/Kanzlei-Modus* importieren (oder Ordner direkt verwenden) und den Offline-Modus einschalten.

## Updates per USB-Stick (ohne Internet)
Murmur aktualisiert sich nie selbst über das Internet. Stattdessen:
1. `Murmur-Update-x.y.z.murmurupdate` von den [Releases](../../releases/latest) laden (oder selbst erzeugen) und auf einen USB-Stick oder eine Freigabe kopieren.
2. Stick einstecken. Murmur erkennt die Datei, prüft die **digitale Signatur** und bietet die Installation per Klick an (oder automatisch, wenn aktiviert). Danach startet es neu; Aufnahmen, Verlauf und Einstellungen bleiben unberührt. Bei einem Fehler wird die vorherige Version wiederhergestellt.

Akzeptiert werden nur Updates, die mit dem privaten Schlüssel des Besitzers signiert sind; gefälschte, veränderte oder beschädigte Dateien werden abgelehnt. Der passende öffentliche Schlüssel steckt in jedem Murmur. Das ist unabhängig von der Windows-Codesignatur und entfernt die SmartScreen-Warnung nicht.

**Für den Betreuer:** `python tools/keygen.py` einmal ausführen. Der private Schlüssel bleibt auf deinem PC (`%USERPROFILE%\.murmur-signing\update-private.pem`), ist per Git-Ignore ausgeschlossen und **muss gesichert werden**: Geht er verloren, können installierte Kopien deine Updates nicht mehr annehmen und müssen manuell neu installiert werden. Paket erzeugen mit `python tools/make_update.py --payload <gebauter Murmur-Ordner> --version x.y.z --out <Ordner>`. Murmur 1.2.0 ist die erste Version, die Updates so installieren kann.

## Hinweis
Nur CPU (int8). Murmur sendet weder Audio noch Text irgendwohin; einziger Netzzugriff ist der optionale, einmalige Modell-Download von huggingface.co. Ob ein Einsatz berufs- oder datenschutzrechtlichen Vorgaben genügt, musst du selbst beurteilen.

## License / Lizenz
MIT. Whisper models © OpenAI (MIT), faster-whisper © SYSTRAN (MIT).
