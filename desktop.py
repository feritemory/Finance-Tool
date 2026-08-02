"""Finance-Tool als Desktop-Programm.

Startet den lokalen Server im Hintergrund und öffnet ihn in einem eigenen
Fenster. Ist ``pywebview`` vorhanden, wird ein natives Fenster verwendet
(unter Windows die eingebaute WebView2-Komponente von Edge) – sonst wird
ersatzweise der Standardbrowser geöffnet.

Start:
    python desktop.py

Der Server lauscht nur auf 127.0.0.1; es ist nichts von aussen erreichbar.
"""

from __future__ import annotations

import logging
import socket
import sys
import threading
import time
import urllib.request

TITEL = "Finance-Tool"


def freier_port() -> int:
    """Freien Port vom Betriebssystem geben lassen."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def starte_server(port: int) -> threading.Thread:
    from finance.server import create_app

    app = create_app()
    # Nur echte Fehler ausgeben – die Zugriffsprotokolle stören im Fenster nicht.
    logging.getLogger("werkzeug").setLevel(logging.ERROR)

    def lauf():
        app.run(host="127.0.0.1", port=port, debug=False,
                use_reloader=False, threaded=True)

    t = threading.Thread(target=lauf, daemon=True, name="finance-server")
    t.start()
    return t


def warte_auf_server(url: str, sekunden: float = 20.0) -> bool:
    """Wartet, bis der Server antwortet."""
    ende = time.time() + sekunden
    while time.time() < ende:
        try:
            with urllib.request.urlopen(url + "/api/meta", timeout=1):
                return True
        except Exception:  # noqa: BLE001
            time.sleep(0.15)
    return False


def main() -> int:
    port = freier_port()
    url = f"http://127.0.0.1:{port}"
    starte_server(port)

    if not warte_auf_server(url):
        print("[FEHLER] Der lokale Server ist nicht gestartet.", file=sys.stderr)
        return 1

    try:
        import webview  # noqa: PLC0415
    except ImportError:
        webview = None

    if webview is not None:
        webview.create_window(TITEL, url, width=1360, height=900,
                              min_size=(900, 640))
        webview.start()          # blockiert bis das Fenster geschlossen wird
        return 0

    # Rückfall: Standardbrowser. Das Programm laeuft weiter, bis es der
    # Nutzer im Terminal beendet.
    import webbrowser  # noqa: PLC0415
    print(f"{TITEL} laeuft: {url}")
    print("Fuer ein eigenes Fenster:  pip install pywebview")
    print("Zum Beenden dieses Fenster schliessen oder Strg+C druecken.")
    webbrowser.open(url)
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    sys.exit(main())
