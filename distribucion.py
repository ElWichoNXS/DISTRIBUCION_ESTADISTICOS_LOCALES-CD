"""
Motor de distribución por días de inventario.

Módulo 1 · Distribución CD a Locales (Próximos a Vencer)
    Reparte las unidades de una bodega entre los locales habilitados sin superar
    los días máximos de inventario. Si no alcanza para todos, nivela: primero
    recibe el local con menos días de inventario.

Módulo 2 · Redistribución entre locales
    Mueve el inventario de un local a otros locales sin superar los días máximos.
    Prioridad: 1) mismo supervisor, 2) mismo gerente, 3) pendiente para asignar manualmente.

Conceptos (por local + estadístico):
    venta diaria   = pronóstico diario (promedio de las columnas de fecha del BI);
                     si no hay pronóstico, CONSUMOS ACU ÷ días que representa (3, como DIAS STOCK SUC del BI).
    stock actual   = INV NETO + ROQ_LTC + ROQ_PTL   (INV NETO ya incluye el tránsito)
    días actuales  = stock actual ÷ venta diaria
    capacidad      = días máx × venta diaria − stock actual  (nunca negativa)
    Un local sin venta no recibe (no se envía producto donde no rota).
    La base ya viene filtrada con los locales habilitados: no se aplican exclusiones adicionales.
    Redondeo opcional a múltiplos de EMPAQUE.
"""
from __future__ import annotations

import heapq
import io
import re
import unicodedata
from dataclasses import dataclass, field

import pandas as pd

# ------------------------------------------------------------------ utilidades


def normalizar(texto) -> str:
    s = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", s).strip().upper()


def codigo(valor):
    """Código numérico de '189-GUASMO…', '051404000_MEDIAS…', 189.0, etc."""
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return None
    if isinstance(valor, bool):
        return None
    if isinstance(valor, (int, float)):
        return int(valor)
    m = re.match(r"\s*0*(\d+)", str(valor))
    return int(m.group(1)) if m else None


def num(v) -> float:
    """Número desde '1.234,5', '1,5', '89,06 %', '' o NaN."""
    if v is None:
        return 0.0
    if isinstance(v, (int, float)):
        return 0.0 if pd.isna(v) else float(v)
    t = str(v).strip().replace(" ", "").replace("%", "")
    if not t:
        return 0.0
    if "," in t and "." in t:
        t = t.replace(".", "").replace(",", ".") if t.rfind(",") > t.rfind(".") else t.replace(",", "")
    elif "," in t:
        t = t.replace(",", ".")
    try:
        return float(t)
    except ValueError:
        return 0.0


def _texto(v) -> str:
    return "" if v is None or (isinstance(v, float) and pd.isna(v)) else str(v).strip()


def leer_tabla(archivo, hoja=None) -> pd.DataFrame:
    """Lee xlsx/xls/xlsb/csv sin encabezado (se detecta después). CSV con , ; o tab, UTF-8 o Latin-1."""
    nombre = getattr(archivo, "name", str(archivo)).lower()
    if nombre.endswith(".csv") or nombre.endswith(".txt"):
        datos = archivo.read() if hasattr(archivo, "read") else open(archivo, "rb").read()
        texto = None
        for enc in ("utf-8-sig", "cp1252", "latin-1"):
            try:
                texto = datos.decode(enc)
                break
            except UnicodeDecodeError:
                continue
        primera = texto.splitlines()[0] if texto else ""
        sep = max([";", ",", "\t"], key=primera.count)
        return pd.read_csv(io.StringIO(texto), header=None, dtype=object, sep=sep, keep_default_na=False)
    engine = "pyxlsb" if nombre.endswith(".xlsb") else None
    return pd.read_excel(archivo, sheet_name=hoja if hoja is not None else 0, header=None, dtype=object, engine=engine)


def _con_encabezado(raw: pd.DataFrame, claves: list[str], max_filas=20) -> pd.DataFrame:
    for i in range(min(max_filas, len(raw))):
        fila = [normalizar(v) for v in raw.iloc[i].tolist()]
        if all(any(k == f or k in f for f in fila) for k in claves):
            df = raw.iloc[i + 1:].copy()
            df.columns = [str(c).strip() for c in raw.iloc[i].tolist()]
            return df.reset_index(drop=True)
    raise ValueError(f"No encontré los encabezados esperados ({', '.join(claves)}).")


def _col(df: pd.DataFrame, *opciones) -> str | None:
    norm = {normalizar(c): c for c in df.columns}
    for o in opciones:
        if normalizar(o) in norm:
            return norm[normalizar(o)]
    return None


FECHA = re.compile(r"^\d{1,2}/[A-Z]{3}/\d{4}$")


# ------------------------------------------------------------------ base de locales habilitados


def leer_base(archivo, hoja=None) -> pd.DataFrame:
    """Base del BI con los locales donde el producto está activo (una fila por local + estadístico)."""
    df = _con_encabezado(leer_tabla(archivo, hoja), ["LOCAL", "ESTADISTICO"])
    c = lambda *o: _col(df, *o)
    req = {"local": c("# Local", "LOCAL", "# LOCAL"), "estadistico": c("ESTADISTICO", "# ESTADIST")}
    if None in req.values():
        raise ValueError("La base debe tener las columnas '# Local' y 'ESTADISTICO'.")
    fechas = [col for col in df.columns if FECHA.match(normalizar(col))]
    out = pd.DataFrame({
        "local": df[req["local"]].map(codigo),
        "estadistico": df[req["estadistico"]].map(codigo),
        "descripcion": df[c("DESCRIPCION")].map(_texto) if c("DESCRIPCION") else "",
        "designacion": df[c("DESIGNACION")].map(_texto) if c("DESIGNACION") else "",
        "supervisor": df[c("SUPERV.", "SUPERVISOR")].map(_texto) if c("SUPERV.", "SUPERVISOR") else "",
        "gerente": df[c("GERENTE")].map(_texto) if c("GERENTE") else "",
        "bodega": df[c("BODEGA")].map(codigo) if c("BODEGA") else None,
        "formato": df[c("FORMATO")].map(_texto) if c("FORMATO") else "",
        "exclusion": df[c("EXCLUSION")].map(_texto) if c("EXCLUSION") else "",
        "observacion": df[c("OBSERVACION")].map(_texto) if c("OBSERVACION") else "",
        "consumo_acu": df[c("CONSUMOS ACU", "CONS ACUM")].map(num) if c("CONSUMOS ACU", "CONS ACUM") else 0.0,
        "inv_neto": df[c("INV NETO", "INV_NETO")].map(num) if c("INV NETO", "INV_NETO") else 0.0,
        "fisico": df[c("Físico", "FISICO")].map(num) if c("Físico", "FISICO") else 0.0,
        "roq_ltc": df[c("ROQ_LTC", "ROQ LTC")].map(num) if c("ROQ_LTC", "ROQ LTC") else 0.0,
        "roq_ptl": df[c("ROQ_PTL", "ROQ PTL")].map(num) if c("ROQ_PTL", "ROQ PTL") else 0.0,
        "exhibicion": df[c("Uni Exhibición", "EXHIBICION")].map(num) if c("Uni Exhibición", "EXHIBICION") else 0.0,
        "empaque": df[c("EMPAQUE")].map(num) if c("EMPAQUE") else 1.0,   # empaque (no Empq_final)
    })
    if fechas:
        pron = df[fechas].apply(lambda s: s.map(lambda v: num(v) if _texto(v) != "" else float("nan")))
        out["pronostico"] = pron.mean(axis=1, skipna=True)
    else:
        out["pronostico"] = float("nan")
    out = out.dropna(subset=["local", "estadistico"])
    out["local"] = out["local"].astype(int)
    out["estadistico"] = out["estadistico"].astype(int)
    out = out.drop_duplicates(["local", "estadistico"], keep="first").reset_index(drop=True)
    return out


def maestro_locales(df: pd.DataFrame) -> pd.DataFrame:
    """Local → designación, supervisor, gerente (desde la base o desde un maestro subido)."""
    m = (df[df["local"].notna()].sort_values("local")
         .drop_duplicates("local")[["local", "designacion", "supervisor", "gerente"]])
    return m.reset_index(drop=True)


def leer_maestro(archivo, hoja=None) -> pd.DataFrame:
    df = _con_encabezado(leer_tabla(archivo, hoja), ["LOCAL"])
    c = lambda *o: _col(df, *o)
    loc = c("# Local", "LOCAL", "# LOCAL", "LOCAL SALIDA", "COD LOCAL")
    if loc is None:
        raise ValueError("El maestro debe tener una columna de local ('# Local').")
    out = pd.DataFrame({
        "local": df[loc].map(codigo),
        "designacion": df[c("DESIGNACION", "NOMBRE LOCAL", "NOMBRE")].map(_texto) if c("DESIGNACION", "NOMBRE LOCAL", "NOMBRE") else "",
        "supervisor": df[c("SUPERV.", "SUPERVISOR")].map(_texto) if c("SUPERV.", "SUPERVISOR") else "",
        "gerente": df[c("GERENTE")].map(_texto) if c("GERENTE") else "",
    }).dropna(subset=["local"])
    out["local"] = out["local"].astype(int)
    return out.drop_duplicates("local").reset_index(drop=True)


# ------------------------------------------------------------------ inventario a mover


def leer_mover_cd(archivo, hoja=None) -> pd.DataFrame:
    """Módulo 1: estadísticos que salen del CD. Cantidad = FISICO_WH (o CANTIDAD)."""
    df = _con_encabezado(leer_tabla(archivo, hoja), ["ESTADIST"])
    return normalizar_mover_cd(df)


def normalizar_mover_cd(df: pd.DataFrame) -> pd.DataFrame:
    c = lambda *o: _col(df, *o)
    est = c("# ESTADIST", "ESTADISTICO", "ESTADÍSTICO")
    cant = c("CANTIDAD", "CANTIDAD A MOVER", "FISICO_WH", "UNIDADES")
    bod = c("BODEGA", "BODEGA DE SALIDA", "LOCAL DE SALIDA", "LOCAL SALIDA", "CD", "CD DE SALIDA")
    if est is None or cant is None:
        raise ValueError("Se necesitan las columnas 'Estadístico' y 'Cantidad' (o FISICO_WH).")
    out = pd.DataFrame({
        "estadistico": df[est].map(codigo),
        "cantidad": df[cant].map(num),
        "bodega": df[bod].map(codigo) if bod else None,
        "descripcion_mov": df[c("DESCRIPCION", "DESCRIPCIÓN")].map(_texto) if c("DESCRIPCION", "DESCRIPCIÓN") else "",
    })
    out = out[out["estadistico"].notna() & (out["cantidad"] > 0)].copy()
    out["estadistico"] = out["estadistico"].astype(int)
    out["cantidad"] = out["cantidad"].round().astype(int)
    return out.reset_index(drop=True)


def leer_mover_locales(archivo, hoja=None) -> pd.DataFrame:
    """Módulo 2: inventario en locales a redistribuir. Cantidad = CANTIDAD si existe, si no INV NETO."""
    df = _con_encabezado(leer_tabla(archivo, hoja), ["ESTADIST", "LOCAL"])
    return normalizar_mover_locales(df)


def normalizar_mover_locales(df: pd.DataFrame, maestro: pd.DataFrame | None = None) -> pd.DataFrame:
    c = lambda *o: _col(df, *o)
    est = c("ESTADISTICO", "ESTADÍSTICO", "# ESTADIST")
    loc = c("Local de salida", "LOCAL SALIDA", "LOCAL ORIGEN", "LOC. ORIGEN", "# Local", "LOCAL")
    cant = c("CANTIDAD", "CANTIDAD A MOVER", "INV NETO", "INV_NETO")
    if est is None or loc is None or cant is None:
        raise ValueError("Se necesitan las columnas 'Estadístico', 'Local de salida' y 'Cantidad' (o INV NETO).")
    out = pd.DataFrame({
        "estadistico": df[est].map(codigo),
        "origen": df[loc].map(codigo),
        "cantidad": df[cant].map(num),
        "supervisor": df[c("SUPERV.", "SUPERVISOR")].map(_texto) if c("SUPERV.", "SUPERVISOR") else "",
        "gerente": df[c("GERENTE")].map(_texto) if c("GERENTE") else "",
        "descripcion_mov": df[c("DESCRIPCION", "DESCRIPCIÓN")].map(_texto) if c("DESCRIPCION", "DESCRIPCIÓN") else "",
    })
    out = out[out["estadistico"].notna() & out["origen"].notna()].copy()
    out["estadistico"] = out["estadistico"].astype(int)
    out["origen"] = out["origen"].astype(int)
    out["cantidad"] = out["cantidad"].clip(lower=0).round().astype(int)
    if maestro is not None and len(maestro):
        out = completar_responsables(out, maestro)
    return out.reset_index(drop=True)


def completar_responsables(mov: pd.DataFrame, maestro: pd.DataFrame) -> pd.DataFrame:
    """Rellena supervisor y gerente vacíos a partir del local de salida."""
    m = maestro.set_index("local")
    mov = mov.copy()
    for col in ("supervisor", "gerente"):
        if col not in mov:
            mov[col] = ""
        vacio = mov[col].map(_texto) == ""
        mov.loc[vacio, col] = mov.loc[vacio, "origen"].map(m[col]).fillna("")
    mov["en_maestro"] = mov["origen"].isin(m.index)
    return mov


# ------------------------------------------------------------------ consumo mensual (export del BI)

MESES = ["", "Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]


def leer_consumo_mensual(archivo, hoja=None) -> pd.DataFrame:
    """
    Export del BI con el consumo acumulado por sucursal y mes ('Cod Sucursal', 'Mes', 'Consumo Unid').
    El estadístico se toma de una columna 'Estadístico' o, si no existe, del encabezado del reporte
    ('Estadístico: COLA INCA KOLA 900 ML - 247239000'). Devuelve una fila por local + estadístico + mes.
    """
    raw = leer_tabla(archivo, hoja)
    df = _con_encabezado(raw, ["SUCURSAL", "CONSUMO"])
    c = lambda *o: _col(df, *o)
    loc, mes, cons = c("Cod Sucursal", "COD SUCURSAL", "# Local", "LOCAL"), c("Mes", "MES", "PERIODO"), \
        c("Consumo Unid", "CONSUMO UNID", "CONSUMO", "CONSUMO UNIDADES")
    if loc is None or mes is None or cons is None:
        raise ValueError("El archivo de consumo debe tener 'Cod Sucursal', 'Mes' y 'Consumo Unid'.")
    est_col = c("ESTADISTICO", "ESTADÍSTICO", "# ESTADIST")
    if est_col:
        est = df[est_col].map(codigo)
    else:
        texto = " ".join(str(v) for v in raw.head(10).values.ravel() if _texto(v))
        m = re.search(r"Estad[ií]stico:.*?(\d{6,})", texto)
        if not m:
            raise ValueError("No encontré el estadístico: agrega una columna 'Estadístico' o usa el export con encabezado.")
        est = int(m.group(1))
    out = pd.DataFrame({"local": df[loc].map(codigo), "estadistico": est,
                        "mes": df[mes].map(_texto).str.slice(0, 7), "consumo": df[cons].map(num)})
    out = out.dropna(subset=["local", "estadistico"])
    out = out[out["mes"].str.match(r"^\d{4}-\d{2}$")]
    out["local"] = out["local"].astype(int)
    out["estadistico"] = out["estadistico"].astype(int)
    return out.reset_index(drop=True)


def consumo_diario(mensual: pd.DataFrame) -> pd.DataFrame:
    """
    Venta diaria por local + estadístico = consumo acumulado ÷ días de los meses del archivo.
    Ej.: octubre 2026 → ÷ 31. Si vienen varios meses, se suman consumos y días.
    """
    import calendar
    if mensual is None or not len(mensual):
        return pd.DataFrame(columns=["local", "estadistico", "consumo", "dias", "venta_diaria", "periodo"])
    m = mensual.groupby(["local", "estadistico", "mes"], as_index=False)["consumo"].sum()
    meses_item = m.groupby("estadistico")["mes"].apply(lambda s: sorted(set(s)))
    dias_item = meses_item.map(lambda ms: sum(calendar.monthrange(int(x[:4]), int(x[5:]))[1] for x in ms))
    periodo = meses_item.map(lambda ms: ", ".join(f"{MESES[int(x[5:])]}-{x[:4]}" for x in ms)
                             + f" ÷ {sum(calendar.monthrange(int(x[:4]), int(x[5:]))[1] for x in ms)} días")
    out = m.groupby(["local", "estadistico"], as_index=False)["consumo"].sum()
    out["dias"] = out["estadistico"].map(dias_item)
    out["venta_diaria"] = out["consumo"].clip(lower=0) / out["dias"]
    out["periodo"] = out["estadistico"].map(periodo)
    return out


# ------------------------------------------------------------------ cálculo


@dataclass
class Parametros:
    dias_max: float = 15.0
    fuente_venta: str = "pronostico"     # "pronostico" | "consumo" | "mensual"
    dias_consumo_acu: float = 3.0       # cuántos días representa CONSUMOS ACU
    redondear_empaque: bool = False
    filtrar_bodega: bool = True         # Módulo 1: solo locales abastecidos por la bodega de salida


def preparar(base: pd.DataFrame, p: Parametros, consumo_mensual: pd.DataFrame | None = None) -> pd.DataFrame:
    b = base.copy()
    por_consumo = b["consumo_acu"] / (p.dias_consumo_acu or 1)
    por_pronostico = b["pronostico"].where(b["pronostico"].notna(), por_consumo)
    b["fuente_venta"] = "Pronóstico BI"
    b.loc[b["pronostico"].isna(), "fuente_venta"] = f"CONSUMOS ACU ÷ {p.dias_consumo_acu:g}"
    if p.fuente_venta == "consumo":
        b["venta_diaria"] = por_consumo
        b["fuente_venta"] = f"CONSUMOS ACU ÷ {p.dias_consumo_acu:g}"
    elif p.fuente_venta == "mensual" and consumo_mensual is not None and len(consumo_mensual):
        # Consumo del mes anterior ÷ días del mes. Los estadísticos que no vienen en el archivo usan el pronóstico.
        diario = consumo_mensual.set_index(["local", "estadistico"])["venta_diaria"]
        cubiertos = set(consumo_mensual["estadistico"])
        etiqueta = consumo_mensual.drop_duplicates("estadistico").set_index("estadistico")["periodo"]
        clave = pd.MultiIndex.from_arrays([b["local"], b["estadistico"]])
        mensual = pd.Series(diario.reindex(clave).values, index=b.index)
        en_archivo = b["estadistico"].isin(cubiertos)
        b["venta_diaria"] = por_pronostico.where(~en_archivo, mensual.fillna(0))   # local sin consumo en el mes = 0
        b.loc[en_archivo, "fuente_venta"] = "Consumo " + b.loc[en_archivo, "estadistico"].map(etiqueta)
    else:
        b["venta_diaria"] = por_pronostico
    b["venta_diaria"] = b["venta_diaria"].fillna(0).clip(lower=0)
    # INV NETO ya considera el tránsito; se suma lo que ya está pedido (ROQ LTC + ROQ PTL)
    b["stock"] = (b["inv_neto"] + b["roq_ltc"].clip(lower=0) + b["roq_ptl"].clip(lower=0)).clip(lower=0)
    b["dias_actuales"] = (b["stock"] / b["venta_diaria"]).where(b["venta_diaria"] > 0)
    b["capacidad"] = (p.dias_max * b["venta_diaria"] - b["stock"]).clip(lower=0).fillna(0).apply(lambda x: int(x + 1e-9))

    def motivo(r):
        if r.venta_diaria <= 0:
            return "SIN VENTA"
        if r.capacidad <= 0:
            return f"YA TIENE {p.dias_max:g}+ DÍAS"
        return ""
    b["motivo_no_recibe"] = [motivo(r) for r in b.itertuples(index=False)]
    return b


def _empaque_item(b_item: pd.DataFrame) -> int:
    e = b_item["empaque"][b_item["empaque"] > 0]
    return int(e.mode().iloc[0]) if len(e) else 1


def nivelar(cantidad: int, cand: pd.DataFrame, asignado_previo: dict, dias_max: float, paso: int = 1) -> dict:
    """
    Reparte `cantidad` en bloques de `paso` unidades dando siempre al local con menos días
    proyectados, sin que ninguno pase de `dias_max`. cand: index=local, cols venta_diaria, stock.
    `asignado_previo` es lo que el local ya recibió (de otro origen/nivel) y cuenta como stock.
    """
    asign: dict[int, int] = {}
    heap = []
    for l, r in cand.iterrows():
        v = r["venta_diaria"]
        if v <= 0:
            continue
        s = r["stock"] + asignado_previo.get(l, 0)
        if (s + paso) / v <= dias_max + 1e-9:
            heapq.heappush(heap, (s / v, -v, l, s, v))
    restante = cantidad
    while heap and restante >= paso:
        d, negv, l, s, v = heapq.heappop(heap)
        asign[l] = asign.get(l, 0) + paso
        restante -= paso
        s += paso
        if (s + paso) / v <= dias_max + 1e-9:
            heapq.heappush(heap, (s / v, negv, l, s, v))
    return asign


@dataclass
class Resultado:
    distribucion: pd.DataFrame          # una fila por traspaso (origen → destino)
    por_item: pd.DataFrame              # resumen por estadístico (y origen en el módulo 2)
    pendientes: pd.DataFrame            # lo que no se pudo asignar
    no_considerados: pd.DataFrame       # locales habilitados que no recibieron y por qué
    resumen: dict = field(default_factory=dict)


def _fila_destino(r, asignado, previo, dias_max):
    v = r.venta_diaria
    stock_final = r.stock + previo + asignado
    return {
        "Local Destino": r.local, "Nombre Destino": r.designacion.title(), "Supervisor Destino": r.supervisor,
        "Gerente Destino": r.gerente, "Venta Diaria": round(v, 3), "Fuente Venta": getattr(r, "fuente_venta", ""),
        "Stock Actual": r.stock,
        "Días Actuales": round(r.stock / v, 1) if v > 0 else None,
        "Cantidad": asignado,
        "Stock Final": stock_final, "Días Finales": round(stock_final / v, 1) if v > 0 else None,
        "Exhibición": r.exhibicion,
    }


def distribuir_cd(base: pd.DataFrame, mover: pd.DataFrame, p: Parametros,
                  consumo_mensual: pd.DataFrame | None = None) -> Resultado:
    b = preparar(base, p, consumo_mensual)
    filas, items, nocons = [], [], []
    for it in mover.itertuples(index=False):
        g, q = it.estadistico, int(it.cantidad)
        bodega = getattr(it, "bodega", None)
        bi = b[b["estadistico"] == g]
        if p.filtrar_bodega and bodega is not None and not pd.isna(bodega) and bi["bodega"].notna().any():
            bi = bi[bi["bodega"] == bodega]
        desc = (bi["descripcion"].iloc[0] if len(bi) else "") or getattr(it, "descripcion_mov", "")
        pack = _empaque_item(bi) if (p.redondear_empaque and len(bi)) else 1
        cand = bi[bi["motivo_no_recibe"] == ""].set_index("local")
        asign = nivelar(q, cand, {}, p.dias_max, pack)
        for l, a in sorted(asign.items(), key=lambda t: -t[1]):
            r = cand.loc[l]
            f = {"Origen": f"CD {int(bodega)}" if bodega is not None and not pd.isna(bodega) else "CD",
                 "Estadístico": g, "Descripción": desc}
            f.update(_fila_destino(_Fila(l, r), a, 0, p.dias_max))
            filas.append(f)
        for r in bi[bi["motivo_no_recibe"] != ""].itertuples(index=False):
            nocons.append({"Estadístico": g, "Descripción": desc, "Local": r.local, "Nombre": r.designacion.title(),
                           "Supervisor": r.supervisor, "Gerente": r.gerente, "Motivo": r.motivo_no_recibe,
                           "Venta Diaria": round(r.venta_diaria, 3), "Fuente Venta": r.fuente_venta, "Stock Actual": r.stock,
                           "Días Actuales": round(r.dias_actuales, 1) if pd.notna(r.dias_actuales) else None})
        asignado = sum(asign.values())
        cap_total = int(cand["capacidad"].sum()) if len(cand) else 0
        recibe = cand.loc[list(asign)] if asign else cand.iloc[0:0]
        dias_fin = ((recibe["stock"] + pd.Series(asign)) / recibe["venta_diaria"]) if asign else pd.Series(dtype=float)
        items.append({
            "Estadístico": g, "Descripción": desc, "Bodega": bodega, "Cantidad a Mover": q,
            "Asignado": asignado, "Sobrante": q - asignado, "% Asignado": asignado / q if q else 0,
            "Locales en Base": len(bi), "Locales Habilitados": len(cand), "Locales que Reciben": len(asign),
            "Capacidad hasta Días Máx": cap_total, "Empaque Usado": pack,
            "Días Finales Mín": round(float(dias_fin.min()), 1) if len(dias_fin) else None,
            "Días Finales Máx": round(float(dias_fin.max()), 1) if len(dias_fin) else None,
            "Observación": _obs_item(len(bi), len(cand), q, asignado, cap_total, pack),
        })
    dist = pd.DataFrame(filas)
    por_item = pd.DataFrame(items)
    pend = por_item[por_item["Sobrante"] > 0][["Estadístico", "Descripción", "Bodega", "Cantidad a Mover", "Asignado",
                                               "Sobrante", "Observación"]].reset_index(drop=True) if len(por_item) else pd.DataFrame()
    res = {
        "items": len(por_item), "und_mover": int(por_item["Cantidad a Mover"].sum()) if len(por_item) else 0,
        "und_asignadas": int(por_item["Asignado"].sum()) if len(por_item) else 0,
        "und_sobrante": int(por_item["Sobrante"].sum()) if len(por_item) else 0,
        "traspasos": len(dist), "locales": int(dist["Local Destino"].nunique()) if len(dist) else 0,
        "dias_max": p.dias_max,
    }
    return Resultado(dist, por_item, pend, pd.DataFrame(nocons), res)


class _Fila:
    """Adaptador: fila de candidatos (indexada por local) con atributos."""
    def __init__(self, local, r):
        self.local = local
        for k, v in r.items():
            setattr(self, k, v)


def _obs_item(en_base, habil, q, asig, cap, pack):
    if en_base == 0:
        return "El estadístico no está en la base de locales"
    if habil == 0:
        return "Ningún local de la base puede recibir (sin venta o ya con los días máx)"
    if asig >= q:
        return "Asignado completo"
    if cap < q:
        return f"Los locales solo pueden recibir {cap} und sin pasar los días máx"
    if pack > 1:
        return f"Queda sobrante por redondeo a empaque de {pack}"
    return "Sobrante sin asignar"


NIVEL_SUP = "1. Mismo supervisor"
NIVEL_GER = "2. Mismo gerente"
NIVEL_MAN = "3. Pendiente manual"


def redistribuir_locales(base: pd.DataFrame, mover: pd.DataFrame, p: Parametros,
                         consumo_mensual: pd.DataFrame | None = None) -> Resultado:
    b = preparar(base, p, consumo_mensual)
    origenes_item = mover.groupby("estadistico")["origen"].apply(set).to_dict()
    resp = maestro_locales(base).set_index("local")
    mov = mover.reset_index(drop=True).copy()
    for col in ("supervisor", "gerente"):
        vacio = mov[col].map(_texto) == ""
        mov.loc[vacio, col] = mov.loc[vacio, "origen"].map(resp[col]).fillna("")
    restante = {i: int(r.cantidad) for i, r in mov.iterrows()}
    asign_nivel = {i: {NIVEL_SUP: 0, NIVEL_GER: 0} for i in mov.index}
    recibido: dict[tuple, int] = {}       # (local, item) -> unidades ya asignadas
    filas = []

    def candidatos(i, nivel):
        r = mov.loc[i]
        g = r.estadistico
        bi = b[(b["estadistico"] == g) & (b["motivo_no_recibe"] == "")]
        bi = bi[~bi["local"].isin(origenes_item.get(g, set()))]
        if nivel == NIVEL_SUP:
            bi = bi[(bi["supervisor"] != "") & (bi["supervisor"] == r.supervisor)] if r.supervisor else bi.iloc[0:0]
        else:
            bi = bi[(bi["gerente"] != "") & (bi["gerente"] == r.gerente) & (bi["supervisor"] != r.supervisor)] if r.gerente else bi.iloc[0:0]
        return bi.set_index("local")

    for nivel in (NIVEL_SUP, NIVEL_GER):
        for i in mov.index:
            if restante[i] <= 0:
                continue
            r = mov.loc[i]
            g = r.estadistico
            cand = candidatos(i, nivel)
            if not len(cand):
                continue
            pack = _empaque_item(b[b["estadistico"] == g]) if p.redondear_empaque else 1
            previo = {l: recibido.get((l, g), 0) for l in cand.index}
            asign = nivelar(restante[i], cand, previo, p.dias_max, pack)
            for l, a in sorted(asign.items(), key=lambda t: -t[1]):
                f = {"Nivel": nivel, "Local Origen": r.origen,
                     "Nombre Origen": str(resp["designacion"].get(r.origen, "")).title() if r.origen in resp.index else "",
                     "Supervisor Origen": r.supervisor, "Gerente Origen": r.gerente,
                     "Estadístico": g, "Descripción": _desc(b, g, r.descripcion_mov)}
                f.update(_fila_destino(_Fila(l, cand.loc[l]), a, previo.get(l, 0), p.dias_max))
                filas.append(f)
                recibido[(l, g)] = recibido.get((l, g), 0) + a
            tot = sum(asign.values())
            restante[i] -= tot
            asign_nivel[i][nivel] += tot

    items, pend = [], []
    for i, r in mov.iterrows():
        g = r.estadistico
        q = int(r.cantidad)
        a1, a2 = asign_nivel[i][NIVEL_SUP], asign_nivel[i][NIVEL_GER]
        falta = restante[i]
        bi_all = b[(b["estadistico"] == g) & (b["motivo_no_recibe"] == "") & ~b["local"].isin(origenes_item.get(g, set()))]
        # sugerencias para asignación manual: otros gerentes con capacidad restante
        sug = ""
        if falta > 0:
            otros = bi_all[bi_all["gerente"] != r.gerente].copy()
            # vectorizado: funciona también cuando no hay locales de otros gerentes (tabla vacía)
            ya = otros["local"].map(lambda l: recibido.get((l, g), 0)).astype(float)
            otros["cap_rest"] = (p.dias_max * otros["venta_diaria"] - otros["stock"] - ya).clip(lower=0).fillna(0).astype(int)
            otros = otros[otros["cap_rest"] > 0].sort_values("cap_rest", ascending=False).head(5)
            sug = ", ".join(f"{int(x.local)} ({x.gerente.split('.')[0].title()}: {int(x.cap_rest)})" for x in otros.itertuples())
        motivo = ""
        if q <= 0:
            motivo = "Cantidad a mover en 0 (INV NETO sin stock)"
        elif not r.supervisor and not r.gerente:
            motivo = "Local de salida sin supervisor ni gerente (no está en la base/maestro)"
        elif falta > 0:
            motivo = (f"Sin capacidad suficiente en locales del mismo supervisor y gerente hasta {p.dias_max:g} días"
                      + (" (o por redondeo a empaque)" if p.redondear_empaque else ""))
        fila = {"Local Origen": r.origen, "Supervisor Origen": r.supervisor, "Gerente Origen": r.gerente,
                "Estadístico": g, "Descripción": _desc(b, g, r.descripcion_mov), "Cantidad a Mover": q,
                NIVEL_SUP: a1, NIVEL_GER: a2, NIVEL_MAN: falta, "% Asignado": (a1 + a2) / q if q else 0,
                "Observación": motivo or "Asignado completo"}
        items.append(fila)
        if falta > 0:
            pend.append({"Local Origen": r.origen, "Supervisor Origen": r.supervisor, "Gerente Origen": r.gerente,
                         "Estadístico": g, "Descripción": fila["Descripción"], "Cantidad a Mover": q,
                         "Asignado": a1 + a2, "Pendiente Manual": falta, "Motivo": motivo,
                         "Sugerencia (otros gerentes · capacidad)": sug or "Sin locales con capacidad"})
    dist = pd.DataFrame(filas)
    por_item = pd.DataFrame(items)
    nocons = []
    for g in mov["estadistico"].unique():
        for r in b[(b["estadistico"] == g) & (b["motivo_no_recibe"] != "")].itertuples(index=False):
            nocons.append({"Estadístico": g, "Descripción": r.descripcion, "Local": r.local, "Nombre": r.designacion.title(),
                           "Supervisor": r.supervisor, "Gerente": r.gerente, "Motivo": r.motivo_no_recibe,
                           "Venta Diaria": round(r.venta_diaria, 3), "Fuente Venta": r.fuente_venta, "Stock Actual": r.stock,
                           "Días Actuales": round(r.dias_actuales, 1) if pd.notna(r.dias_actuales) else None})
    sm = lambda c: int(por_item[c].sum()) if len(por_item) else 0
    res = {"origenes": len(por_item), "und_mover": sm("Cantidad a Mover"), "nivel_sup": sm(NIVEL_SUP),
           "nivel_ger": sm(NIVEL_GER), "pendiente": sm(NIVEL_MAN), "traspasos": len(dist),
           "locales": int(dist["Local Destino"].nunique()) if len(dist) else 0, "dias_max": p.dias_max}
    return Resultado(dist, por_item, pd.DataFrame(pend), pd.DataFrame(nocons), res)


def _desc(b, g, alterna=""):
    d = b.loc[b["estadistico"] == g, "descripcion"]
    return (d.iloc[0] if len(d) and d.iloc[0] else "") or alterna
