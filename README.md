# Hangrys – Familien-Essensapp

Statische iPhone-Web-App: `index.html`, `gerichte.json`, `bilder/`, `sw.js`. Kein Build.

## Lokal ansehen

```
python -m http.server 8765
```
Dann http://localhost:8765 öffnen (in den Entwicklertools auf iPhone-Ansicht stellen).

## Für alle speichern direkt aus der App

Mit einem GitHub-Schlüssel schreibt die App Fotos und Änderungen direkt ins Repo. Nach 1–2 Minuten sehen es alle.

1. github.com → Profilbild → Settings → Developer settings → Personal access tokens → **Fine-grained tokens** → Generate new token.
2. Name „Essen-App“, Ablauf z. B. 1 Jahr, Repository access: **Only select repositories** → dieses Repo.
3. Permissions → Repository permissions → **Contents: Read and write**. Generate, Schlüssel kopieren.
4. In der App: Einstellungen → „Für alle speichern“ → Schlüssel einfügen → Verbinden.

Der Schlüssel liegt nur auf dem eigenen Handy und kann nur dieses eine Repo ändern. Favoriten bleiben immer pro Handy.
Wer lokal Scripts laufen lässt, vorher `git pull`, weil die App selbst Commits macht.

## Neue Bilder per Script einbauen

Bilder in einen Ordner legen, am besten nach ID benannt (`33.jpg`, `33_spaghetti-bolognese.png`), notfalls nach Titel.

```
python tools/bilder_zuordnen.py ORDNER --probe   # erst nur ansehen
python tools/bilder_zuordnen.py ORDNER           # dann wirklich
```

Das Script schneidet quadratisch auf 800×800 zu, speichert nach `bilder/<id>.jpg`, setzt `image` in `gerichte.json`,
zählt die Cache-Version in `sw.js` hoch und listet Gerichte ohne Bild sowie Bilder ohne sichere Zuordnung.
Bilder unter 400 px werden übernommen, aber als unscharf gemeldet. Braucht Pillow (`pip install pillow`).

## Änderungen der Familie übernehmen

Auf dem Handy: Einstellungen → „Als Datei teilen“ → Datei an den Admin. Dann:

```
python tools/export_uebernehmen.py gerichte-export-JJJJ-MM-TT.json
```

Schreibt `gerichte.json` neu, speichert in der App aufgenommene Fotos nach `bilder/` und zeigt, was neu, geändert oder gelöscht ist.
Danach committen und pushen – nach dem nächsten Öffnen haben alle den neuen Stand.

## Veröffentlichen (GitHub Pages)

Repo auf GitHub anlegen, alles pushen, unter Settings → Pages „Deploy from branch“ → `main` / root wählen.
Der Link `https://<name>.github.io/<repo>/` geht per WhatsApp raus → in Safari öffnen → Teilen → „Zum Home-Bildschirm“.

`index.html` und `gerichte.json` holt die App immer frisch (offline aus dem Cache). Bilder kommen aus dem Cache;
die Scripts zählen dafür die Version in `sw.js` hoch. Wer Bilder von Hand austauscht, muss `VERSION` in `sw.js` selbst erhöhen.

`tools/erzeuge_gerichte.py` erzeugt `gerichte.json` aus der Liste in `CLAUDE.md` neu und behält dabei Bilder sowie die Tags „schnell“ und „kids“.
