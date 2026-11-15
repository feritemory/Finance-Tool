"""Anwendungsschicht zwischen Oberfläche und Fachlogik.

Hier werden die Rohdaten gefiltert, ausgewertet und in einfache Strukturen
(dicts/lists) übersetzt, die die Oberfläche direkt anzeigen kann. Die Schicht
kennt kein Qt – dadurch lässt sie sich ohne Fenster testen.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import date

import pandas as pd

from . import analytics, ml, paths, sampledata, storage
from .categories import CATEGORIES, CATEGORY_NAMES
from .importer import parse_file

FREQ = {"tag": "D", "monat": "M", "jahr": "Y"}
DATUMSFORMAT = {"D": "%d.%m.%Y", "M": "%m/%Y", "Y": "%Y"}
_REIHENFOLGE = {name: i for i, name in enumerate(CATEGORY_NAMES)}


@dataclass
class Filter:
    jahr: str = "alle"              # "alle" oder "2026"
    monat: str = "alle"             # "alle" oder "2026-03"
    kategorie: str = ""             # "" = alle

    def anwenden(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return df
        d = df
        if self.jahr != "alle":
            d = d[d["year"] == int(self.jahr)]
        if self.monat != "alle":
            d = d[d["month"] == self.monat]
        if self.kategorie:
            d = d[d["category"] == self.kategorie]
        return d


def _f(v) -> float:
    """NaN/None -> 0.0."""
    try:
        return 0.0 if v is None or pd.isna(v) else float(v)
    except (TypeError, ValueError):
        return 0.0


def _nach_kategorie_ordnen(namen) -> list[str]:
    """Feste Kategorie-Reihenfolge (= Farb-Slot-Reihenfolge) statt Alphabet –
    so liegen in gestapelten Balken stets die geprüften Farbnachbarn
    nebeneinander."""
    return sorted(namen, key=lambda n: _REIHENFOLGE.get(n, 999))


# ---------------------------------------------------------------------------
# Stammdaten
# ---------------------------------------------------------------------------

def meta() -> dict:
    df = storage.load_dataframe()
    return {
        "jahre": [str(j) for j in analytics.available_years(df)],
        "monate": sorted(df["month"].unique().tolist()) if not df.empty else [],
        "anzahl": int(len(df)),
        "von": df["date"].min().strftime("%d.%m.%Y") if not df.empty else "",
        "bis": df["date"].max().strftime("%d.%m.%Y") if not df.empty else "",
        "ml_verfuegbar": ml.sklearn_available(),
        "ml_trainiert": ml.model_exists(),
        "gelernte_regeln": storage.count_learned(),
        "manuelle_fixkosten": storage.count_recurring_manual(),
        "demo_anzahl": storage.count_demo(),
        "datenordner": str(paths.data_dir()),
    }


# ---------------------------------------------------------------------------
# Übersicht
# ---------------------------------------------------------------------------

def uebersicht(flt: Filter, aufloesung: str = "monat") -> dict:
    df = flt.anwenden(storage.load_dataframe())
    freq = FREQ.get(aufloesung, "M")
    fmt = DATUMSFORMAT[freq]

    ts = analytics.timeseries(df, freq)
    reihen = [] if ts.empty else [{
        "label": p.strftime(fmt), "einnahmen": _f(e), "ausgaben": _f(a),
        "sparen": _f(s), "saldo": _f(sa),
    } for p, e, a, s, sa in zip(ts["periode"], ts["einnahmen"], ts["ausgaben"],
                                ts["sparen"], ts["saldo"])]

    def kategorien(typ: str) -> list[dict]:
        k = analytics.by_category(df, typ)
        return [] if k.empty else [
            {"kategorie": r.category, "betrag": _f(r.betrag)} for r in k.itertuples()]

    def verlauf(typ: str) -> dict:
        piv = analytics.category_over_time(df, freq, typ)
        if piv.empty:
            return {"perioden": [], "kategorien": [], "werte": {}}
        spalten = _nach_kategorie_ordnen(piv.columns)
        return {
            "perioden": [p.strftime(fmt) for p in piv.index],
            "kategorien": spalten,
            "werte": {c: [_f(v) for v in piv[c]] for c in spalten},
        }

    avg = analytics.monthly_average(df)
    return {
        "summe": {k: _f(v) for k, v in analytics.summary(df).items()},
        "schnitt": {"einnahmen": _f(avg["einnahmen"]), "ausgaben": _f(avg["ausgaben"]),
                    "sparen": _f(avg["sparen"]), "monate": int(avg["monate"])},
        "fixkosten_monat": _f(analytics.monthly_fixed_costs(df)),
        "reihen": reihen,
        "ausgaben_kategorien": kategorien("ausgabe"),
        "verlauf_ausgaben": verlauf("ausgabe"),
        "verlauf_einnahmen": verlauf("einnahme"),
    }


# ---------------------------------------------------------------------------
# Fixkosten
# ---------------------------------------------------------------------------

def fixkosten(flt: Filter) -> dict:
    rec = analytics.detect_recurring(flt.anwenden(storage.load_dataframe()))
    if rec.empty:
        return {"fixkosten": [], "sparen": [], "summe_fixkosten": 0.0,
                "summe_sparen": 0.0}

    def zeilen(teil: pd.DataFrame) -> list[dict]:
        return [{
            "empfaenger": r.merchant, "kategorie": r.category,
            "monate": int(r.monate), "rhythmus": r.rhythmus,
            "je_zahlung": _f(r.median_betrag), "monatsbetrag": _f(r.monatsbetrag),
            "manuell": bool(r.manuell),
        } for r in teil.itertuples()]

    fx, sp = rec[~rec["ist_sparen"]], rec[rec["ist_sparen"]]
    return {
        "fixkosten": zeilen(fx), "sparen": zeilen(sp),
        "summe_fixkosten": _f(fx["monatsbetrag"].sum()),
        "summe_sparen": _f(sp["monatsbetrag"].sum()),
    }


# ---------------------------------------------------------------------------
# Transaktionen
# ---------------------------------------------------------------------------

def transaktionen(flt: Filter, suche: str = "") -> list[dict]:
    df = flt.anwenden(storage.load_dataframe())
    suche = (suche or "").strip()
    if suche and not df.empty:
        maske = (df["counterparty"].str.contains(suche, case=False, na=False, regex=False)
                 | df["description"].str.contains(suche, case=False, na=False, regex=False))
        df = df[maske]
    if df.empty:
        return []
    df = df.sort_values(["date", "id"], ascending=[False, False])
    return [{
        "id": int(r.id), "datum": r.date.to_pydatetime().date(),
        "betrag": _f(r.amount), "kategorie": r.category,
        "empfaenger": r.counterparty or "", "zweck": r.description or "",
        "fixkosten": bool(r.is_recurring),
    } for r in df.itertuples()]


def kategorie_setzen(tx_id: int, kategorie: str) -> int:
    """Setzt die Kategorie, lernt den Händler; Rückgabe: mitgeänderte Buchungen."""
    if kategorie not in CATEGORY_NAMES:
        raise ValueError(f"Unbekannte Kategorie: {kategorie}")
    mit = storage.update_category(tx_id, kategorie, manual=True)
    fixkosten_neu_bewerten()
    return mit


def fixkosten_setzen(tx_id: int, ist_fix: bool) -> int:
    """Setzt das Fixkosten-Kennzeichen für den ganzen Empfänger."""
    return storage.set_recurring(tx_id, ist_fix, manual=True)


def fixkosten_neu_bewerten() -> None:
    """Schreibt das automatisch erkannte Fixkosten-Kennzeichen zurück
    (manuelle Entscheidungen bleiben unangetastet)."""
    df = storage.load_dataframe()
    if df.empty:
        return
    rec = analytics.detect_recurring(df)
    ids = {i for lst in rec["tx_ids"] for i in lst} if not rec.empty else set()
    storage.set_recurring_bulk([(int(i), i in ids) for i in df["id"]])


# ---------------------------------------------------------------------------
# Import
# ---------------------------------------------------------------------------

@dataclass
class ImportErgebnis:
    neu: int = 0
    duplikate: int = 0
    gelesen: int = 0
    fehler: list[str] = field(default_factory=list)
    diagnose: list[str] = field(default_factory=list)


def importieren(dateien: list[str]) -> ImportErgebnis:
    erg = ImportErgebnis()
    for pfad in dateien:
        name = os.path.basename(pfad)
        try:
            with open(pfad, "rb") as fh:
                txs = parse_file(name, fh.read())
            n, s = storage.add_transactions(txs)
            erg.neu += n
            erg.duplikate += s
            erg.gelesen += len(txs)
            erg.diagnose.append(f"{name}: {len(txs)} Zeilen gelesen → {n} neu, {s} Duplikate")
        except Exception as exc:  # noqa: BLE001 – jede Datei einzeln melden
            erg.fehler.append(f"{name}: {exc}")
            erg.diagnose.append(f"{name}: FEHLER – {exc}")
    try:
        storage.recategorize_all()
        fixkosten_neu_bewerten()
    except Exception as exc:  # noqa: BLE001
        erg.diagnose.append(f"Nachbereitung übersprungen: {exc}")
    return erg


def psd2_import(transaktionen_liste) -> int:
    """Speichert über PSD2 abgerufene Umsätze und bereitet sie nach."""
    neu, _ = storage.add_transactions(transaktionen_liste)
    storage.recategorize_all()
    fixkosten_neu_bewerten()
    return neu


# ---------------------------------------------------------------------------
# Aktionen aus den Einstellungen
# ---------------------------------------------------------------------------

def modell_trainieren(schwelle: float) -> str:
    m = storage.train_model()                       # wirft RuntimeError bei zu wenig Daten
    n = storage.recategorize_all(ml_threshold=schwelle)
    fixkosten_neu_bewerten()
    acc = m.get("accuracy")
    zusatz = f", Trefferquote ≈ {acc * 100:.0f} %" if acc else ""
    return (f"Modell trainiert auf {m['n_samples']} Buchungen in "
            f"{m['n_classes']} Kategorien{zusatz}. {n} Umsätze neu kategorisiert.")


def modell_loeschen() -> str:
    ml.delete_model()
    storage.recategorize_all()
    fixkosten_neu_bewerten()
    return "Modell gelöscht. Es gelten wieder nur Regeln und gelernte Händler."


def neu_kategorisieren() -> str:
    n = storage.recategorize_all()
    fixkosten_neu_bewerten()
    return f"{n} Umsätze neu kategorisiert."


def gelernte_loeschen() -> str:
    storage.clear_learned()
    storage.recategorize_all()
    fixkosten_neu_bewerten()
    return "Gelernte Händler-Regeln gelöscht."


def fixkosten_zuruecksetzen() -> str:
    n = storage.clear_recurring_manual()
    fixkosten_neu_bewerten()
    return f"{n} manuelle Fixkosten-Entscheidungen verworfen."


def demo_laden() -> str:
    neu, vorhanden = storage.add_transactions(sampledata.generate(up_to=date.today()))
    fixkosten_neu_bewerten()
    return f"{neu} Demo-Umsätze geladen ({vorhanden} waren schon vorhanden)."


def demo_entfernen() -> str:
    n = storage.clear_demo()
    fixkosten_neu_bewerten()
    return f"{n} Demo-Umsätze entfernt. Deine echten Umsätze bleiben erhalten."


def alles_loeschen() -> str:
    storage.clear_all()
    return "Alle Umsätze gelöscht."


def datenbank_uebernehmen(pfad: str) -> str:
    info = storage.adopt_database(pfad)
    storage.recategorize_all()
    fixkosten_neu_bewerten()
    text = (f"{info['umsaetze']} Umsätze und {info['regeln']} gelernte Regeln "
            "übernommen.")
    if info["sicherung"]:
        text += " Die bisherige Datenbank wurde als finance.db.bak gesichert."
    return text


def exportieren(ziel: str) -> int:
    df = storage.load_dataframe()
    if df.empty:
        raise ValueError("Es sind keine Umsätze vorhanden.")
    out = df[["date", "amount", "currency", "category", "counterparty",
              "description", "is_recurring"]].copy()
    out["date"] = out["date"].dt.strftime("%d.%m.%Y")
    out.columns = ["Datum", "Betrag", "Währung", "Kategorie", "Empfänger",
                   "Verwendungszweck", "Fixkosten"]
    # Semikolon + Dezimalkomma + BOM: öffnet sich in deutschem Excel korrekt.
    out.to_csv(ziel, index=False, sep=";", decimal=",", encoding="utf-8-sig")
    return len(out)


def kategorie_typ(name: str) -> str:
    for c in CATEGORIES:
        if c.name == name:
            return c.typ
    return "ausgabe"
