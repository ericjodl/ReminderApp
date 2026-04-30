# RapStudio

Einfacher Mehrspur-Recorder fuer Windows zum Aufnehmen von Rap-Vocals ueber ein Audio-Interface, mit Beat-Import, Wellenform-Anzeige und Schneiden.

## Funktionen

- Mehrspur-Timeline (mehrere Tracks uebereinander, z. B. Beat + Vocals)
- Aufnahme ueber jedes WASAPI/MME/ASIO-Eingabegeraet (Audio-Interface mit Mikro)
- Import: WAV, MP3, FLAC, OGG, M4A/AAC
- Export: WAV (immer), MP3 (per ffmpeg)
- Wellenform-Darstellung mit Zoom (Strg + Mausrad)
- Clips verschieben, an den Kanten trimmen, am Playhead schneiden
- Mute / Solo / Lautstaerke pro Spur, Aufnahme-Arming

## Installation (Windows, ab Python 3.10)

```bat
git clone <repo>
cd ReminderApp
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

Fuer MP3-Import und MP3-Export wird zusaetzlich `ffmpeg` benoetigt (https://www.gyan.dev/ffmpeg/builds/, Variante "release essentials"). Den Ordner mit `ffmpeg.exe` zur PATH-Umgebungsvariable hinzufuegen.

## Standalone EXE bauen

### Variante A: Lokal auf Windows

```bat
build_windows.bat
```

Erstellt `dist\RapStudio.exe`.

### Variante B: Automatisch in der Cloud (kein Windows noetig)

Der GitHub-Actions-Workflow `.github/workflows/build-windows.yml` baut auf jedem Push automatisch eine `RapStudio.exe` (inklusive eingebettetem `ffmpeg.exe`) auf einem Windows-Runner.

So holst du die fertige EXE:

1. Auf GitHub den Reiter **Actions** oeffnen.
2. Den letzten Lauf "Build Windows EXE" anklicken.
3. Unter **Artifacts** liegt `RapStudio-Windows.zip` (~80 MB) -> herunterladen.
4. Entpacken -> `RapStudio.exe` per WhatsApp / Drive / Mail teilen.

Fuer eine richtige Versions-Veroeffentlichung Tag pushen, dann haengt der Workflow die EXE automatisch an einen GitHub-Release:

```bat
git tag v0.1.0
git push origin v0.1.0
```

## Bedienung

| Aktion | Tastenkuerzel |
|---|---|
| Wiedergabe / Stop | Leertaste |
| Aufnahme starten / stoppen | R |
| Am Playhead schneiden | S |
| Auswahl loeschen | Entf |
| Audio importieren | Strg+I |
| Als WAV exportieren | Strg+E |
| Neue Spur | Strg+T |
| Zoom | Strg + Mausrad |
| Beenden | Strg+Q |

### Erste Aufnahme

1. Audio-Interface anschliessen, Windows-Eingang waehlen.
2. In RapStudio in der Transportleiste oben das **Eingangsgeraet** auswaehlen.
3. Beat per `Strg+I` importieren -> landet auf der ersten nicht-armed Spur.
4. Vocal-Spur mit dem **REC**-Knopf am Track-Header scharfschalten.
5. Aufnahme mit **R** oder dem REC-Knopf in der Transportleiste starten.
6. Mit Leertaste/Stop beenden -> Take erscheint als Clip auf der Spur.
7. Clip ziehen, an den Kanten trimmen, am Playhead mit **S** schneiden.
8. Mit `Strg+E` als WAV mischen oder per Menue als MP3 exportieren.

## Projektstruktur

```
rapstudio/
  __init__.py
  __main__.py
  audio_engine.py    # sounddevice-Streams, Mixing, Recording
  io_utils.py        # Laden/Speichern WAV/MP3
  main_window.py     # QMainWindow + Menues + Verkabelung
  project.py         # Datenmodell: Project / Track / Clip
  timeline.py        # Wellenform-Canvas, Drag, Schneiden
  track_header.py    # Mute/Solo/Arm/Lautstaerke pro Spur
  transport.py       # Transportleiste oben
run.py               # Einstiegspunkt
requirements.txt
build_windows.bat    # PyInstaller-Build
```

## Hinweise

- Das interne Audioformat ist 32-bit float bei 48 kHz Stereo. Importierte Dateien werden bei Bedarf einfach (linear) auf die Projekt-Samplerate gebracht.
- Aufnahmen liegen rein im Speicher, bis sie ueber Export oder ein gespeichertes Mixdown auf die Platte geschrieben werden.
- Der erste Block beim Wiedergabestart kann je nach Treiber-Latenz leicht verzoegert sein. Fuer minimale Latenz ein Geraet mit ASIO oder dem WASAPI-Exklusivmodus verwenden.
