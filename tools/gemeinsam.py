"""Gemeinsame Helfer für die Scripts in tools/."""
import json
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GERICHTE = ROOT / "gerichte.json"
BILDER = ROOT / "bilder"
SW = ROOT / "sw.js"
BILD_GROESSE = 800
JPG_QUALITAET = 80


def lade_gerichte(pfad=GERICHTE):
    daten = json.loads(Path(pfad).read_text(encoding="utf-8"))
    return daten["gerichte"] if isinstance(daten, dict) else daten


def schreibe_gerichte(gerichte, pfad=GERICHTE):
    """Eine Zeile pro Gericht, damit Änderungen im Git-Diff gut lesbar sind."""
    zeilen = ",\n".join("  " + json.dumps(g, ensure_ascii=False) for g in gerichte)
    # newline="\n": auch unter Windows LF schreiben, so wie die App es per GitHub-API tut
    Path(pfad).write_text("[\n" + zeilen + "\n]\n", encoding="utf-8", newline="\n")


def norm(text):
    """Wie die Suche in der App: ä=a=ae, ß=ss, Akzente und Satzzeichen weg."""
    s = str(text).lower().replace("ß", "ss")
    s = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
    s = s.replace("ae", "a").replace("oe", "o").replace("ue", "u")
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def speichere_quadrat(bild, ziel):
    """Mittig quadratisch zuschneiden, auf 800×800 skalieren, als JPG speichern."""
    from PIL import Image, ImageOps

    bild = ImageOps.exif_transpose(bild)
    if bild.mode in ("RGBA", "LA", "P"):
        bild = bild.convert("RGBA")
        hintergrund = Image.new("RGB", bild.size, (255, 255, 255))
        hintergrund.paste(bild, mask=bild.split()[-1])
        bild = hintergrund
    else:
        bild = bild.convert("RGB")
    bild = ImageOps.fit(bild, (BILD_GROESSE, BILD_GROESSE), Image.LANCZOS)
    ziel.parent.mkdir(parents=True, exist_ok=True)
    bild.save(ziel, "JPEG", quality=JPG_QUALITAET, optimize=True, progressive=True)


def cache_version_hochzaehlen():
    """Neue Cache-Version im Service Worker, damit Handys geänderte Bilder neu laden."""
    text = SW.read_text(encoding="utf-8")
    m = re.search(r"const VERSION = 'essen-v(\d+)';", text)
    if not m:
        return None
    neu = int(m.group(1)) + 1
    SW.write_text(text.replace(m.group(0), f"const VERSION = 'essen-v{neu}';"), encoding="utf-8", newline="\n")
    return neu
