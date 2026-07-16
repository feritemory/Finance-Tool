"""Händler-Normalisierung: aus den verrauschten Bankfeldern einen stabilen
Schlüssel (für Lernen & Fixkosten-Gruppierung) und einen lesbaren Namen ableiten.

Beispiele für Rauschen im Consorsbank-Export:
  "Lidl sagt Danke Berlin 276"                 -> "lidl"
  "SF Burger King Hbf Berlin 2"                -> "burger king hbf"
  "TRANSACT 22207682 BERLIN 27"                -> "transact"
  PayPal: Empfänger "PayPal Europe ..." + Zweck "... Urban Sp orts GmbH ..."
  Dauerauftrag Revolut/Trade Republic: nur BIC identifiziert das Konto.
"""

from __future__ import annotations

import re

# BICs, die ein bestimmtes Konto eindeutig identifizieren (auch ohne Namen).
KNOWN_BIC_PREFIXES = ("REVODEB2", "TRBKDEBB")

# Füllwörter, die für die Händler-Identität irrelevant sind.
_STOP = {
    "gmbh", "ag", "kg", "se", "co", "ohg", "ug", "mbh", "eur", "de", "der",
    "die", "das", "und", "fuer", "fur", "von", "vom", "the", "inc", "ltd",
    "berlin", "hamburg", "muenchen", "münchen", "koeln", "köln", "sagt",
    "danke", "filiale", "store", "shop", "gmbhco",
}

# Buchungs-/Karten-Floskeln, die aus dem Text entfernt werden.
_NOISE = re.compile(
    r"visa|mastercard|maestro|girocard|kartenzahlung|kontaktlos|"
    r"lastschrift|einzugserm\w*|dauerauftrag|ueberweisung|überweisung|"
    r"echtzeit|euro-?\w*|gutschrift|sepa|mandat|pp\.\d+\.pp|"
    r"ihr einkauf bei|ihr ei nkauf bei|vorgemerkter umsatz",
    re.IGNORECASE,
)


def _is_paypal(name: str) -> bool:
    return "paypal" in name.lower()


def merchant_key(counterparty: str, description: str = "",
                 booking_text: str = "", bic: str = "") -> str:
    """Stabiler Schlüssel zur Wiedererkennung eines Händlers/Kontos.

    Wird zum Lernen (Nutzer-Korrekturen) und zur Fixkosten-Gruppierung genutzt.
    """
    b = (bic or "").upper().strip()
    for prefix in KNOWN_BIC_PREFIXES:
        if b.startswith(prefix):
            return "bic:" + prefix

    # Bei PayPal steht der echte Händler im Verwendungszweck, nicht im Empfänger.
    name = counterparty or ""
    if _is_paypal(name) and description:
        name = description

    s = name.lower()
    s = _NOISE.sub(" ", s)
    s = re.sub(r"\d{1,2}[.,]\d{2}\s*eur", " ", s)   # "6,88 EUR"
    s = re.sub(r"\b\d{2}\.\d{2}\.?\b", " ", s)        # Datumsreste
    s = re.sub(r"\d{3,}", " ", s)                     # lange Ziffernfolgen
    s = re.sub(r"[^a-zäöüß ]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()

    tokens = [t for t in s.split() if len(t) > 1 and t not in _STOP]
    key = " ".join(tokens[:3])
    return key


def clean_name(counterparty: str, description: str = "", bic: str = "") -> str:
    """Lesbarer, gekürzter Händlername für Anzeige/Fixkostenliste."""
    b = (bic or "").upper().strip()
    if b.startswith("REVODEB2"):
        return "Revolut"
    if b.startswith("TRBKDEBB"):
        return "Trade Republic"

    name = counterparty or ""
    if _is_paypal(name) and description:
        # "... 1051/PP.7506.PP/. Urban Sp orts GmbH, Ihr Einkauf bei ..."
        m = re.search(r"PP\.\d+\.PP[/.]*\s*(.+?)(?:,|$)", description, re.IGNORECASE)
        if m:
            name = "PayPal: " + m.group(1).strip()
        else:
            name = "PayPal"
    # Ort/Terminal-Anhängsel wie " Berlin 276" entfernen
    name = re.sub(r"\s+\d{2,}\s*$", "", name.strip())
    name = re.sub(r"\s+(Berlin|Potsdam|Hamburg|Vilnius|Luxembour\w*)\s*\d*\s*$", "",
                  name, flags=re.IGNORECASE)
    name = re.sub(r"\s+", " ", name).strip()
    return name or (counterparty or "").strip()
