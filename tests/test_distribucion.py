from pathlib import Path

import distribucion as d

D = Path(__file__).parent / "datos"
BASE = d.leer_base(D / "base_ejemplo.csv")


def test_lectura():
    assert len(BASE) == 7
    assert BASE.loc[BASE.local == 1, "pronostico"].iloc[0] == 1          # promedio de columnas de fecha
    assert d.codigo("051404000_MEDIAS") == 51404000 and d.num("89,06 %") == 89.06


def test_cd_no_supera_dias_y_nivela():
    p = d.Parametros(dias_max=10, cubrir_exhibicion=False)
    res = d.distribuir_cd(BASE, d.leer_mover_cd(D / "mover_cd.csv"), p)
    dist = res.distribucion.set_index("Local Destino")
    # capacidad: L1 10, L2 0 (ya tiene 10 días), L3 20, L4 20, L5 20; L6 sin venta, L7 sobrestock
    # la base ya viene filtrada: un local con EXCLUSION en la base SÍ recibe (L4)
    assert res.resumen["und_asignadas"] == 70 and res.resumen["und_sobrante"] == 30
    assert set(dist.index) == {1, 3, 4, 5}
    assert (res.distribucion["Días Finales"] <= 10).all()
    motivos = set(res.no_considerados["Motivo"])
    assert "SIN VENTA" in motivos and not any("EXCLUS" in m for m in motivos)


def test_cd_nivelacion_con_poco_stock():
    mov = d.normalizar_mover_cd(__import__("pandas").DataFrame({"Estadístico": [111], "Cantidad": [6]}))
    res = d.distribuir_cd(BASE, mov, d.Parametros(dias_max=10))
    dist = res.distribucion.set_index("Local Destino")["Días Finales"]
    # todos parten en 0 días; deben quedar parejos (1 o 2 días), no todo en un solo local
    assert dist.max() - dist.min() <= 1


def test_empaque_usa_columna_empaque_no_empq_final():
    res = d.distribuir_cd(BASE, d.leer_mover_cd(D / "mover_cd.csv"), d.Parametros(dias_max=10, redondear_empaque=True))
    assert (res.distribucion["Cantidad"] % 6 == 0).all()          # EMPAQUE = 6
    assert (res.distribucion["Cantidad"] % 12 != 0).any()         # no Empq_final = 12
    assert res.por_item["Empaque Usado"].iloc[0] == 6


def test_locales_prioridad_supervisor_luego_gerente():
    res = d.redistribuir_locales(BASE, d.leer_mover_locales(D / "mover_locales.csv"), d.Parametros(dias_max=10))
    dist = res.distribucion
    sup = dist[dist["Nivel"] == d.NIVEL_SUP]
    ger = dist[dist["Nivel"] == d.NIVEL_GER]
    assert set(sup["Local Destino"]) == {1}           # mismo supervisor sup.a1 (L2 ya tiene 10 días)
    assert set(ger["Local Destino"]) == {3, 4}        # mismo gerente ger.a
    assert 5 not in set(dist["Local Destino"])        # otro gerente: no se asigna automáticamente
    assert res.resumen["nivel_sup"] == 10 and res.resumen["nivel_ger"] == 30 and res.resumen["pendiente"] == 0


def test_locales_pendiente_con_sugerencia_de_otro_gerente():
    import pandas as pd
    mov = pd.DataFrame({"estadistico": [111], "origen": [7], "cantidad": [60], "supervisor": ["sup.a1"],
                        "gerente": ["ger.a"], "descripcion_mov": [""]})
    res = d.redistribuir_locales(BASE, mov, d.Parametros(dias_max=10))
    # capacidad sup.a1 = 10, ger.a = 40 → 10 pendientes; L5 (ger.b) se sugiere
    assert res.resumen["pendiente"] == 10
    assert "5 (" in res.pendientes["Sugerencia (fuera del filtro · capacidad)"].iloc[0]


def _llenar(bytes_xlsx, filas):
    import io
    import openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(bytes_xlsx))
    ws = wb["PLANTILLA"]
    for i, fila in enumerate(filas, 2):
        for j, v in enumerate(fila, 1):
            ws.cell(i, j, v)
    out = io.BytesIO()
    wb.save(out)
    out.seek(0)
    out.name = "plantilla.xlsx"
    return out


def test_plantilla_cd_se_lee():
    from plantillas import plantilla_cd
    f = _llenar(plantilla_cd(), [("111", "ITEM PRUEBA", 100, 30), (None, None, None, None)])
    mov = d.leer_mover_cd(f)
    assert len(mov) == 1 and mov.loc[0, "estadistico"] == 111 and mov.loc[0, "bodega"] == 100 and mov.loc[0, "cantidad"] == 30
    res = d.distribuir_cd(BASE, mov, d.Parametros(dias_max=10))
    assert res.resumen["und_asignadas"] == 30


def test_plantilla_locales_se_lee_y_completa():
    from plantillas import plantilla_locales
    f = _llenar(plantilla_locales(), [("111", "", "7-LOCAL 7", 40, "", "")])
    mov = d.normalizar_mover_locales(d._con_encabezado(d.leer_tabla(f), ["ESTADIST", "LOCAL"]), d.maestro_locales(BASE))
    assert mov.loc[0, "origen"] == 7 and mov.loc[0, "supervisor"] == "sup.a1" and mov.loc[0, "gerente"] == "ger.a"
    res = d.redistribuir_locales(BASE, mov, d.Parametros(dias_max=10))
    assert res.resumen["nivel_sup"] == 10


def test_pendiente_sin_locales_de_otros_gerentes():
    # todos los locales son del mismo gerente: no hay a quién sugerir y no debe fallar
    import pandas as pd
    base = BASE[BASE["gerente"] == "ger.a"]
    mov = pd.DataFrame({"estadistico": [111], "origen": [7], "cantidad": [60], "supervisor": ["sup.a1"],
                        "gerente": ["ger.a"], "descripcion_mov": [""]})
    res = d.redistribuir_locales(base, mov, d.Parametros(dias_max=10))
    assert res.resumen["pendiente"] == 10
    assert res.pendientes["Sugerencia (fuera del filtro · capacidad)"].iloc[0] == "Sin locales con capacidad"


def test_stock_es_inv_neto_mas_roq_ltc_y_ptl_sin_transito():
    b = BASE.copy()
    b.loc[b.local == 1, ["inv_neto", "roq_ltc", "roq_ptl", "transito"]] = [1, 2, 3, 50]
    prep = d.preparar(b, d.Parametros(dias_max=10)).set_index("local")
    assert prep.loc[1, "stock"] == 6                    # 1 + 2 + 3; el tránsito no se suma
    assert prep.loc[1, "capacidad"] == 4                # 10 días × 1 und/día − 6


def test_venta_diaria_consumos_acu_dividido_dias():
    p = d.Parametros(fuente_venta="consumo", dias_consumo_acu=3)
    prep = d.preparar(BASE, p).set_index("local")
    assert prep.loc[3, "venta_diaria"] == 6 / 3         # CONSUMOS ACU 6 ÷ 3 días
    p.dias_consumo_acu = 6
    assert d.preparar(BASE, p).set_index("local").loc[3, "venta_diaria"] == 1


def test_consumo_mes_anterior_dividido_dias_del_mes():
    cm = d.consumo_diario(d.leer_consumo_mensual(D / "consumo_mensual.csv"))
    v = cm.set_index("local")["venta_diaria"]
    assert v[1] == 2 and v[3] == 1 and v[4] == 3          # octubre ÷ 31 días
    assert cm["periodo"].iloc[0] == "Oct-2026 ÷ 31 días"
    prep = d.preparar(BASE, d.Parametros(dias_max=10, fuente_venta="mensual"), cm).set_index("local")
    assert prep.loc[1, "venta_diaria"] == 2
    assert prep.loc[5, "venta_diaria"] == 0               # no vendió en el mes → no recibe
    assert prep.loc[5, "motivo_no_recibe"] == "SIN VENTA"
    # capacidad L1 = 10 días × 2 − 0 = 20; con el pronóstico (1/día) era 10
    assert prep.loc[1, "capacidad"] == 20
    res = d.distribuir_cd(BASE, d.leer_mover_cd(D / "mover_cd.csv"),
                          d.Parametros(dias_max=10, fuente_venta="mensual", cubrir_exhibicion=False), cm)
    assert set(res.distribucion["Local Destino"]) <= {1, 3, 4}
    assert (res.distribucion["Fuente Venta"] == "Consumo Oct-2026 ÷ 31 días").all()


def test_consumo_mensual_desde_export_con_encabezado(tmp_path):
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Iproduct"])
    ws.append(["Generado el: 6th November 2026 / Desde: 2026-09 hasta: 2026-10 / Estadístico: COLA INCA KOLA 900 ML - 247239000"])
    ws.append([])
    ws.append([None, None, None, 91])
    ws.append([])
    ws.append(["Cod Sucursal", "Desc Sucursal", "Mes", "Consumo Unid"])
    ws.append([201, "LLANO GRANDE", "2026-09", 30])
    ws.append([201, "LLANO GRANDE", "2026-10", 31])
    ws.append([421, "ESMERALDAS", "2026-10", 30])
    f = tmp_path / "export.xlsx"
    wb.save(f)
    cm = d.consumo_diario(d.leer_consumo_mensual(f))
    v = cm.set_index("local")["venta_diaria"]
    assert set(cm["estadistico"]) == {247239000}
    assert v[201] == 1                                    # (30 + 31) ÷ (30 + 31 días)
    assert round(v[421], 4) == round(30 / 61, 4)          # sin consumo en septiembre cuenta como 0


def test_excel_cd_hoja_forzados():
    import io
    import openpyxl
    from exportar import excel_cd
    p = d.Parametros(dias_max=10)
    res = d.distribuir_cd(BASE, d.leer_mover_cd(D / "mover_cd.csv"), p)
    wb = openpyxl.load_workbook(io.BytesIO(excel_cd(res, p)))
    assert wb.sheetnames[:3] == ["RESUMEN", "FORZADOS", "DISTRIBUCIÓN"]
    ws = wb["FORZADOS"]
    filas = list(ws.iter_rows(values_only=True))
    assert filas[0] == ("Estadístico", "Descripción", "Local Destino", "Cantidad")
    assert len(filas) - 1 == len(res.distribucion)
    assert sum(f[3] for f in filas[1:]) == res.resumen["und_asignadas"]
    cant = [f[3] for f in filas[1:]]
    assert cant == sorted(cant, reverse=True)            # de mayor a menor por estadístico


def test_excel_locales_hoja_forzados_con_origen():
    import io
    import openpyxl
    import pandas as pd
    from exportar import excel_locales
    p = d.Parametros(dias_max=10)
    mov = pd.DataFrame({"estadistico": [111, 111], "origen": [7, 2], "cantidad": [40, 5], "supervisor": ["sup.a1", "sup.a1"],
                        "gerente": ["ger.a", "ger.a"], "descripcion_mov": ["", ""]})
    res = d.redistribuir_locales(BASE, mov, p)
    wb = openpyxl.load_workbook(io.BytesIO(excel_locales(res, p)))
    assert wb.sheetnames[:3] == ["RESUMEN", "FORZADOS", "DISTRIBUCIÓN"]
    filas = list(wb["FORZADOS"].iter_rows(values_only=True))
    assert filas[0] == ("Local Origen", "Estadístico", "Descripción", "Local Destino", "Cantidad")
    assert sum(f[4] for f in filas[1:]) == res.resumen["nivel_sup"] + res.resumen["nivel_ger"]
    origenes = [f[0] for f in filas[1:]]
    assert origenes == sorted(origenes)                  # ordenado por local de origen


def _mov7(cant):
    import pandas as pd
    return pd.DataFrame({"estadistico": [111], "origen": [7], "cantidad": [cant], "supervisor": ["sup.a1"],
                         "gerente": ["ger.a"], "descripcion_mov": [""]})


def test_filtro_solo_supervisor():
    res = d.redistribuir_locales(BASE, _mov7(40), d.Parametros(dias_max=10, nivel_m2="supervisor"))
    assert res.resumen["nivel_sup"] == 10 and res.resumen["nivel_ger"] == 0 and res.resumen["pendiente"] == 30
    assert set(res.distribucion["Local Destino"]) == {1}
    sug = res.pendientes[d.COL_SUG].iloc[0]
    assert sug.startswith("3 (") or sug.startswith("4 (")          # primero otros supervisores del mismo gerente
    assert "del mismo supervisor" in res.pendientes["Motivo"].iloc[0]


def test_filtro_solo_gerente_incluye_locales_del_mismo_supervisor():
    res = d.redistribuir_locales(BASE, _mov7(40), d.Parametros(dias_max=10, nivel_m2="gerente"))
    assert res.resumen["nivel_sup"] == 0 and res.resumen["nivel_ger"] == 40 and res.resumen["pendiente"] == 0
    assert set(res.distribucion["Nivel"]) == {d.NIVEL_GER}
    assert {1, 3, 4} == set(res.distribucion["Local Destino"])     # L1 es del mismo supervisor y también recibe
    assert 5 not in set(res.distribucion["Local Destino"])        # otro gerente


def test_filtro_ambos_es_el_comportamiento_original():
    res = d.redistribuir_locales(BASE, _mov7(40), d.Parametros(dias_max=10, nivel_m2="ambos"))
    assert res.resumen["nivel_sup"] == 10 and res.resumen["nivel_ger"] == 30 and res.resumen["pendiente"] == 0


# ---------------------------------------------------------------- exhibición en locales sin venta
def test_cd_sin_venta_completa_exhibicion_con_el_sobrante():
    res = d.distribuir_cd(BASE, d.leer_mover_cd(D / "mover_cd.csv"), d.Parametros(dias_max=10))
    dist = res.distribucion.set_index("Local Destino")
    # 70 und por días (L1, L3, L4, L5) y luego L6 (sin venta, stock 0, exhibición 4) recibe 4
    assert dist.loc[6, "Criterio"] == d.CRIT_EXHIB and dist.loc[6, "Cantidad"] == 4
    assert (res.distribucion.loc[res.distribucion["Criterio"] == d.CRIT_DIAS, "Días Finales"] <= 10).all()
    assert res.resumen["und_asignadas"] == 74 and res.resumen["und_exhib"] == 4 and res.resumen["und_sobrante"] == 26
    assert res.por_item["Para Exhibición"].iloc[0] == 4
    assert 6 not in set(res.no_considerados["Local"])


def test_cd_locales_con_venta_tienen_prioridad_sobre_exhibicion():
    import pandas as pd
    mov = d.normalizar_mover_cd(pd.DataFrame({"Estadístico": [111], "Cantidad": [30]}))
    res = d.distribuir_cd(BASE, mov, d.Parametros(dias_max=10))
    assert 6 not in set(res.distribucion["Local Destino"])       # no sobró nada para la exhibición
    nc = res.no_considerados.set_index("Local").loc[6]
    assert nc["Motivo"] == d.MOT_EXHIB and nc["Falta Exhibición"] == 4


def test_exhibicion_con_empaque_envia_empaque_completo():
    res = d.distribuir_cd(BASE, d.leer_mover_cd(D / "mover_cd.csv"), d.Parametros(dias_max=10, redondear_empaque=True))
    dist = res.distribucion.set_index("Local Destino")
    assert dist.loc[6, "Cantidad"] == 6                          # falta 4, se envía 1 empaque de 6


def test_exhibicion_completa_no_recibe():
    b = BASE.copy()
    b.loc[b.local == 6, "inv_neto"] = 4                          # ya tiene la exhibición completa
    res = d.distribuir_cd(b, d.leer_mover_cd(D / "mover_cd.csv"), d.Parametros(dias_max=10))
    assert 6 not in set(res.distribucion["Local Destino"])
    assert res.no_considerados.set_index("Local").loc[6, "Motivo"] == "SIN VENTA"


def test_locales_exhibicion_despues_de_dias_en_mismo_supervisor():
    import pandas as pd
    b = pd.concat([BASE, BASE[BASE.local == 1].assign(local=8, designacion="LOCAL 8", consumo_acu=0, pronostico=0.0,
                                                       inv_neto=1)], ignore_index=True)
    res = d.redistribuir_locales(b, _mov7(60), d.Parametros(dias_max=10))
    dist = res.distribucion.set_index("Local Destino")
    assert dist.loc[8, "Criterio"] == d.CRIT_EXHIB and dist.loc[8, "Cantidad"] == 3 and dist.loc[8, "Nivel"] == d.NIVEL_SUP
    assert res.resumen["nivel_sup"] == 13 and res.resumen["nivel_ger"] == 40 and res.resumen["pendiente"] == 7
    assert res.resumen["exhib"] == 3


# ---------------------------------------------------------------- otros gerentes (módulo 2)
def test_otros_gerentes_despues_de_su_gerente():
    res = d.redistribuir_locales(BASE, _mov7(80), d.Parametros(dias_max=10, gerentes_extra=("ger.b",)))
    dist = res.distribucion
    assert res.resumen["nivel_sup"] == 10 and res.resumen["nivel_ger"] == 40
    otr = dist[dist["Nivel"] == d.NIVEL_OTR]
    # L5 (ger.b) recibe por días (capacidad 20) y luego L6 (ger.b, sin venta) completa exhibición (4)
    assert otr.set_index("Local Destino")["Cantidad"].to_dict() == {5: 20, 6: 4}
    assert res.resumen["nivel_otr"] == 24 and res.resumen["pendiente"] == 6
    assert "otros gerentes elegidos" in res.pendientes["Motivo"].iloc[0]


def test_otros_gerentes_con_exceso_no_reciben():
    b = BASE.copy()
    b.loc[b.local == 5, "inv_neto"] = 100                            # 50 días: exceso
    res = d.redistribuir_locales(b, _mov7(80), d.Parametros(dias_max=10, gerentes_extra=("ger.b",),
                                                            cubrir_exhibicion=False))
    assert 5 not in set(res.distribucion["Local Destino"])
    assert res.resumen["nivel_otr"] == 0 and res.resumen["pendiente"] == 30


def test_otros_gerentes_sin_elegir_no_cambia_nada():
    res = d.redistribuir_locales(BASE, _mov7(80), d.Parametros(dias_max=10))
    assert res.resumen["nivel_otr"] == 0 and d.NIVEL_OTR not in set(res.distribucion["Nivel"])


def test_otros_gerentes_con_filtro_solo_supervisor():
    res = d.redistribuir_locales(BASE, _mov7(40), d.Parametros(dias_max=10, nivel_m2="supervisor", gerentes_extra=("ger.b",),
                                                              cubrir_exhibicion=False))
    dist = res.distribucion
    assert set(dist.loc[dist["Nivel"] == d.NIVEL_OTR, "Local Destino"]) == {5}   # no los otros supervisores de ger.a
    assert res.resumen["nivel_sup"] == 10 and res.resumen["nivel_otr"] == 20 and res.resumen["pendiente"] == 10
    assert not res.pendientes[d.COL_SUG].iloc[0].startswith("5 (")             # ger.b ya está en el filtro


def test_excel_locales_con_otros_gerentes():
    import io
    import openpyxl
    from exportar import excel_locales
    p = d.Parametros(dias_max=10, gerentes_extra=("ger.b",))
    res = d.redistribuir_locales(BASE, _mov7(80), p)
    ws = openpyxl.load_workbook(io.BytesIO(excel_locales(res, p)))["RESUMEN"]
    cab = [c.value for c in ws[8]]
    assert cab[8] == d.NIVEL_OTR and cab[9] == d.NIVEL_MAN
    assert "ger.b" in ws["A2"].value
