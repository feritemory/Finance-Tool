"""Erzeugt realistische Demo-Umsätze ab Januar 2026.

Wird beim ersten Start genutzt, damit das Tool sofort rückwirkende Einnahmen
und Ausgaben seit 2026 darstellen kann. Die Daten sind frei erfunden und
können jederzeit über "Alle Daten löschen" entfernt werden.
"""

from __future__ import annotations

import calendar
import random
from datetime import date

from .importer import Transaction


def _d(year: int, month: int, day: int) -> date:
    last = calendar.monthrange(year, month)[1]
    return date(year, month, min(day, last))


# (Empfänger, Verwendungszweck, typischer Betrag, Streuung)
GROCERY = [
    ("REWE SAGT DANKE", "REWE Filiale Berlin", 42, 18),
    ("EDEKA", "EDEKA Einkauf", 38, 15),
    ("ALDI SUED", "ALDI SUED SAGT DANKE", 27, 12),
    ("LIDL", "LIDL Dienstleistung", 31, 14),
    ("DM DROGERIE MARKT", "DM Filiale", 19, 9),
]
EATING_OUT = [
    ("Lieferando.de", "Lieferando Bestellung", 24, 8),
    ("MC DONALDS", "McDonalds Restaurant", 12, 5),
    ("Doener Point", "Doener Point Imbiss", 9, 3),
    ("L'Osteria", "LOsteria Abendessen", 33, 12),
    ("Starbucks", "Starbucks Coffee", 6, 2),
]
SHOPPING = [
    ("AMAZON EU SARL", "Amazon Bestellung", 45, 30),
    ("Zalando SE", "Zalando Kleidung", 60, 40),
    ("MediaMarkt", "MediaMarkt Elektronik", 120, 90),
    ("H&M", "H und M Filiale", 35, 20),
]
LEISURE = [
    ("Netflix", "Netflix Abo", 13.99, 0),
    ("Spotify", "Spotify Premium", 10.99, 0),
    ("Steam Games", "Steam Kauf", 25, 20),
    ("CinemaxX", "Kino Ticket", 14, 4),
]
TRAVEL = [
    ("DB Vertrieb GmbH", "Deutsche Bahn Ticket", 49, 30),
    ("FlixBus", "FlixBus Fahrt", 22, 12),
    ("Ryanair", "Ryanair Flug", 89, 60),
    ("Booking.com", "Booking Hotel", 130, 80),
]
SPORT = [
    ("FitX", "FitX Mitgliedsbeitrag", 29.99, 0),
]
HOUSING = [
    ("Hausverwaltung Mueller", "Miete Wohnung", 680, 0),
    ("Vodafone GmbH", "Vodafone Internet", 39.99, 0),
    ("Telekom Deutschland", "Telekom Mobilfunk Handy", 24.99, 0),
    ("Stadtwerke", "Stadtwerke Strom Abschlag", 55, 0),
]
SAVINGS = [
    ("Trade Republic", "TRADE REPUBLIC Sparplan", 200, 0),
    ("Revolut", "REVOLUT Sparen Uebertrag", 150, 0),
]


def _amt(base: float, spread: float, rng: random.Random) -> float:
    if spread == 0:
        return round(-base, 2)
    val = base + rng.uniform(-spread, spread)
    return round(-max(1.0, val), 2)


def generate(seed: int = 42, up_to: date | None = None) -> list[Transaction]:
    rng = random.Random(seed)
    up_to = up_to or date.today()
    txs: list[Transaction] = []

    year = 2026
    for month in range(1, 13):
        if date(year, month, 1) > up_to:
            break

        # --- Einnahmen ---
        txs.append(Transaction(
            _d(year, month, 28), None, 1750.0, "EUR",
            "Muster GmbH", "", f"Gehalt {month:02d}/{year} Lohn/Gehalt",
            "Gutschrift Gehalt", "sample"))
        txs.append(Transaction(
            _d(year, month, 15), None, 452.0, "EUR",
            "Bundesverwaltungsamt", "", "BAFOEG Ausbildungsfoerderung",
            "Gutschrift", "sample"))

        # --- Fixkosten (monatlich, gleicher Betrag) ---
        for name, zweck, base, spread in HOUSING + SPORT + SAVINGS:
            day = rng.randint(1, 5)
            txs.append(Transaction(
                _d(year, month, day), None, _amt(base, spread, rng), "EUR",
                name, "", zweck, "Lastschrift", "sample"))

        # --- variable Ausgaben ---
        for _ in range(rng.randint(10, 16)):
            name, zweck, base, spread = rng.choice(GROCERY)
            txs.append(Transaction(
                _d(year, month, rng.randint(1, 28)), None, _amt(base, spread, rng),
                "EUR", name, "", zweck, "Kartenzahlung", "sample"))

        for _ in range(rng.randint(4, 9)):
            name, zweck, base, spread = rng.choice(EATING_OUT)
            txs.append(Transaction(
                _d(year, month, rng.randint(1, 28)), None, _amt(base, spread, rng),
                "EUR", name, "", zweck, "Kartenzahlung", "sample"))

        for _ in range(rng.randint(1, 4)):
            name, zweck, base, spread = rng.choice(SHOPPING)
            txs.append(Transaction(
                _d(year, month, rng.randint(1, 28)), None, _amt(base, spread, rng),
                "EUR", name, "", zweck, "Kartenzahlung", "sample"))

        # Freizeit-Abos (fix) + gelegentliche Extras
        for name, zweck, base, spread in LEISURE[:2]:
            txs.append(Transaction(
                _d(year, month, rng.randint(1, 8)), None, _amt(base, spread, rng),
                "EUR", name, "", zweck, "Lastschrift", "sample"))
        for _ in range(rng.randint(0, 2)):
            name, zweck, base, spread = rng.choice(LEISURE[2:])
            txs.append(Transaction(
                _d(year, month, rng.randint(1, 28)), None, _amt(base, spread, rng),
                "EUR", name, "", zweck, "Kartenzahlung", "sample"))

        # Reisen: nicht jeden Monat
        if rng.random() < 0.5:
            name, zweck, base, spread = rng.choice(TRAVEL)
            txs.append(Transaction(
                _d(year, month, rng.randint(1, 28)), None, _amt(base, spread, rng),
                "EUR", name, "", zweck, "Kartenzahlung", "sample"))

    return [t for t in txs if t.date <= up_to]
