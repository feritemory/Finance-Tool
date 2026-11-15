"""Oberflächen-Tests: echte Fenster (ohne Bildschirm) und echte Interaktionen."""

import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import QCoreApplication, Qt  # noqa: E402
from PySide6.QtWidgets import QComboBox  # noqa: E402

from finance import analytics, service, storage  # noqa: E402
from finance.gui.app import _anwendung  # noqa: E402
from finance.gui.widgets import warte_auf_hintergrund  # noqa: E402


@pytest.fixture(scope="session")
def app():
    return _anwendung(["test"])


@pytest.fixture
def fenster(app):
    from finance.gui.hauptfenster import Hauptfenster
    f = Hauptfenster()
    f.resize(1360, 900)
    f.show()
    QCoreApplication.processEvents()
    yield f
    warte_auf_hintergrund()
    f.close()
    f.deleteLater()
    QCoreApplication.processEvents()


def _ereignisse(n: int = 5) -> None:
    for _ in range(n):
        QCoreApplication.processEvents()


def _mit_daten(fenster, consors_csv):
    service.importieren([consors_csv])
    fenster.zustand.daten_geaendert.emit()
    _ereignisse()


def _zeile(seite, text: str) -> int:
    m = seite.modell
    for i, z in enumerate(m.zeilen):
        if text in z["empfaenger"] or text in z["zweck"]:
            return i
    raise AssertionError(text)


def test_leerzustand(fenster):
    ueb = fenster.seiten["uebersicht"]
    assert ueb.leer.isVisible() and not ueb.inhalt_box.isVisible()


def test_import_ueber_oberflaeche(fenster, consors_csv):
    fenster.zeige("import")
    imp = fenster.seiten["import"]
    imp._dateien_setzen([consors_csv])
    assert imp.knopf.isEnabled()
    imp.knopf.click()
    assert warte_auf_hintergrund()
    _ereignisse()
    meldung = imp.ergebnis_platz.itemAt(0).widget()
    assert meldung.property("art") == "erfolg"
    fenster.zeige("uebersicht")
    _ereignisse()
    assert fenster.seiten["uebersicht"].inhalt_box.isVisible()
    assert "Umsätze" in fenster.fuss.text()


def test_kategorie_per_auswahlliste_aendern(fenster, consors_csv):
    _mit_daten(fenster, consors_csv)
    fenster.zeige("transaktionen")
    _ereignisse()
    tx = fenster.seiten["transaktionen"]
    zeile = _zeile(tx, "Golden Rice")
    quelle = tx.modell.index(zeile, 2)
    index = tx.proxy.mapFromSource(quelle)

    # Wie ein Klick: Editor öffnen, Eintrag wählen
    tx.tabelle.setCurrentIndex(index)
    tx.tabelle.edit(index)
    _ereignisse()
    box = tx.tabelle.findChild(QComboBox)
    assert box is not None, "Auswahlliste hat sich nicht geöffnet"
    box.setCurrentText("Auswärts Essen und Trinken")
    box.activated.emit(box.currentIndex())
    _ereignisse(10)

    df = storage.load_dataframe()
    gr = df[df["counterparty"].str.contains("Golden Rice")]
    assert set(gr["category"]) == {"Auswärts Essen und Trinken"}   # alle mitgezogen
    assert "weitere Buchung" in fenster.toast.text()


def test_fixkosten_haekchen_wirkt_auf_alle_seiten(fenster, consors_csv):
    _mit_daten(fenster, consors_csv)
    fix_seite = fenster.seiten["fixkosten"]
    fenster.zeige("fixkosten")
    _ereignisse()
    vorher = fix_seite.kpi.kacheln[0].wert.text()

    fenster.zeige("transaktionen")
    _ereignisse()
    tx = fenster.seiten["transaktionen"]
    i = _zeile(tx, "S-Bahn")
    assert tx.modell.setData(tx.modell.index(i, 5), Qt.CheckState.Unchecked.value,
                             Qt.ItemDataRole.CheckStateRole)
    _ereignisse(10)

    fenster.zeige("fixkosten")
    _ereignisse()
    nachher = fix_seite.kpi.kacheln[0].wert.text()
    assert nachher != vorher
    namen = [fix_seite.tabelle.item(r, 0).text() for r in range(fix_seite.tabelle.rowCount())]
    assert not any("S-Bahn" in n for n in namen)
    # Übersicht zeigt dieselbe Zahl
    fenster.zeige("uebersicht")
    _ereignisse()
    assert fenster.seiten["uebersicht"].kpi_schnitt.kacheln[2].wert.text() == nachher


def test_monatsfilter(fenster, consors_csv):
    _mit_daten(fenster, consors_csv)
    ueb = fenster.seiten["uebersicht"]
    gesamt = ueb.kpi_summe.kacheln[1].wert.text()
    fenster.f_jahr.setCurrentIndex(fenster.f_jahr.findData("2026"))
    fenster.f_monat.setCurrentIndex(fenster.f_monat.findData("2026-03"))
    _ereignisse()
    assert fenster.zustand.filter.monat == "2026-03"
    assert ueb.kpi_summe.kacheln[1].wert.text() != gesamt
    assert len(ueb.vergleich.perioden) == 1


def test_sortierung_neueste_zuerst(fenster, consors_csv):
    _mit_daten(fenster, consors_csv)
    fenster.zeige("transaktionen")
    _ereignisse()
    tx = fenster.seiten["transaktionen"]
    daten = [tx.proxy.index(r, 0).data(Qt.ItemDataRole.UserRole + 1)
             for r in range(tx.proxy.rowCount())]
    assert daten == sorted(daten, reverse=True)


def test_modell_trainieren_im_hintergrund(fenster, consors_csv):
    _mit_daten(fenster, consors_csv)
    fenster.zeige("einstellungen")
    _ereignisse()
    e = fenster.seiten["einstellungen"]
    e.b_trainieren.click()
    assert not e.b_trainieren.isEnabled()            # während des Trainings gesperrt
    assert warte_auf_hintergrund(120000)
    _ereignisse()
    assert e.b_trainieren.isEnabled()
    assert "Modell trainiert" in fenster.toast.text()
    assert "trainiert" in e.ml_status.text()


def test_rhythmus_in_fixkosten_tabelle(fenster, consors_csv):
    _mit_daten(fenster, consors_csv)
    df = storage.load_dataframe()
    service.fixkosten_setzen(int(df[df["description"].str.contains("BUKA")].iloc[0]["id"]), True)
    fenster.zustand.daten_geaendert.emit()
    fenster.zeige("fixkosten")
    _ereignisse()
    t = fenster.seiten["fixkosten"].tabelle
    zeilen = {t.item(r, 1).text(): (t.item(r, 2).text(), t.item(r, 4).text())
              for r in range(t.rowCount())}
    assert zeilen["Bafög-Rückzahlung"] == ("vierteljährlich", "130,00 €")
    assert analytics.monthly_fixed_costs(storage.load_dataframe()) > 0
