"""Finance-Tool – Streamlit-Desktop-App zur Einnahmen-/Ausgaben-Verwaltung.

Start:  streamlit run app.py
"""

from __future__ import annotations

from datetime import date

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from finance import analytics, ml, storage, ui
from finance.categories import (CATEGORY_NAMES, COLOR_MAP, SERIES_COLORS,
                                UNCATEGORIZED)
from finance.importer import parse_file
from finance import sampledata

st.set_page_config(page_title="Finance-Tool", page_icon="💶", layout="wide")
st.markdown(ui.CSS, unsafe_allow_html=True)

EUR = "€"


def fmt(v: float) -> str:
    return f"{v:,.2f} {EUR}".replace(",", "X").replace(".", ",").replace("X", ".")


def fmt_kurz(v: float) -> str:
    """Kompakte Beschriftung direkt am Balken (ohne Nachkommastellen)."""
    return f"{v:,.0f}".replace(",", ".") + " €"


def caption(text: str) -> None:
    st.markdown(f'<div class="kpi-caption">{text}</div>', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Daten laden / erststart
# ---------------------------------------------------------------------------

def _recurring_pairs() -> list[tuple[int, bool]]:
    df = storage.load_dataframe()
    rec = analytics.detect_recurring(df)
    ids = {i for lst in rec["tx_ids"].tolist() for i in lst} if not rec.empty else set()
    return [(int(i), i in ids) for i in df["id"].tolist()]


@st.cache_data(show_spinner=False)
def get_data(version: int) -> pd.DataFrame:
    # 'version' MUSS ohne führenden Unterstrich heißen – sonst schließt
    # st.cache_data das Argument vom Cache-Schlüssel aus und der Cache wird
    # nach einem Import nie invalidiert (andere Tabs blieben dann leer).
    return storage.load_dataframe()


def refresh() -> None:
    st.session_state["data_version"] = st.session_state.get("data_version", 0) + 1


def load() -> pd.DataFrame:
    return get_data(st.session_state.get("data_version", 0))


# ---------------------------------------------------------------------------
# Sidebar-Filter
# ---------------------------------------------------------------------------

def sidebar_filters(df: pd.DataFrame) -> pd.DataFrame:
    st.sidebar.header("🔎 Filter")
    if df.empty:
        return df

    years = analytics.available_years(df)
    year_opts = ["Alle"] + [str(y) for y in years]
    sel_year = st.sidebar.selectbox("Jahr", year_opts, index=len(year_opts) - 1)

    d = df
    if sel_year != "Alle":
        d = d[d["year"] == int(sel_year)]

        months = sorted(d["month"].unique().tolist())
        month_opts = ["Alle"] + months
        sel_month = st.sidebar.selectbox("Monat", month_opts, index=0)
        if sel_month != "Alle":
            d = d[d["month"] == sel_month]

    cats = st.sidebar.multiselect("Kategorien", CATEGORY_NAMES, default=[],
                                  placeholder="Alle Kategorien")
    if cats:
        d = d[d["category"].isin(cats)]

    return d


# ---------------------------------------------------------------------------
# Tab: Übersicht (Dashboard)
# ---------------------------------------------------------------------------

def tab_overview(df: pd.DataFrame) -> None:
    if df.empty:
        st.info("👋 Willkommen! Noch keine Umsätze vorhanden. Lade deine Kontoauszüge "
                "im Tab **📥 Import** hoch (CSV/CAMT-Export der Consorsbank). "
                "Zum reinen Ausprobieren kannst du in den **⚙️ Einstellungen** "
                "optional Demo-Daten laden.")
        return

    s = analytics.summary(df)
    fix = analytics.monthly_fixed_costs(df)
    avg = analytics.monthly_average(df)

    # --- Kennzahlen: Summen im Zeitraum ---
    caption("Gesamt im gewählten Zeitraum")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Einnahmen", fmt(s["einnahmen"]))
    c2.metric("Ausgaben", fmt(s["ausgaben"]))
    c3.metric("Sparen", fmt(s["sparen"]))
    c4.metric("Saldo", fmt(s["saldo"]))

    # --- Kennzahlen: Durchschnitt pro Monat ---
    st.write("")
    monate = avg["monate"]
    caption(f"Pro Monat &nbsp;·&nbsp; Ø über {monate} vollständige"
            f"{'n' if monate == 1 else ''} Monat{'e' if monate != 1 else ''}")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Ø Einnahmen", fmt(avg["einnahmen"]))
    m2.metric("Ø Ausgaben", fmt(avg["ausgaben"]))
    m3.metric("davon Fixkosten", fmt(fix))
    m4.metric("Ø Sparen", fmt(avg["sparen"]))
    if avg["ausgaben"] > 0:
        variabel = max(avg["ausgaben"] - fix, 0.0)
        st.caption(f"Das entspricht rund **{fmt(variabel)}** variablen Ausgaben "
                   f"pro Monat (Ø Ausgaben abzüglich Fixkosten).")

    st.divider()

    # --- Zeitraum-Umschalter ---
    gran = st.radio("Zeitliche Auflösung", ["Täglich", "Monatlich", "Jährlich"],
                    index=1, horizontal=True)
    freq = {"Täglich": "D", "Monatlich": "M", "Jährlich": "Y"}[gran]

    ts = analytics.timeseries(df, freq)
    datumsformat = {"D": "%d.%m.%Y", "M": "%b %Y", "Y": "%Y"}[freq]

    st.markdown("### Einnahmen, Ausgaben und Sparen im Vergleich")
    if ts.empty:
        st.caption("Keine Daten im Zeitraum.")
    else:
        # Gruppierte Balken: alle Werte positiv nebeneinander auf einer Achse.
        beschriften = len(ts) <= 14      # Zahlen nur zeigen, wenn sie lesbar bleiben
        fig = go.Figure()
        for name, spalte in (("Einnahmen", "einnahmen"),
                             ("Ausgaben", "ausgaben"),
                             ("Sparen", "sparen")):
            fig.add_bar(
                x=ts["periode"], y=ts[spalte], name=name,
                marker=dict(color=SERIES_COLORS[spalte], cornerradius=4),
                # Nullwerte nicht beschriften – sie erzeugen sonst nur Rauschen.
                text=[fmt_kurz(v) if v else "" for v in ts[spalte]]
                     if beschriften else None,
                textposition="outside",
                textfont=dict(size=10, color=ui.INK_SOFT),
                cliponaxis=False,
                hovertemplate=f"<b>{name}</b>: %{{y:,.2f}} €<extra></extra>",
            )
        fig.update_layout(barmode="group", hovermode="x unified")
        ui.style_fig(fig, height=400)
        fig.update_xaxes(hoverformat=datumsformat)
        st.plotly_chart(fig, use_container_width=True)

        with st.expander("Werte als Tabelle anzeigen"):
            tab = ts.copy()
            tab["periode"] = tab["periode"].dt.strftime(
                "%d.%m.%Y" if freq == "D" else ("%m/%Y" if freq == "M" else "%Y"))
            tab = tab.rename(columns={
                "periode": "Zeitraum", "einnahmen": "Einnahmen",
                "ausgaben": "Ausgaben", "sparen": "Sparen", "saldo": "Saldo"})
            for spalte in ("Einnahmen", "Ausgaben", "Sparen", "Saldo"):
                tab[spalte] = tab[spalte].map(fmt)
            st.dataframe(tab, use_container_width=True, hide_index=True)

    left, right = st.columns([3, 2], gap="large")

    with left:
        st.markdown("### Saldo je Zeitraum")
        st.caption("Einnahmen abzüglich Ausgaben und Sparen.")
        if not ts.empty:
            fig = go.Figure()
            fig.add_hline(y=0, line_width=1, line_color=ui.LINE)
            fig.add_trace(go.Scatter(
                x=ts["periode"], y=ts["saldo"], mode="lines+markers",
                name="Saldo", line=dict(color=ui.INK, width=2),
                marker=dict(size=8, color=ui.INK,
                            line=dict(width=2, color=ui.SURFACE)),
                hovertemplate=f"%{{x|{datumsformat}}}<br>"
                              "%{y:,.2f} €<extra></extra>"))
            ui.style_fig(fig, height=320, legend=False)
            st.plotly_chart(fig, use_container_width=True)

    with right:
        st.markdown("### Ausgaben nach Kategorie")
        cat = analytics.by_category(df, "ausgabe")
        if cat.empty:
            st.caption("Keine Ausgaben im Zeitraum.")
        else:
            # Waagerechte Balken statt Tortendiagramm: Die Kategorienamen stehen
            # direkt an der Achse, kleine Beträge bleiben lesbar (im Kreis
            # würden sie zu unlesbaren Splittern) und die Beträge lassen sich
            # der Länge nach vergleichen.
            gesamt = cat["betrag"].sum()
            cat = cat.sort_values("betrag")
            fig = go.Figure(go.Bar(
                x=cat["betrag"], y=cat["category"], orientation="h",
                marker=dict(color=[COLOR_MAP.get(c, ui.INK_FAINT)
                                   for c in cat["category"]], cornerradius=4),
                text=[fmt_kurz(v) for v in cat["betrag"]],
                textposition="outside",
                textfont=dict(size=11, color=ui.INK_SOFT),
                cliponaxis=False,
                customdata=(cat["betrag"] / gesamt * 100 if gesamt else cat["betrag"]),
                hovertemplate="<b>%{y}</b><br>%{x:,.2f} € · "
                              "%{customdata:.1f} %<extra></extra>",
            ))
            ui.style_fig(fig, height=320, legend=False, show_grid=False)
            fig.update_xaxes(visible=False, range=[0, cat["betrag"].max() * 1.28])
            fig.update_yaxes(tickfont=dict(color=ui.INK_SOFT, size=11))
            fig.update_layout(margin=dict(t=8, b=8, l=8, r=8))
            st.plotly_chart(fig, use_container_width=True)

    # --- Gestapelte Kategorien über die Zeit ---
    st.markdown("### Kategorien im Zeitverlauf")
    art = st.radio("Anzeigen", ["Ausgaben", "Einnahmen"], index=0, horizontal=True,
                   label_visibility="collapsed")
    typ = "ausgabe" if art == "Ausgaben" else "einnahme"
    piv = analytics.category_over_time(df, freq, typ)
    if piv.empty:
        st.caption("Keine Daten im Zeitraum.")
    else:
        long = piv.reset_index().melt(id_vars="periode", var_name="Kategorie",
                                      value_name="Betrag")
        fig = px.bar(long, x="periode", y="Betrag", color="Kategorie",
                     color_discrete_map=COLOR_MAP)
        fig.update_traces(marker=dict(line=dict(color=ui.SURFACE, width=1)),
                          hovertemplate="<b>%{fullData.name}</b><br>"
                                        f"%{{x|{datumsformat}}}<br>"
                                        "%{y:,.2f} €<extra></extra>")
        ui.style_fig(fig, height=400)
        fig.update_xaxes(title_text=None)
        fig.update_yaxes(title_text=None)
        st.plotly_chart(fig, use_container_width=True)


# ---------------------------------------------------------------------------
# Tab: Fixkosten
# ---------------------------------------------------------------------------

def tab_fixed(df: pd.DataFrame) -> None:
    st.subheader("🔁 Monatliche Fixkosten")
    if df.empty:
        st.info("Keine Daten vorhanden.")
        return

    rec = analytics.detect_recurring(df)
    if rec.empty:
        st.info("Es wurden (noch) keine wiederkehrenden Zahlungen erkannt. "
                "Fixkosten werden erkannt, sobald ein Empfänger in mind. 3 "
                "Monaten mit ähnlichem Betrag auftaucht.")
        return

    fixkosten = rec[~rec["ist_sparen"]]
    sparen = rec[rec["ist_sparen"]]

    c1, c2 = st.columns(2)
    c1.metric("Fixkosten pro Monat", fmt(fixkosten["median_betrag"].sum()))
    c2.metric("Festes Sparen pro Monat", fmt(sparen["median_betrag"].sum()))

    def _table(r: pd.DataFrame):
        view = r.rename(columns={
            "merchant": "Empfänger (erkannt)",
            "category": "Kategorie",
            "monate": "Monate",
            "median_betrag": "Betrag/Monat",
        })[["Empfänger (erkannt)", "Kategorie", "Monate", "Betrag/Monat"]].copy()
        view["Betrag/Monat"] = view["Betrag/Monat"].map(fmt)
        return view

    st.markdown("#### 🔁 Fixkosten")
    if fixkosten.empty:
        st.caption("Keine wiederkehrenden Fixkosten erkannt.")
    else:
        # Volle Breite für beides: die Empfängernamen sind lang, nebeneinander
        # würden Tabelle und Diagramm sich gegenseitig abschneiden.
        f = fixkosten.sort_values("median_betrag")
        fig = go.Figure(go.Bar(
            x=f["median_betrag"], y=f["merchant"], orientation="h",
            marker=dict(color=[COLOR_MAP.get(c, ui.INK_FAINT) for c in f["category"]],
                        cornerradius=4),
            text=[fmt_kurz(v) for v in f["median_betrag"]],
            textposition="outside",
            textfont=dict(size=11, color=ui.INK_SOFT),
            cliponaxis=False,
            customdata=f["category"],
            hovertemplate="<b>%{y}</b><br>%{x:,.2f} € / Monat"
                          "<br>%{customdata}<extra></extra>",
        ))
        ui.style_fig(fig, height=max(260, 34 * len(f)), legend=False, show_grid=False)
        fig.update_xaxes(visible=False,
                         range=[0, f["median_betrag"].max() * 1.18])
        fig.update_yaxes(tickfont=dict(color=ui.INK_SOFT, size=11))
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(_table(fixkosten), use_container_width=True, hide_index=True)

    if not sparen.empty:
        st.markdown("#### 💰 Feste Sparbeträge (Überträge auf Sparkonten)")
        st.dataframe(_table(sparen), use_container_width=True, hide_index=True)

    st.caption("Heuristische Erkennung anhand wiederkehrender Empfänger/Konten und "
               "konstanter Beträge. Häufig frequentierte Händler (z. B. Supermärkte) "
               "werden bewusst ausgeschlossen. Schwellen anpassbar in "
               "`finance/analytics.py` → `detect_recurring`.")


# ---------------------------------------------------------------------------
# Tab: Transaktionen (bearbeiten)
# ---------------------------------------------------------------------------

def tab_transactions(df: pd.DataFrame) -> None:
    st.subheader("📋 Transaktionen")
    if df.empty:
        st.info("Keine Daten vorhanden.")
        return

    search = st.text_input("Suche (Empfänger / Verwendungszweck)", "")
    d = df
    if search:
        mask = (d["counterparty"].str.contains(search, case=False, na=False) |
                d["description"].str.contains(search, case=False, na=False))
        d = d[mask]

    show = d[["id", "date", "amount", "category", "counterparty",
              "description", "is_recurring"]].copy()
    show = show.sort_values("date", ascending=False)
    show["date"] = show["date"].dt.strftime("%d.%m.%Y")
    show["is_recurring"] = show["is_recurring"].astype(bool)
    show = show.rename(columns={
        "date": "Datum", "amount": "Betrag", "category": "Kategorie",
        "counterparty": "Empfänger", "description": "Verwendungszweck",
        "is_recurring": "Fixkosten",
    })

    edited = st.data_editor(
        show, use_container_width=True, hide_index=True, height=520,
        disabled=["id", "Datum", "Betrag", "Empfänger", "Verwendungszweck"],
        column_config={
            "id": None,
            "Betrag": st.column_config.NumberColumn(format="%.2f €"),
            "Kategorie": st.column_config.SelectboxColumn(options=CATEGORY_NAMES),
            "Fixkosten": st.column_config.CheckboxColumn(),
        },
        key="tx_editor",
    )

    if st.button("💾 Änderungen speichern", type="primary"):
        orig = show.set_index("id")
        new = edited.set_index("id")
        changes = also = 0
        for tx_id in new.index:
            if new.loc[tx_id, "Kategorie"] != orig.loc[tx_id, "Kategorie"]:
                also += storage.update_category(
                    int(tx_id), new.loc[tx_id, "Kategorie"], manual=True)
                changes += 1
            if bool(new.loc[tx_id, "Fixkosten"]) != bool(orig.loc[tx_id, "Fixkosten"]):
                storage.set_recurring(int(tx_id), bool(new.loc[tx_id, "Fixkosten"]), manual=True)
                changes += 1
        refresh()
        msg = f"{changes} Änderung(en) gespeichert."
        if also:
            msg += f" {also} weitere Buchung(en) desselben Händlers automatisch angepasst."
        st.success(msg)
        st.rerun()

    st.caption(f"{len(show)} Transaktionen angezeigt. Wenn du eine Kategorie änderst, "
               "**merkt sich das Tool den Händler** und ordnet künftige (und weitere "
               "vorhandene) Buchungen automatisch genauso ein.")


# ---------------------------------------------------------------------------
# Tab: Import
# ---------------------------------------------------------------------------

def tab_import(df: pd.DataFrame) -> None:
    st.subheader("📥 Umsätze importieren")

    st.markdown(
        "**So exportierst du deine Umsätze bei der Consorsbank:**\n"
        "1. Im Online-Banking / in der App unter **Umsätze** den Zeitraum wählen.\n"
        "2. Export als **CSV** (oder CAMT/XML) herunterladen.\n"
        "3. Datei hier hochladen – Kategorien werden automatisch zugeordnet.\n\n"
        "Der Import erkennt Duplikate automatisch, du kannst also gefahrlos "
        "überlappende Zeiträume laden."
    )

    # Ergebnis eines vorherigen Imports anzeigen (überlebt den Rerun).
    res = st.session_state.pop("import_result", None)
    if res:
        if res["new"] or res["skip"]:
            st.success(f"✅ {res['new']} neue Umsätze importiert, "
                       f"{res['skip']} Duplikate übersprungen.")
        if res["read"] == 0 and not res["errors"]:
            st.warning("⚠️ Die Datei wurde gelesen, aber es konnten **0 Umsätze** "
                       "erkannt werden. Wahrscheinlich weicht das Spaltenformat ab. "
                       "Sieh dir die Diagnose unten an.")
        elif res["new"] == 0 and res["skip"] and not res["errors"]:
            st.info("Alle Umsätze aus dieser Datei waren bereits vorhanden.")
        for e in res["errors"]:
            st.error(f"❌ {e}")
        if res.get("diag"):
            with st.expander("🔍 Import-Diagnose (bei Problemen hilfreich)"):
                st.code(res["diag"])

    files = st.file_uploader("CSV- oder CAMT/XML-Dateien", type=["csv", "xml"],
                             accept_multiple_files=True)
    if files and st.button("Importieren", type="primary"):
        total_new = total_skip = total_read = 0
        errors, diag = [], []
        for f in files:
            try:
                data = f.read()
                txs = parse_file(f.name, data)
                new, skip = storage.add_transactions(txs)
                total_new += new
                total_skip += skip
                total_read += len(txs)
                diag.append(f"{f.name}: {len(txs)} Zeilen gelesen "
                            f"→ {new} neu, {skip} Duplikate")
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{f.name}: {exc}")
                diag.append(f"{f.name}: FEHLER – {exc}")

        # Bestehende Umsätze (mit ggf. nachgetragener BIC) neu kategorisieren,
        # damit z. B. Trade-Republic-/Revolut-Überträge nachträglich stimmen.
        try:
            storage.recategorize_all()
        except Exception as exc:  # noqa: BLE001
            diag.append(f"Neu-Kategorisierung übersprungen: {exc}")

        # Fixkosten-Erkennung darf den Import nicht scheitern lassen.
        try:
            storage.set_recurring_bulk(_recurring_pairs())
        except Exception as exc:  # noqa: BLE001
            diag.append(f"Fixkosten-Erkennung übersprungen: {exc}")

        refresh()
        st.session_state["import_result"] = {
            "new": total_new, "skip": total_skip, "read": total_read,
            "errors": errors, "diag": "\n".join(diag),
        }
        st.rerun()

    st.divider()
    with st.expander("🔗 Automatischer Kontoabruf (PSD2 / Consorsbank) – optional"):
        _psd2_ui()


def _psd2_ui() -> None:
    from finance.banking import gocardless

    st.markdown(
        "Über die kostenlose **GoCardless Bank Account Data**-Schnittstelle "
        "(früher Nordigen) lassen sich Umsätze direkt aus deinem Consorsbank-Konto "
        "abrufen – PSD2-konform.\n\n"
        "1. Kostenloses Konto: https://bankaccountdata.gocardless.com/\n"
        "2. Secret ID + Secret Key erzeugen und unten eintragen (oder als "
        "Umgebungsvariablen `GOCARDLESS_SECRET_ID` / `GOCARDLESS_SECRET_KEY`).\n"
        "3. Bank-Login-Link erzeugen, einmalig bei der Consorsbank bestätigen "
        "(gilt 90 Tage), danach Umsätze abrufen."
    )

    col1, col2 = st.columns(2)
    sid = col1.text_input("Secret ID", type="password",
                          value=st.session_state.get("gc_sid", ""))
    skey = col2.text_input("Secret Key", type="password",
                           value=st.session_state.get("gc_skey", ""))

    if st.button("1) Bank-Login-Link erzeugen"):
        try:
            client = gocardless.GoCardlessClient(sid or None, skey or None)
            req = client.create_requisition()
            st.session_state["gc_sid"] = sid
            st.session_state["gc_skey"] = skey
            st.session_state["gc_req_id"] = req["id"]
            st.success("Link erzeugt. Bitte einloggen und Zugriff bestätigen:")
            st.link_button("🔐 Bei Consorsbank anmelden", req["link"])
        except Exception as exc:  # noqa: BLE001
            st.error(f"Fehler: {exc}")

    if st.session_state.get("gc_req_id") and st.button("2) Umsätze abrufen"):
        try:
            client = gocardless.GoCardlessClient(
                st.session_state.get("gc_sid") or None,
                st.session_state.get("gc_skey") or None)
            accounts = client.list_accounts(st.session_state["gc_req_id"])
            if not accounts:
                st.warning("Noch kein Konto verknüpft – Bank-Login abgeschlossen?")
                return
            total = 0
            for acc in accounts:
                txs = client.get_transactions(acc)
                new, _ = storage.add_transactions(txs)
                total += new
            storage.set_recurring_bulk(_recurring_pairs())
            refresh()
            st.success(f"{total} Umsätze abgerufen und importiert.")
        except Exception as exc:  # noqa: BLE001
            st.error(f"Fehler: {exc}")


# ---------------------------------------------------------------------------
# Tab: Einstellungen
# ---------------------------------------------------------------------------

def _ml_ui() -> None:
    st.markdown("### 🤖 Selbstlernende Kategorisierung (ML)")
    if not ml.sklearn_available():
        st.warning("Für das lernende Modell fehlt das Paket **scikit-learn**. "
                   "Installiere es einmalig mit `pip install scikit-learn` "
                   "(oder starte `run.bat`/`run.sh` neu – es installiert die "
                   "Abhängigkeiten automatisch).")
        return

    st.caption(
        "Das Modell lernt aus deinen bereits kategorisierten **Ausgaben** und "
        "ordnet ähnliche neue Buchungen automatisch zu – nur wenn Regeln & "
        "gelernte Händler nichts finden und die Sicherheit hoch genug ist. "
        "Alles bleibt lokal auf deinem Rechner."
    )

    status = "✅ trainiert" if ml.model_exists() else "— noch nicht trainiert"
    st.markdown(f"**Modellstatus:** {status}")

    threshold = st.slider(
        "Mindest-Sicherheit für eine automatische Zuordnung", 0.40, 0.90,
        ml.DEFAULT_THRESHOLD, 0.05,
        help="Höher = weniger, aber sicherere automatische Zuordnungen.")

    c1, c2 = st.columns(2)
    if c1.button("🧠 Modell trainieren & anwenden", type="primary"):
        try:
            with st.spinner("Trainiere Modell …"):
                metrics = storage.train_model()
                n = storage.recategorize_all(ml_threshold=threshold)
            storage.set_recurring_bulk(_recurring_pairs())
            refresh()
            acc = metrics.get("accuracy")
            acc_txt = f", geschätzte Trefferquote ≈ {acc*100:.0f}%" if acc else ""
            st.success(
                f"Modell trainiert auf {metrics['n_samples']} Buchungen in "
                f"{metrics['n_classes']} Kategorien{acc_txt}. "
                f"{n} Umsätze neu kategorisiert.")
            st.rerun()
        except RuntimeError as exc:
            st.error(str(exc))

    if ml.model_exists() and c2.button("🗑️ Modell löschen"):
        ml.delete_model()
        storage.recategorize_all()
        refresh()
        st.success("Modell gelöscht. Es gelten wieder nur Regeln & gelernte Händler.")
        st.rerun()


def tab_settings(df: pd.DataFrame) -> None:
    st.subheader("⚙️ Einstellungen & Daten")

    st.markdown(f"**Gespeicherte Umsätze:** {storage.count()}")

    c1, c2, c3 = st.columns(3)

    with c1:
        st.markdown("**Neu kategorisieren**")
        st.caption("Wendet die Regeln aus `config/rules.yaml` erneut an "
                   "(manuelle Zuordnungen bleiben erhalten).")
        if st.button("🔄 Regeln neu anwenden"):
            n = storage.recategorize_all()
            storage.set_recurring_bulk(_recurring_pairs())
            refresh()
            st.success(f"{n} Umsätze neu kategorisiert.")

    with c2:
        st.markdown("**Demo-Daten**")
        n_demo = storage.count_demo()
        st.caption(f"Beispiel-Umsätze zum Ausprobieren. Aktuell {n_demo} vorhanden.")
        if st.button("➕ Demo-Daten laden"):
            txs = sampledata.generate(up_to=date.today())
            new, skip = storage.add_transactions(txs)
            storage.set_recurring_bulk(_recurring_pairs())
            refresh()
            st.success(f"{new} Demo-Umsätze geladen ({skip} bereits vorhanden).")
            st.rerun()
        if st.button("🧹 Demo-Daten entfernen", disabled=n_demo == 0):
            removed = storage.clear_demo()
            storage.set_recurring_bulk(_recurring_pairs())
            refresh()
            st.success(f"{removed} Demo-Umsätze entfernt. Echte Umsätze bleiben erhalten.")
            st.rerun()

    with c3:
        st.markdown("**Zurücksetzen**")
        st.caption("Löscht alle gespeicherten Umsätze unwiderruflich.")
        confirm = st.checkbox("Ich bin sicher")
        if st.button("🗑️ Alle Daten löschen", disabled=not confirm):
            storage.clear_all()
            refresh()
            st.success("Alle Daten gelöscht.")
            st.rerun()

    st.divider()
    _ml_ui()

    st.divider()
    n_learned = storage.count_learned()
    st.markdown(f"**Gelernte Händler-Regeln:** {n_learned}")
    st.caption("Jede manuelle Kategorie-Korrektur im Tab *Transaktionen* wird hier "
               "als Regel gespeichert und künftig automatisch angewendet.")
    if n_learned and st.checkbox("Gelernte Regeln zurücksetzen"):
        if st.button("🧠 Gelernte Regeln löschen"):
            storage.clear_learned()
            refresh()
            st.success("Gelernte Regeln gelöscht.")
            st.rerun()

    st.divider()
    if not df.empty:
        csv = df[["date", "amount", "currency", "category", "counterparty",
                  "description", "is_recurring"]].copy()
        csv["date"] = csv["date"].dt.strftime("%Y-%m-%d")
        st.download_button("⬇️ Alle Umsätze als CSV exportieren",
                           csv.to_csv(index=False).encode("utf-8"),
                           file_name="umsaetze_export.csv", mime="text/csv")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    st.title("💶 Finance-Tool")
    st.caption("Einnahmen & Ausgaben tracken, kategorisieren, visualisieren – "
               "täglich, monatlich, jährlich.")

    df_all = load()
    df = sidebar_filters(df_all)

    st.sidebar.divider()
    st.sidebar.caption(f"Datenbestand: {len(df_all)} Umsätze")
    if not df_all.empty:
        st.sidebar.caption(
            f"Zeitraum: {df_all['date'].min():%d.%m.%Y} – {df_all['date'].max():%d.%m.%Y}")

    tabs = st.tabs(["📊 Übersicht", "🔁 Fixkosten", "📋 Transaktionen",
                    "📥 Import", "⚙️ Einstellungen"])
    with tabs[0]:
        tab_overview(df)
    with tabs[1]:
        tab_fixed(df)
    with tabs[2]:
        tab_transactions(df)
    with tabs[3]:
        tab_import(df_all)
    with tabs[4]:
        tab_settings(df_all)


if __name__ == "__main__":
    main()
