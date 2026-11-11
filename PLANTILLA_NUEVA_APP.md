# Plantilla para crear una app nueva de abastecimiento

Las apps de abastecimiento (Distribución de estadísticos, Min/Max por local y Verificación de traspasos)
comparten el mismo diseño. Para que una app nueva se vea igual, usa el prompt de abajo y el esqueleto de `app.py`.

**Archivos que se copian tal cual** desde este repositorio (son idénticos en todas las apps):

| Archivo | Para qué sirve |
|---|---|
| `estilo.py` | Todo el diseño: franja roja con pasos, tipografía Archivo, KPIs, pestañas, chips, avisos, gráficos |
| `portal.py` | Menú «Mis apps» de la barra lateral |
| `.streamlit/config.toml` | Tema claro fijo (cambia solo `maxUploadSize` si hace falta) |

---

## 1. Prompt para Claude

Copia y completa lo que está entre `< >`:

```text
Crea una app nueva de Streamlit en el repositorio <owner/repo> llamada "<Nombre de la app>".
Qué hace: <describe el proceso, qué archivos se cargan, qué se calcula y qué se descarga>.

Usa el mismo diseño que mis otras apps de abastecimiento. El modelo está en
https://github.com/ElWichoNXS/DISTRIBUCION_ESTADISTICOS_LOCALES-CD (rama main):
- Copia tal cual estilo.py, portal.py y .streamlit/config.toml. No escribas CSS propio en app.py.
- Sigue el esqueleto de PLANTILLA_NUEVA_APP.md: set_page_config con ícono Material, menu_apps(),
  aplicar_estilo(), encabezado() con 3 pasos, seccion("Carga de archivos"), file_uploader con
  chips() debajo al cargar, vacio() mientras falten archivos y st.stop(), luego una barra con
  nota_html() + botón de descarga del Excel, y st.tabs() con "Resumen" primero (kpis() + grafico()).
- Íconos de Streamlit (":material/...:"), sin emojis. Textos en español, números con n() (1.234).
- Números de días sin decimales (format="%g" en number_input).
- Agrega la app nueva a APPS en portal.py de este repositorio Y de los demás
  (DISTRIBUCION_ESTADISTICOS_LOCALES-CD, ElWichoNXS-ABASTO, VERIFICACION_DE_SOLICITUDES_AGOTADOS),
  dejando portal.py idéntico en todos. Si aún no tiene dirección, deja "" (se ve en gris).
- Separa la lógica (motor.py, sin Streamlit, con pruebas en tests/) de la interfaz (app.py).
- Pruébala con datos de ejemplo, muéstrame capturas en escritorio y móvil, y súbela a una rama.
```

Si después cambias el diseño en una app, pide: *"Copia estilo.py y portal.py de esta app a las demás
y sube estilo.VERSION en todas"*.

---

## 2. Esqueleto de `app.py`

```python
"""
app.py  -  <Nombre de la app> (Streamlit)
Ejecutar:  streamlit run app.py
"""
import io
from datetime import datetime

import altair as alt
import pandas as pd
import streamlit as st

import estilo
import motor            # la lógica de la app (sin Streamlit)
import portal

# Si estilo.py o portal.py cambian, Streamlit Cloud puede conservar la versión vieja en memoria:
# este número debe ser igual a estilo.VERSION; si no coincide, se recargan antes de importar sus nombres.
VERSION_ESTILO = "2026-11-11.3"
if getattr(estilo, "VERSION", None) != VERSION_ESTILO:
    import importlib
    for _m in (estilo, motor, portal):
        importlib.reload(_m)

from estilo import (C_ALT, C_BAJO, C_EXT, C_OK, C_PEND, ROJO, alto_tabla, aplicar_estilo, chips,  # noqa: E402
                    encabezado, grafico, kpis, n, nota, nota_html, pct, seccion, vacio)
from portal import menu_apps  # noqa: E402

st.set_page_config(page_title="<Nombre de la app>", page_icon=":material/<icono>:", layout="wide")
menu_apps("<Nombre de la app>")          # el mismo nombre que en APPS de portal.py
aplicar_estilo()

# ---------------- Barra lateral: parámetros ----------------
with st.sidebar:
    st.header("Parámetros")
    dias = st.number_input("Días máximos", min_value=1.0, value=15.0, step=1.0, format="%g",
                           help="Explica aquí qué hace el parámetro.")
    with st.expander("Cómo decide el programa", icon=":material/help:"):
        st.markdown("- Regla 1…\n- Regla 2…")

# ---------------- Encabezado ----------------
hay_a = st.session_state.get("archivo_a") is not None
hay_b = st.session_state.get("archivo_b") is not None
encabezado("<Nombre de la app>", "<Una frase que diga qué hace la app.>",
           [("Cargar archivo A", hay_a), ("Cargar archivo B", hay_b), ("Revisar y descargar", hay_a and hay_b)])

# ---------------- Carga ----------------
seccion("Carga de archivos", "<Qué debe traer cada archivo>")
c1, c2 = st.columns(2)
a = b = None
with c1:
    f_a = st.file_uploader("1) Archivo A", type=["xlsx", "xls", "xlsb", "csv"], key="archivo_a",
                           help="Columnas necesarias: …")
    if f_a:
        try:
            a = motor.leer_a(f_a)
            chips([f"<b>{n(len(a))}</b> registros", f"<b>{a['local'].nunique()}</b> locales"])
        except Exception as e:
            st.error(str(e))
with c2:
    f_b = st.file_uploader("2) Archivo B", type=["xlsx", "xls", "xlsb", "csv"], key="archivo_b")
    if f_b:
        try:
            b = motor.leer_b(f_b)
            chips([f"<b>{n(len(b))}</b> registros"])
        except Exception as e:
            st.error(str(e))

if a is None or b is None:
    vacio("Carga los archivos para ver el resultado",
          "Sube el archivo A y el archivo B. Los gráficos y el Excel de resultados aparecen aquí.",
          [("Archivo A", a is not None), ("Archivo B", b is not None)])
    st.stop()

# ---------------- Cálculo ----------------
res = motor.calcular(a, b, dias)

d1, d2 = st.columns([3, 1.3], vertical_alignment="center")
d1.markdown(nota_html("Se procesó todo sin problemas.", "ok"), unsafe_allow_html=True)   # tipos: "", "ok", "warn", "err"
d2.download_button("Descargar Excel de resultados", icon=":material/download:", data=res.excel,
                   file_name=f"RESULTADO_{datetime.now():%Y%m%d_%H%M}.xlsx",
                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", width="stretch")

t_res, t_det = st.tabs(["Resumen", f"Detalle ({len(res.detalle)})"])
with t_res:
    kpis([("Unidades", n(res.total), "a mover", ROJO),
          ("Asignadas", n(res.asignadas), f"{pct(res.asignadas, res.total)} del total", C_OK),
          ("Pendientes", n(res.pendientes), "para revisar", C_BAJO)])
    ch = alt.Chart(res.por_local).mark_bar(cornerRadiusEnd=3).encode(
        y=alt.Y("Local:N", sort="-x", title=None), x=alt.X("Unidades:Q", title=None), color=alt.value(C_ALT))
    grafico("Unidades por local", "Subtítulo corto que explica el gráfico.", ch)
with t_det:
    st.dataframe(res.detalle, hide_index=True, width="stretch", height=alto_tabla(len(res.detalle)))
```

### Piezas de `estilo.py`

| Función | Uso |
|---|---|
| `encabezado(titulo, subtitulo, pasos)` | Franja roja con los pasos `[(etiqueta, completado), …]` |
| `seccion(titulo, sub)` | Título de sección con subtítulo |
| `chips([...])` | Etiquetas bajo un archivo cargado; la primera va en verde con ✓ |
| `vacio(titulo, texto, pasos)` | Tarjeta mientras faltan archivos |
| `kpis([(etiqueta, valor, sub, color), …])` | Tarjetas de indicadores |
| `nota(texto, tipo)` / `nota_html(...)` | Avisos con ícono (`""`, `"ok"`, `"warn"`, `"err"`) |
| `grafico(titulo, sub, chart)` | Panel blanco con un gráfico de Altair |
| `n(x)`, `pct(a, b)`, `alto_tabla(filas)` | Formato 1.234, porcentaje y alto justo de tablas |
| Colores | `ROJO`, `C_OK` (verde), `C_ALT` (azul), `C_BAJO` (ámbar), `C_EXT` (rojo), `C_PEND` (gris) |
