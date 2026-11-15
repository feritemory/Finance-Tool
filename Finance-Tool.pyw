"""Startdatei des Finance-Tools (auch Einstiegspunkt für den Windows-Build).

Aus dem Quellcode starten:  python Finance-Tool.pyw
"""

import sys

from finance.gui.app import main

if __name__ == "__main__":
    sys.exit(main())
