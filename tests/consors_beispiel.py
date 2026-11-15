"""Erzeugt einen synthetischen Consorsbank-Export für Tests.

Bildet die Eigenheiten des echten Exports nach – mit erfundenen Namen und
IBANs, damit keine echten Kontodaten ins Repository gelangen:

* mehrere Vorspann-Blöcke (Allgemeine Informationen, Kontostand) vor der Tabelle
* Kopfzeile "Buchung ;Valuta;Sender / Empfänger;IBAN;BIC;…;Betrag;Währung"
* vorgemerkte Umsätze (Valuta = "vorgemerkt")
* Daueraufträge an Trade Republic / Revolut, die nur über die BIC erkennbar sind
* durch Zeilenumbruch zerrissene Wörter ("Urban Sp orts")
* Gehalt der Bundeskasse mit Erhöhung ab Mai, vierteljährliche BAföG-Rückzahlung
"""

from __future__ import annotations

import calendar
import random

KOPF = "Buchung ;Valuta;Sender / Empfänger;IBAN;BIC;Buchungstext;Verwendungszweck;Betrag;Währung"


def _betrag(v: float) -> str:
    s = f"{abs(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return ("-" if v < 0 else "") + s


def _letzter_werktag(jahr: int, monat: int) -> int:
    tag = calendar.monthrange(jahr, monat)[1]
    while calendar.weekday(jahr, monat, tag) >= 5:
        tag -= 1
    return tag


def zeilen(jahr: int = 2026, bis_monat: int = 6, seed: int = 7) -> list[str]:
    rng = random.Random(seed)
    z: list[tuple[str, str, str, str, str, str, str, float]] = []

    def add(t, m, name, iban, bic, art, zweck, betrag):
        d = f"{t:02d}.{m:02d}.{jahr}"
        z.append((d, d, name, iban, bic, art, zweck, betrag))

    for m in range(1, bis_monat + 1):
        lwt = _letzter_werktag(jahr, m)
        gehalt = 3056.82 if m < 5 else 3304.55
        add(lwt, m, "Bundeskasse - Dienstort Trier -", "DE00590000000000000001",
            "MARKDEF1590", "Gehalt/Rente", f"BK TR ITZB BEZUEGE {m:02d}.26 0106/00000",
            gehalt)
        add(1, m, "Max Beispiel", "DE00100101780000000002", "REVODEB2XXX",
            "Dauerauftrag", "Dauerauftrag", -400.0)
        add(lwt, m, "Max Beispiel", "DE00100123450000000003", "TRBKDEBBXXX",
            "Dauerauftrag", "Dauerauftrag", -800.0)
        add(lwt, m, "Erika Mustermann", "DE00100100100000000004", "PBNKDEFFXXX",
            "Dauerauftrag", "Miete Musterstr. 1", -637.45)
        add(6, m, "PayPal Europe S.a.r.l. et Cie S.C.A", "LU00751000000000000005",
            "PPLXLUL2", "Lastschrift (Einzugsermächtigung)",
            "1048081890675/PP.7506.PP/. Urban Sp orts GmbH, Ihr Einkauf bei Urban Sp orts GmbH",
            -69.0)
        add(2, m, "Grünwelt Wärmestrom GmbH", "DE00202208000000000006", "SXPYDEHH",
            "Lastschrift (Einzugsermächtigung)", f"ABSCHLAG Gas {m:02d}/26", -63.0)
        add(2, m, "S-Bahn Berlin GmbH", "DE00100100100000000007", "PBNKDEFFXXX",
            "Lastschrift (Einzugsermächtigung)", "Lastschrift (Einzugsermächtigung)", -59.85)
        if m % 3 == 1:
            add(15, m, "Bundeskasse", "DE00860000000000000008", "MARKDEF1860",
                "Lastschrift (Einzugsermächtigung)", "BUKA HALLE DARLEHEN 55200000000", -390.0)
        for _ in range(rng.randint(6, 10)):
            v = round(rng.uniform(3, 45), 2)
            add(rng.randint(1, 27), m, "Lidl sagt Danke Berlin 276" + " " * 30, "n/a", "n/a",
                "Lastschrift (Einzugsermächtigung)",
                f"VISA 61840018 Berlin {_betrag(v)} EUR {m:02d}.         10355411", -v)
        for lokal in ("Golden Rice Berlin 276", "Kumpelnest3000 Berlin 276",
                      "LS Curry 36 Berlin 276"):
            v = round(rng.uniform(6, 30), 2)
            add(rng.randint(1, 27), m, lokal, "n/a", "n/a",
                "Lastschrift (Einzugsermächtigung)",
                f"VISA 61840018 Berlin {_betrag(v)} EUR {m:02d}.         10355812", -v)
        add(rng.randint(3, 25), m, "TRANSACT 22207682 BERLIN 27", "n/a", "n/a",
            "Lastschrift (Einzugsermächtigung)", "VISA 61840018 BERLIN 50,00 EUR", -50.0)
        add(rng.randint(3, 25), m, "Max Beispiel", "DE00100101780000000002", "REVODEB2XXX",
            "ECHTZEIT EURO-UEBERW.", "Gesendet von Revolut", 60.0)

    add(31, 3, "ZAHLUNGSVERKEHR BERLINER FINANZAEMTER", "DE00100500000000000009",
        "BELADEBEXXX", "EURO-Überweisung", "ERSTATT.034/120/11640 EST-VERANL.", 2255.0)
    add(21, 1, "Bundeskasse Dienstort Halle", "DE00860000000000000010", "MARKDEF1860",
        "EURO-Überweisung", "DR 02.12.25 FRANKFURT/ MAIN", 39.90)

    z.sort(key=lambda r: (r[0][6:], r[0][3:5], r[0][:2]), reverse=True)
    vorgemerkt = [("15.07.2026", "vorgemerkt", "19grams", "n/a", "n/a",
                   "VISA Kartenzahlung", "Vorgemerkter Umsatz: VISA Kartenzahlung", -4.20)]
    return [";".join([*r[:7], _betrag(r[7]), "EUR"]) for r in vorgemerkt + z]


def csv_text(**kw) -> str:
    vorspann = [
        "Konto;Inhaber;Exportdatum",
        "000000000;Max Beispiel;08.07.2026, 16:03:45",
        "",
        "Allgemeine Informationen",
        "Konto;Inhaber;Exportdatum",
        "000000000;Max Beispiel;08.07.2026, 16:03:45",
        "Kontostand",
        "Saldo;Währung für Saldo;Datum;max. Verfügungsrahmen;Währung für max. Verfügungsrahmen",
        "1.298,68;EUR;08.07.2026;1.264,09;EUR",
        "Kontoumsätze",
        KOPF,
    ]
    return "\n".join(vorspann + zeilen(**kw)) + "\n"


def schreibe(pfad, **kw) -> str:
    # Wie der Originalexport: UTF-8 mit BOM.
    with open(pfad, "w", encoding="utf-8-sig", newline="\r\n") as fh:
        fh.write(csv_text(**kw))
    return str(pfad)
