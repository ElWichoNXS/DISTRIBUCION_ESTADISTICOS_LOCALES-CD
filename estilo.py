"""Estilo visual compartido (mismo lenguaje que las apps Min/Max y Verificación de traspasos)."""
import altair as alt
import streamlit as st

ROJO, ROJO_OSC = "#E30613", "#A30410"
C_OK, C_ALT, C_BAJO, C_EXT, C_PEND = "#1FA391", "#4B86E6", "#D39A2E", "#E5414B", "#8C8C8C"
BORDE = "color-mix(in srgb, currentColor 16%, transparent)"
TARJETA = "color-mix(in srgb, currentColor 4%, transparent)"

CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
html, body, .stApp, h1, h2, h3, h4, p, label, li, button, input, textarea {{ font-family: 'Inter', system-ui, -apple-system, 'Segoe UI', sans-serif; }}
.block-container {{ padding-top: 1rem; max-width: 1480px; }}
header[data-testid="stHeader"] {{ background: transparent; }}

.hero {{ background: linear-gradient(115deg, {ROJO} 0%, {ROJO_OSC} 100%); border-radius: 16px;
    padding: 22px 30px; display: flex; justify-content: space-between; align-items: center; gap: 24px;
    box-shadow: 0 8px 24px rgba(227,6,19,.25); flex-wrap: wrap; }}
.hero h1 {{ color:#fff !important; margin:0; font-size:1.75rem; font-weight:800; letter-spacing:-.4px; padding:0; }}
.hero p {{ color:#ffe3e5 !important; margin:4px 0 0 0; font-size:.95rem; }}
.pasos {{ display:flex; gap:10px; flex-wrap:wrap; }}
.paso {{ display:flex; align-items:center; gap:8px; background:rgba(255,255,255,.14); color:#fff;
    padding:7px 14px 7px 8px; border-radius:30px; font-size:.82rem; font-weight:600; }}
.paso b {{ width:22px; height:22px; border-radius:50%; background:rgba(255,255,255,.28); display:flex;
    align-items:center; justify-content:center; font-size:.78rem; }}
.paso.ok {{ background:#fff; color:{ROJO}; }}
.paso.ok b {{ background:{ROJO}; color:#fff; }}

.kpis {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:14px; margin:6px 0 4px 0; }}
.kpi {{ background:{TARJETA}; border:1px solid {BORDE}; border-radius:14px; padding:16px 18px; position:relative; overflow:hidden; }}
.kpi::before {{ content:""; position:absolute; left:0; top:0; bottom:0; width:5px; background:var(--ac, {ROJO}); }}
.kpi .l {{ font-size:.8rem; font-weight:600; opacity:.7; }}
.kpi .v {{ font-size:1.9rem; font-weight:800; letter-spacing:-.6px; line-height:1.15; margin-top:2px; }}
.kpi .s {{ font-size:.78rem; opacity:.62; margin-top:2px; }}

.seccion {{ margin: 22px 0 8px 0; font-size:1.12rem; font-weight:800; letter-spacing:-.2px; }}
.seccion small {{ display:block; font-weight:400; opacity:.62; font-size:.84rem; letter-spacing:0; margin-top:1px; }}
.nota {{ border-left:4px solid {ROJO}; background:{TARJETA}; padding:10px 14px; border-radius:0 10px 10px 0; font-size:.88rem; }}
.nota.ok {{ border-left-color:{C_OK}; }}
.nota.warn {{ border-left-color:{C_BAJO}; }}

/* Embudo de cobertura */
.flujo {{ display:flex; gap:0; border-radius:12px; overflow:hidden; border:1px solid {BORDE}; margin:6px 0 2px 0; }}
.flujo div {{ padding:10px 12px; color:#fff; font-size:.8rem; font-weight:700; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
.leyenda {{ display:flex; gap:16px; flex-wrap:wrap; font-size:.8rem; opacity:.85; margin-top:6px; }}
.leyenda span::before {{ content:""; display:inline-block; width:10px; height:10px; border-radius:3px; margin-right:6px; background:var(--c); }}

section[data-testid="stSidebar"] {{ border-right:1px solid {BORDE}; }}
section[data-testid="stSidebar"] h2 {{ color:{ROJO} !important; font-size:1.15rem; font-weight:800; }}
div[data-testid="stFileUploader"] section {{ background:rgba(227,6,19,.06); border:2px dashed {ROJO}; border-radius:14px; min-height:92px; align-items:center; }}
div[data-testid="stFileUploader"] label p {{ white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
button[data-testid="stBaseButton-primary"], div[data-testid="stDownloadButton"] button {{
    background:{ROJO}; color:#fff; border:none; border-radius:10px; font-weight:700; box-shadow:0 3px 10px rgba(227,6,19,.3); }}
button[data-testid="stBaseButton-primary"]:hover, div[data-testid="stDownloadButton"] button:hover {{ background:{ROJO_OSC}; color:#fff; border:none; }}
button[data-testid="stBaseButton-primary"] p, div[data-testid="stDownloadButton"] button p {{ color:#fff; }}
button[data-testid="stBaseButton-secondary"] {{ border:1.5px solid {ROJO}; border-radius:10px; font-weight:600; }}
button[data-baseweb="tab"] {{ font-weight:700; }}
button[data-baseweb="tab"][aria-selected="true"] {{ color:{ROJO}; }}
div[data-baseweb="tab-highlight"] {{ background-color:{ROJO}; height:3px; }}
div[data-testid="stDataFrame"] {{ border:1px solid {BORDE}; border-radius:12px; overflow:hidden; }}
div[data-testid="stExpander"] {{ border:1px solid {BORDE}; border-radius:12px; background:{TARJETA}; }}
div[data-testid="stExpander"] summary p {{ font-weight:700; }}
div[data-testid="stVerticalBlockBorderWrapper"] {{ border-radius:14px; }}
hr {{ border-color:{BORDE}; }}
/* selector de módulo */
div[data-testid="stButtonGroup"] button {{ border-radius:10px; font-weight:700; padding:6px 16px; }}
div[data-testid="stButtonGroup"] button[aria-checked="true"], div[data-testid="stButtonGroup"] button[kind="segmented_controlActive"] {{
    background:{ROJO}; color:#fff; border-color:{ROJO}; }}
div[data-testid="stButtonGroup"] button[kind="segmented_controlActive"] p {{ color:#fff; }}
</style>
"""


def aplicar_estilo():
    st.markdown(CSS, unsafe_allow_html=True)



# ----------------------------------------------------------------------
# Utilidades de presentación
# ----------------------------------------------------------------------
def seccion(titulo, sub=""):
    st.markdown(f'<div class="seccion">{titulo}<small>{sub}</small></div>', unsafe_allow_html=True)


def kpis(items):
    """items: (etiqueta, valor, subtítulo, color)"""
    html = "".join(
        f'<div class="kpi" style="--ac:{c}"><div class="l">{l}</div><div class="v">{v}</div><div class="s">{s}</div></div>'
        for l, v, s, c in items)
    st.markdown(f'<div class="kpis">{html}</div>', unsafe_allow_html=True)


def nota(texto, tipo=""):
    st.markdown(f'<div class="nota {tipo}">{texto}</div>', unsafe_allow_html=True)


def n(x):
    x = float(x or 0)
    return f"{int(round(x)):,}".replace(",", ".") if abs(x - round(x)) < 1e-9 else f"{x:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".")


def alto_tabla(filas, maximo=460):
    """Alto justo para la tabla (sin filas vacías), con tope."""
    return min(maximo, 35 * (filas + 1) + 3)


def pct(a, b):
    return f"{a / b:.0%}" if b else "0%"


def grafico(titulo, sub, chart):
    with st.container(border=True):
        st.markdown(f"**{titulo}**" + (f"  \n<span style='opacity:.62;font-size:.82rem'>{sub}</span>" if sub else ""),
                    unsafe_allow_html=True)
        # fit-x: el ancho se ajusta al contenedor; el alto se respeta (la leyenda no aplasta las barras)
        chart = chart.properties(autosize=alt.AutoSizeParams(type="fit-x", contains="padding"))
        st.altair_chart(chart, width="stretch")


