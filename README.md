# Distribución por Días de Inventario

App en Streamlit con dos módulos para repartir inventario sin que ningún local supere los **días máximos de
inventario** que definas.

## Módulo 1 · Distribución CD a Locales (Próximos a Vencer)
Reparte las unidades que salen de una bodega entre los locales donde el producto está habilitado.

## Módulo 2 · Redistribución entre locales
Mueve el inventario de un local de salida a otros locales con esta prioridad:
1. Locales del **mismo supervisor**.
2. Locales del **mismo gerente**.
3. Lo que no cabe queda **pendiente de asignación manual**, con sugerencias de locales de otros gerentes con capacidad.

## Cómo decide
| Concepto | Cálculo |
|---|---|
| Venta diaria | A elegir: **consumo del mes anterior** (export del BI con `Cod Sucursal`, `Mes`, `Consumo Unid`) ÷ días de ese mes — p. ej. octubre ÷ 31; **pronóstico diario** del BI (promedio de las columnas de fecha); o `CONSUMOS ACU ÷ días`. Si un estadístico no tiene dato en la fuente elegida, se usa el pronóstico. |
| Stock actual | `INV NETO + ROQ_LTC + ROQ_PTL` (INV NETO ya incluye el tránsito) |
| Capacidad | `días máx × venta diaria − stock actual` |
| Reparto | **Nivelación**: se entrega de a una unidad (o un `EMPAQUE`, si se activa el redondeo) al local con menos días de inventario, hasta repartir todo o hasta que todos lleguen a los días máximos. |

La base ya viene filtrada con los locales habilitados, así que no se aplican exclusiones adicionales. No reciben:
locales **sin venta** y los que ya tienen los días máximos cubiertos. En el módulo 2 tampoco recibe un local que sea origen del mismo estadístico.

## Archivos de entrada
| Archivo | Columnas |
|---|---|
| Base de locales habilitados (BI) | `GERENTE`, `SUPERV.`, `BODEGA`, `# Local`, `DESIGNACION`, `ESTADISTICO`, `DESCRIPCION`, `CONSUMOS ACU`, `INV NETO`, `ROQ_LTC`, `ROQ_PTL`, `Uni Exhibición`, `EMPAQUE` y columnas de pronóstico por fecha (`04/NOV/2026`…) |
| Módulo 1 · Inventario a mover | `BODEGA`, `# ESTADIST` (o `Estadístico`), cantidad en `FISICO_WH` (o `Cantidad`) |
| Módulo 2 · Inventario a mover | `# Local` (o `Local de salida`), `ESTADISTICO`, cantidad en `Cantidad` o, si no existe, `INV NETO`; opcional `SUPERV.` y `GERENTE` |
| Consumo del mes anterior (opcional) | Export del BI: `Cod Sucursal`, `Mes` (`2026-10`), `Consumo Unid`; el estadístico se lee del encabezado del reporte o de una columna `Estadístico`. Se pueden subir varios archivos. Un local que no aparece en el mes cuenta con venta 0. |
| Maestro de locales (opcional) | `# Local`, `SUPERV.`, `GERENTE`, `DESIGNACION` |

### Plantillas
Cada módulo tiene el botón **📄 Descargar plantilla para llenar** debajo del cargador del inventario a mover:

| Plantilla | Columnas (rojas = obligatorias, grises = opcionales) |
|---|---|
| `PLANTILLA_DISTRIBUCION_CD.xlsx` | **Estadístico**, Descripción, **Bodega de salida**, **Cantidad** |
| `PLANTILLA_REDISTRIBUCION_LOCALES.xlsx` | **Estadístico**, Descripción, **Local de salida**, **Cantidad**, Supervisor, Gerente |

Cada plantilla trae las hojas PLANTILLA (la que se llena y se lee), EJEMPLO e INSTRUCCIONES. Si Supervisor y
Gerente quedan vacíos, se completan con el local de salida.

Acepta xlsx, xls, xlsb y csv (separador `,` o `;`). El inventario a mover también se puede **digitar o pegar** en la
app; en el módulo 2, al escribir el local de salida se completan el supervisor y el gerente.

## Resultado
Gráficos en la app y Excel descargable con: **RESUMEN** (indicadores y gráficos), **DISTRIBUCIÓN** (lista para grabar),
**SOBRANTE** / **PENDIENTE MANUAL** y **LOCALES NO CONSIDERADOS** (con el motivo).

## Ejecutar
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Pruebas
```bash
pip install pytest
python -m pytest
```

## Estructura
```
app.py            interfaz (dos módulos)
distribucion.py   lectura de archivos y lógica de reparto
exportar.py       Excel de resultados con gráficos
plantillas.py     plantillas descargables para ingresar el inventario a mover
estilo.py         estilo visual compartido
portal.py         menú "Mis apps"
tests/            pruebas con datos de ejemplo
```
