"""Lokaler HTTP-Server für die Desktop-Oberfläche.

Stellt die vorhandene Logik (Import, Kategorisierung, ML, Auswertung) als
schlanke JSON-Schnittstelle bereit und liefert die Oberfläche aus ``webui/``
aus. Der Server lauscht ausschliesslich auf 127.0.0.1 – es ist nichts von
aussen erreichbar, alle Daten bleiben auf dem Rechner.
"""

from __future__ import annotations

import io
import os
from datetime import date

import pandas as pd
from flask import Flask, jsonify, request, send_from_directory

from . import analytics, ml, sampledata, storage
from .categories import (CATEGORIES, CATEGORY_NAMES, COLOR_MAP,
                         INCOME_UNCATEGORIZED, SERIES_COLORS, UNCATEGORIZED)
from .importer import parse_file

WEBUI_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "webui")


def _f(v) -> float:
    """NaN/None -> 0.0, damit JSON gültig bleibt."""
    try:
        if v is None or pd.isna(v):
            return 0.0
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _filter(df: pd.DataFrame) -> pd.DataFrame:
    """Wendet Jahr-/Monats-/Kategorie-Filter aus der Anfrage an."""
    if df.empty:
        return df
    jahr = request.args.get("jahr", "")
    monat = request.args.get("monat", "")
    kategorien = [c for c in request.args.getlist("kategorie") if c]

    d = df
    if jahr and jahr != "alle":
        d = d[d["year"] == int(jahr)]
    if monat and monat != "alle":
        d = d[d["month"] == monat]
    if kategorien:
        d = d[d["category"].isin(kategorien)]
    return d


def create_app() -> Flask:
    app = Flask(__name__, static_folder=None)
    storage.init_db()

    # ---------------- Oberfläche ausliefern ----------------
    @app.get("/")
    def index():
        return send_from_directory(WEBUI_DIR, "index.html")

    @app.get("/<path:datei>")
    def statisch(datei: str):
        return send_from_directory(WEBUI_DIR, datei)

    # ---------------- Stammdaten ----------------
    @app.get("/api/meta")
    def meta():
        df = storage.load_dataframe()
        jahre = analytics.available_years(df)
        monate = sorted(df["month"].unique().tolist()) if not df.empty else []
        return jsonify({
            "kategorien": CATEGORY_NAMES,
            "farben": COLOR_MAP,
            "serienfarben": SERIES_COLORS,
            "kategorie_typen": {c.name: c.typ for c in CATEGORIES},
            "auffang": {"ausgabe": UNCATEGORIZED, "einnahme": INCOME_UNCATEGORIZED},
            "jahre": jahre,
            "monate": monate,
            "anzahl": int(len(df)),
            "von": df["date"].min().strftime("%d.%m.%Y") if not df.empty else "",
            "bis": df["date"].max().strftime("%d.%m.%Y") if not df.empty else "",
            "ml_verfuegbar": ml.sklearn_available(),
            "ml_trainiert": ml.model_exists(),
            "gelernte_regeln": storage.count_learned(),
            "manuelle_fixkosten": storage.count_recurring_manual(),
            "demo_anzahl": storage.count_demo(),
        })

    # ---------------- Übersicht ----------------
    @app.get("/api/uebersicht")
    def uebersicht():
        alle = storage.load_dataframe()
        df = _filter(alle)
        freq = {"tag": "D", "monat": "M", "jahr": "Y"}.get(
            request.args.get("aufloesung", "monat"), "M")

        s = analytics.summary(df)
        avg = analytics.monthly_average(df)
        fix = analytics.monthly_fixed_costs(df)

        ts = analytics.timeseries(df, freq)
        reihen = [{
            "periode": p.strftime("%Y-%m-%d"),
            "label": p.strftime("%d.%m.%Y" if freq == "D"
                                else ("%m/%Y" if freq == "M" else "%Y")),
            "einnahmen": _f(e), "ausgaben": _f(a),
            "sparen": _f(sp), "saldo": _f(sa),
        } for p, e, a, sp, sa in zip(ts["periode"], ts["einnahmen"], ts["ausgaben"],
                                     ts["sparen"], ts["saldo"])] if not ts.empty else []

        def kat_liste(typ: str):
            k = analytics.by_category(df, typ)
            if k.empty:
                return []
            return [{"kategorie": r.category, "betrag": _f(r.betrag)}
                    for r in k.itertuples()]

        # Kategorien im Zeitverlauf (gestapelt)
        def verlauf(typ: str):
            piv = analytics.category_over_time(df, freq, typ)
            if piv.empty:
                return {"perioden": [], "kategorien": [], "werte": {}}
            perioden = [p.strftime("%d.%m.%Y" if freq == "D"
                                   else ("%m/%Y" if freq == "M" else "%Y"))
                        for p in piv.index]
            return {
                "perioden": perioden,
                "kategorien": list(piv.columns),
                "werte": {str(c): [_f(v) for v in piv[c]] for c in piv.columns},
            }

        return jsonify({
            "summe": {k: _f(v) for k, v in s.items()},
            "schnitt": {**{k: _f(v) for k, v in avg.items() if k != "monate"},
                        "monate": int(avg["monate"])},
            "fixkosten_monat": _f(fix),
            "reihen": reihen,
            "ausgaben_kategorien": kat_liste("ausgabe"),
            "einnahmen_kategorien": kat_liste("einnahme"),
            "verlauf_ausgaben": verlauf("ausgabe"),
            "verlauf_einnahmen": verlauf("einnahme"),
        })

    # ---------------- Fixkosten ----------------
    @app.get("/api/fixkosten")
    def fixkosten():
        df = _filter(storage.load_dataframe())
        rec = analytics.detect_recurring(df)
        if rec.empty:
            return jsonify({"fixkosten": [], "sparen": [],
                            "summe_fixkosten": 0.0, "summe_sparen": 0.0})

        def zeilen(teil: pd.DataFrame):
            return [{
                "empfaenger": r.merchant, "kategorie": r.category,
                "monate": int(r.monate), "betrag": _f(r.median_betrag),
                "manuell": bool(r.manuell),
            } for r in teil.itertuples()]

        fx = rec[~rec["ist_sparen"]]
        sp = rec[rec["ist_sparen"]]
        return jsonify({
            "fixkosten": zeilen(fx),
            "sparen": zeilen(sp),
            "summe_fixkosten": _f(fx["median_betrag"].sum()),
            "summe_sparen": _f(sp["median_betrag"].sum()),
        })

    # ---------------- Transaktionen ----------------
    @app.get("/api/transaktionen")
    def transaktionen():
        df = _filter(storage.load_dataframe())
        suche = (request.args.get("suche") or "").strip()
        if suche and not df.empty:
            maske = (df["counterparty"].str.contains(suche, case=False, na=False) |
                     df["description"].str.contains(suche, case=False, na=False))
            df = df[maske]
        if df.empty:
            return jsonify({"zeilen": [], "gesamt": 0})

        df = df.sort_values("date", ascending=False)
        grenze = int(request.args.get("limit", 500))
        gesamt = len(df)
        zeilen = [{
            "id": int(r.id),
            "datum": r.date.strftime("%d.%m.%Y"),
            "betrag": _f(r.amount),
            "kategorie": r.category,
            "empfaenger": r.counterparty or "",
            "zweck": r.description or "",
            "fixkosten": bool(r.is_recurring),
            "kategorie_manuell": bool(r.category_manual),
        } for r in df.head(grenze).itertuples()]
        return jsonify({"zeilen": zeilen, "gesamt": gesamt})

    @app.post("/api/transaktionen/<int:tx_id>")
    def transaktion_aendern(tx_id: int):
        daten = request.get_json(silent=True) or {}
        mit = 0
        if "kategorie" in daten:
            mit += storage.update_category(tx_id, daten["kategorie"], manual=True)
        if "fixkosten" in daten:
            mit += storage.set_recurring(tx_id, bool(daten["fixkosten"]), manual=True)
        return jsonify({"ok": True, "mitgeaendert": mit})

    # ---------------- Import ----------------
    @app.post("/api/import")
    def importieren():
        neu = uebersprungen = gelesen = 0
        fehler, diagnose = [], []
        for f in request.files.getlist("dateien"):
            try:
                txs = parse_file(f.filename, f.read())
                n, s = storage.add_transactions(txs)
                neu += n
                uebersprungen += s
                gelesen += len(txs)
                diagnose.append(f"{f.filename}: {len(txs)} Zeilen gelesen "
                                f"→ {n} neu, {s} Duplikate")
            except Exception as exc:  # noqa: BLE001
                fehler.append(f"{f.filename}: {exc}")
                diagnose.append(f"{f.filename}: FEHLER – {exc}")
        try:
            storage.recategorize_all()
            storage.set_recurring_bulk(_paare())
        except Exception as exc:  # noqa: BLE001
            diagnose.append(f"Nachbereitung übersprungen: {exc}")
        return jsonify({"neu": neu, "duplikate": uebersprungen, "gelesen": gelesen,
                        "fehler": fehler, "diagnose": "\n".join(diagnose)})

    # ---------------- Aktionen ----------------
    @app.post("/api/aktion/<name>")
    def aktion(name: str):
        daten = request.get_json(silent=True) or {}
        if name == "neu-kategorisieren":
            n = storage.recategorize_all()
            storage.set_recurring_bulk(_paare())
            return jsonify({"ok": True, "meldung": f"{n} Umsätze neu kategorisiert."})

        if name == "modell-trainieren":
            try:
                m = storage.train_model()
                schwelle = float(daten.get("schwelle", ml.DEFAULT_THRESHOLD))
                n = storage.recategorize_all(ml_threshold=schwelle)
                storage.set_recurring_bulk(_paare())
                acc = m.get("accuracy")
                zusatz = f", Trefferquote ≈ {acc*100:.0f} %" if acc else ""
                return jsonify({"ok": True, "meldung":
                                f"Modell trainiert auf {m['n_samples']} Buchungen "
                                f"in {m['n_classes']} Kategorien{zusatz}. "
                                f"{n} Umsätze neu kategorisiert."})
            except RuntimeError as exc:
                return jsonify({"ok": False, "meldung": str(exc)}), 400

        if name == "modell-loeschen":
            ml.delete_model()
            storage.recategorize_all()
            return jsonify({"ok": True, "meldung": "Modell gelöscht."})

        if name == "demo-laden":
            neu, vorhanden = storage.add_transactions(
                sampledata.generate(up_to=date.today()))
            storage.set_recurring_bulk(_paare())
            return jsonify({"ok": True, "meldung":
                            f"{neu} Demo-Umsätze geladen ({vorhanden} bereits da)."})

        if name == "demo-entfernen":
            n = storage.clear_demo()
            storage.set_recurring_bulk(_paare())
            return jsonify({"ok": True, "meldung": f"{n} Demo-Umsätze entfernt."})

        if name == "gelernte-loeschen":
            storage.clear_learned()
            storage.recategorize_all()
            return jsonify({"ok": True, "meldung": "Gelernte Regeln gelöscht."})

        if name == "fixkosten-zuruecksetzen":
            n = storage.clear_recurring_manual()
            storage.set_recurring_bulk(_paare())
            return jsonify({"ok": True, "meldung":
                            f"{n} manuelle Fixkosten-Entscheidungen verworfen."})

        if name == "alles-loeschen":
            storage.clear_all()
            return jsonify({"ok": True, "meldung": "Alle Umsätze gelöscht."})

        return jsonify({"ok": False, "meldung": f"Unbekannte Aktion: {name}"}), 404

    @app.get("/api/export.csv")
    def export():
        df = storage.load_dataframe()
        if df.empty:
            return "", 204
        csv = df[["date", "amount", "currency", "category", "counterparty",
                  "description", "is_recurring"]].copy()
        csv["date"] = csv["date"].dt.strftime("%Y-%m-%d")
        puffer = io.StringIO()
        csv.to_csv(puffer, index=False)
        return puffer.getvalue(), 200, {
            "Content-Type": "text/csv; charset=utf-8",
            "Content-Disposition": "attachment; filename=umsaetze_export.csv",
        }

    return app


def _paare() -> list[tuple[int, bool]]:
    """(id, ist_fixkosten) für alle Umsätze – für set_recurring_bulk."""
    df = storage.load_dataframe()
    if df.empty:
        return []
    rec = analytics.detect_recurring(df)
    ids = {i for lst in rec["tx_ids"].tolist() for i in lst} if not rec.empty else set()
    return [(int(i), i in ids) for i in df["id"].tolist()]
