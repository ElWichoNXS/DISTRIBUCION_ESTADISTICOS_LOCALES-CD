"""
app.py  -  Distribución por días de inventario (Streamlit)
Módulo 1: Distribución CD a Locales (Próximos a Vencer)
Módulo 2: Redistribución entre locales (supervisor → gerente → manual)
Ejecutar:  streamlit run app.py
"""
import io
from datetime import datetime

import altair as alt
import pandas as pd
import streamlit as st

import distribucion as d
from estilo import (C_ALT, C_BAJO, C_EXT, C_OK, C_PEND, ROJO, ROJO_OSC, alto_tabla, aplicar_estilo, grafico,
                    kpis, n, nota, pct, seccion)
from exportar import excel_cd, excel_locales
from plantillas import plantilla_cd, plantilla_locales
from portal import menu_apps

# Streamlit Cloud a veces vuelve a ejecutar app.py con una versión anterior del motor en memoria
# (después de actualizar el repositorio). Si las versiones no coinciden, se recargan los módulos.
VERSION_MOTOR = "2026-11-06.4"
if getattr(d, "VERSION", None) != VERSION_MOTOR:
    import importlib

    import exportar
    import plantillas
    for _m in (d, exportar, plantillas):
        importlib.reload(_m)
    from exportar import excel_cd, excel_locales  # noqa: F811
    from plantillas import plantilla_cd, plantilla_locales  # noqa: F811

F_MES = "Consumo del mes anterior (archivo)"
F_PRON = "Pronóstico diario del BI"
F_ACU = "CONSUMOS ACU"
st.set_page_config(page_title="Distribución por días de inventario", page_icon="🚚", layout="wide")
menu_apps("Distribución próximos a vencer")
aplicar_estilo()

M1 = "📦 Distribución CD a Locales (Próximos a Vencer)"
M2 = "🔁 Redistribución entre locales"
ESC_NIVEL = alt.Scale(domain=[d.NIVEL_SUP, d.NIVEL_GER, d.NIVEL_MAN], range=[C_OK, C_ALT, C_EXT])


# ----------------------------------------------------------------------
# Lectura en caché
# ----------------------------------------------------------------------
class _Archivo(io.BytesIO):
    def __init__(self, data: bytes, name: str):
        super().__init__(data)
        self.name = name


@st.cache_data(show_spinner=False)
def hojas_de(data: bytes, nombre: str):
    if nombre.lower().endswith((".csv", ".txt")):
        return []
    return pd.ExcelFile(io.BytesIO(data), engine="pyxlsb" if nombre.lower().endswith(".xlsb") else None).sheet_names


@st.cache_data(show_spinner="Leyendo archivo…")
def leer(funcion: str, data: bytes, nombre: str, hoja):
    return getattr(d, funcion)(_Archivo(data, nombre), hoja)


def subir(etiqueta, key, funcion, ayuda, preferidas=()):
    f = st.file_uploader(etiqueta, type=["xlsx", "xlsm", "xls", "xlsb", "csv"], key=key, help=ayuda)
    if not f:
        return None
    data = f.getvalue()
    hojas = hojas_de(data, f.name)
    hoja = None
    if "PLANTILLA" in hojas:          # archivo hecho con la plantilla: se lee directo esa hoja
        hoja = "PLANTILLA"
    elif len(hojas) > 1:
        idx = next((i for i, h in enumerate(hojas) if any(p in d.normalizar(h) for p in preferidas)), 0)
        hoja = st.selectbox("Hoja", hojas, index=idx, key=f"{key}_hoja")
    try:
        return leer(funcion, data, f.name, hoja)
    except Exception as e:
        st.error(str(e))
        return None


# ----------------------------------------------------------------------
# Barra lateral: parámetros
# ----------------------------------------------------------------------
with st.sidebar:
    st.header("Parámetros")
    dias_max = st.number_input("Días máximos de inventario en el local", min_value=1.0, max_value=180.0, value=15.0,
                               step=1.0, help="Ningún local queda con más de estos días de inventario después del traspaso.")
    with st.expander("Venta diaria y stock", expanded=False):
        fuente = st.radio("Venta diaria", [F_MES, F_PRON, F_ACU], index=0,
                          help="Mes anterior: consumo acumulado del archivo de consumo ÷ días de ese mes (ej. octubre ÷ 31). "
                               "Pronóstico: promedio de las columnas de fecha del BI. "
                               "CONSUMOS ACU: CONSUMOS ACU ÷ los días de abajo. "
                               "Si un estadístico no tiene dato en la fuente elegida, se usa el pronóstico (y si falta, CONSUMOS ACU).")
        dias_acu = st.number_input("CONSUMOS ACU representa (días)", min_value=1.0, value=3.0, step=1.0,
                                   help="Venta diaria = CONSUMOS ACU ÷ este número. Con 3 coincide con DIAS STOCK SUC del BI.")
        st.caption("Stock del local = INV NETO + ROQ LTC + ROQ PTL (INV NETO ya incluye el tránsito).")
    with st.expander("Reglas de envío", expanded=True):
        empaque = st.checkbox("Redondear a múltiplos de EMPAQUE", value=False,
                              help="Usa la columna EMPAQUE de la base: cada local recibe empaques completos; puede quedar sobrante.")
        filtrar_bodega = st.checkbox("Módulo 1: solo locales de la bodega de salida", value=True,
                                     help="Usa la columna BODEGA de la base para cruzar con la bodega del inventario a mover.")
    with st.expander("📘 Cómo decide el programa"):
        st.markdown(
            "- **Venta diaria** del local según el parámetro elegido (mes anterior: consumo del mes ÷ días del mes).\n"
            "- **Stock actual** = INV NETO + ROQ LTC + ROQ PTL (INV NETO ya incluye el tránsito).\n"
            "- **Capacidad** = días máx × venta diaria − stock actual.\n"
            "- **Nivelación:** se entrega de a una unidad (o empaque) al local con **menos días de inventario**, "
            "hasta repartir todo o hasta que todos lleguen a los días máximos.\n"
            "- Un local **sin venta** no recibe.\n"
            "- **Módulo 2:** primero locales del **mismo supervisor**, luego del **mismo gerente**; lo que no cabe queda "
            "**pendiente manual** con sugerencias de otros gerentes.")
params = d.Parametros(dias_max=dias_max, fuente_venta={F_MES: "mensual", F_PRON: "pronostico", F_ACU: "consumo"}[fuente],
                      dias_consumo_acu=dias_acu,
                      redondear_empaque=empaque, filtrar_bodega=filtrar_bodega)

# ----------------------------------------------------------------------
# Encabezado + selector de módulo
# ----------------------------------------------------------------------
modulo = st.session_state.get("modulo", M1) or M1
hay_base = st.session_state.get("base") is not None
hay_mov = (st.session_state.get(f"mov_{modulo == M1 and 1 or 2}") is not None
           or bool(st.session_state.get(f"_manual_{modulo == M1 and 1 or 2}")))
paso = lambda ok: "paso ok" if ok else "paso"
sub = ("Reparte el inventario de una bodega entre los locales habilitados según los días máximos de inventario."
       if modulo == M1 else
       "Mueve inventario entre locales: primero mismo supervisor, luego mismo gerente; lo demás queda para asignación manual.")
st.markdown(f"""
<div class="hero">
  <div>
    <h1>Distribución por Días de Inventario</h1>
    <p>{sub}</p>
  </div>
  <div class="pasos">
    <div class="{paso(hay_base)}"><b>1</b>Base de locales</div>
    <div class="{paso(hay_mov)}"><b>2</b>Inventario a mover</div>
    <div class="{paso(hay_base and hay_mov)}"><b>3</b>Revisar y descargar</div>
  </div>
</div>
""", unsafe_allow_html=True)
st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
modulo = st.segmented_control("Módulo", [M1, M2], default=M1, key="modulo", label_visibility="collapsed") or M1
es_m1 = modulo == M1

# ----------------------------------------------------------------------
# Carga
# ----------------------------------------------------------------------
seccion("Carga de archivos", "La base del BI trae los locales donde el producto está activo (local, supervisor, gerente, stock y venta)")
c1, c2 = st.columns(2)
with c1:
    base = subir("1) Base de locales habilitados (BI)", "base", "leer_base",
                 "Una fila por local + estadístico: '# Local', 'ESTADISTICO', 'SUPERV.', 'GERENTE', 'INV NETO', "
                 "'ROQ_LTC', 'ROQ_PTL', 'CONSUMOS ACU' y las columnas de pronóstico por fecha.", ["BASE", "INVENTARIO"])
    if base is not None:
        st.caption(f"✅ {n(len(base))} registros · {base['local'].nunique()} locales · "
                   f"{base['estadistico'].nunique()} estadísticos · {base['gerente'].replace('', pd.NA).nunique()} gerentes")
with c2:
    clave_mod = "1" if es_m1 else "2"
    if es_m1:
        mov = subir("2) Inventario a mover desde el CD", "mov_1", "leer_mover_cd",
                    "Usa la plantilla (Estadístico, Bodega de salida, Cantidad) o el archivo INV A MOVER "
                    "('# ESTADIST', 'BODEGA', 'FISICO_WH').", ["PLANTILLA", "MOVER", "INV"])
    else:
        mov = subir("2) Inventario a mover entre locales", "mov_2", "leer_mover_locales",
                    "Usa la plantilla (Estadístico, Local de salida, Cantidad, Supervisor, Gerente) o un archivo del BI "
                    "con '# Local', 'ESTADISTICO' e 'INV NETO'.", ["PLANTILLA", "MOVER", "INV"])
    estado = st.empty()
    st.markdown(f"""<style>.st-key-plantilla button {{ background:transparent !important; color:{ROJO} !important;
        border:1.5px solid {ROJO} !important; box-shadow:none !important; }}
        .st-key-plantilla button p {{ color:{ROJO} !important; }}</style>""", unsafe_allow_html=True)
    st.container(key="plantilla").download_button(
        "📄 Descargar plantilla para llenar",
        data=plantilla_cd() if es_m1 else plantilla_locales(),
        file_name="PLANTILLA_DISTRIBUCION_CD.xlsx" if es_m1 else "PLANTILLA_REDISTRIBUCION_LOCALES.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", width="stretch",
        type="secondary", key=f"plantilla_{clave_mod}",
        help=("Estadístico, Descripción (opcional), Bodega de salida y Cantidad." if es_m1 else
              "Estadístico, Descripción (opcional), Local de salida, Cantidad, Supervisor y Gerente (estos dos se completan solos si los dejas vacíos)."))

    # ---- ingreso manual
    clave = "1" if es_m1 else "2"
    maestro = None
    with st.expander("✏️ ¿Sin archivo? Digita o pega el inventario a mover",
                     expanded=bool(st.session_state.get(f"_manual_{clave}"))):
        if es_m1:
            st.caption("Copia desde Excel y pega en la primera celda (Ctrl+V). Si también subes un archivo, se usa el archivo.")
            if "m1_df" not in st.session_state:
                st.session_state["m1_df"] = pd.DataFrame({"Estadístico": [""] * 6, "Cantidad": pd.array([pd.NA] * 6, dtype="Int64"),
                                                          "Bodega de salida": [""] * 6})
            ed = st.data_editor(st.session_state["m1_df"], num_rows="dynamic", width="stretch", key="ed_m1", height=245,
                                column_config={"Cantidad": st.column_config.NumberColumn(min_value=0, step=1)})
            manual = ed.replace("", pd.NA).dropna(how="all")
            st.session_state["_manual_1"] = len(manual) > 0
            if mov is None and len(manual):
                try:
                    mov = d.normalizar_mover_cd(manual)
                except Exception as e:
                    st.error(str(e))
        else:
            maestro_f = st.file_uploader("Maestro de locales (opcional): '# Local', 'SUPERV.', 'GERENTE'",
                                         type=["xlsx", "xls", "csv"], key="maestro",
                                         help="Si no lo subes, se usa la base de locales del paso 1.")
            if maestro_f:
                try:
                    maestro = leer("leer_maestro", maestro_f.getvalue(), maestro_f.name, None)
                    st.caption(f"✅ Maestro: {len(maestro)} locales")
                except Exception as e:
                    st.error(str(e))
            if maestro is None and base is not None:
                maestro = d.maestro_locales(base)
            st.caption("Digita el **local de salida** y el supervisor y gerente se completan solos con el maestro o la base.")
            if "m2_df" not in st.session_state:
                st.session_state["m2_df"] = pd.DataFrame({"Estadístico": [""] * 6, "Cantidad": pd.array([pd.NA] * 6, dtype="Int64"),
                                                          "Local de salida": [""] * 6, "Supervisor": [""] * 6,
                                                          "Gerente": [""] * 6})
            st.session_state.setdefault("m2_v", 0)
            ed = st.data_editor(st.session_state["m2_df"], num_rows="dynamic", width="stretch",
                                key=f"ed_m2_{st.session_state['m2_v']}", height=245,
                                column_config={"Cantidad": st.column_config.NumberColumn(min_value=0, step=1),
                                               "Supervisor": st.column_config.TextColumn(help="Se completa solo con el local"),
                                               "Gerente": st.column_config.TextColumn(help="Se completa solo con el local")})
            manual = ed.replace("", pd.NA).dropna(how="all")
            st.session_state["_manual_2"] = len(manual) > 0
            if len(manual):
                try:
                    tmp = manual.fillna("").rename(columns={"Supervisor": "SUPERV.", "Gerente": "GERENTE"})
                    m_norm = d.normalizar_mover_locales(tmp, maestro)
                    faltan = (~m_norm["en_maestro"]).sum() if "en_maestro" in m_norm else 0
                    completos = ed.copy()
                    loc_cod = completos["Local de salida"].map(d.codigo)
                    if maestro is not None and len(maestro):
                        mm = maestro.set_index("local")
                        for col_ui, col_m in (("Supervisor", "supervisor"), ("Gerente", "gerente")):
                            vacio = completos[col_ui].fillna("").astype(str).str.strip() == ""
                            completos.loc[vacio, col_ui] = loc_cod[vacio].map(mm[col_m]).fillna("")
                    sg = ["Supervisor", "Gerente"]
                    cambia = (completos[sg].fillna("").astype(str).values != ed[sg].fillna("").astype(str).values).any()
                    if cambia:
                        if st.button("↻ Completar supervisor y gerente en la tabla", width="stretch"):
                            st.session_state["m2_df"] = completos
                            st.session_state["m2_v"] += 1
                            st.rerun()
                    if faltan:
                        st.warning(f"{faltan} local(es) de salida no están en el maestro/base: escribe su supervisor y gerente.")
                    if mov is None:
                        mov = m_norm
                except Exception as e:
                    st.error(str(e))
    if not es_m1 and mov is not None and maestro is not None and len(maestro):
        mov = d.completar_responsables(mov, maestro)
    if mov is not None and len(mov):
        estado.caption(f"✅ {len(mov)} registros · {n(mov['cantidad'].sum())} unidades a mover · "
                       f"{mov['estadistico'].nunique()} estadísticos")

# ---- consumo del mes anterior (export del BI, uno o varios archivos)
consumo = None
if params.fuente_venta == "mensual":
    seccion("3) Consumo del mes anterior",
            "Export del BI con 'Cod Sucursal', 'Mes' y 'Consumo Unid'. Puedes subir varios archivos (uno por estadístico).")
    f_cons = st.file_uploader("Archivos de consumo mensual", type=["xlsx", "xls", "csv"], key="consumo",
                              accept_multiple_files=True, label_visibility="collapsed")
    partes, errores = [], []
    for f in f_cons or []:
        try:
            partes.append(leer("leer_consumo_mensual", f.getvalue(), f.name, None))
        except Exception as e:
            errores.append(f"{f.name}: {e}")
    for e in errores:
        st.error(e)
    if partes:
        mensual = pd.concat(partes).drop_duplicates(["local", "estadistico", "mes"], keep="last")
        consumo = d.consumo_diario(mensual)
        per = consumo.drop_duplicates("estadistico")[["estadistico", "periodo"]]
        st.caption("✅ " + " · ".join(f"{r.estadistico}: {r.periodo}" for r in per.itertuples()) +
                   f" · {consumo['local'].nunique()} locales")
    else:
        nota("Sube el export de consumo del mes anterior. Mientras no lo subas, se usa el <b>pronóstico diario del BI</b>.", "warn")

if base is None or mov is None or not len(mov):
    nota("Sube la base de locales habilitados y el inventario a mover (o digítalo) para ver la distribución y descargar el Excel. "
         "Ajusta los <b>días máximos</b> en la barra lateral.")
    st.stop()


# ----------------------------------------------------------------------
# Cálculo
# ----------------------------------------------------------------------
@st.cache_data(show_spinner="Calculando distribución…", max_entries=6)
def calcular(es_m1, base, mov, p_tuple, consumo):
    p = d.Parametros(*p_tuple)
    if es_m1:
        res = d.distribuir_cd(base, mov, p, consumo)
        return res, excel_cd(res, p)
    res = d.redistribuir_locales(base, mov, p, consumo)
    return res, excel_locales(res, p)


p_tuple = (params.dias_max, params.fuente_venta, params.dias_consumo_acu,
           params.redondear_empaque, params.filtrar_bodega)
if consumo is not None:
    sin_consumo = sorted(set(mov["estadistico"]) - set(consumo["estadistico"]))
    if sin_consumo:
        st.warning(f"Sin archivo de consumo mensual para {len(sin_consumo)} estadístico(s): "
                   f"{', '.join(map(str, sin_consumo[:12]))}{'…' if len(sin_consumo) > 12 else ''}. Para esos se usa el pronóstico del BI.")
res, excel = calcular(es_m1, base, mov, p_tuple, consumo)
r = res.resumen
dist = res.distribucion

st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
a1, a2 = st.columns([3, 1.3])
falta = r["und_sobrante"] if es_m1 else r["pendiente"]
if falta > 0:
    a1.markdown(f'<div class="nota warn">Se asignan <b>{n(r["und_mover"] - falta)}</b> de <b>{n(r["und_mover"])}</b> unidades. '
                f'Quedan <b>{n(falta)}</b> {"en el CD (sobrante)" if es_m1 else "para asignación manual"}: '
                f'los locales {"habilitados" if es_m1 else "del mismo supervisor y gerente"} no pueden recibir más sin pasar '
                f'<b>{dias_max:g} días</b>.</div>', unsafe_allow_html=True)
else:
    a1.markdown(f'<div class="nota ok">✅ Se asigna todo el inventario sin que ningún local pase de {dias_max:g} días.</div>',
                unsafe_allow_html=True)
nombre = "DISTRIBUCION_CD_LOCALES" if es_m1 else "REDISTRIBUCION_LOCALES"
a2.download_button("⬇️ Descargar Excel de resultados", data=excel, file_name=f"{nombre}_{datetime.now():%Y%m%d_%H%M}.xlsx",
                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", width="stretch")

def filtrar(df, filtros):
    """filtros: lista de (columna, valores seleccionados); sin selección = todos."""
    m = pd.Series(True, index=df.index)
    for col, sel in filtros:
        if sel:
            m &= df[col].isin(sel)
    return df[m]


def tabla(df, **kw):
    if df is None or not len(df):
        st.info("Sin registros.")
        return
    cfg = {"Descripción": st.column_config.TextColumn(width="medium"),
           "% Asignado": st.column_config.ProgressColumn("% asignado", format="percent", min_value=0, max_value=1),
           "Observación": st.column_config.TextColumn(width="large"), "Motivo": st.column_config.TextColumn(width="large")}
    st.dataframe(df, hide_index=True, width="stretch", height=alto_tabla(len(df)), column_config=cfg, **kw)


def grafico_dias(dist, sub):
    """Días de inventario antes y después en los locales que reciben (top 25 por cantidad)."""
    if not len(dist):
        return
    dd = dist.groupby(["Local Destino", "Nombre Destino", "Estadístico", "Descripción"], as_index=False).agg(
        antes=("Días Actuales", "min"), despues=("Días Finales", "max"), cant=("Cantidad", "sum"))
    dd["antes"] = dd["antes"].fillna(0)
    dd = dd.sort_values("cant", ascending=False).head(25)
    dd["loc"] = (dd["Local Destino"].astype(str) + " · " + dd["Nombre Destino"].astype(str).str.slice(0, 16) + " · "
                 + dd["Descripción"].astype(str).str.slice(0, 22).str.title())
    orden = dd.sort_values("despues", ascending=False)["loc"].tolist()
    base_c = alt.Chart(dd).encode(y=alt.Y("loc:N", sort=orden, title=None, axis=alt.Axis(labelLimit=220)))
    regla = base_c.mark_rule(strokeWidth=3, color=C_ALT, opacity=.55).encode(x=alt.X("antes:Q", title="Días de inventario"), x2="despues:Q")
    p1 = base_c.mark_circle(size=90, color=C_PEND, opacity=1).encode(x="antes:Q",
          tooltip=[alt.Tooltip("loc:N", title="Local"), alt.Tooltip("antes:Q", title="Días antes", format=".1f")])
    p2 = base_c.mark_circle(size=110, color=C_OK, opacity=1).encode(x="despues:Q",
          tooltip=[alt.Tooltip("loc:N", title="Local"), alt.Tooltip("despues:Q", title="Días después", format=".1f"),
                   alt.Tooltip("cant:Q", title="Unidades recibidas")])
    lim = alt.Chart(pd.DataFrame({"x": [dias_max]})).mark_rule(color=ROJO, strokeDash=[6, 4], strokeWidth=2).encode(x="x:Q")
    grafico("Días de inventario: antes → después (local · estadístico)", sub, (regla + p1 + p2 + lim).properties(height=max(200, 22 * len(dd) + 50)))


def barras_apiladas(df, cat, cols, colores, titulo, sub, orden=None, alto_fila=30, leyenda=True):
    largo = df.melt(id_vars=[cat], value_vars=cols, var_name="serie", value_name="und")
    largo = largo[largo["und"] > 0]
    if not len(largo):
        return
    orden = orden or df.sort_values(cols[0], ascending=False)[cat].tolist()
    ch = alt.Chart(largo).mark_bar(cornerRadiusEnd=3).encode(
        y=alt.Y(f"{cat}:N", sort=orden, title=None, axis=alt.Axis(labelLimit=300)),
        x=alt.X("und:Q", title=None, axis=alt.Axis(format="~s")),
        color=alt.Color("serie:N", scale=alt.Scale(domain=cols, range=colores),
                        legend=alt.Legend(title=None, orient="bottom") if (leyenda and len(cols) > 1) else None),
        order=alt.Order("serie:N"),
        tooltip=[alt.Tooltip(f"{cat}:N", title=" "), alt.Tooltip("serie:N", title="Concepto"), alt.Tooltip("und:Q", title="Unidades", format=",")]
    ).properties(height=max(170, alto_fila * df[cat].nunique() + 60))
    grafico(titulo, sub, ch)


# ============================ MÓDULO 1 ============================
if es_m1:
    t_res, t_dist, t_sob, t_no = st.tabs([f"Resumen", f"Distribución a grabar ({len(dist)})",
                                           f"Sobrante ({len(res.pendientes)})", f"Locales no considerados ({len(res.no_considerados)})"])
    with t_res:
        kpis([
            ("Unidades a mover", n(r["und_mover"]), f"{r['items']} estadísticos", ROJO),
            ("Asignadas", n(r["und_asignadas"]), f"{pct(r['und_asignadas'], r['und_mover'])} del total", C_OK),
            ("Sobrante en CD", n(r["und_sobrante"]), f"{pct(r['und_sobrante'], r['und_mover'])} del total", C_PEND),
            ("Traspasos", n(r["traspasos"]), "líneas a grabar", C_ALT),
            ("Locales que reciben", n(r["locales"]), f"tope {dias_max:g} días", C_BAJO),
            ("Días finales (máx.)", n(dist["Días Finales"].max()) if len(dist) else "—", "en los locales que reciben", ROJO_OSC),
        ])
        pi = res.por_item.copy()
        pi["prod"] = pi["Estadístico"].astype(str) + " · " + pi["Descripción"].str.slice(0, 34).str.title()
        g1, g2 = st.columns([1.5, 1])
        with g1:
            barras_apiladas(pi.rename(columns={"Asignado": "Asignado", "Sobrante": "Sobrante"}), "prod", ["Asignado", "Sobrante"],
                            [C_OK, C_PEND], "Asignado vs. sobrante por estadístico",
                            "El sobrante es lo que los locales no pueden recibir sin pasar los días máximos.")
        with g2:
            if len(res.no_considerados):
                mc = res.no_considerados["Motivo"].value_counts().rename_axis("Motivo").reset_index(name="Locales")
                ch = alt.Chart(mc).mark_arc(innerRadius=55).encode(
                    theta="Locales:Q", color=alt.Color("Motivo:N", scale=alt.Scale(range=[C_PEND, C_BAJO, C_EXT, C_ALT, ROJO_OSC]),
                                                       legend=alt.Legend(title=None, orient="bottom", columns=1)),
                    tooltip=["Motivo:N", "Locales:Q"]).properties(height=230)
                grafico("¿Por qué no reciben algunos locales?", "Locales de la base que quedan fuera (por estadístico).", ch)
        if len(dist):
            h1, h2 = st.columns(2)
            with h1:
                gg = dist.groupby("Gerente Destino", as_index=False)["Cantidad"].sum().rename(columns={"Cantidad": "Unidades"})
                barras_apiladas(gg, "Gerente Destino", ["Unidades"], [ROJO], "Unidades por gerente",
                                "Cómo se reparte el inventario entre las gerencias.")
            with h2:
                ss = dist.groupby("Supervisor Destino", as_index=False)["Cantidad"].sum().rename(columns={"Cantidad": "Unidades"})
                ss = ss.sort_values("Unidades", ascending=False).head(15)
                barras_apiladas(ss, "Supervisor Destino", ["Unidades"], [C_ALT], "Top 15 supervisores que reciben", "")
            grafico_dias(dist, f"Top 25 locales por unidades recibidas. La línea roja es el tope de {dias_max:g} días.")
        st.markdown("##### Detalle por estadístico")
        tabla(res.por_item)
    with t_dist:
        nota("Lista para grabar: <b>origen (CD) → local destino · estadístico · cantidad</b>. Incluye días antes y después.")
        if len(dist):
            f1, f2 = st.columns(2)
            s_it = f1.multiselect("Estadístico", sorted(dist["Estadístico"].unique()), placeholder="Todos")
            s_ge = f2.multiselect("Gerente", sorted(dist["Gerente Destino"].unique()), placeholder="Todos")
            vista = filtrar(dist, [("Estadístico", s_it), ("Gerente Destino", s_ge)])
            tabla(vista)
            st.caption(f"{len(vista)} traspasos · {n(vista['Cantidad'].sum())} unidades")
        else:
            tabla(dist)
    with t_sob:
        if len(res.pendientes):
            nota(f"Estas unidades quedan en el CD: los locales habilitados no pueden recibir más sin pasar {dias_max:g} días. "
                 "Puedes subir los días máximos desde la barra lateral o agregar locales a la base.", "warn")
        tabla(res.pendientes)
    with t_no:
        tabla(res.no_considerados)

# ============================ MÓDULO 2 ============================
else:
    t_res, t_dist, t_pen, t_no = st.tabs([f"Resumen", f"Traspasos a grabar ({len(dist)})",
                                           f"Pendiente manual ({len(res.pendientes)})", f"Locales no considerados ({len(res.no_considerados)})"])
    with t_res:
        kpis([
            ("Unidades a mover", n(r["und_mover"]), f"{r['origenes']} registros origen", ROJO),
            ("Mismo supervisor", n(r["nivel_sup"]), f"{pct(r['nivel_sup'], r['und_mover'])} del total", C_OK),
            ("Mismo gerente", n(r["nivel_ger"]), f"{pct(r['nivel_ger'], r['und_mover'])} del total", C_ALT),
            ("Pendiente manual", n(r["pendiente"]), f"{pct(r['pendiente'], r['und_mover'])} del total", C_EXT),
            ("Traspasos", n(r["traspasos"]), "líneas a grabar", C_BAJO),
            ("Locales que reciben", n(r["locales"]), f"tope {dias_max:g} días", ROJO_OSC),
        ])
        tot = max(r["und_mover"], 1)
        partes = [(d.NIVEL_SUP, r["nivel_sup"], C_OK), (d.NIVEL_GER, r["nivel_ger"], C_ALT), (d.NIVEL_MAN, r["pendiente"], C_EXT)]
        barras = "".join(f'<div style="flex:{v};background:{c}" title="{p}: {n(v)}">{pct(v, tot)}</div>' for p, v, c in partes if v > 0)
        ley = "".join(f'<span style="--c:{c}">{p}: <b>{n(v)}</b></span>' for p, v, c in partes)
        seccion("¿Dónde se ubica el inventario?", "Reparto de las unidades según el nivel de prioridad")
        st.markdown(f'<div class="flujo">{barras}</div><div class="leyenda">{ley}</div>', unsafe_allow_html=True)

        pi = res.por_item.copy()
        pi = pi[pi["Cantidad a Mover"] > 0]
        pi["origen"] = pi["Local Origen"].astype(str) + " · " + pi["Descripción"].str.slice(0, 30).str.title()
        g1, g2 = st.columns([1.5, 1])
        with g1:
            barras_apiladas(pi, "origen", [d.NIVEL_SUP, d.NIVEL_GER, d.NIVEL_MAN], [C_OK, C_ALT, C_EXT],
                            "Cómo se ubicó cada local de salida", "Local de salida · estadístico. Colores como en la barra de arriba.",
                            orden=pi.sort_values(d.NIVEL_MAN, ascending=False)["origen"].tolist(), alto_fila=26, leyenda=False)
        with g2:
            gg = pi.groupby("Gerente Origen", as_index=False)[[d.NIVEL_SUP, d.NIVEL_GER, d.NIVEL_MAN]].sum()
            barras_apiladas(gg, "Gerente Origen", [d.NIVEL_SUP, d.NIVEL_GER, d.NIVEL_MAN], [C_OK, C_ALT, C_EXT],
                            "Por gerente del local de salida", "Colores como en la barra de arriba.", leyenda=False)
        if len(dist):
            mx = dist.groupby(["Local Origen", "Local Destino"], as_index=False)["Cantidad"].sum()
            mx["Origen"] = mx["Local Origen"].astype(str)
            mx["Destino"] = mx["Local Destino"].astype(str)
            bm = alt.Chart(mx).encode(x=alt.X("Destino:N", title="Local destino", axis=alt.Axis(labelAngle=-45)),
                                      y=alt.Y("Origen:N", title="Local de salida"))
            heat = bm.mark_rect(cornerRadius=4).encode(
                color=alt.Color("Cantidad:Q", scale=alt.Scale(scheme="reds"), legend=alt.Legend(title="Unidades")),
                tooltip=["Origen:N", "Destino:N", alt.Tooltip("Cantidad:Q", title="Unidades")])
            txt = bm.mark_text(fontSize=10, fontWeight="bold").encode(
                text="Cantidad:Q", color=alt.condition(alt.datum.Cantidad > mx["Cantidad"].max() * .5, alt.value("white"), alt.value("black")))
            grafico("Matriz de traspasos", "Unidades que envía cada local de salida (filas) a cada destino (columnas).",
                    (heat + txt).properties(height=max(160, 34 * mx["Origen"].nunique() + 70)))
            grafico_dias(dist, f"Top 25 locales destino por unidades. La línea roja es el tope de {dias_max:g} días.")
        st.markdown("##### Detalle por local de salida")
        tabla(res.por_item)
    with t_dist:
        nota("Lista para grabar: <b>local de salida → local destino · estadístico · cantidad</b>, con el nivel en que se asignó.")
        if len(dist):
            f1, f2, f3 = st.columns(3)
            s_n = f1.multiselect("Nivel", [d.NIVEL_SUP, d.NIVEL_GER], placeholder="Todos")
            s_o = f2.multiselect("Local de salida", sorted(dist["Local Origen"].unique()), placeholder="Todos")
            s_it = f3.multiselect("Estadístico", sorted(dist["Estadístico"].unique()), placeholder="Todos")
            vista = filtrar(dist, [("Nivel", s_n), ("Local Origen", s_o), ("Estadístico", s_it)])
            tabla(vista)
            st.caption(f"{len(vista)} traspasos · {n(vista['Cantidad'].sum())} unidades")
        else:
            tabla(dist)
    with t_pen:
        if len(res.pendientes):
            nota("Estas unidades no caben en locales del <b>mismo supervisor</b> ni del <b>mismo gerente</b>. "
                 "Asígnalas manualmente; la última columna sugiere locales de otros gerentes con capacidad.", "warn")
        else:
            nota("✅ No queda nada pendiente de asignación manual.", "ok")
        tabla(res.pendientes)
    with t_no:
        tabla(res.no_considerados)
