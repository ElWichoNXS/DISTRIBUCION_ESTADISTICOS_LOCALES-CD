"""Excel de resultados (con gráficos nativos en la hoja RESUMEN)."""
from __future__ import annotations

import io
from datetime import datetime

import pandas as pd
from openpyxl import Workbook
from openpyxl.chart import BarChart, Reference
from openpyxl.chart.label import DataLabelList
from openpyxl.formatting.rule import CellIsRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from distribucion import NIVEL_GER, NIVEL_MAN, NIVEL_SUP, Parametros, Resultado

ROJO, ROJO_OSC = "E30613", "A30410"
C_OK, C_ALT, C_BAJO, C_PEND = "1FA391", "4B86E6", "D39A2E", "8C8C8C"
thin = Side(style="thin", color="BFBFBF")
BORDE = Border(left=thin, right=thin, top=thin, bottom=thin)
F_ROJO = PatternFill("solid", fgColor="F8CBAD")
ANCHOS = {"Descripción": 40, "Observación": 52, "Motivo": 52, "Sugerencia (otros gerentes · capacidad)": 60,
          "Nombre Destino": 20, "Nombre Origen": 20, "Nombre": 20, "Supervisor Destino": 18, "Gerente Destino": 18,
          "Supervisor Origen": 18, "Gerente Origen": 18, "Supervisor": 18, "Gerente": 18, "Nivel": 20}
PCT = {"% Asignado"}
TEXTO_IZQ = {"Descripción", "Observación", "Motivo", "Sugerencia (otros gerentes · capacidad)", "Nombre Destino",
             "Nombre Origen", "Nombre"}


def _escribir_tabla(ws, df: pd.DataFrame, fila: int, col: int = 1, color: str = ROJO_OSC):
    for j, c in enumerate(df.columns, col):
        x = ws.cell(fila, j, c)
        x.fill = PatternFill("solid", fgColor=color)
        x.font = Font(bold=True, color="FFFFFF", size=10)
        x.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        x.border = BORDE
        letra = get_column_letter(j)
        ws.column_dimensions[letra].width = max(ws.column_dimensions[letra].width or 0,
                                                ANCHOS.get(c, max(11, min(18, len(str(c)) + 2))))
    ws.row_dimensions[fila].height = 36
    for i, r in enumerate(df.itertuples(index=False), fila + 1):
        for j, v in enumerate(r, col):
            if isinstance(v, float):
                v = None if pd.isna(v) else (int(v) if v.is_integer() and df.columns[j - col] not in PCT else v)
            x = ws.cell(i, j, v)
            x.border = BORDE
            nombre = df.columns[j - col]
            if nombre in PCT:
                x.number_format = "0%"
            if nombre not in TEXTO_IZQ:
                x.alignment = Alignment(horizontal="center")
    return fila + len(df)


def _hoja(wb, nombre, df, titulo, nota, color=ROJO_OSC):
    ws = wb.create_sheet(nombre)
    ws["A1"] = titulo
    ws["A1"].font = Font(bold=True, size=14, color=ROJO)
    ws["A2"] = nota
    ws["A2"].font = Font(italic=True, size=9, color="595959")
    if len(df):
        ultima = _escribir_tabla(ws, df, 4, color=color)
        ws.auto_filter.ref = f"A4:{get_column_letter(len(df.columns))}{ultima}"
    else:
        ws["A4"] = "Sin registros."
    ws.freeze_panes = "A5"
    return ws


def _encabezado_resumen(ws, titulo, p: Parametros, kpis: list[tuple]):
    ws["A1"] = titulo
    ws["A1"].font = Font(bold=True, size=15, color=ROJO)
    ws["A2"] = (f"Generado {datetime.now():%d/%m/%Y %H:%M} · Días máx {p.dias_max:g} · "
                f"Venta diaria: {'pronóstico diario del BI' if p.fuente_venta == 'pronostico' else f'CONSUMOS ACU ÷ {p.dias_consumo_acu:g}'}"
                f" · Stock = INV NETO{' + TRÁNSITO' if p.usar_transito else ''}"
                f" · {'Redondeo a múltiplos de EMPAQUE' if p.redondear_empaque else 'Unidades sueltas'}")
    ws["A2"].font = Font(italic=True, size=9, color="595959")
    for k, (lbl, val) in enumerate(kpis):
        c = 1 + k * 2
        a = ws.cell(4, c, lbl)
        a.font = Font(bold=True, size=9, color="595959")
        b = ws.cell(5, c, val)
        b.font = Font(bold=True, size=16, color=ROJO_OSC)
        for f in (4, 5):
            ws.cell(f, c).fill = PatternFill("solid", fgColor="F7F7F7")
    ws.column_dimensions["A"].width = 16


def _grafico_barras(ws, titulo, fila_h, fila_fin, col_cat, cols_val, colores, ancla, apilado=True, alto=9, ancho=26):
    ch = BarChart()
    ch.type = "bar"
    ch.grouping = "stacked" if apilado else "clustered"
    if apilado:
        ch.overlap = 100
    ch.title = titulo
    ch.style = 10
    ch.height, ch.width = alto, ancho
    for c, color in zip(cols_val, colores):
        ref = Reference(ws, min_col=c, min_row=fila_h, max_row=fila_fin)
        ch.add_data(ref, titles_from_data=True)
        s = ch.series[-1]
        s.graphicalProperties.solidFill = color
        s.graphicalProperties.line.solidFill = color
    ch.set_categories(Reference(ws, min_col=col_cat, min_row=fila_h + 1, max_row=fila_fin))
    ch.y_axis.majorGridlines = None
    ch.x_axis.scaling.orientation = "maxMin"     # primer estadístico arriba
    ch.legend.position = "b"
    ch.dataLabels = DataLabelList()
    ch.dataLabels.showVal = True
    ch.dataLabels.showSerName = ch.dataLabels.showCatName = ch.dataLabels.showLegendKey = False
    ch.visible_cells_only = False   # los datos del gráfico están en columnas ocultas
    ws.add_chart(ch, ancla)


def excel_cd(res: Resultado, p: Parametros) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "RESUMEN"
    r = res.resumen
    _encabezado_resumen(ws, "DISTRIBUCIÓN CD A LOCALES (PRÓXIMOS A VENCER)", p, [
        ("Estadísticos", r["items"]), ("Und. a mover", r["und_mover"]), ("Und. asignadas", r["und_asignadas"]),
        ("Sobrante", r["und_sobrante"]), ("Traspasos", r["traspasos"]), ("Locales que reciben", r["locales"])])
    pi = res.por_item.copy()
    if len(pi):
        tabla = pi[["Estadístico", "Descripción", "Cantidad a Mover", "Asignado", "Sobrante", "% Asignado",
                    "Locales Habilitados", "Locales que Reciben", "Capacidad hasta Días Máx", "Observación"]]
        ini = 8
        fin = _escribir_tabla(ws, tabla, ini)
        # tabla auxiliar para el gráfico (etiqueta corta)
        aux_c = 14
        ws.cell(ini, aux_c, "Estadístico ")
        ws.cell(ini, aux_c + 1, "Asignado")
        ws.cell(ini, aux_c + 2, "Sobrante")
        for i, row in enumerate(tabla.itertuples(index=False), ini + 1):
            ws.cell(i, aux_c, f"{row[0]} · {str(row[1])[:28]}")
            ws.cell(i, aux_c + 1, int(row[3]))
            ws.cell(i, aux_c + 2, int(row[4]))
        for c in range(aux_c, aux_c + 3):
            ws.column_dimensions[get_column_letter(c)].hidden = True
        _grafico_barras(ws, "Unidades asignadas vs. sobrante por estadístico", ini, fin, aux_c, [aux_c + 1, aux_c + 2],
                        [C_OK, C_PEND], f"A{fin + 3}", alto=max(7, 0.9 * len(tabla) + 3))
        ws.conditional_formatting.add(f"E{ini + 1}:E{fin}", CellIsRule(operator="greaterThan", formula=["0"],
                                      fill=F_ROJO, font=Font(bold=True, color=ROJO)))
    ws.freeze_panes = "A8"
    _hoja(wb, "DISTRIBUCIÓN", res.distribucion, "DISTRIBUCIÓN A GRABAR",
          f"Origen → local destino · estadístico · cantidad. Ningún local supera {p.dias_max:g} días de inventario.")
    _hoja(wb, "SOBRANTE", res.pendientes, "UNIDADES SIN ASIGNAR",
          "Quedan en el CD: los locales habilitados no pueden recibir más sin pasar los días máximos.", ROJO)
    _hoja(wb, "LOCALES NO CONSIDERADOS", res.no_considerados, "LOCALES DE LA BASE QUE NO RECIBEN",
          "Motivo: sin venta o ya con los días máximos cubiertos.", "595959")
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def excel_locales(res: Resultado, p: Parametros) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "RESUMEN"
    r = res.resumen
    _encabezado_resumen(ws, "REDISTRIBUCIÓN ENTRE LOCALES", p, [
        ("Und. a mover", r["und_mover"]), ("Mismo supervisor", r["nivel_sup"]), ("Mismo gerente", r["nivel_ger"]),
        ("Pendiente manual", r["pendiente"]), ("Traspasos", r["traspasos"]), ("Locales que reciben", r["locales"])])
    pi = res.por_item.copy()
    if len(pi):
        tabla = pi[["Local Origen", "Supervisor Origen", "Gerente Origen", "Estadístico", "Descripción",
                    "Cantidad a Mover", NIVEL_SUP, NIVEL_GER, NIVEL_MAN, "% Asignado", "Observación"]]
        ini = 8
        fin = _escribir_tabla(ws, tabla, ini)
        ws.conditional_formatting.add(f"I{ini + 1}:I{fin}", CellIsRule(operator="greaterThan", formula=["0"],
                                      fill=F_ROJO, font=Font(bold=True, color=ROJO)))
        # gráfico 1: por nivel (total)
        aux_c = 14
        ws.cell(ini, aux_c, "Nivel")
        ws.cell(ini, aux_c + 1, "Unidades")
        for i, (lbl, v) in enumerate([("Mismo supervisor", r["nivel_sup"]), ("Mismo gerente", r["nivel_ger"]),
                                      ("Pendiente manual", r["pendiente"])], ini + 1):
            ws.cell(i, aux_c, lbl)
            ws.cell(i, aux_c + 1, v)
        ch = BarChart()
        ch.type, ch.style, ch.title = "col", 10, "Unidades por nivel de asignación"
        ch.add_data(Reference(ws, min_col=aux_c + 1, min_row=ini, max_row=ini + 3), titles_from_data=True)
        ch.set_categories(Reference(ws, min_col=aux_c, min_row=ini + 1, max_row=ini + 3))
        from openpyxl.chart.series import DataPoint
        for k, color in enumerate([C_OK, C_ALT, ROJO]):
            pt = DataPoint(idx=k)
            pt.graphicalProperties.solidFill = color
            pt.graphicalProperties.line.solidFill = color
            ch.series[0].dPt.append(pt)
        ch.legend = None
        ch.y_axis.majorGridlines = None
        ch.dataLabels = DataLabelList()
        ch.dataLabels.showVal = True
        ch.dataLabels.showSerName = ch.dataLabels.showCatName = ch.dataLabels.showLegendKey = False
        ch.height, ch.width = 8, 13
        ch.visible_cells_only = False
        ws.add_chart(ch, f"A{fin + 3}")
        # gráfico 2: por gerente de origen, apilado por nivel
        g = pi.groupby("Gerente Origen")[[NIVEL_SUP, NIVEL_GER, NIVEL_MAN]].sum().reset_index()
        g2 = ini + 6
        for j, h in enumerate(["Gerente", "Mismo supervisor", "Mismo gerente", "Pendiente manual"]):
            ws.cell(g2, aux_c + j, h)
        for i, row in enumerate(g.itertuples(index=False), g2 + 1):
            ws.cell(i, aux_c, str(row[0]) or "(sin gerente)")
            for j in range(3):
                ws.cell(i, aux_c + 1 + j, int(row[1 + j]))
        _grafico_barras(ws, "Unidades por gerente del local de origen", g2, g2 + len(g), aux_c,
                        [aux_c + 1, aux_c + 2, aux_c + 3], [C_OK, C_ALT, ROJO], f"H{fin + 3}",
                        alto=max(8, 0.8 * len(g) + 3), ancho=18)
        for c in range(aux_c, aux_c + 4):
            ws.column_dimensions[get_column_letter(c)].hidden = True
    ws.freeze_panes = "A8"
    _hoja(wb, "DISTRIBUCIÓN", res.distribucion, "TRASPASOS ENTRE LOCALES A GRABAR",
          f"Local origen → local destino. Prioridad: mismo supervisor, luego mismo gerente. Ningún destino supera {p.dias_max:g} días.")
    _hoja(wb, "PENDIENTE MANUAL", res.pendientes, "PENDIENTE DE ASIGNACIÓN MANUAL",
          "No hay capacidad en locales del mismo supervisor ni del mismo gerente. Se sugieren locales de otros gerentes con capacidad.", ROJO)
    _hoja(wb, "LOCALES NO CONSIDERADOS", res.no_considerados, "LOCALES DE LA BASE QUE NO RECIBEN",
          "Motivo: sin venta o ya con los días máximos cubiertos.", "595959")
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
