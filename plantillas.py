"""Plantillas de Excel para ingresar el inventario a mover (se descargan desde la app)."""
from __future__ import annotations

import io

from openpyxl import Workbook
from openpyxl.comments import Comment
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.worksheet.datavalidation import DataValidation

ROJO, ROJO_OSC, GRIS = "E30613", "A30410", "8C8C8C"
thin = Side(style="thin", color="BFBFBF")
BORDE = Border(left=thin, right=thin, top=thin, bottom=thin)
FILAS = 500

# (encabezado, obligatoria, ancho, nota)
COLS_CD = [
    ("Estadístico", True, 15, "Código del estadístico. Acepta 240765000 o 240765000_DESCRIPCIÓN."),
    ("Descripción", False, 42, "Opcional: solo para que sea fácil de leer. El programa toma la descripción de la base."),
    ("Bodega de salida", True, 16, "Código de la bodega / CD de donde sale el producto (ej. 100)."),
    ("Cantidad", True, 12, "Unidades a distribuir a los locales. Número entero mayor a 0."),
]
COLS_LOC = [
    ("Estadístico", True, 15, "Código del estadístico. Acepta 240765000 o 240765000_DESCRIPCIÓN."),
    ("Descripción", False, 42, "Opcional: solo para que sea fácil de leer. El programa toma la descripción de la base."),
    ("Local de salida", True, 15, "Código del local de donde sale el producto. Acepta 598 o 598-ATARAZANA."),
    ("Cantidad", True, 12, "Unidades a mover desde ese local. Número entero mayor a 0."),
    ("Supervisor", False, 20, "Opcional: si lo dejas vacío se completa con la base de locales o el maestro."),
    ("Gerente", False, 20, "Opcional: si lo dejas vacío se completa con la base de locales o el maestro."),
]
EJ_CD = [(240765000, "JUGO PANELADA 22 G LIMON", 100, 120), (240744000, "JUGO FRESCO SOLO SOBRE 10 G X 7", 100, 22)]
EJ_LOC = [(240714005, "JUGO YA 15 G PINA COCO", 106, 29, "virginia.carreno", "nancy.zamora"),
          (240756000, "TE SUNTEA 20 G LIMON", 598, 11, "", "")]


def _plantilla(columnas, ejemplos, titulo, instrucciones) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "PLANTILLA"
    for j, (h, obligatoria, ancho, nota) in enumerate(columnas, 1):
        c = ws.cell(1, j, h)
        c.fill = PatternFill("solid", fgColor=ROJO_OSC if obligatoria else GRIS)
        c.font = Font(bold=True, color="FFFFFF")
        c.alignment = Alignment(horizontal="center", vertical="center")
        c.border = BORDE
        c.comment = Comment(("OBLIGATORIA. " if obligatoria else "") + nota, "Distribución")
        ws.column_dimensions[c.column_letter].width = ancho
        for i in range(2, FILAS + 2):
            ws.cell(i, j).border = BORDE
            if h in ("Estadístico", "Bodega de salida", "Local de salida", "Cantidad"):
                ws.cell(i, j).alignment = Alignment(horizontal="center")
    ws.row_dimensions[1].height = 24
    ws.freeze_panes = "A2"
    col_cant = [h for h, *_ in columnas].index("Cantidad") + 1
    letra = ws.cell(1, col_cant).column_letter
    dv = DataValidation(type="whole", operator="greaterThan", formula1="0", allow_blank=True,
                        error="La cantidad debe ser un número entero mayor a 0.", errorTitle="Cantidad no válida")
    dv.add(f"{letra}2:{letra}{FILAS + 1}")
    ws.add_data_validation(dv)

    ej = wb.create_sheet("EJEMPLO")
    for j, (h, obligatoria, ancho, _) in enumerate(columnas, 1):
        c = ej.cell(1, j, h)
        c.fill = PatternFill("solid", fgColor=ROJO_OSC if obligatoria else GRIS)
        c.font = Font(bold=True, color="FFFFFF")
        ej.column_dimensions[c.column_letter].width = ancho
    for i, fila in enumerate(ejemplos, 2):
        for j, v in enumerate(fila, 1):
            ej.cell(i, j, v).border = BORDE

    ins = wb.create_sheet("INSTRUCCIONES")
    ins["A1"] = titulo
    ins["A1"].font = Font(bold=True, size=14, color=ROJO)
    for i, t in enumerate(instrucciones, 3):
        ins.cell(i, 1, t).alignment = Alignment(wrap_text=True, vertical="top")
    ins.column_dimensions["A"].width = 110
    i = 3 + len(instrucciones) + 1
    ins.cell(i, 1, "Columnas").font = Font(bold=True, color=ROJO)
    for k, (h, obligatoria, _, nota) in enumerate(columnas, i + 1):
        ins.cell(k, 1, f"• {h} ({'obligatoria' if obligatoria else 'opcional'}): {nota}").alignment = Alignment(wrap_text=True)
    wb.active = 0
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def plantilla_cd() -> bytes:
    return _plantilla(COLS_CD, EJ_CD, "PLANTILLA · DISTRIBUCIÓN CD A LOCALES (PRÓXIMOS A VENCER)", [
        "1. Llena la hoja PLANTILLA: una fila por estadístico que sale del CD (las columnas rojas son obligatorias).",
        "2. La hoja EJEMPLO muestra cómo llenarla; no se lee al subir el archivo.",
        "3. Guarda el archivo y súbelo en el programa, en '2) Inventario a mover desde el CD'.",
        "4. El programa reparte la cantidad entre los locales habilitados de la base sin pasar los días máximos de inventario.",
    ])


def plantilla_locales() -> bytes:
    return _plantilla(COLS_LOC, EJ_LOC, "PLANTILLA · REDISTRIBUCIÓN ENTRE LOCALES", [
        "1. Llena la hoja PLANTILLA: una fila por local de salida + estadístico (las columnas rojas son obligatorias).",
        "2. Supervisor y Gerente son opcionales: si los dejas vacíos, el programa los completa con el local de salida.",
        "3. La hoja EJEMPLO muestra cómo llenarla; no se lee al subir el archivo.",
        "4. Guarda el archivo y súbelo en el programa, en '2) Inventario a mover entre locales'.",
        "5. Prioridad de envío: locales del mismo supervisor, luego del mismo gerente; lo demás queda pendiente manual.",
    ])
