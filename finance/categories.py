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

CATEGORIES: list[Category] = [
    Category("Lebensmittel",                 "ausgabe", "#4E79A7"),
    Category("Auswärts Essen und Trinken",   "ausgabe", "#F28E2B"),
    Category("Shoppen",                      "ausgabe", "#E15759"),
    Category("Freizeit",                     "ausgabe", "#76B7B2"),
    Category("Reisen",                       "ausgabe", "#59A14F"),
    Category("Wohnkosten inkl. Internet und Handykosten", "ausgabe", "#EDC948", fixkosten=True),
    Category("Sport",                        "ausgabe", "#B07AA1", fixkosten=True),
    Category("Gehalt",                       "einnahme", "#2E7D32"),
    Category("Bafög",                        "einnahme", "#9C755F"),
    Category(INCOME_UNCATEGORIZED,           "einnahme", "#7FB069"),
    Category("Überweisung an Sparkonten",    "sparen",   "#4C72B0", fixkosten=True),
    Category(UNCATEGORIZED,                  "ausgabe", "#BAB0AC"),
]

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
