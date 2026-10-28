"""Ordnet Bilder aus einem Ordner den Gerichten zu und legt sie als bilder/<id>.jpg ab.

Aufruf:
    python tools/bilder_zuordnen.py ORDNER            # zuordnen, verkleinern, gerichte.json aktualisieren
    python tools/bilder_zuordnen.py ORDNER --probe    # nur anzeigen, nichts schreiben

Zuordnung:
  1. Dateiname beginnt mit einer ID ("33.jpg", "33_spaghetti-bolognese.png", "B14 gratin.webp").
  2. Sonst Abgleich des Dateinamens mit den Titeln. Nur eindeutige Treffer werden übernommen,
     alles Unsichere landet in der Liste am Ende – es wird nicht geraten.
"""
import argparse
import difflib
import hashlib
import re
import sys
from collections import defaultdict
from pathlib import Path

from gemeinsam import BILDER, ROOT, cache_version_hochzaehlen, lade_gerichte, norm, schreibe_gerichte, speichere_quadrat

ENDUNGEN = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif"}
SICHER_AB = 0.93     # Ähnlichkeit, ab der ein Titel-Treffer als eindeutig gilt …
ABSTAND = 0.10       # … und so weit vor dem Zweitbesten liegen muss.
MINDESTENS = 400     # kleinere Bilder werden übernommen, aber als unscharf gemeldet


def aehnlichkeit(a, b):
    return difflib.SequenceMatcher(None, a, b).ratio()


def kandidaten(name, gerichte):
    n = norm(name)
    werte = sorted(((aehnlichkeit(n, norm(g["title"])), g) for g in gerichte), key=lambda x: -x[0])
    return werte[:3]


def zuordnen(datei, gerichte, nach_id):
    """Gibt (id, None) bei sicherer Zuordnung zurück, sonst (None, grund)."""
    stamm = datei.stem.strip()
    m = re.match(r"^(B?\d+)(?=$|[\s_\-.])(.*)$", stamm, re.I)
    if m:
        gid, rest = m.group(1).upper(), m.group(2).strip(" _-.")
        if gid not in nach_id:
            return None, f"ID {gid} gibt es nicht"
        if rest:
            passt = aehnlichkeit(norm(rest), norm(nach_id[gid]["title"]))
            (best_wert, best), *_ = kandidaten(rest, gerichte)
            if passt < 0.5 and best["id"] != gid and best_wert >= 0.8:
                return None, f"ID {gid} ({nach_id[gid]['title']}) passt nicht zum Namen – eher {best['id']} {best['title']}?"
        return gid, None

    if not norm(stamm):
        return None, "Dateiname ohne ID oder Titel"
    exakt = [g for g in gerichte if norm(g["title"]) == norm(stamm)]
    if len(exakt) == 1:
        return exakt[0]["id"], None
    top = kandidaten(stamm, gerichte)
    (w1, g1), (w2, _) = top[0], top[1]
    if w1 >= SICHER_AB and w1 - w2 >= ABSTAND:
        return g1["id"], None
    vorschlaege = ", ".join(f"{g['id']} {g['title']} ({w:.0%})" for w, g in top)
    return None, f"unsicher – Kandidaten: {vorschlaege}"


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("ordner", type=Path)
    p.add_argument("--probe", action="store_true", help="nur anzeigen, nichts schreiben")
    args = p.parse_args()

    try:
        import pillow_heif
        pillow_heif.register_heif_opener()
    except ImportError:
        pass
    from PIL import Image

    gerichte = lade_gerichte()
    nach_id = {g["id"]: g for g in gerichte}
    dateien = sorted(f for f in args.ordner.iterdir() if f.is_file() and f.suffix.lower() in ENDUNGEN)
    if not dateien:
        sys.exit(f"Keine Bilder in {args.ordner} gefunden.")

    treffer = defaultdict(list)
    ohne = []
    for datei in dateien:
        gid, grund = zuordnen(datei, gerichte, nach_id)
        if gid:
            treffer[gid].append(datei)
        else:
            ohne.append((datei.name, grund))
    for gid, liste in list(treffer.items()):
        # Byte-gleiche Kopien zählen als ein Bild, echte Alternativen muss ein Mensch auswählen.
        if len({hashlib.sha256(d.read_bytes()).digest() for d in liste}) > 1:
            del treffer[gid]
            for d in liste:
                ohne.append((d.name, f"mehrere verschiedene Bilder für {gid} {nach_id[gid]['title']}"))
        else:
            treffer[gid] = liste[:1]

    fertig = []
    for gid, (datei,) in sorted(treffer.items(), key=lambda x: x[0]):
        ziel = BILDER / f"{gid}.jpg"
        try:
            with Image.open(datei) as bild:
                groesse = bild.size
                if not args.probe:
                    speichere_quadrat(bild, ziel)
        except Exception as e:
            ohne.append((datei.name, f"Bild nicht lesbar ({e})"))
            continue
        if not args.probe:
            nach_id[gid]["image"] = f"bilder/{gid}.jpg"
        hinweis = f"   ⚠ nur {groesse[0]}×{groesse[1]} px – wird unscharf" if min(groesse) < MINDESTENS else ""
        fertig.append((datei.name, gid, hinweis))

    if not args.probe and fertig:
        schreibe_gerichte(gerichte)
        version = cache_version_hochzaehlen()

    print(f"\n{'PROBELAUF – nichts geschrieben' if args.probe else 'Fertig'}: {len(fertig)} von {len(dateien)} Bildern zugeordnet.\n")
    for name, gid, hinweis in fertig:
        print(f"  ✓ {name}  →  {gid} {nach_id[gid]['title']}{hinweis}")

    if ohne:
        print(f"\nBilder ohne Zuordnung ({len(ohne)}) – bitte umbenennen (z. B. „33.jpg“) und neu starten:")
        for name, grund in sorted(ohne):
            print(f"  ? {name}: {grund}")

    neu = {gid for _, gid, _ in fertig}
    fehlen = [g for g in gerichte
              if g["id"] not in neu and not (g.get("image", "").startswith("bilder/") and (ROOT / g["image"].split("?")[0]).exists())]
    print(f"\nGerichte ohne Bild ({len(fehlen)}):")
    for g in fehlen:
        print(f"  – {g['id']:>4}  {g['title']}")

    if not args.probe and fertig:
        print(f"\ngerichte.json aktualisiert, Cache-Version in sw.js auf v{version} erhöht. Jetzt committen und pushen.")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
