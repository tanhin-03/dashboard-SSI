"""
theme.py
Shared 'Modern Dark Finance' styling constants for Streamlit + Plotly,
matching the same color system used in the Power BI version of this project.
"""

import plotly.graph_objects as go
import plotly.io as pio

COLORS = {
    "background": "#0E1117",
    "surface": "#161B22",
    "surface2": "#1C222D",
    "border": "#252B36",
    "text": "#F5F5F5",
    "text_secondary": "#9AA4B2",
    "green": "#00C896",
    "red": "#FF4B4B",
    "blue": "#2D9CDB",
    "gold": "#F2C94C",
    "purple": "#9B51E0",
}

CATEGORICAL_PALETTE = [
    "#00C896", "#2D9CDB", "#F2C94C", "#9B51E0", "#FF4B4B",
    "#56CCF2", "#F2994A", "#BB6BD9", "#6FCF97", "#EB5757",
]


def register_plotly_theme():
    """Register a 'dark_finance' Plotly template and set it as default."""
    template = go.layout.Template()
    template.layout = go.Layout(
        paper_bgcolor=COLORS["surface"],
        plot_bgcolor=COLORS["surface"],
        font=dict(family="Segoe UI, sans-serif", color=COLORS["text"], size=12),
        colorway=CATEGORICAL_PALETTE,
        xaxis=dict(
            gridcolor=COLORS["border"], zerolinecolor=COLORS["border"],
            linecolor=COLORS["border"], tickfont=dict(color=COLORS["text_secondary"]),
        ),
        yaxis=dict(
            gridcolor=COLORS["border"], zerolinecolor=COLORS["border"],
            linecolor=COLORS["border"], tickfont=dict(color=COLORS["text_secondary"]),
        ),
        legend=dict(font=dict(color=COLORS["text_secondary"])),
        margin=dict(l=40, r=20, t=40, b=40),
    )
    pio.templates["dark_finance"] = template
    pio.templates.default = "dark_finance"


def inject_css():
    """Returns a CSS string to inject via st.markdown(..., unsafe_allow_html=True)."""
    return f"""
    <style>
    :root {{
        color-scheme: dark;
    }}
    .stApp {{
        background-color: {COLORS['background']};
        overflow-x: hidden;
    }}
    .stApp [data-testid="stHeader"] {{
        background: transparent;
        z-index: 1000;
    }}
    .stApp [data-testid="stToolbar"] {{
        z-index: 1001;
        pointer-events: auto !important;
    }}
    .stApp [data-testid="stToolbar"] button,
    .stApp [data-testid="stToolbar"] [role="button"] {{
        pointer-events: auto !important;
    }}
    .stApp [data-testid="stToolbar"] [title*="Edit"],
    .stApp [data-testid="stToolbar"] [title*="edit"],
    .stApp [data-testid="stToolbar"] [aria-label*="Edit"],
    .stApp [data-testid="stToolbar"] [aria-label*="edit"] {{
        display: none !important;
        visibility: hidden !important;
        opacity: 0 !important;
        pointer-events: none !important;
    }}
    .stApp [data-testid="stMainBlockContainer"] {{
        overflow: visible;
    }}
    div[data-testid="stMetric"] {{
        background-color: {COLORS['surface']};
        border: 1px solid {COLORS['border']};
        border-radius: 16px;
        padding: 16px 20px;
    }}
    div[data-testid="stMetricLabel"] {{
        color: {COLORS['text_secondary']} !important;
        font-size: 0.8rem !important;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }}
    div[data-testid="stMetricValue"] {{
        color: {COLORS['text']} !important;
        font-weight: 600;
    }}
    section[data-testid="stSidebar"] {{
        background-color: {COLORS['surface']};
        border-right: 1px solid {COLORS['border']};
        z-index: 1000;
    }}
    .block-container {{
        padding-top: 2rem;
    }}
    </style>
    """


def fmt_vnd(value: float) -> str:
    """Format a number as VND currency, e.g. 12,345,000 ₫."""
    if value is None or value != value:  # NaN check
        return "—"
    sign = "-" if value < 0 else ""
    return f"{sign}{abs(value):,.0f} ₫"


def fmt_pct(value: float) -> str:
    if value is None or value != value:
        return "—"
    return f"{value * 100:,.2f}%"
