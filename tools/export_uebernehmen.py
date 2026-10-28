"""Übernimmt einen Export aus der App (Einstellungen → Exportieren) in gerichte.json.

Aufruf:  python tools/export_uebernehmen.py gerichte-export-2026-10-28.json

In der App aufgenommene Fotos stecken im Export als eingebettete Daten. Sie werden
als bilder/<id>.jpg gespeichert und in gerichte.json durch den Pfad ersetzt.
Favoriten im Export werden ignoriert, die bleiben auf den einzelnen Handys.
"""
import base64
import io
import sys
from pathlib import Path

from gemeinsam import BILDER, GERICHTE, cache_version_hochzaehlen, lade_gerichte, schreibe_gerichte, speichere_quadrat

FELDER = ("id", "title", "category", "subcategory", "tags", "image")


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    from PIL import Image

    neu = [{k: g.get(k, [] if k == "tags" else "") for k in FELDER} for g in lade_gerichte(sys.argv[1])]
    alt = {g["id"]: g for g in lade_gerichte()} if GERICHTE.exists() else {}

    fotos = 0
    for g in neu:
        if g["image"].startswith("data:image"):
            roh = base64.b64decode(g["image"].split(",", 1)[1])
            with Image.open(io.BytesIO(roh)) as bild:
                speichere_quadrat(bild, BILDER / f"{g['id']}.jpg")
            g["image"] = f"bilder/{g['id']}.jpg"
            fotos += 1

    ids = {g["id"] for g in neu}
    hinzu = [g for g in neu if g["id"] not in alt]
    geaendert = [g for g in neu if g["id"] in alt and g != {k: alt[g["id"]].get(k, "") for k in FELDER}]
    weg = [g for i, g in alt.items() if i not in ids]

    schreibe_gerichte(neu)
    print(f"{len(neu)} Gerichte nach gerichte.json übernommen.")
    for titel, liste in (("Neu", hinzu), ("Geändert", geaendert), ("Gelöscht", weg)):
        if liste:
            print(f"\n{titel} ({len(liste)}):")
            for g in liste:
                print(f"  {g['id']:>4}  {g['title']}")
    if fotos:
        version = cache_version_hochzaehlen()
        print(f"\n{fotos} Fotos nach bilder/ geschrieben, Cache-Version in sw.js auf v{version} erhöht.")
    print("\nJetzt committen und pushen.")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
