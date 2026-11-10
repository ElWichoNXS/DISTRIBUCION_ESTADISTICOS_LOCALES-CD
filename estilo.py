"""Estilo visual de la app (mismo lenguaje que las apps Min/Max y Verificación de traspasos).

Dirección: herramienta de trabajo diaria para abastecimiento. Una sola pieza fuerte —la franja roja del
encabezado con los pasos— y todo lo demás sobrio: superficies blancas, líneas finas, números tabulares.
Tipografía: Archivo (grotesca de alto rendimiento; ancho semicondensado para títulos y cifras).
"""
import altair as alt
import streamlit as st

# ---- Marca
ROJO, ROJO_OSC = "#E30613", "#A30410"
# ---- Neutros
TINTA, GRAFITO, NIEBLA_TXT = "#1C2127", "#59626E", "#8C949F"
FONDO, SUPERFICIE, LINEA, LINEA_2, REJILLA = "#F3F4F6", "#FFFFFF", "#DEE2E7", "#C5CBD3", "#EEF0F3"
ROJO_SUAVE = "#FDECED"
# ---- Estados (los mismos colores en KPIs, gráficos y barras)
C_OK, C_ALT, C_BAJO, C_EXT, C_PEND = "#188C7C", "#3A6FD8", "#C7861A", "#D3343F", "#8C949F"
NEUTRO = GRAFITO
# compatibilidad con nombres anteriores
TEXTO, TEXTO_2, TEXTO_3 = TINTA, GRAFITO, NIEBLA_TXT
BORDE, TARJETA = LINEA, SUPERFICIE

FUENTE = "Archivo"
ICONO = {"": "info", "ok": "check_circle", "warn": "warning", "err": "error"}

CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@62..125,100..900&display=swap');
html, body, .stApp, h1, h2, h3, h4, h5, p, label, li, button, input, textarea, [data-testid="stMarkdownContainer"] {{
    font-family:'{FUENTE}', system-ui, -apple-system, 'Segoe UI', sans-serif; }}
.stApp {{ background:{FONDO}; color:{TINTA}; }}
.block-container {{ padding-top:1.4rem; padding-bottom:3rem; max-width:1440px; }}
header[data-testid="stHeader"] {{ background:transparent; }}
h1, h2, h3, h4, h5 {{ color:{TINTA}; font-stretch:87.5%; }}
.ms {{ font-family:'Material Symbols Rounded'; font-weight:400; font-style:normal; font-size:1.15em; line-height:1;
    display:inline-block; vertical-align:-.2em; letter-spacing:normal; text-transform:none; white-space:nowrap;
    -webkit-font-feature-settings:'liga'; font-feature-settings:'liga'; }}

/* ================= Encabezado: franja roja + pasos ================= */
.hero {{ background:{ROJO}; border-radius:10px; padding:26px 32px 24px 32px; display:flex; justify-content:space-between;
    align-items:center; gap:32px; flex-wrap:wrap; position:relative; overflow:hidden; }}
.hero::after {{ content:""; position:absolute; left:0; right:0; bottom:0; height:4px; background:{ROJO_OSC}; }}
.hero h1 {{ color:#fff !important; margin:0; padding:0; font-size:2.05rem; font-weight:800; font-stretch:80%;
    letter-spacing:-.01em; line-height:1.05; }}
.hero p {{ color:rgba(255,255,255,.86) !important; margin:8px 0 0 0; font-size:.95rem; max-width:62ch; line-height:1.45; }}
.pasos {{ display:flex; align-items:flex-start; margin:0; padding:0; list-style:none; }}
.paso {{ display:flex; flex-direction:column; align-items:center; gap:8px; width:118px; position:relative; }}
.paso::before {{ content:""; position:absolute; top:15px; right:50%; width:100%; height:2px; background:rgba(255,255,255,.32); }}
.paso:first-child::before {{ display:none; }}
.paso .nodo {{ width:32px; height:32px; border-radius:50%; display:flex; align-items:center; justify-content:center; z-index:1;
    font-size:.9rem; font-weight:700; font-variant-numeric:tabular-nums; color:rgba(255,255,255,.8);
    background:{ROJO}; border:2px solid rgba(255,255,255,.45); }}
.paso .txt {{ font-size:.78rem; font-weight:600; color:rgba(255,255,255,.75); text-align:center; line-height:1.2; }}
.paso.hecho .nodo {{ background:#fff; border-color:#fff; color:{ROJO}; }}
.paso.hecho::before, .paso.actual::before {{ background:#fff; }}
.paso.actual .nodo {{ background:#fff; border-color:#fff; color:{ROJO}; box-shadow:0 0 0 5px rgba(255,255,255,.28); }}
.paso.hecho .txt, .paso.actual .txt {{ color:#fff; }}

/* ================= KPIs: una sola franja con divisiones ================= */
.kpis {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); background:{SUPERFICIE};
    border:1px solid {LINEA}; border-radius:10px; margin:10px 0 14px 0; overflow:hidden; }}
.kpi {{ padding:16px 20px 18px 20px; border-left:1px solid {LINEA}; margin-left:-1px; }}
.kpi .l {{ font-size:.82rem; font-weight:600; color:{GRAFITO}; display:flex; align-items:center; gap:7px; }}
.kpi .l::before {{ content:""; width:8px; height:8px; border-radius:2px; background:var(--ac, {ROJO}); flex:none; }}
.kpi .v {{ font-size:2.1rem; font-weight:700; font-stretch:80%; line-height:1.1; margin-top:6px; color:{TINTA};
    font-variant-numeric:tabular-nums; letter-spacing:-.01em; }}
.kpi .s {{ font-size:.78rem; color:{NIEBLA_TXT}; margin-top:2px; }}

/* ================= Secciones y avisos ================= */
.seccion {{ margin:28px 0 12px 0; font-size:1.2rem; font-weight:700; font-stretch:87.5%; color:{TINTA}; line-height:1.2; }}
.seccion small {{ display:block; font-weight:400; font-stretch:100%; color:{GRAFITO}; font-size:.85rem; margin-top:4px; }}
.nota {{ background:{SUPERFICIE}; border:1px solid {LINEA}; border-left:3px solid {GRAFITO}; padding:11px 16px 11px 14px;
    border-radius:8px; font-size:.88rem; color:{GRAFITO}; display:flex; gap:10px; align-items:flex-start; line-height:1.45; }}
.nota .ms {{ color:{GRAFITO}; font-size:1.25rem; vertical-align:0; }}
.nota b {{ color:{TINTA}; }}
.nota.ok {{ border-left-color:{C_OK}; }} .nota.ok .ms {{ color:{C_OK}; }}
.nota.warn {{ border-left-color:{C_BAJO}; }} .nota.warn .ms {{ color:{C_BAJO}; }}
.nota.err {{ border-left-color:{ROJO}; }} .nota.err .ms {{ color:{ROJO}; }}

/* ================= Barra de reparto (módulo 2) ================= */
.flujo {{ display:flex; gap:2px; border-radius:8px; overflow:hidden; margin:6px 0 4px 0; }}
.flujo div {{ padding:10px 12px; color:#fff; font-size:.8rem; font-weight:700; white-space:nowrap; overflow:hidden;
    text-overflow:ellipsis; font-variant-numeric:tabular-nums; }}
.leyenda {{ display:flex; gap:20px; flex-wrap:wrap; font-size:.82rem; color:{GRAFITO}; margin-top:8px; }}
.leyenda b {{ color:{TINTA}; font-variant-numeric:tabular-nums; }}
.leyenda span::before {{ content:""; display:inline-block; width:8px; height:8px; border-radius:2px; margin-right:7px; background:var(--c); }}

/* ================= Barra lateral ================= */
section[data-testid="stSidebar"] {{ background:{SUPERFICIE}; border-right:1px solid {LINEA}; }}
section[data-testid="stSidebar"] h2 {{ color:{TINTA} !important; font-size:1.05rem; font-weight:700; padding-top:.4rem; }}
section[data-testid="stSidebar"] h4 {{ color:{NIEBLA_TXT} !important; font-size:.8rem; font-weight:600; margin-bottom:-6px; }}
section[data-testid="stSidebar"] hr {{ margin:14px 0 6px 0; }}
.st-key-menu_apps {{ gap:2px !important; }}
.st-key-menu_apps a, .st-key-menu_apps button {{ justify-content:flex-start !important; border:none !important;
    background:transparent !important; box-shadow:none !important; border-radius:6px !important; color:{GRAFITO} !important;
    font-weight:500 !important; padding:7px 10px !important; min-height:0 !important; }}
.st-key-menu_apps a > div, .st-key-menu_apps button > div, .st-key-menu_apps a > div > span, .st-key-menu_apps button > div > span,
.st-key-menu_apps [data-testid="stMarkdownContainer"], .st-key-menu_apps [data-testid="stTooltipHoverTarget"] {{
    justify-content:flex-start !important; width:100% !important; text-align:left !important; }}
.st-key-menu_apps p {{ text-align:left !important; display:flex; align-items:center; gap:10px; }}
.st-key-menu_apps p span[role="img"] {{ font-size:1.15rem; vertical-align:middle !important; }}
.st-key-menu_apps a:hover {{ background:{FONDO} !important; color:{TINTA} !important; }}
.st-key-menu_apps a p, .st-key-menu_apps button p {{ color:inherit !important; }}
.st-key-menu_apps button:disabled {{ background:{ROJO_SUAVE} !important; color:{ROJO_OSC} !important; opacity:1 !important;
    font-weight:600 !important; box-shadow:inset 3px 0 0 {ROJO} !important; border-radius:0 6px 6px 0 !important; }}
section[data-testid="stSidebar"] div[data-testid="stExpander"] {{ box-shadow:none; }}

/* ================= Carga de archivos ================= */
div[data-testid="stFileUploader"] label p {{ white-space:nowrap; overflow:hidden; text-overflow:ellipsis; color:{TINTA};
    font-weight:600; font-size:.92rem; }}
div[data-testid="stFileUploader"] section {{ background:{SUPERFICIE}; border:1.5px dashed {LINEA_2}; border-radius:8px;
    min-height:92px; align-items:center; transition:border-color .15s, background .15s; }}
div[data-testid="stFileUploader"] section:hover {{ border-color:{ROJO}; background:#FFFBFB; }}
div[data-testid="stFileUploader"] section button {{ background:{ROJO}; color:#fff; border:none; border-radius:6px; font-weight:600; }}
div[data-testid="stFileUploader"] section button:hover {{ background:{ROJO_OSC}; color:#fff; }}
div[data-testid="stFileUploader"] section button p, div[data-testid="stFileUploader"] section button span {{ color:#fff; }}
div[data-testid="stFileUploaderFile"] {{ background:{FONDO}; border-radius:6px; padding:4px 8px; }}

/* ================= Botones ================= */
button[data-testid="stBaseButton-primary"], div[data-testid="stDownloadButton"] button {{
    background:{ROJO}; color:#fff; border:none; border-radius:8px; font-weight:600; min-height:44px; }}
button[data-testid="stBaseButton-primary"]:hover, div[data-testid="stDownloadButton"] button:hover {{
    background:{ROJO_OSC}; color:#fff; border:none; }}
button[data-testid="stBaseButton-primary"] p, div[data-testid="stDownloadButton"] button p,
div[data-testid="stDownloadButton"] button span {{ color:#fff; }}
button[data-testid="stBaseButton-secondary"] {{ background:{SUPERFICIE}; border:1px solid {LINEA_2}; border-radius:8px;
    font-weight:600; color:{TINTA}; }}
button[data-testid="stBaseButton-secondary"]:hover {{ border-color:{ROJO}; color:{ROJO}; }}
.st-key-plantilla button {{ background:{SUPERFICIE} !important; color:{TINTA} !important; border:1px solid {LINEA_2} !important;
    min-height:40px !important; }}
.st-key-plantilla button p, .st-key-plantilla button span {{ color:inherit !important; }}
.st-key-plantilla button:hover {{ border-color:{ROJO} !important; color:{ROJO} !important; background:{SUPERFICIE} !important; }}
button:focus-visible, a:focus-visible {{ outline:2px solid {ROJO} !important; outline-offset:2px; }}

/* ================= Selector de módulo ================= */
div[data-testid="stButtonGroup"] [role="radiogroup"] {{ background:#E7E9ED; border-radius:9px; padding:3px; display:inline-flex; gap:2px; }}
div[data-testid="stButtonGroup"] button {{ border:none !important; border-radius:7px !important; font-weight:600;
    padding:7px 18px; background:transparent; color:{GRAFITO}; min-height:38px; }}
div[data-testid="stButtonGroup"] button:hover {{ color:{TINTA}; background:rgba(255,255,255,.55); }}
div[data-testid="stButtonGroup"] button[aria-checked="true"] {{ background:{SUPERFICIE} !important;
    color:{TINTA} !important; box-shadow:0 1px 2px rgba(28,33,39,.12), 0 1px 1px rgba(28,33,39,.06); }}
div[data-testid="stButtonGroup"] button[aria-checked="true"] p {{ color:{TINTA} !important; }}
div[data-testid="stButtonGroup"] button[aria-checked="true"] [data-testid="stIconMaterial"] {{ color:{ROJO}; }}
div[data-testid="stButtonGroup"] [data-testid="stIconMaterial"] {{ font-size:1.15rem; }}

/* ================= Pestañas ================= */
div[data-baseweb="tab-list"] {{ gap:22px; border-bottom:1px solid {LINEA}; margin-top:14px; }}
button[data-baseweb="tab"] {{ padding:0 2px 10px 2px; }}
button[data-baseweb="tab"] p {{ font-weight:600; color:{GRAFITO}; font-size:.92rem; }}
button[data-baseweb="tab"][aria-selected="true"] p {{ color:{TINTA} !important; }}
div[data-baseweb="tab-highlight"] {{ background-color:{ROJO}; height:2px; }}
div[data-baseweb="tab-border"] {{ display:none; }}

/* ================= Paneles de gráficos, tablas, desplegables ================= */
div[class*="st-key-tarjeta"] {{ background:{SUPERFICIE}; border:1px solid {LINEA}; border-radius:10px; padding:18px 20px 12px 20px; }}
.tit-graf {{ font-weight:700; color:{TINTA}; font-size:1rem; font-stretch:87.5%; }}
.sub-graf {{ color:{GRAFITO}; font-size:.82rem; margin:3px 0 8px 0; }}
div[data-testid="stDataFrame"] {{ border:1px solid {LINEA}; border-radius:8px; overflow:hidden; background:{SUPERFICIE}; }}
div[data-testid="stExpander"] details {{ border:1px solid {LINEA}; border-radius:8px; background:{SUPERFICIE}; }}
div[data-testid="stExpander"] summary p {{ font-weight:600; color:{TINTA}; }}
div[data-testid="stExpander"] summary [data-testid="stIconMaterial"] {{ color:{GRAFITO}; }}
div[data-baseweb="input"], div[data-baseweb="select"] > div {{ border-radius:6px !important; }}
[data-testid="stCaptionContainer"] {{ color:{GRAFITO}; }}
hr {{ border-color:{LINEA}; }}

@media (max-width: 760px) {{
  .hero {{ padding:20px; }} .hero h1 {{ font-size:1.6rem; }}
  .paso {{ width:96px; }}
}}
@media (prefers-reduced-motion: reduce) {{ * {{ transition:none !important; }} }}
</style>
"""

_n_graf = [0]          # contador de paneles de gráfico (claves únicas por ejecución)


def ico(nombre: str) -> str:
    """Ícono Material (para HTML propio)."""
    return f'<span class="ms" aria-hidden="true">{nombre}</span>'


def encabezado(titulo: str, subtitulo: str, pasos: list[tuple[str, bool]], eyebrow: str = "") -> None:
    """Franja roja con el título y los pasos conectados. pasos: (etiqueta, completado).
    El primer paso sin completar se marca como actual. (`eyebrow` se mantiene por compatibilidad.)"""
    actual = next((i for i, (_, ok) in enumerate(pasos) if not ok), None)
    nodos = ""
    for i, (lbl, ok) in enumerate(pasos):
        clase = "hecho" if ok else ("actual" if i == actual else "")
        marca = ico("check") if ok else str(i + 1)
        nodos += f'<li class="paso {clase}"><div class="nodo">{marca}</div><div class="txt">{lbl}</div></li>'
    st.markdown(f'<div class="hero"><div><h1>{titulo}</h1><p>{subtitulo}</p></div>'
                f'<ol class="pasos" aria-label="Pasos">{nodos}</ol></div>', unsafe_allow_html=True)


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


def nota_html(texto, tipo=""):
    return f'<div class="nota {tipo}">{ico(ICONO.get(tipo, "info"))}<div>{texto}</div></div>'


def nota(texto, tipo=""):
    st.markdown(nota_html(texto, tipo), unsafe_allow_html=True)


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
        st.markdown(f'<div class="tit-graf">{titulo}</div>' + (f'<div class="sub-graf">{sub}</div>' if sub else
                    '<div style="height:8px"></div>'), unsafe_allow_html=True)
        # fit-x: el ancho se ajusta al panel; el alto se respeta (la leyenda no aplasta las barras)
        chart = chart.properties(autosize=alt.AutoSizeParams(type="fit-x", contains="padding"), background=SUPERFICIE)
        chart = (chart.configure_view(stroke=None)
                 .configure_axis(gridColor=REJILLA, domain=False, tickColor=LINEA, labelColor=GRAFITO, titleColor=GRAFITO,
                                 labelFontSize=11, titleFontSize=11, titleFontWeight=600, labelPadding=6)
                 .configure_axisY(ticks=False, grid=False)
                 .configure(font=FUENTE)
                 .configure_text(font=FUENTE)
                 .configure_legend(labelColor=GRAFITO, titleColor=GRAFITO, labelFontSize=11, symbolType="square"))
        st.altair_chart(chart, width="stretch", theme=None)   # sin tema de Streamlit: fondo del panel
