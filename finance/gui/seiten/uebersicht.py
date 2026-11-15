"""Seite „Übersicht": Kennzahlen und Diagramme."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QFrame, QGridLayout, QHeaderView, QTableWidget,
                               QTableWidgetItem, QVBoxLayout, QWidget)

from ... import service
from ...categories import COLOR_MAP, SERIES_COLORS
from .. import theme
from ..charts import BalkenWaagerecht, Gestapelt, GruppierteBalken, Linie
from ..widgets import (Aufklapper, Karte, KpiReihe, Segment, Seite, euro, label)


class Uebersicht(Seite):
    def __init__(self, zustand):
        super().__init__("Übersicht",
                         "Einnahmen und Ausgaben tracken, kategorisieren und auswerten.")
        self.zustand = zustand
        self.aufloesung = "monat"
        self.verlauf_art = "ausgaben"
        self._daten = None

        # --- Leerzustand -------------------------------------------------
        self.leer = QFrame()
        self.leer.setObjectName("LeerKarte")
        lv = QVBoxLayout(self.leer)
        lv.setContentsMargins(34, 34, 34, 34)
        t = label("Noch keine Umsätze vorhanden", "KarteTitel")
        t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lv.addWidget(t)
        h = label("Lade deine Kontoauszüge im Bereich <b>Import</b> hoch (CSV- oder "
                  "CAMT-Export der Consorsbank). Du hast schon Daten aus der "
                  "früheren Version? Übernimm sie unter <b>Einstellungen → Daten "
                  "→ Datenbank übernehmen</b>. Zum Ausprobieren gibt es dort "
                  "auch Demo-Daten.", "Hinweis", umbruch=True)
        h.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lv.addWidget(h)
        self.hinzufuegen(self.leer)

        # --- Inhalt --------------------------------------------------------
        self.inhalt_box = QWidget()
        v = QVBoxLayout(self.inhalt_box)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)

        v.addWidget(label("GESAMT IM GEWÄHLTEN ZEITRAUM", "KpiLabel"))
        v.addSpacing(8)
        self.kpi_summe = KpiReihe(4)
        v.addWidget(self.kpi_summe)
        v.addSpacing(22)
        self.kpi_schnitt_label = label("PRO MONAT", "KpiLabel")
        v.addWidget(self.kpi_schnitt_label)
        v.addSpacing(8)
        self.kpi_schnitt = KpiReihe(4)
        v.addWidget(self.kpi_schnitt)
        v.addSpacing(8)
        self.variabel = label("", "Hinweis", umbruch=True)
        v.addWidget(self.variabel)

        # Vergleich
        self.seg_aufl = Segment([("tag", "Täglich"), ("monat", "Monatlich"),
                                 ("jahr", "Jährlich")], self.aufloesung)
        self.seg_aufl.geaendert.connect(self._aufloesung_geaendert)
        karte = Karte("Einnahmen, Ausgaben und Sparen im Vergleich", self.seg_aufl)
        self.vergleich = karte.add(GruppierteBalken())
        self.tabelle = QTableWidget(0, 5)
        self.tabelle.setHorizontalHeaderLabels(
            ["Zeitraum", "Einnahmen", "Ausgaben", "Sparen", "Saldo"])
        self.tabelle.verticalHeader().setVisible(False)
        self.tabelle.horizontalHeader().setDefaultAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.tabelle.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tabelle.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tabelle.setMinimumHeight(240)
        karte.add(Aufklapper("Werte als Tabelle anzeigen", self.tabelle))
        v.addSpacing(20)
        v.addWidget(karte)

        # Saldo + Kategorien nebeneinander
        raster = QGridLayout()
        raster.setHorizontalSpacing(20)
        raster.setContentsMargins(0, 20, 0, 0)
        k_saldo = Karte("Saldo je Zeitraum")
        k_saldo.add(label("Einnahmen abzüglich Ausgaben und Sparen.", "Hinweis"))
        self.saldo = k_saldo.add(Linie())
        k_kat = Karte("Ausgaben nach Kategorie")
        self.kategorien = k_kat.add(BalkenWaagerecht())
        k_kat.v.addStretch(1)
        raster.addWidget(k_saldo, 0, 0)            # gleiche Höhe wie die Nachbarkarte
        raster.addWidget(k_kat, 0, 1)
        raster.setColumnStretch(0, 1)
        raster.setColumnStretch(1, 1)
        v.addLayout(raster)

        # Kategorien im Zeitverlauf
        self.seg_verlauf = Segment([("ausgaben", "Ausgaben"), ("einnahmen", "Einnahmen")],
                                   self.verlauf_art)
        self.seg_verlauf.geaendert.connect(self._verlauf_geaendert)
        k_verlauf = Karte("Kategorien im Zeitverlauf", self.seg_verlauf)
        self.verlauf = k_verlauf.add(Gestapelt())
        v.addSpacing(20)
        v.addWidget(k_verlauf)

        self.hinzufuegen(self.inhalt_box)
        self.abschliessen()

        zustand.daten_geaendert.connect(self.als_veraltet_markieren)
        zustand.filter_geaendert.connect(self.als_veraltet_markieren)

    # ------------------------------------------------------------------
    def _aufloesung_geaendert(self, wert: str) -> None:
        self.aufloesung = wert
        self.aktualisieren()

    def _verlauf_geaendert(self, wert: str) -> None:
        self.verlauf_art = wert
        self._verlauf_zeichnen()

    def aktualisieren(self) -> None:
        d = service.uebersicht(self.zustand.filter, self.aufloesung)
        self._daten = d
        hat = bool(d["reihen"])
        self.leer.setVisible(not hat)
        self.inhalt_box.setVisible(hat)
        if not hat:
            return

        s, a = d["summe"], d["schnitt"]
        self.kpi_summe.setzen([("Einnahmen", s["einnahmen"]), ("Ausgaben", s["ausgaben"]),
                               ("Sparen", s["sparen"]), ("Saldo", s["saldo"], True)])
        n = a["monate"]
        self.kpi_schnitt_label.setText(
            f"PRO MONAT  ·  Ø ÜBER {n} VOLLSTÄNDIGE{'N' if n == 1 else ''} "
            f"MONAT{'' if n == 1 else 'E'}")
        self.kpi_schnitt.setzen([("Ø Einnahmen", a["einnahmen"]),
                                 ("Ø Ausgaben", a["ausgaben"]),
                                 ("davon Fixkosten", d["fixkosten_monat"]),
                                 ("Ø Sparen", a["sparen"])])
        variabel = max(a["ausgaben"] - d["fixkosten_monat"], 0.0)
        self.variabel.setText(
            f"Das entspricht rund <b>{euro(variabel)}</b> variablen Ausgaben pro Monat "
            "(Ø Ausgaben abzüglich Fixkosten)." if a["ausgaben"] > 0 else "")

        reihen = d["reihen"]
        perioden = [r["label"] for r in reihen]
        self.vergleich.setzen(perioden, [
            {"name": "Einnahmen", "farbe": SERIES_COLORS["einnahmen"],
             "werte": [r["einnahmen"] for r in reihen]},
            {"name": "Ausgaben", "farbe": SERIES_COLORS["ausgaben"],
             "werte": [r["ausgaben"] for r in reihen]},
            {"name": "Sparen", "farbe": SERIES_COLORS["sparen"],
             "werte": [r["sparen"] for r in reihen]},
        ], beschriften=len(reihen) <= 14)

        self.tabelle.setRowCount(len(reihen))
        for i, r in enumerate(reihen):
            werte = [r["label"], euro(r["einnahmen"]), euro(r["ausgaben"]),
                     euro(r["sparen"]), euro(r["saldo"])]
            for j, w in enumerate(werte):
                item = QTableWidgetItem(w)
                if j:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                if j == 4 and r["saldo"] < 0:
                    item.setForeground(QColor(theme.GEFAHR))
                self.tabelle.setItem(i, j, item)

        self.saldo.setzen(perioden, [r["saldo"] for r in reihen])
        gesamt = sum(k["betrag"] for k in d["ausgaben_kategorien"])
        self.kategorien.setzen([{"label": k["kategorie"], "wert": k["betrag"],
                                 "farbe": COLOR_MAP.get(k["kategorie"], theme.INK_FAINT)}
                                for k in d["ausgaben_kategorien"]], gesamt)
        self._verlauf_zeichnen()

    def _verlauf_zeichnen(self) -> None:
        if not self._daten:
            return
        v = self._daten["verlauf_ausgaben" if self.verlauf_art == "ausgaben"
                        else "verlauf_einnahmen"]
        self.verlauf.setzen(v["perioden"], v["kategorien"], v["werte"], COLOR_MAP)
