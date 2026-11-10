"""Estilo visual compartido (mismo lenguaje que las apps Min/Max y Verificación de traspasos)."""
import altair as alt
import streamlit as st

ROJO, ROJO_OSC = "#E30613", "#B8050F"
C_OK, C_ALT, C_BAJO, C_EXT, C_PEND = "#1FA391", "#4B86E6", "#D39A2E", "#E5414B", "#8C8C8C"

# Paleta neutra (gris claro + blanco); el rojo es solo acento.
FONDO, SUPERFICIE = "#F4F5F7", "#FFFFFF"
TEXTO, TEXTO_2, TEXTO_3 = "#1F2933", "#52606D", "#8A94A3"
LINEA, LINEA_2 = "#E6E8EC", "#D3D8DF"
ROJO_SUAVE = "#FDEDEE"
SOMBRA = "0 1px 2px rgba(16,24,40,.04), 0 6px 16px rgba(16,24,40,.06)"
SOMBRA_2 = "0 2px 4px rgba(16,24,40,.05), 0 12px 28px rgba(16,24,40,.08)"
BORDE = LINEA          # compatibilidad con el código existente
TARJETA = SUPERFICIE

CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
html, body, .stApp, h1, h2, h3, h4, p, label, li, button, input, textarea {{ font-family: 'Inter', system-ui, -apple-system, 'Segoe UI', sans-serif; }}
.stApp {{ background:{FONDO}; color:{TEXTO}; }}
.block-container {{ padding-top: 1.6rem; padding-bottom: 3rem; max-width: 1440px; }}
header[data-testid="stHeader"] {{ background: transparent; }}
h1, h2, h3, h4 {{ color:{TEXTO}; }}

/* ---------- Banner superior: blanco, acento rojo a la izquierda, stepper horizontal ---------- */
.hero {{ background:{SUPERFICIE}; border:1px solid {LINEA}; border-left:4px solid {ROJO}; border-radius:14px;
    padding:22px 28px; display:flex; justify-content:space-between; align-items:center; gap:28px; flex-wrap:wrap;
    box-shadow:{SOMBRA}; }}
.hero h1 {{ color:{TEXTO} !important; margin:0; font-size:1.55rem; font-weight:800; letter-spacing:-.4px; padding:0; }}
.hero p {{ color:{TEXTO_2} !important; margin:6px 0 0 0; font-size:.92rem; max-width:620px; }}
.hero .eyebrow {{ color:{ROJO}; font-size:.72rem; font-weight:700; letter-spacing:.08em; text-transform:uppercase; margin-bottom:4px; }}
.stepper {{ display:flex; align-items:flex-start; gap:0; min-width:420px; }}
.step {{ display:flex; flex-direction:column; align-items:center; gap:8px; width:120px; position:relative; }}
.step .dot {{ width:30px; height:30px; border-radius:50%; display:flex; align-items:center; justify-content:center;
    font-size:.8rem; font-weight:700; background:{SUPERFICIE}; color:{TEXTO_3}; border:2px solid {LINEA_2}; z-index:1; }}
.step .lbl {{ font-size:.76rem; font-weight:600; color:{TEXTO_3}; text-align:center; line-height:1.2; }}
.step::before {{ content:""; position:absolute; top:15px; left:-50%; width:100%; height:2px; background:{LINEA_2}; }}
.step:first-child::before {{ display:none; }}
.step.done .dot {{ background:{ROJO}; border-color:{ROJO}; color:#fff; }}
.step.done .lbl, .step.actual .lbl {{ color:{TEXTO}; }}
.step.done::before, .step.actual::before {{ background:{ROJO}; }}
.step.actual .dot {{ border-color:{ROJO}; color:{ROJO}; box-shadow:0 0 0 4px {ROJO_SUAVE}; }}
/* compatibilidad: chips antiguos */
.pasos {{ display:flex; gap:10px; flex-wrap:wrap; }}

/* ---------- Tarjetas KPI ---------- */
.kpis {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(160px,1fr)); gap:16px; margin:8px 0 6px 0; }}
.kpi {{ background:{SUPERFICIE}; border:1px solid {LINEA}; border-radius:14px; padding:18px 20px; position:relative;
    overflow:hidden; box-shadow:{SOMBRA}; }}
.kpi::before {{ content:""; position:absolute; left:0; top:16px; bottom:16px; width:3px; border-radius:0 3px 3px 0;
    background:var(--ac, {ROJO}); }}
.kpi .l {{ font-size:.74rem; font-weight:600; color:{TEXTO_2}; text-transform:uppercase; letter-spacing:.04em; }}
.kpi .v {{ font-size:1.85rem; font-weight:800; letter-spacing:-.6px; line-height:1.15; margin-top:6px; color:{TEXTO}; }}
.kpi .s {{ font-size:.78rem; color:{TEXTO_3}; margin-top:4px; }}

/* ---------- Secciones y notas ---------- */
.seccion {{ margin: 30px 0 12px 0; font-size:1.05rem; font-weight:700; letter-spacing:-.2px; color:{TEXTO}; }}
.seccion small {{ display:block; font-weight:400; color:{TEXTO_3}; font-size:.84rem; letter-spacing:0; margin-top:3px; }}
.nota {{ background:{SUPERFICIE}; border:1px solid {LINEA}; border-left:3px solid {TEXTO_3}; padding:12px 16px;
    border-radius:10px; font-size:.88rem; color:{TEXTO_2}; box-shadow:{SOMBRA}; }}
.nota b {{ color:{TEXTO}; }}
.nota.ok {{ border-left-color:{C_OK}; }}
.nota.warn {{ border-left-color:{C_BAJO}; }}
.nota.err {{ border-left-color:{ROJO}; }}

/* ---------- Barra de reparto ---------- */
.flujo {{ display:flex; gap:3px; border-radius:10px; overflow:hidden; margin:8px 0 4px 0; background:{SUPERFICIE};
    padding:4px; border:1px solid {LINEA}; box-shadow:{SOMBRA}; }}
.flujo div {{ padding:9px 12px; color:#fff; font-size:.78rem; font-weight:700; white-space:nowrap; overflow:hidden;
    text-overflow:ellipsis; border-radius:7px; }}
.leyenda {{ display:flex; gap:18px; flex-wrap:wrap; font-size:.8rem; color:{TEXTO_2}; margin-top:8px; }}
.leyenda span::before {{ content:""; display:inline-block; width:9px; height:9px; border-radius:50%; margin-right:6px; background:var(--c); }}

/* ---------- Barra lateral (menú de navegación) ---------- */
section[data-testid="stSidebar"] {{ background:{SUPERFICIE}; border-right:1px solid {LINEA}; }}
section[data-testid="stSidebar"] h2 {{ color:{TEXTO} !important; font-size:.78rem; font-weight:700; letter-spacing:.08em;
    text-transform:uppercase; }}
section[data-testid="stSidebar"] h4 {{ color:{TEXTO_3} !important; font-size:.72rem; font-weight:700; letter-spacing:.08em;
    text-transform:uppercase; }}
.st-key-menu_apps a, .st-key-menu_apps button {{ justify-content:flex-start !important; border:none !important;
    background:transparent !important; box-shadow:none !important; border-radius:8px !important; color:{TEXTO_2} !important;
    font-weight:600 !important; padding:8px 12px !important; }}
.st-key-menu_apps a > div, .st-key-menu_apps button > div, .st-key-menu_apps a span, .st-key-menu_apps button span,
.st-key-menu_apps [data-testid="stMarkdownContainer"], .st-key-menu_apps [data-testid="stTooltipHoverTarget"] {{
    justify-content:flex-start !important; width:100% !important; text-align:left !important; }}
.st-key-menu_apps p {{ text-align:left !important; }}
.st-key-menu_apps a:hover {{ background:{FONDO} !important; color:{TEXTO} !important; }}
.st-key-menu_apps a p, .st-key-menu_apps button p {{ color:inherit !important; }}
.st-key-menu_apps button:disabled {{ background:{ROJO_SUAVE} !important; color:{ROJO} !important; opacity:1 !important;
    box-shadow:inset 3px 0 0 {ROJO} !important; }}

/* ---------- Carga de archivos ---------- */
div[data-testid="stFileUploader"] section {{ background:{SUPERFICIE}; border:1.5px dashed {LINEA_2}; border-radius:12px;
    min-height:96px; align-items:center; box-shadow:{SOMBRA}; transition:border-color .15s; }}
div[data-testid="stFileUploader"] section:hover {{ border-color:{ROJO}; }}
div[data-testid="stFileUploader"] section button {{ background:{ROJO}; color:#fff; border:none; border-radius:8px;
    font-weight:600; box-shadow:0 2px 6px rgba(227,6,19,.25); }}
div[data-testid="stFileUploader"] section button:hover {{ background:{ROJO_OSC}; color:#fff; }}
div[data-testid="stFileUploader"] label p {{ white-space:nowrap; overflow:hidden; text-overflow:ellipsis; color:{TEXTO}; font-weight:600; }}
div[data-testid="stFileUploaderFile"] {{ background:{FONDO}; border-radius:8px; padding:4px 8px; }}

/* ---------- Botones ---------- */
button[data-testid="stBaseButton-primary"], div[data-testid="stDownloadButton"] button {{
    background:{ROJO}; color:#fff; border:none; border-radius:10px; font-weight:600; box-shadow:0 2px 8px rgba(227,6,19,.25); }}
button[data-testid="stBaseButton-primary"]:hover, div[data-testid="stDownloadButton"] button:hover {{ background:{ROJO_OSC}; color:#fff; border:none; }}
button[data-testid="stBaseButton-primary"] p, div[data-testid="stDownloadButton"] button p {{ color:#fff; }}
button[data-testid="stBaseButton-secondary"] {{ background:{SUPERFICIE}; border:1px solid {LINEA_2}; border-radius:10px;
    font-weight:600; color:{TEXTO}; }}
button[data-testid="stBaseButton-secondary"]:hover {{ border-color:{ROJO}; color:{ROJO}; }}

/* ---------- Pestañas ---------- */
div[data-baseweb="tab-list"] {{ gap:6px; border-bottom:1px solid {LINEA}; }}
button[data-baseweb="tab"] {{ font-weight:600; color:{TEXTO_2}; }}
button[data-baseweb="tab"][aria-selected="true"] {{ color:{TEXTO}; }}
div[data-baseweb="tab-highlight"] {{ background-color:{ROJO}; height:2px; }}
div[data-baseweb="tab-border"] {{ display:none; }}

/* ---------- Tarjetas (gráficos), tablas, desplegables ---------- */
div[data-testid="stVerticalBlockBorderWrapper"] {{ border-radius:14px; }}
div[data-testid="stVerticalBlockBorderWrapper"]:has(> div > div[data-testid="stVerticalBlock"]) {{ background:{SUPERFICIE}; }}
.stVerticalBlock.st-key-tarjeta, div[class*="st-key-tarjeta"] {{ background:{SUPERFICIE}; border:1px solid {LINEA};
    border-radius:14px; padding:18px 20px 10px 20px; box-shadow:{SOMBRA}; }}
div[data-testid="stDataFrame"] {{ border:1px solid {LINEA}; border-radius:12px; overflow:hidden; box-shadow:{SOMBRA};
    background:{SUPERFICIE}; }}
div[data-testid="stExpander"] {{ border:1px solid {LINEA}; border-radius:12px; background:{SUPERFICIE}; box-shadow:{SOMBRA}; }}
div[data-testid="stExpander"] details {{ border:none; }}
div[data-testid="stExpander"] summary p {{ font-weight:600; color:{TEXTO}; }}
hr {{ border-color:{LINEA}; }}

/* ---------- Selector de módulo (segmented control) ---------- */
div[data-testid="stButtonGroup"] {{ background:{SUPERFICIE}; border:1px solid {LINEA}; border-radius:12px; padding:4px;
    display:inline-flex; box-shadow:{SOMBRA}; }}
div[data-testid="stButtonGroup"] button {{ border:none !important; border-radius:9px !important; font-weight:600;
    padding:7px 18px; background:transparent; color:{TEXTO_2}; }}
div[data-testid="stButtonGroup"] button[kind="segmented_controlActive"] {{ background:{ROJO_SUAVE} !important;
    color:{ROJO} !important; box-shadow:inset 0 0 0 1px {ROJO}; }}
div[data-testid="stButtonGroup"] button[kind="segmented_controlActive"] p {{ color:{ROJO} !important; }}

/* ---------- Campos ---------- */
div[data-baseweb="input"], div[data-baseweb="select"] > div {{ border-radius:8px !important; }}
</style>
"""


_n_graf = [0]          # contador de tarjetas de gráfico (claves únicas por ejecución)


def encabezado(titulo: str, subtitulo: str, pasos: list[tuple[str, bool]], eyebrow: str = "") -> None:
    """Banner blanco con acento rojo y rastreador de pasos horizontal.
    pasos: (etiqueta, completado). El primer paso no completado se marca como actual."""
    actual = next((i for i, (_, ok) in enumerate(pasos) if not ok), None)
    nodos = ""
    for i, (lbl, ok) in enumerate(pasos):
        clase = "done" if ok else ("actual" if i == actual else "")
        marca = "✓" if ok else str(i + 1)
        nodos += f'<div class="step {clase}"><div class="dot">{marca}</div><div class="lbl">{lbl}</div></div>'
    ey = f'<div class="eyebrow">{eyebrow}</div>' if eyebrow else ""
    st.markdown(f'''<div class="hero"><div>{ey}<h1>{titulo}</h1><p>{subtitulo}</p></div>
<div class="stepper">{nodos}</div></div>''', unsafe_allow_html=True)


def aplicar_estilo():
    _n_graf[0] = 0
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
    _n_graf[0] += 1
    with st.container(key=f"tarjeta_{_n_graf[0]}"):
        st.markdown(f"<div style='font-weight:700;color:{TEXTO};font-size:.95rem'>{titulo}</div>"
                    + (f"<div style='color:{TEXTO_3};font-size:.8rem;margin:2px 0 6px 0'>{sub}</div>" if sub else ""),
                    unsafe_allow_html=True)
        # fit-x: el ancho se ajusta al contenedor; el alto se respeta (la leyenda no aplasta las barras)
        chart = chart.properties(autosize=alt.AutoSizeParams(type="fit-x", contains="padding"), background=SUPERFICIE)
        chart = chart.configure_view(stroke=None).configure_axis(gridColor=LINEA, domainColor=LINEA_2, labelColor=TEXTO_2,
                                                                  tickColor=LINEA_2, titleColor=TEXTO_2)
        chart = chart.configure(font="Inter").configure_legend(labelColor=TEXTO_2, titleColor=TEXTO_2)
        st.altair_chart(chart, width="stretch", theme=None)   # sin tema de Streamlit: fondo blanco de la tarjeta


