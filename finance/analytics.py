"""Auswertungen: Aggregation nach Tag/Monat/Jahr, Kategorien, Fixkosten."""

from __future__ import annotations

import pandas as pd

from .categories import is_saving
from .merchants import clean_name, merchant_key


# ---------------------------------------------------------------------------
# Grund-Kennzahlen
#
# Einnahme/Ausgabe werden am VORZEICHEN festgemacht (Geld rein = Einnahme,
# Geld raus = Ausgabe) – nicht an der Kategorie. So zählen auch Erstattungen,
# Rückzahlungen von Freunden usw. korrekt als Eingang. Ausgenommen sind
# Überträge auf eigene Sparkonten (Kategorie-Typ "sparen"), die separat als
# "Sparen" ausgewiesen werden und keine echten Ausgaben sind.
# ---------------------------------------------------------------------------

def _masks(df: pd.DataFrame):
    """(is_saving, is_income, is_expense) als boolesche Series."""
    sav = df["category"].map(is_saving)
    inc = (~sav) & (df["amount"] > 0)
    exp = (~sav) & (df["amount"] < 0)
    return sav, inc, exp


def summary(df: pd.DataFrame) -> dict:
    """Gesamtsummen für Einnahmen, Ausgaben, Sparen, Saldo."""
    if df.empty:
        return {"einnahmen": 0.0, "ausgaben": 0.0, "sparen": 0.0,
                "saldo": 0.0, "sparquote": 0.0}
    sav, inc, exp = _masks(df)
    einnahmen = df.loc[inc, "amount"].sum()
    ausgaben = -df.loc[exp, "amount"].sum()          # positiv machen
    sparen = -df.loc[sav, "amount"].sum()            # netto auf Sparkonten
    saldo = df["amount"].sum()
    sparquote = (sparen / einnahmen * 100) if einnahmen > 0 else 0.0
    return {
        "einnahmen": float(einnahmen),
        "ausgaben": float(ausgaben),
        "sparen": float(sparen),
        "saldo": float(saldo),
        "sparquote": float(sparquote),
    }


def by_category(df: pd.DataFrame, typ: str = "ausgabe") -> pd.DataFrame:
    """Summen je Kategorie (Betrag positiv). typ: 'ausgabe'|'einnahme'|'sparen'."""
    if df.empty:
        return pd.DataFrame(columns=["category", "betrag"])
    sav, inc, exp = _masks(df)
    mask = {"einnahme": inc, "sparen": sav}.get(typ, exp)
    sub = df[mask]
    if sub.empty:
        return pd.DataFrame(columns=["category", "betrag"])
    grp = sub.groupby("category")["amount"].sum().reset_index()
    grp["betrag"] = grp["amount"].abs()
    grp = grp[["category", "betrag"]].sort_values("betrag", ascending=False)
    return grp[grp["betrag"] > 0].reset_index(drop=True)


# ---------------------------------------------------------------------------
# Zeitreihen: Tag / Monat / Jahr
# ---------------------------------------------------------------------------

def timeseries(df: pd.DataFrame, freq: str = "M") -> pd.DataFrame:
    """Einnahmen/Ausgaben/Sparen/Saldo je Periode.

    freq: 'D' (Tag), 'M' (Monat), 'Y' (Jahr).
    """
    cols = ["periode", "einnahmen", "ausgaben", "sparen", "saldo"]
    if df.empty:
        return pd.DataFrame(columns=cols)

    d = df.copy()
    sav, inc, exp = _masks(d)
    d["periode"] = d["date"].dt.to_period(freq).dt.to_timestamp()
    d["einnahmen"] = d["amount"].where(inc, 0.0)
    d["ausgaben"] = (-d["amount"]).where(exp, 0.0)
    d["sparen"] = (-d["amount"]).where(sav, 0.0)

    g = d.groupby("periode").agg(
        einnahmen=("einnahmen", "sum"),
        ausgaben=("ausgaben", "sum"),
        sparen=("sparen", "sum"),
    ).reset_index()
    g["saldo"] = g["einnahmen"] - g["ausgaben"] - g["sparen"]
    return g.sort_values("periode").reset_index(drop=True)


def monthly_average(df: pd.DataFrame) -> dict:
    """Durchschnitt je Monat für Einnahmen, Ausgaben und Sparen.

    Ein angebrochener letzter Monat (z. B. der laufende) wird ausgeklammert,
    damit er den Schnitt nicht nach unten zieht. ``monate`` gibt zurück, über
    wie viele vollständige Monate gemittelt wurde.
    """
    leer = {"einnahmen": 0.0, "ausgaben": 0.0, "sparen": 0.0, "monate": 0}
    if df.empty:
        return leer

    ts = timeseries(df, "M")
    if ts.empty:
        return leer

    # Letzten Monat verwerfen, wenn die Daten dort vor dem Monatsende enden.
    letzter = ts["periode"].max()
    max_datum = df["date"].max()
    monatsende = letzter + pd.offsets.MonthEnd(0)
    if max_datum < monatsende and len(ts) > 1:
        ts = ts[ts["periode"] < letzter]

    n = len(ts)
    if n == 0:
        return leer
    return {
        "einnahmen": float(ts["einnahmen"].sum() / n),
        "ausgaben": float(ts["ausgaben"].sum() / n),
        "sparen": float(ts["sparen"].sum() / n),
        "monate": int(n),
    }


def category_over_time(df: pd.DataFrame, freq: str = "M",
                       typ: str = "ausgabe") -> pd.DataFrame:
    """Pivot: Periode x Kategorie (Beträge positiv) – für gestapelte Diagramme."""
    if df.empty:
        return pd.DataFrame()
    sav, inc, exp = _masks(df)
    mask = {"einnahme": inc, "sparen": sav}.get(typ, exp)
    sub = df[mask].copy()
    if sub.empty:
        return pd.DataFrame()
    sub["periode"] = sub["date"].dt.to_period(freq).dt.to_timestamp()
    sub["betrag"] = sub["amount"].abs()
    piv = sub.pivot_table(index="periode", columns="category",
                          values="betrag", aggfunc="sum", fill_value=0.0)
    return piv.sort_index()


# ---------------------------------------------------------------------------
# Fixkosten-Erkennung
# ---------------------------------------------------------------------------

def detect_recurring(df: pd.DataFrame, min_months: int = 3,
                     max_per_month: float = 1.6) -> pd.DataFrame:
    """Erkennt wiederkehrende Zahlungen (Fixkosten & feste Sparbeträge).

    Gruppiert wird nach Händler/Konto UND ungefährem Betrag: eine Gruppe gilt
    als wiederkehrend, wenn derselbe Empfänger mit (nahezu) gleichem Betrag in
    mindestens ``min_months`` verschiedenen Monaten und höchstens ~1×/Monat
    auftaucht. Dadurch werden auch feste Überträge erkannt, deren Text nur
    "Dauerauftrag" lautet (z. B. Revolut −400, Trade Republic −800, Miete −637),
    während schwankende Ausgaben (Shopping, Essen) ausgeschlossen bleiben.

    Rückgabe je Gruppe: merchant, category, monate, median_betrag, tx_ids,
                        ist_sparen
    """
    cols = ["merchant", "category", "monate", "median_betrag", "tx_ids", "ist_sparen"]
    empty = pd.DataFrame(columns=cols)
    if df.empty:
        return empty

    sub = df[df["amount"] < 0].copy()          # nur Abflüsse
    if sub.empty:
        return empty

    sub["key"] = sub.apply(
        lambda r: merchant_key(r["counterparty"], r["description"],
                               r["booking_text"], r.get("bic") or ""),
        axis=1,
    )
    sub["betrag"] = sub["amount"].abs()
    sub["amt_round"] = sub["betrag"].round(0)     # auf ganze Euro bündeln
    sub["ym"] = sub["date"].dt.to_period("M").astype(str)
    sub = sub[sub["key"] != ""]

    # Häufig frequentierte Händler (z. B. Lidl, Restaurants) sind variable
    # Ausgaben, keine Fixkosten – auch wenn einzelne Beträge zufällig
    # wiederkehren. Eigene Konten (BIC) sind ausgenommen, da dort neben festen
    # Sparraten auch andere Überträge laufen.
    keyfreq = sub.groupby("key").agg(n=("id", "size"), m=("ym", "nunique"))
    frequent = {
        k for k, row in keyfreq.iterrows()
        if not k.startswith("bic:") and row["n"] / max(row["m"], 1) > 1.5
    }

    results = []
    for (key, _amt), grp in sub.groupby(["key", "amt_round"]):
        if key in frequent:
            continue
        months = grp["ym"].nunique()
        if months < min_months:
            continue
        if len(grp) > months * max_per_month:      # ~1×/Monat
            continue
        first = grp.iloc[0]
        name = clean_name(first["counterparty"], first["description"],
                          first.get("bic") or "")
        cat = grp["category"].mode().iat[0]
        results.append({
            "merchant": name or key,
            "category": cat,
            "monate": int(months),
            "median_betrag": float(grp["betrag"].median()),
            "tx_ids": grp["id"].tolist(),
            "ist_sparen": bool(is_saving(cat)),
        })

    out = pd.DataFrame(results, columns=cols)
    if out.empty:
        return empty
    return out.sort_values("median_betrag", ascending=False).reset_index(drop=True)


def monthly_fixed_costs(df: pd.DataFrame) -> float:
    """Monatliche Fixkosten = Summe wiederkehrender Zahlungen OHNE Sparen."""
    rec = detect_recurring(df)
    if rec.empty:
        return 0.0
    return float(rec.loc[~rec["ist_sparen"], "median_betrag"].sum())


def monthly_savings(df: pd.DataFrame) -> float:
    """Monatlich fest gesparter Betrag (wiederkehrende Sparkonten-Überträge)."""
    rec = detect_recurring(df)
    if rec.empty:
        return 0.0
    return float(rec.loc[rec["ist_sparen"], "median_betrag"].sum())


def available_years(df: pd.DataFrame) -> list[int]:
    if df.empty:
        return []
    return sorted(df["year"].unique().tolist())
