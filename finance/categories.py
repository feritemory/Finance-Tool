"""Kategorie-Definitionen für das Finance-Tool.

Jede Kategorie hat einen Typ:
    - "einnahme"  : Geldeingang (Gehalt, Bafög)
    - "ausgabe"   : Konsum / Kosten
    - "sparen"    : Übertrag auf eigene Spar-/Depotkonten (kein echter Verlust)

Die Reihenfolge entspricht der vom Nutzer gewünschten Reihenfolge.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Category:
    name: str
    typ: str          # "einnahme" | "ausgabe" | "sparen"
    farbe: str        # Hex-Farbe für Diagramme
    fixkosten: bool = False   # typischerweise wiederkehrende Fixkosten?


# Kategorie "Sonstiges" fängt unklare AUSGABEN ab; "Sonstige Einnahmen"
# entsprechend unklare EINGÄNGE (Erstattungen, Überweisungen, PayPal ...).
UNCATEGORIZED = "Sonstiges"
INCOME_UNCATEGORIZED = "Sonstige Einnahmen"

# Farben: validierte kategoriale Palette (feste Slot-Reihenfolge, auf
# Farbfehlsichtigkeit geprüft). Ausgaben- und Einnahmen-Kategorien erscheinen
# nie im selben Diagramm, dürfen sich die Slots also teilen.
# Auffang-Kategorien ("Sonstiges") bekommen bewusst Neutralgrau.
CATEGORIES: list[Category] = [
    Category("Lebensmittel",                 "ausgabe", "#2a78d6"),   # Slot 1 blau
    Category("Auswärts Essen und Trinken",   "ausgabe", "#eb6834"),   # Slot 2 orange
    Category("Shoppen",                      "ausgabe", "#1baf7a"),   # Slot 3 aqua
    Category("Freizeit",                     "ausgabe", "#eda100"),   # Slot 4 gelb
    Category("Reisen",                       "ausgabe", "#e87ba4"),   # Slot 5 magenta
    Category("Wohnkosten inkl. Internet und Handykosten", "ausgabe", "#008300", fixkosten=True),
    Category("Sport",                        "ausgabe", "#4a3aa7", fixkosten=True),
    Category("Gehalt",                       "einnahme", "#1baf7a"),
    Category("Bafög",                        "einnahme", "#eda100"),
    Category(INCOME_UNCATEGORIZED,           "einnahme", "#2a78d6"),
    Category("Überweisung an Sparkonten",    "sparen",   "#2a78d6", fixkosten=True),
    Category(UNCATEGORIZED,                  "ausgabe", "#9a9a94"),   # Auffang: grau
]

# Semantische Farben der Hauptkennzahlen (gleiche validierte Slots).
SERIES_COLORS = {
    "einnahmen": "#1baf7a",
    "ausgaben": "#eb6834",
    "sparen": "#2a78d6",
}

CATEGORY_BY_NAME: dict[str, Category] = {c.name: c for c in CATEGORIES}
CATEGORY_NAMES: list[str] = [c.name for c in CATEGORIES]

# Farbzuordnung für Diagramme (Plotly)
COLOR_MAP: dict[str, str] = {c.name: c.farbe for c in CATEGORIES}


def typ_of(category: str) -> str:
    cat = CATEGORY_BY_NAME.get(category)
    return cat.typ if cat else "ausgabe"


def is_income(category: str) -> bool:
    return typ_of(category) == "einnahme"


def is_saving(category: str) -> bool:
    return typ_of(category) == "sparen"


def is_expense(category: str) -> bool:
    return typ_of(category) == "ausgabe"
