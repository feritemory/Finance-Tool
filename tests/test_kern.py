"""Tests für Import, Kategorisierung, Auswertung und Service-Schicht.

Jeder Test steht für ein Problem, das im echten Betrieb aufgetreten ist.
"""

from datetime import date

import pytest

from finance import analytics, paths, service, storage
from finance.importer import parse_amount, parse_date, parse_file


def _laden(consors_csv):
    erg = service.importieren([consors_csv])
    assert not erg.fehler, erg.fehler
    return storage.load_dataframe()


# --- Parser ----------------------------------------------------------------

@pytest.mark.parametrize("roh, erwartet", [
    ("-1.234,56", -1234.56), ("1234,56", 1234.56), ("12.50", 12.50),
    ("1.234", 1234.0), ("-49,99 €", -49.99), ("3.304,55", 3304.55),
])
def test_betraege_deutsch_und_englisch(roh, erwartet):
    assert parse_amount(roh) == erwartet


def test_datum():
    assert parse_date("08.07.2026") == date(2026, 7, 8)
    assert parse_date("vorgemerkt") is None


def test_consorsbank_vorspann_und_vorgemerkte(consors_csv):
    txs = parse_file("export.csv", open(consors_csv, "rb").read())
    # Vorspann "Konto;Inhaber;Exportdatum" darf nicht als Kopfzeile gelten,
    # vorgemerkte Umsätze werden ausgelassen.
    assert len(txs) > 100
    assert all(t.counterparty != "19grams" for t in txs)
    assert any(t.bic.startswith("TRBKDEBB") for t in txs)


def test_duplikate_beim_zweiten_import(consors_csv):
    erste = service.importieren([consors_csv])
    zweite = service.importieren([consors_csv])
    assert erste.neu > 100
    assert zweite.neu == 0 and zweite.duplikate == erste.neu


# --- Kategorisierung ---------------------------------------------------------

def test_kategorien_aus_echtem_format(consors_csv):
    df = _laden(consors_csv)

    def kat(teil, betrag=None):
        sel = df[df["counterparty"].str.contains(teil, regex=False)
                 | df["description"].str.contains(teil, regex=False)]
        if betrag is not None:
            sel = sel[sel["amount"] == betrag]
        return set(sel["category"])

    assert kat("BEZUEGE") == {"Gehalt"}
    # Trade Republic / Revolut nur über die BIC erkennbar ("Dauerauftrag")
    assert kat("Max Beispiel", -800.0) == {"Überweisung an Sparkonten"}
    assert kat("Max Beispiel", -400.0) == {"Überweisung an Sparkonten"}
    assert kat("Urban Sp orts") == {"Sport"}             # zerrissenes Wort
    assert kat("Miete Musterstr") == {"Wohnkosten inkl. Internet und Handykosten"}
    assert kat("BUKA HALLE DARLEHEN") == {"Bafög-Rückzahlung"}
    assert kat("ERSTATT") == {"Sonstige Einnahmen"}      # Steuererstattung
    # Dienstreise-Erstattung der Bundeskasse ist kein Gehalt und keine Rückzahlung
    assert kat("DR 02.12.25") == {"Sonstige Einnahmen"}


def test_einnahmen_ausgaben_nach_vorzeichen(consors_csv):
    df = _laden(consors_csv)
    s = analytics.summary(df)
    # Die Steuererstattung (+2255) ist eine Einnahme, keine "negative Ausgabe".
    assert s["einnahmen"] > df[df["category"] == "Gehalt"]["amount"].sum()
    assert s["ausgaben"] > 0 and s["sparen"] > 0


def test_lernen_aus_korrektur(consors_csv):
    df = _laden(consors_csv)
    gr = df[df["counterparty"].str.contains("Golden Rice")]
    assert len(gr) > 1
    mit = service.kategorie_setzen(int(gr.iloc[0]["id"]), "Auswärts Essen und Trinken")
    assert mit == len(gr) - 1
    df = storage.load_dataframe()
    assert set(df[df["counterparty"].str.contains("Golden Rice")]["category"]) == \
        {"Auswärts Essen und Trinken"}
    # ...und auch für künftige Importe (gelernte Regel bleibt nach Löschen der Umsätze)
    storage.clear_all()
    service.importieren([consors_csv])
    df = storage.load_dataframe()
    assert set(df[df["counterparty"].str.contains("Golden Rice")]["category"]) == \
        {"Auswärts Essen und Trinken"}


# --- Fixkosten -----------------------------------------------------------------

def test_fixkosten_erkennung(consors_csv):
    df = _laden(consors_csv)
    rec = analytics.detect_recurring(df)
    namen = " | ".join(rec["merchant"])
    assert "Erika Mustermann" in namen and "S-Bahn" in namen
    assert "Lidl" not in namen                       # häufiger Händler ≠ Fixkosten
    sparen = rec[rec["ist_sparen"]]
    assert sorted(sparen["monatsbetrag"].round(2)) == [400.0, 800.0]


def test_vierteljaehrliche_zahlung_wird_umgerechnet(consors_csv):
    df = _laden(consors_csv)
    # Im Halbjahr nur 2 Zahlungen (Jan + Apr) – zu wenig für die Automatik,
    # also wie im echten Leben per Häkchen als Fixkosten markieren.
    assert "Bafög-Rückzahlung" not in set(analytics.detect_recurring(df)["category"])
    tx = df[df["description"].str.contains("BUKA HALLE")].iloc[0]
    service.fixkosten_setzen(int(tx["id"]), True)
    rec = analytics.detect_recurring(storage.load_dataframe())
    z = rec[rec["category"] == "Bafög-Rückzahlung"].iloc[0]
    assert z["rhythmus"] == "vierteljährlich"
    assert z["median_betrag"] == 390.0 and z["monatsbetrag"] == pytest.approx(130.0)


def test_manuelles_fixkosten_haekchen_wirkt(consors_csv):
    df = _laden(consors_csv)
    vorher = analytics.monthly_fixed_costs(df)
    assert "S-Bahn Berlin GmbH" in set(analytics.detect_recurring(df)["merchant"])

    # Häkchen entfernen → verschwindet, Summe sinkt um genau den Monatsbetrag
    sbahn = df[df["counterparty"].str.contains("S-Bahn")].iloc[0]
    mit = service.fixkosten_setzen(int(sbahn["id"]), False)
    assert mit == 5                                   # alle 6 Monate betroffen
    df = storage.load_dataframe()
    assert "S-Bahn Berlin GmbH" not in set(analytics.detect_recurring(df)["merchant"])
    assert analytics.monthly_fixed_costs(df) == pytest.approx(vorher - 59.85, abs=0.01)

    # Häkchen setzen bei etwas, das die Automatik nie erkennen würde
    gr = df[df["counterparty"].str.contains("Golden Rice")].iloc[0]
    service.fixkosten_setzen(int(gr["id"]), True)
    rec = analytics.detect_recurring(storage.load_dataframe())
    assert rec[rec["merchant"].str.contains("Golden Rice")]["manuell"].all()


def test_monatsschnitt_ignoriert_angebrochenen_monat(consors_csv):
    df = _laden(consors_csv)
    avg = analytics.monthly_average(df)
    assert avg["monate"] == 6       # Jan–Jun vollständig


# --- Datenpfade & Übernahme ------------------------------------------------

def test_daten_im_benutzerordner(datenordner, consors_csv):
    _laden(consors_csv)
    assert paths.db_path().parent == datenordner
    assert paths.rules_path().exists()          # Standardregeln wurden kopiert


def test_datenbank_uebernehmen(tmp_path, monkeypatch, consors_csv):
    alt = tmp_path / "alt"
    monkeypatch.setenv("FINANCE_TOOL_DATA", str(alt))
    _laden(consors_csv)
    anzahl = storage.count()
    alte_db = str(paths.db_path())

    monkeypatch.setenv("FINANCE_TOOL_DATA", str(tmp_path / "neu"))
    service.demo_laden()                         # es gibt schon etwas
    text = service.datenbank_uebernehmen(alte_db)
    assert storage.count() == anzahl
    assert "gesichert" in text


def test_datenbank_uebernehmen_lehnt_fremde_datei_ab(tmp_path):
    fremd = tmp_path / "x.db"
    fremd.write_bytes(b"keine datenbank")
    with pytest.raises(ValueError):
        service.datenbank_uebernehmen(str(fremd))


def test_export_fuer_excel(tmp_path, consors_csv):
    _laden(consors_csv)
    ziel = tmp_path / "export.csv"
    n = service.exportieren(str(ziel))
    text = ziel.read_text(encoding="utf-8-sig")
    assert n > 100 and text.startswith("Datum;Betrag;")


def test_ml_training_und_vorhersage(consors_csv):
    _laden(consors_csv)
    meldung = service.modell_trainieren(0.6)
    assert "Modell trainiert" in meldung
    assert paths.model_path().exists()
