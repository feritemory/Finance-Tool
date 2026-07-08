"""Automatische Kategorisierung von Umsätzen anhand von Stichwort-Regeln."""

from __future__ import annotations

import os
from functools import lru_cache

import yaml

from .categories import CATEGORY_NAMES, UNCATEGORIZED, is_income

RULES_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "config",
    "rules.yaml",
)


@lru_cache(maxsize=1)
def _load_rules_cached(mtime: float) -> dict[str, list[str]]:
    with open(RULES_PATH, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    # Nur bekannte Kategorien übernehmen, Stichwörter kleinschreiben.
    rules: dict[str, list[str]] = {}
    for cat in CATEGORY_NAMES:
        keywords = data.get(cat, []) or []
        rules[cat] = [str(k).lower().strip() for k in keywords if str(k).strip()]
    return rules


def load_rules() -> dict[str, list[str]]:
    """Lädt die Regeln aus config/rules.yaml (mit Cache-Invalidierung bei Änderung)."""
    try:
        mtime = os.path.getmtime(RULES_PATH)
    except OSError:
        mtime = 0.0
    return _load_rules_cached(mtime)


def categorize(counterparty: str, description: str, booking_text: str,
               amount: float) -> str:
    """Ordnet einem Umsatz eine Kategorie zu.

    Sucht in Empfänger, Verwendungszweck und Buchungstext nach Stichwörtern.
    Einnahmen-Kategorien werden nur bei positivem Betrag gewählt, damit z. B.
    eine Rücklastschrift von "Gehalt" nicht als Einnahme zählt.
    """
    haystack = " ".join(
        part.lower() for part in (counterparty, description, booking_text) if part
    )

    rules = load_rules()
    for cat, keywords in rules.items():
        # Einnahmen nur bei Geldeingang, Ausgaben nur bei Geldausgang zulassen.
        if is_income(cat) and amount <= 0:
            continue
        for kw in keywords:
            if kw and kw in haystack:
                return cat

    return UNCATEGORIZED
