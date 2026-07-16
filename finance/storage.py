"""SQLite-Persistenz für Umsätze."""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from datetime import date

import pandas as pd

from . import ml
from .categories import CATEGORIES, UNCATEGORIZED
from .categorize import categorize
from .importer import Transaction
from .merchants import merchant_key

DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data"
)
DB_PATH = os.path.join(DATA_DIR, "finance.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS transactions (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    dedup_hash    TEXT UNIQUE,
    date          TEXT NOT NULL,
    value_date    TEXT,
    amount        REAL NOT NULL,
    currency      TEXT DEFAULT 'EUR',
    counterparty  TEXT,
    iban          TEXT,
    bic           TEXT,
    description   TEXT,
    booking_text  TEXT,
    category      TEXT,
    category_manual INTEGER DEFAULT 0,   -- 1 = vom Nutzer manuell gesetzt
    is_recurring  INTEGER DEFAULT 0,     -- Fixkosten-Flag (auto erkannt / manuell)
    recurring_manual INTEGER DEFAULT 0,
    source        TEXT,
    imported_at   TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_tx_date ON transactions(date);
CREATE INDEX IF NOT EXISTS idx_tx_category ON transactions(category);

-- Gelernte Zuordnungen aus Nutzer-Korrekturen (Händler-Schlüssel -> Kategorie).
CREATE TABLE IF NOT EXISTS merchant_rules (
    merchant_key TEXT PRIMARY KEY,
    category     TEXT NOT NULL,
    updated_at   TEXT DEFAULT CURRENT_TIMESTAMP
);
"""


@contextmanager
def _connect():
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with _connect() as conn:
        conn.executescript(SCHEMA)
        # Leichte Migration: fehlende Spalten in bestehenden DBs ergänzen.
        existing = {row[1] for row in conn.execute("PRAGMA table_info(transactions)")}
        for col, ddl in (("bic", "bic TEXT"),):
            if col not in existing:
                conn.execute(f"ALTER TABLE transactions ADD COLUMN {ddl}")


def get_learned() -> dict[str, str]:
    """Gelernte Händler->Kategorie-Zuordnungen aus Nutzer-Korrekturen."""
    init_db()
    with _connect() as conn:
        return {r["merchant_key"]: r["category"]
                for r in conn.execute("SELECT merchant_key, category FROM merchant_rules")}


def add_transactions(transactions: list[Transaction]) -> tuple[int, int]:
    """Fügt Umsätze hinzu, überspringt Duplikate. Rückgabe: (neu, übersprungen).

    Selbstheilend: Ist ein Umsatz bereits vorhanden, aber BIC/IBAN fehlten
    (z. B. aus einem älteren Import), werden sie nachgetragen – so werden
    Trade-Republic-/Revolut-Überträge auch nachträglich korrekt erkannt.
    """
    init_db()
    learned = get_learned()
    model = ml.load_model()
    inserted = skipped = 0
    with _connect() as conn:
        for t in transactions:
            category = categorize(t.counterparty, t.description, t.booking_text,
                                  t.amount, t.iban, t.bic, learned, model)
            try:
                conn.execute(
                    """INSERT INTO transactions
                       (dedup_hash, date, value_date, amount, currency, counterparty,
                        iban, bic, description, booking_text, category, source)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        t.dedup_hash(), t.date.isoformat(),
                        t.value_date.isoformat() if t.value_date else None,
                        t.amount, t.currency, t.counterparty, t.iban, t.bic,
                        t.description, t.booking_text, category, t.source,
                    ),
                )
                inserted += 1
            except sqlite3.IntegrityError:
                skipped += 1
                # BIC/IBAN in bestehender Zeile nachtragen, falls sie fehlten.
                if t.bic or t.iban:
                    conn.execute(
                        """UPDATE transactions
                           SET bic = COALESCE(NULLIF(bic, ''), ?),
                               iban = COALESCE(NULLIF(iban, ''), ?)
                           WHERE dedup_hash = ?""",
                        (t.bic, t.iban, t.dedup_hash()),
                    )
    return inserted, skipped


def learn_merchant(merchant: str, category: str) -> None:
    """Speichert eine Nutzer-Korrektur als Regel für künftige Umsätze."""
    if not merchant:
        return
    with _connect() as conn:
        conn.execute(
            """INSERT INTO merchant_rules (merchant_key, category)
               VALUES (?, ?)
               ON CONFLICT(merchant_key) DO UPDATE SET
                   category=excluded.category, updated_at=CURRENT_TIMESTAMP""",
            (merchant, category),
        )


def load_dataframe() -> pd.DataFrame:
    init_db()
    with _connect() as conn:
        df = pd.read_sql_query("SELECT * FROM transactions", conn)
    if df.empty:
        return _empty_frame()
    df["date"] = pd.to_datetime(df["date"])
    df["value_date"] = pd.to_datetime(df["value_date"], errors="coerce")
    df["amount"] = df["amount"].astype(float)
    df["year"] = df["date"].dt.year
    df["month"] = df["date"].dt.to_period("M").astype(str)
    df["day"] = df["date"].dt.date
    return df.sort_values("date").reset_index(drop=True)


def _empty_frame() -> pd.DataFrame:
    cols = [
        "id", "dedup_hash", "date", "value_date", "amount", "currency",
        "counterparty", "iban", "bic", "description", "booking_text", "category",
        "category_manual", "is_recurring", "recurring_manual", "source",
        "imported_at", "year", "month", "day",
    ]
    return pd.DataFrame(columns=cols)


def update_category(tx_id: int, category: str, manual: bool = True,
                    learn: bool = True) -> int:
    """Setzt die Kategorie eines Umsatzes.

    Bei einer manuellen Korrektur wird die Zuordnung gelernt und – sofern
    ``learn`` – auf alle weiteren (nicht manuell gesetzten) Umsätze desselben
    Händlers übertragen. Rückgabe: Anzahl zusätzlich angepasster Umsätze.
    """
    also = 0
    with _connect() as conn:
        conn.execute(
            "UPDATE transactions SET category=?, category_manual=? WHERE id=?",
            (category, 1 if manual else 0, tx_id),
        )
        if manual and learn:
            row = conn.execute(
                "SELECT counterparty, description, booking_text, bic "
                "FROM transactions WHERE id=?", (tx_id,)
            ).fetchone()
            if row:
                key = merchant_key(row["counterparty"], row["description"],
                                   row["booking_text"], row["bic"] or "")
                if key:
                    conn.execute(
                        """INSERT INTO merchant_rules (merchant_key, category)
                           VALUES (?, ?)
                           ON CONFLICT(merchant_key) DO UPDATE SET
                               category=excluded.category, updated_at=CURRENT_TIMESTAMP""",
                        (key, category),
                    )
                    # Gleiche Händler-Buchungen (nicht manuell) mitziehen.
                    others = conn.execute(
                        "SELECT id, counterparty, description, booking_text, bic "
                        "FROM transactions WHERE category_manual=0 AND id!=?", (tx_id,)
                    ).fetchall()
                    for o in others:
                        if merchant_key(o["counterparty"], o["description"],
                                        o["booking_text"], o["bic"] or "") == key:
                            conn.execute("UPDATE transactions SET category=? WHERE id=?",
                                         (category, o["id"]))
                            also += 1
    return also


def set_recurring(tx_id: int, recurring: bool, manual: bool = True) -> None:
    with _connect() as conn:
        conn.execute(
            "UPDATE transactions SET is_recurring=?, recurring_manual=? WHERE id=?",
            (1 if recurring else 0, 1 if manual else 0, tx_id),
        )


def set_recurring_bulk(pairs: list[tuple[int, bool]]) -> None:
    """Setzt automatisch erkannte Fixkosten (ohne manuelle Flags zu überschreiben)."""
    with _connect() as conn:
        for tx_id, rec in pairs:
            conn.execute(
                "UPDATE transactions SET is_recurring=? "
                "WHERE id=? AND recurring_manual=0",
                (1 if rec else 0, tx_id),
            )


def recategorize_all(ml_threshold: float = ml.DEFAULT_THRESHOLD) -> int:
    """Kategorisiert alle nicht manuell gesetzten Umsätze neu (nach Regeländerung).

    Berücksichtigt gelernte Zuordnungen, aktuelle Regeln und – falls vorhanden –
    das lokale ML-Modell.
    """
    learned = get_learned()
    model = ml.load_model()
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, counterparty, description, booking_text, amount, iban, bic "
            "FROM transactions WHERE category_manual=0"
        ).fetchall()
        n = 0
        for r in rows:
            cat = categorize(r["counterparty"], r["description"], r["booking_text"],
                             r["amount"], r["iban"], r["bic"], learned, model,
                             ml_threshold)
            conn.execute("UPDATE transactions SET category=? WHERE id=?", (cat, r["id"]))
            n += 1
    return n


# Ausgaben-Kategorien (ohne Auffang-Kategorie) – nur diese lernt das ML-Modell.
_EXPENSE_CATS = [c.name for c in CATEGORIES
                 if c.typ == "ausgabe" and c.name != UNCATEGORIZED]


def train_model() -> dict:
    """Trainiert das lokale ML-Modell aus den bisher kategorisierten Ausgaben.

    Manuell korrigierte Buchungen fließen stärker gewichtet ein. Rückgabe:
    Metriken (Anzahl, Kategorien, geschätzte Genauigkeit).
    """
    init_db()
    with _connect() as conn:
        rows = conn.execute(
            "SELECT counterparty, description, booking_text, category, category_manual "
            "FROM transactions WHERE amount < 0 AND category IN "
            "(%s)" % ",".join("?" * len(_EXPENSE_CATS)),
            _EXPENSE_CATS,
        ).fetchall()

    samples = []
    for r in rows:
        text = ml.make_text(r["counterparty"], r["description"], r["booking_text"])
        weight = 3.0 if r["category_manual"] else 1.0
        samples.append((text, r["category"], weight))

    metrics = ml.train(samples)          # kann RuntimeError werfen (zu wenig Daten)
    return metrics


def count() -> int:
    init_db()
    with _connect() as conn:
        return conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]


def clear_all() -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM transactions")


def count_demo() -> int:
    """Anzahl der Demo-/Beispiel-Buchungen (source = 'sample')."""
    init_db()
    with _connect() as conn:
        return conn.execute(
            "SELECT COUNT(*) FROM transactions WHERE source='sample'"
        ).fetchone()[0]


def clear_demo() -> int:
    """Entfernt nur die Demo-Buchungen, echte importierte Umsätze bleiben erhalten."""
    with _connect() as conn:
        cur = conn.execute("DELETE FROM transactions WHERE source='sample'")
        return cur.rowcount


def count_learned() -> int:
    init_db()
    with _connect() as conn:
        return conn.execute("SELECT COUNT(*) FROM merchant_rules").fetchone()[0]


def clear_learned() -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM merchant_rules")
