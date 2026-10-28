"""Erzeugt gerichte.json aus der verbindlichen Gerichteliste in CLAUDE.md.

Aufruf:  python tools/erzeuge_gerichte.py

Bereits vorhandene Felder `image` sowie die Tags `schnell` und `kids` aus einer
bestehenden gerichte.json bleiben erhalten, damit ein erneuter Lauf nichts
kaputt macht.
"""
import json
import re
import sys

from gemeinsam import GERICHTE as ZIEL, ROOT, schreibe_gerichte

CLAUDE_MD = ROOT / "CLAUDE.md"

# Ernährungs-Tags nur dort, wo der Titel eindeutig ist. Alles andere bleibt leer.
FLEISCH = """
11 32 33 35 113
36 37 67 73 74
28 75 76 77 79 86 103 104
25 59 60 61 62 63 64 65 66 68 69 70 71 72
78 82 90 91 92 94
1 2 3 4 5 6 7 8 14 15 24
80
12 26 51 54 56
39 42 101
""".split()

FISCH = """
34 50 58 115
23 29 43 44 45 46 47 48 49 57
97
81 89
""".split()

VEGETARISCH = """
38 96 111 112
13 100 109 B14
95 98 99
22 106
17 110
18 19 20 21 30 87
52 53 55 108 114 B10 B15
84 107
B4 B5 B6 B7 B8 B13 B16 B17 B18 B19 B20 B21 B23 B24 B25 B26 B27
B1 B2 B3
""".split()
# Bewusst ohne Tag (unklar): 16 Dumplings, 93 Massaman-Curry, 9 Pide,
# 10 Tschebureki, 27 Burritos, 102 Sarma, B11/B12 Kartoffelsalate,
# 40/41/83/85/88/105 Suppen (Brühe/Wurst unklar), B22 Caesar-Dressing (Sardellen).


def lies_liste():
    text = CLAUDE_MD.read_text(encoding="utf-8")
    m = re.search(r"### Gerichteliste.*?```json\s*(\{.*?\})\s*```", text, re.S)
    if not m:
        sys.exit("Gerichteliste in CLAUDE.md nicht gefunden.")
    return json.loads(m.group(1))


def ernaehrung(gid):
    treffer = [t for t, ids in (("fleisch", FLEISCH), ("fisch", FISCH), ("vegetarisch", VEGETARISCH)) if gid in ids]
    if len(treffer) > 1:
        sys.exit(f"ID {gid} hat widersprüchliche Tags: {treffer}")
    return treffer


def main():
    liste = lies_liste()
    alt = {}
    if ZIEL.exists():
        daten = json.loads(ZIEL.read_text(encoding="utf-8"))
        alt = {g["id"]: g for g in (daten["gerichte"] if isinstance(daten, dict) else daten)}

    gerichte = []
    for kategorie, inhalt in liste.items():
        gruppen = inhalt.items() if isinstance(inhalt, dict) else [("", inhalt)]
        for unterkategorie, eintraege in gruppen:
            for gid, titel in eintraege:
                vorher = alt.get(gid, {})
                tags = ernaehrung(gid) + [t for t in vorher.get("tags", []) if t in ("schnell", "kids")]
                gerichte.append({
                    "id": gid,
                    "title": titel,
                    "category": kategorie,
                    "subcategory": unterkategorie,
                    "tags": tags,
                    "image": vorher.get("image", ""),
                })

    ids = [g["id"] for g in gerichte]
    assert len(ids) == len(set(ids)), "doppelte IDs"
    assert "31" not in ids and "B9" not in ids
    unbekannt = set(FLEISCH + FISCH + VEGETARISCH) - set(ids)
    assert not unbekannt, f"Tags für unbekannte IDs: {unbekannt}"

    schreibe_gerichte(gerichte, ZIEL)
    ohne = sum(1 for g in gerichte if not any(t in g["tags"] for t in ("fleisch", "fisch", "vegetarisch")))
    print(f"{len(gerichte)} Gerichte geschrieben nach {ZIEL.name} ({ohne} ohne Ernährungs-Tag).")


if __name__ == "__main__":
    main()
