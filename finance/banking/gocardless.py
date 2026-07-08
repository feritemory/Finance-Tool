"""Optionale PSD2-Anbindung über die GoCardless Bank Account Data API
(früher Nordigen) – kostenloser Kontozugriff für Banken in der EU,
inkl. Consorsbank.

Dieses Modul ist bewusst als eigenständiger, optionaler Baustein gehalten. Es
wird nur aktiv, wenn du dich (kostenlos) registrierst und deine API-Zugangs-
daten hinterlegst:

    1. Konto anlegen: https://bankaccountdata.gocardless.com/  (kostenlos)
    2. Unter "User Secrets" ein Secret ID + Secret Key erzeugen.
    3. Als Umgebungsvariablen setzen (oder in der App eingeben):
           GOCARDLESS_SECRET_ID
           GOCARDLESS_SECRET_KEY

Ablauf (PSD2 / Open Banking):
    - Token holen  -> create_requisition() erzeugt einen Bank-Login-Link.
    - Du loggst dich einmalig bei der Consorsbank ein und bestätigst den
      Zugriff (Starke Kundenauthentifizierung, SCA).
    - Danach können 90 Tage lang Umsätze abgerufen werden; danach ist eine
      erneute Bestätigung nötig (gesetzlich vorgeschrieben).

Die zurückgegebenen Umsätze werden in ``importer.Transaction`` übersetzt und
können über ``storage.add_transactions`` gespeichert werden – exakt wie ein
CSV-Import.

Hinweis: Für den reinen CSV-Betrieb ist dieses Modul nicht erforderlich; es
importiert ``requests`` nur bei Bedarf, damit die App auch ohne dieses Paket
läuft.
"""

from __future__ import annotations

import os
from datetime import date, datetime

BASE_URL = "https://bankaccountdata.gocardless.com/api/v2"

# GoCardless-Institution-ID der Consorsbank in Deutschland.
CONSORSBANK_INSTITUTION_ID = "CONSORSBANK_CSDBDE71"


class GoCardlessError(RuntimeError):
    pass


def _requests():
    try:
        import requests  # noqa: PLC0415
        return requests
    except ImportError as exc:  # pragma: no cover
        raise GoCardlessError(
            "Das Paket 'requests' wird für die PSD2-Anbindung benötigt. "
            "Installiere es mit:  pip install requests"
        ) from exc


class GoCardlessClient:
    def __init__(self, secret_id: str | None = None, secret_key: str | None = None):
        self.secret_id = secret_id or os.getenv("GOCARDLESS_SECRET_ID", "")
        self.secret_key = secret_key or os.getenv("GOCARDLESS_SECRET_KEY", "")
        self._access_token: str | None = None
        if not self.secret_id or not self.secret_key:
            raise GoCardlessError(
                "Keine GoCardless-Zugangsdaten gefunden. Setze GOCARDLESS_SECRET_ID "
                "und GOCARDLESS_SECRET_KEY oder übergib sie direkt."
            )

    # -- Authentifizierung ---------------------------------------------------
    def authenticate(self) -> str:
        r = _requests().post(
            f"{BASE_URL}/token/new/",
            json={"secret_id": self.secret_id, "secret_key": self.secret_key},
            timeout=30,
        )
        if r.status_code != 200:
            raise GoCardlessError(f"Token-Anfrage fehlgeschlagen: {r.status_code} {r.text}")
        self._access_token = r.json()["access"]
        return self._access_token

    def _headers(self) -> dict:
        if not self._access_token:
            self.authenticate()
        return {"Authorization": f"Bearer {self._access_token}",
                "Content-Type": "application/json"}

    # -- Bank-Login (Requisition) -------------------------------------------
    def create_requisition(self, redirect_url: str = "https://localhost/finance",
                           institution_id: str = CONSORSBANK_INSTITUTION_ID,
                           reference: str | None = None) -> dict:
        """Erzeugt einen Bank-Login-Link. Rückgabe enthält 'link' und 'id'."""
        req = _requests()
        payload = {
            "redirect": redirect_url,
            "institution_id": institution_id,
            "reference": reference or f"finance-tool-{datetime.now():%Y%m%d%H%M%S}",
            "user_language": "DE",
        }
        r = req.post(f"{BASE_URL}/requisitions/", headers=self._headers(),
                     json=payload, timeout=30)
        if r.status_code not in (200, 201):
            raise GoCardlessError(f"Requisition fehlgeschlagen: {r.status_code} {r.text}")
        return r.json()

    def get_requisition(self, requisition_id: str) -> dict:
        r = _requests().get(f"{BASE_URL}/requisitions/{requisition_id}/",
                            headers=self._headers(), timeout=30)
        if r.status_code != 200:
            raise GoCardlessError(f"Requisition-Abruf fehlgeschlagen: {r.text}")
        return r.json()

    # -- Umsätze abrufen -----------------------------------------------------
    def list_accounts(self, requisition_id: str) -> list[str]:
        return self.get_requisition(requisition_id).get("accounts", [])

    def get_transactions(self, account_id: str,
                         date_from: date | None = None) -> list:
        """Ruft Umsätze eines Kontos ab und liefert importer.Transaction-Objekte."""
        from ..importer import Transaction, parse_amount, parse_date

        params = {}
        if date_from:
            params["date_from"] = date_from.isoformat()
        r = _requests().get(f"{BASE_URL}/accounts/{account_id}/transactions/",
                           headers=self._headers(), params=params, timeout=60)
        if r.status_code != 200:
            raise GoCardlessError(f"Umsatz-Abruf fehlgeschlagen: {r.text}")

        data = r.json().get("transactions", {})
        raw = data.get("booked", []) + data.get("pending", [])
        result: list[Transaction] = []
        for tx in raw:
            amt_obj = tx.get("transactionAmount", {})
            try:
                amount = float(amt_obj.get("amount"))
            except (TypeError, ValueError):
                continue
            d = parse_date(tx.get("bookingDate") or tx.get("valueDate") or "")
            if d is None:
                continue
            counterparty = (tx.get("creditorName") or tx.get("debtorName") or "")
            desc = tx.get("remittanceInformationUnstructured") or ""
            if not desc:
                desc = " ".join(tx.get("remittanceInformationUnstructuredArray", []) or [])
            result.append(Transaction(
                date=d,
                value_date=parse_date(tx.get("valueDate") or ""),
                amount=amount,
                currency=(amt_obj.get("currency") or "EUR").upper(),
                counterparty=counterparty.strip(),
                iban=(tx.get("creditorAccount", {}) or {}).get("iban", "")
                     or (tx.get("debtorAccount", {}) or {}).get("iban", ""),
                description=desc.strip(),
                booking_text=tx.get("bankTransactionCode", "") or "",
                source="consorsbank-psd2",
            ))
        return result


def is_configured() -> bool:
    return bool(os.getenv("GOCARDLESS_SECRET_ID") and os.getenv("GOCARDLESS_SECRET_KEY"))
