"""Import von Kontoumsätzen aus CSV- und CAMT-Dateien.

Schwerpunkt: Consorsbank-CSV-Export, aber der CSV-Parser ist flexibel genug
für die meisten deutschen Banken (Sparkasse, DKB, ING, ...), da Spalten über
Alias-Namen erkannt und Zahlen/Daten im deutschen Format geparst werden.
"""

from __future__ import annotations

import csv
import hashlib
import io
import re
from dataclasses import dataclass, asdict
from datetime import date, datetime
from xml.etree import ElementTree as ET


@dataclass
class Transaction:
    date: date                 # Buchungsdatum
    value_date: date | None    # Valutadatum
    amount: float              # negativ = Ausgabe, positiv = Einnahme
    currency: str
    counterparty: str          # Sender / Empfänger
    iban: str
    description: str           # Verwendungszweck
    booking_text: str          # Buchungstext / Art
    source: str                # Dateiname / Quelle

    def dedup_hash(self) -> str:
        raw = f"{self.date.isoformat()}|{self.amount:.2f}|{self.counterparty}|{self.description}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


# ---------------------------------------------------------------------------
# Hilfsfunktionen: deutsche Zahlen und Daten
# ---------------------------------------------------------------------------

def parse_amount(raw: str) -> float:
    """Parst Beträge in deutschem oder englischem Format.

    Beispiele: "-1.234,56" -> -1234.56 ; "1234,56" -> 1234.56 ;
               "12.50" -> 12.50 ; "1.234" -> 1234.0 (Tausenderpunkt)
    """
    if raw is None:
        raise ValueError("leerer Betrag")
    s = str(raw).strip()
    s = s.replace("€", "").replace("EUR", "").replace(" ", "").replace("\xa0", "")
    if not s:
        raise ValueError("leerer Betrag")

    sign = 1
    # führendes/anhängendes Minus, evtl. in Klammern (Buchhaltung)
    if s.startswith("(") and s.endswith(")"):
        sign = -1
        s = s[1:-1]
    if s.startswith("-"):
        sign = -1
        s = s[1:]
    elif s.startswith("+"):
        s = s[1:]

    has_comma = "," in s
    has_dot = "." in s

    if has_comma and has_dot:
        # rechtester Trenner ist Dezimaltrenner
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif has_comma:
        s = s.replace(",", ".")
    elif has_dot:
        # Lone dot: wenn genau 3 Nachkommastellen -> Tausendertrennung
        after = s.rsplit(".", 1)[1]
        if s.count(".") > 1 or len(after) == 3:
            s = s.replace(".", "")
        # sonst als Dezimaltrenner belassen

    return sign * float(s)


_DATE_FORMATS = ("%d.%m.%Y", "%d.%m.%y", "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y")


def parse_date(raw: str) -> date | None:
    if not raw:
        return None
    s = str(raw).strip()
    if not s:
        return None
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


# ---------------------------------------------------------------------------
# CSV-Import
# ---------------------------------------------------------------------------

# Spalten-Aliase (kleingeschrieben, ohne Sonderzeichen-Vergleich per "in")
_COLUMN_ALIASES = {
    "date": ["buchung", "buchungstag", "buchungsdatum", "datum", "date"],
    "value_date": ["valuta", "valutadatum", "wertstellung", "wert"],
    "amount": ["betrag", "umsatz", "betrag in eur", "betrag eur", "amount", "wert in eur"],
    "currency": ["währung", "waehrung", "currency"],
    "counterparty": [
        "sender/empfänger", "sender/empfaenger", "empfänger", "empfaenger",
        "auftraggeber/empfänger", "auftraggeber", "name", "beguenstigter",
        "begünstigter", "zahlungspflichtiger", "payee",
    ],
    "iban": ["iban", "kontonummer", "iban/konto-nr.", "konto-nr", "account"],
    "description": [
        "verwendungszweck", "buchungstext", "vwz", "zweck", "beschreibung",
        "reference", "remittance",
    ],
    "booking_text": ["buchungstext", "umsatzart", "art", "typ", "vorgang", "transaction type"],
}


def _detect_columns(header: list[str]) -> dict[str, int]:
    norm = [h.strip().lower() for h in header]
    mapping: dict[str, int] = {}
    for field, aliases in _COLUMN_ALIASES.items():
        for alias in aliases:
            for idx, col in enumerate(norm):
                if col == alias:
                    mapping[field] = idx
                    break
            if field in mapping:
                break
        if field in mapping:
            continue
        # zweite Runde: Teilstring-Treffer
        for alias in aliases:
            for idx, col in enumerate(norm):
                if alias in col:
                    mapping[field] = idx
                    break
            if field in mapping:
                break
    return mapping


def _sniff_dialect(sample: str) -> csv.Dialect:
    try:
        return csv.Sniffer().sniff(sample, delimiters=";,\t|")
    except csv.Error:
        class _D(csv.Dialect):
            delimiter = ";"
            quotechar = '"'
            doublequote = True
            skipinitialspace = True
            lineterminator = "\r\n"
            quoting = csv.QUOTE_MINIMAL
        return _D()


def _decode(data: bytes) -> str:
    for enc in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("latin-1", errors="replace")


def parse_csv(data: bytes, source: str = "csv") -> list[Transaction]:
    text = _decode(data)

    # Manche Bank-Exporte haben Vorspann-Zeilen ("Umsätze Girokonto ..." usw.).
    # Wir suchen die Header-Zeile: die erste Zeile, die mind. 3 Trennzeichen und
    # ein bekanntes Alias enthält.
    lines = text.splitlines()
    header_idx = 0
    all_aliases = {a for lst in _COLUMN_ALIASES.values() for a in lst}
    for i, line in enumerate(lines[:30]):
        low = line.lower()
        if any(a in low for a in ("betrag", "buchung", "datum", "amount")) and \
                (line.count(";") >= 2 or line.count(",") >= 2 or line.count("\t") >= 2):
            header_idx = i
            break

    body = "\n".join(lines[header_idx:])
    dialect = _sniff_dialect("\n".join(lines[header_idx:header_idx + 5]))

    reader = csv.reader(io.StringIO(body), dialect)
    rows = list(reader)
    if not rows:
        return []

    header = rows[0]
    cols = _detect_columns(header)
    if "date" not in cols or "amount" not in cols:
        raise ValueError(
            "CSV konnte nicht erkannt werden – benötige mindestens eine "
            "Datums- und eine Betragsspalte. Erkannte Spalten: "
            + ", ".join(header)
        )

    def get(row: list[str], field: str) -> str:
        idx = cols.get(field)
        if idx is None or idx >= len(row):
            return ""
        return row[idx].strip()

    transactions: list[Transaction] = []
    for row in rows[1:]:
        if not any(cell.strip() for cell in row):
            continue
        raw_amount = get(row, "amount")
        raw_date = get(row, "date")
        if not raw_amount or not raw_date:
            continue
        d = parse_date(raw_date)
        if d is None:
            continue
        try:
            amount = parse_amount(raw_amount)
        except ValueError:
            continue

        transactions.append(Transaction(
            date=d,
            value_date=parse_date(get(row, "value_date")),
            amount=amount,
            currency=(get(row, "currency") or "EUR")[:3].upper(),
            counterparty=_clean(get(row, "counterparty")),
            iban=get(row, "iban"),
            description=_clean(get(row, "description")),
            booking_text=_clean(get(row, "booking_text")),
            source=source,
        ))
    return transactions


def _clean(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


# ---------------------------------------------------------------------------
# CAMT.052/053 (XML) – ISO 20022 Kontoauszug
# ---------------------------------------------------------------------------

def parse_camt(data: bytes, source: str = "camt") -> list[Transaction]:
    text = _decode(data)
    # Namespace entfernen für einfacheres Parsen
    text = re.sub(r'\sxmlns(:\w+)?="[^"]+"', "", text, count=0)
    root = ET.fromstring(text)

    transactions: list[Transaction] = []
    for ntry in root.iter("Ntry"):
        amt_el = ntry.find("Amt")
        if amt_el is None or not amt_el.text:
            continue
        amount = parse_amount(amt_el.text)
        currency = (amt_el.get("Ccy") or "EUR").upper()
        cdtdbt = (ntry.findtext("CdtDbtInd") or "").upper()
        if cdtdbt == "DBIT":
            amount = -abs(amount)
        else:
            amount = abs(amount)

        book_dt = ntry.findtext("BookgDt/Dt") or ntry.findtext("BookgDt/DtTm", "")[:10]
        val_dt = ntry.findtext("ValDt/Dt") or ntry.findtext("ValDt/DtTm", "")[:10]
        d = parse_date(book_dt) or parse_date(val_dt)
        if d is None:
            continue

        # Detailinformationen (Empfänger, Verwendungszweck)
        counterparty = ""
        description = ""
        booking_text = ntry.findtext("AddtlNtryInf") or ""
        dtl = ntry.find("NtryDtls/TxDtls")
        if dtl is not None:
            if cdtdbt == "DBIT":
                counterparty = dtl.findtext("RltdPties/Cdtr/Nm") or ""
            else:
                counterparty = dtl.findtext("RltdPties/Dbtr/Nm") or ""
            ustrd = [e.text for e in dtl.iter("Ustrd") if e.text]
            description = " ".join(ustrd)

        transactions.append(Transaction(
            date=d,
            value_date=parse_date(val_dt),
            amount=amount,
            currency=currency,
            counterparty=_clean(counterparty),
            iban="",
            description=_clean(description),
            booking_text=_clean(booking_text),
            source=source,
        ))
    return transactions


def parse_file(filename: str, data: bytes) -> list[Transaction]:
    """Erkennt anhand von Dateiendung/Inhalt das Format und parst entsprechend."""
    name = filename.lower()
    head = data[:512].lstrip()
    if name.endswith(".xml") or head.startswith(b"<?xml") or b"<Document" in data[:2048]:
        return parse_camt(data, source=filename)
    return parse_csv(data, source=filename)


def to_dict(t: Transaction) -> dict:
    d = asdict(t)
    d["date"] = t.date.isoformat()
    d["value_date"] = t.value_date.isoformat() if t.value_date else None
    return d
