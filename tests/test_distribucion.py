from pathlib import Path

import distribucion as d

D = Path(__file__).parent / "datos"
BASE = d.leer_base(D / "base_ejemplo.csv")


def test_lectura():
    assert len(BASE) == 7
    assert BASE.loc[BASE.local == 1, "pronostico"].iloc[0] == 1          # promedio de columnas de fecha
    assert d.codigo("051404000_MEDIAS") == 51404000 and d.num("89,06 %") == 89.06


def test_cd_no_supera_dias_y_nivela():
    p = d.Parametros(dias_max=10)
    res = d.distribuir_cd(BASE, d.leer_mover_cd(D / "mover_cd.csv"), p)
    dist = res.distribucion.set_index("Local Destino")
    # capacidad: L1 10, L2 0 (ya tiene 10 días), L3 20, L5 20; L4 exclusión, L6 sin venta, L7 sobrestock
    assert res.resumen["und_asignadas"] == 50 and res.resumen["und_sobrante"] == 50
    assert set(dist.index) == {1, 3, 5}
    assert (res.distribucion["Días Finales"] <= 10).all()
    motivos = set(res.no_considerados["Motivo"])
    assert {"EXCLUSIÓN IP", "SIN VENTA"} <= motivos


def test_cd_nivelacion_con_poco_stock():
    mov = d.normalizar_mover_cd(__import__("pandas").DataFrame({"Estadístico": [111], "Cantidad": [6]}))
    res = d.distribuir_cd(BASE, mov, d.Parametros(dias_max=10))
    dist = res.distribucion.set_index("Local Destino")["Días Finales"]
    # todos parten en 0 días; deben quedar parejos (1 o 2 días), no todo en un solo local
    assert dist.max() - dist.min() <= 1


def test_empaque():
    res = d.distribuir_cd(BASE, d.leer_mover_cd(D / "mover_cd.csv"), d.Parametros(dias_max=10, redondear_empaque=True))
    assert (res.distribucion["Cantidad"] % 6 == 0).all()


def test_locales_prioridad_supervisor_luego_gerente():
    res = d.redistribuir_locales(BASE, d.leer_mover_locales(D / "mover_locales.csv"), d.Parametros(dias_max=10))
    dist = res.distribucion
    sup = dist[dist["Nivel"] == d.NIVEL_SUP]
    ger = dist[dist["Nivel"] == d.NIVEL_GER]
    assert set(sup["Local Destino"]) == {1}           # mismo supervisor sup.a1 (L2 ya tiene 10 días)
    assert set(ger["Local Destino"]) == {3}           # mismo gerente ger.a (L4 excluido)
    assert 5 not in set(dist["Local Destino"])        # otro gerente: no se asigna automáticamente
    assert res.resumen["nivel_sup"] == 10 and res.resumen["nivel_ger"] == 20 and res.resumen["pendiente"] == 10
    assert "5 (" in res.pendientes["Sugerencia (otros gerentes · capacidad)"].iloc[0]


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
    base = BASE[BASE["gerente"] == "ger.a"]
    res = d.redistribuir_locales(base, d.leer_mover_locales(D / "mover_locales.csv"), d.Parametros(dias_max=10))
    assert res.resumen["pendiente"] == 10
    assert res.pendientes["Sugerencia (otros gerentes · capacidad)"].iloc[0] == "Sin locales con capacidad"
