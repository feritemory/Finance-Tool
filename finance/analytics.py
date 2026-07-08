"""Auswertungen: Aggregation nach Tag/Monat/Jahr, Kategorien, Fixkosten."""

from __future__ import annotations

import re

import pandas as pd

from .categories import is_saving


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

def _normalize_merchant(name: str, description: str, category: str) -> str:
    base = (name or "").lower().strip()
    if not base:
        # Fallback: erste sinnvollen Wörter des Verwendungszwecks
        base = (description or "").lower().strip()
    base = re.sub(r"[0-9]{4,}", "", base)          # lange Ziffernfolgen entfernen
    base = re.sub(r"\b(datum|nr|ref|beleg|mandat|iban)\b.*", "", base)
    base = re.sub(r"[^a-zäöüß ]", " ", base)
    base = re.sub(r"\s+", " ", base).strip()
    tokens = base.split()
    key = " ".join(tokens[:3]) if tokens else category.lower()
    return key or category.lower()


def detect_recurring(df: pd.DataFrame, min_months: int = 3,
                     max_cv: float = 0.12, max_per_month: float = 1.4) -> pd.DataFrame:
    """Erkennt echte Fixkosten (wiederkehrende Zahlungen).

    Eine Zahlung gilt als Fixkosten, wenn ein Empfänger
      * in mindestens ``min_months`` verschiedenen Monaten auftaucht,
      * durchschnittlich höchstens ~1× pro Monat gebucht wird
        (``max_per_month``) – schließt Lebensmittel/Essen aus, die mehrfach
        pro Monat anfallen,
      * mit weitgehend konstantem Betrag (Variationskoeffizient ≤ ``max_cv``) –
        schließt schwankende Ausgaben wie Shopping aus.

    Rückgabe je erkannter Fixkosten-Gruppe:
        merchant, category, monate, median_betrag, tx_ids
    """
    empty = pd.DataFrame(columns=["merchant", "category", "monate",
                                  "median_betrag", "tx_ids"])
    if df.empty:
        return empty

    # nur Ausgaben & Sparen betrachten (Einnahmen sind keine Fixkosten)
    sub = df[df["amount"] < 0].copy()
    if sub.empty:
        return empty

    sub["merchant"] = sub.apply(
        lambda r: _normalize_merchant(r["counterparty"], r["description"], r["category"]),
        axis=1,
    )
    sub["betrag"] = sub["amount"].abs()
    sub["ym"] = sub["date"].dt.to_period("M").astype(str)

    results = []
    for merchant, grp in sub.groupby("merchant"):
        if not merchant:
            continue
        months = grp["ym"].nunique()
        if months < min_months:
            continue
        # ~1× pro Monat? (variable, häufige Ausgaben ausschließen)
        if len(grp) / months > max_per_month:
            continue
        median = grp["betrag"].median()
        mean = grp["betrag"].mean()
        if median <= 0 or mean <= 0:
            continue
        # Betrags-Konstanz: Variationskoeffizient (Streuung relativ zum Mittel)
        cv = grp["betrag"].std(ddof=0) / mean
        if cv > max_cv:
            continue
        results.append({
            "merchant": merchant,
            "category": grp["category"].mode().iat[0],
            "monate": int(months),
            "median_betrag": float(median),
            "tx_ids": grp["id"].tolist(),
        })

    out = pd.DataFrame(results)
    if out.empty:
        return empty
    return out.sort_values("median_betrag", ascending=False).reset_index(drop=True)


def monthly_fixed_costs(df: pd.DataFrame) -> float:
    """Geschätzte monatliche Fixkosten = Summe der Mediane erkannter Fixkosten."""
    rec = detect_recurring(df)
    if rec.empty:
        return 0.0
    return float(rec["median_betrag"].sum())


def available_years(df: pd.DataFrame) -> list[int]:
    if df.empty:
        return []
    return sorted(df["year"].unique().tolist())
