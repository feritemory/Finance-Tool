"""Optik der App: Notion-artiges Styling und einheitliches Diagramm-Chrome.

Die Farbwerte der Diagramme stammen aus einer auf Farbfehlsichtigkeit
geprüften kategorialen Palette (siehe finance/categories.py). Hier liegt nur
das "Drumherum": Flächen, Typografie, Raster, Achsen, Legenden.
"""

from __future__ import annotations

# --- Notion-artige Design-Token ------------------------------------------
INK = "#37352f"          # Haupttext
INK_SOFT = "#787774"     # Sekundärtext
INK_FAINT = "#9b9a97"    # Tertiärtext / Achsen
LINE = "#e9e9e7"         # Rahmen / Raster
SURFACE = "#ffffff"
SURFACE_SOFT = "#f7f7f5"

FONT = ('ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI", '
        'Inter, Helvetica, Arial, sans-serif')

CSS = f"""
<style>
  /* ---------- Grundfläche & Typografie ---------- */
  html, body, [class*="css"], .stApp {{
      font-family: {FONT};
      color: {INK};
  }}
  .stApp {{ background: {SURFACE}; }}
  .block-container {{ padding-top: 2.2rem; max-width: 1400px; }}

  h1, h2, h3, h4 {{
      color: {INK};
      font-weight: 650;
      letter-spacing: -0.011em;
  }}
  h1 {{ font-size: 1.9rem !important; }}
  h2 {{ font-size: 1.25rem !important; }}
  h3 {{ font-size: 1.05rem !important; }}

  /* ---------- Kennzahl-Kacheln ---------- */
  [data-testid="stMetric"] {{
      background: {SURFACE_SOFT};
      border: 1px solid {LINE};
      border-radius: 8px;
      padding: 14px 16px;
  }}
  [data-testid="stMetricLabel"] p {{
      color: {INK_SOFT} !important;
      font-size: 0.78rem !important;
      font-weight: 500 !important;
      letter-spacing: 0.01em;
  }}
  [data-testid="stMetricValue"] {{
      color: {INK} !important;
      font-size: 1.45rem !important;
      font-weight: 600 !important;
      letter-spacing: -0.02em;
  }}

  /* ---------- Reiter ---------- */
  .stTabs [data-baseweb="tab-list"] {{
      gap: 4px;
      border-bottom: 1px solid {LINE};
  }}
  .stTabs [data-baseweb="tab"] {{
      height: 40px;
      padding: 0 14px;
      background: transparent;
      border-radius: 6px 6px 0 0;
      color: {INK_SOFT};
      font-size: 0.92rem;
      font-weight: 500;
  }}
  .stTabs [aria-selected="true"] {{
      background: {SURFACE_SOFT};
      color: {INK};
  }}

  /* ---------- Seitenleiste ---------- */
  [data-testid="stSidebar"] {{
      background: {SURFACE_SOFT};
      border-right: 1px solid {LINE};
  }}
  [data-testid="stSidebar"] .block-container {{ padding-top: 1.5rem; }}

  /* ---------- Bedienelemente ---------- */
  .stButton > button {{
      border-radius: 6px;
      border: 1px solid {LINE};
      font-weight: 500;
      transition: background 120ms ease, border-color 120ms ease;
  }}
  .stButton > button:hover {{
      background: {SURFACE_SOFT};
      border-color: #d6d5d2;
  }}
  div[data-testid="stExpander"] details {{
      border: 1px solid {LINE};
      border-radius: 8px;
      background: {SURFACE};
  }}
  div[data-baseweb="select"] > div, .stTextInput input {{
      border-radius: 6px !important;
      border-color: {LINE} !important;
  }}

  /* ---------- Tabellen & Trenner ---------- */
  hr {{ border-color: {LINE}; margin: 1.6rem 0; }}
  [data-testid="stDataFrame"] {{
      border: 1px solid {LINE};
      border-radius: 8px;
  }}
  /* Kopfzeile über Kennzahlgruppen */
  .kpi-caption {{
      color: {INK_FAINT};
      font-size: 0.76rem;
      font-weight: 600;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      margin: 0 0 6px 2px;
  }}
</style>
"""


def style_fig(fig, height: int = 380, legend: bool = True,
              show_grid: bool = True):
    """Legt das einheitliche, zurückhaltende Diagramm-Chrome an.

    Feines, durchgezogenes Raster (nur waagerecht), keine Achsenlinien, Legende
    oben – so tritt das Diagramm-Drumherum hinter die Daten zurück.
    """
    fig.update_layout(
        height=height,
        font=dict(family=FONT, size=12, color=INK_SOFT),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=10 if not legend else 34, b=8, l=8, r=8),
        hoverlabel=dict(bgcolor=SURFACE, bordercolor=LINE,
                        font=dict(family=FONT, size=12, color=INK)),
        showlegend=legend,
        legend=dict(orientation="h", yanchor="bottom", y=1.0,
                    xanchor="left", x=0, title_text="",
                    font=dict(size=12, color=INK_SOFT)),
        bargap=0.28,
        bargroupgap=0.08,   # schmaler Flächenspalt zwischen Balken einer Gruppe
    )
    fig.update_xaxes(showgrid=False, showline=False, zeroline=False,
                     ticks="outside", tickcolor=LINE, ticklen=4,
                     tickfont=dict(color=INK_FAINT, size=11))
    fig.update_yaxes(showgrid=show_grid, gridcolor=LINE, gridwidth=1,
                     griddash="solid", showline=False, zeroline=False,
                     tickfont=dict(color=INK_FAINT, size=11))
    return fig
