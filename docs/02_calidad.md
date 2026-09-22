# Fase 2 — Calidad de los datos

> Estado: **cerrada** (2026-09-22). Todo lo que sigue se midió sobre los 687 archivos
> descargados en la [Fase 1](01_adquisicion.md).

Los cuadros de la SBS son hojas de Excel pensadas para leerse, no para procesarse. Esta fase
revisó los 5 cuadros × 139 meses para encontrar todo lo que cambia entre archivos antes de
escribir el pipeline. Cada problema tiene una decisión, y cada decisión quedó implementada en
[`src/parse_sbs.py`](../src/parse_sbs.py) o [`src/transform.py`](../src/transform.py).

## 1. Estructura de los archivos

| # | Hallazgo | Evidencia | Decisión |
|---|---|---|---|
| E1 | La extensión `.XLS` no indica el formato | 38 de 687 archivos son xlsx (zip) | Detectar el formato por la firma de los primeros bytes |
| E2 | `xlrd` no puede abrir algunos `.xls` | 18 archivos de B-230803 dan `UnicodeDecodeError` | Usar `python-calamine`, que abre los 687 |
| E3 | El encabezado cambia de fila | B-2362 lo tiene en la fila 5 en 136 meses y en la fila 4 en 3 meses | Buscar el encabezado por su texto ("Empresas" / "Concepto") |
| E4 | El encabezado cambia de columna | En B-230803 de 2015-01 a 2015-10 hay una columna extra de códigos internos a la izquierda | Buscar el texto en las 3 primeras columnas y leer a su derecha |
| E5 | Encabezados en varias filas con celdas combinadas | B-2334 combina el tipo de crédito (fila 1) con la situación (fila 3) | Propagar el tipo hacia la derecha y combinar ambas filas |
| E6 | Consumo viene partido | En B-2334, consumo tiene 6 columnas (revolvente y no revolvente × 3 situaciones) | Ambas mitades quedan como "consumo" y se suman |
| E7 | La fila de total cambia de significado | En B-2362, de 2020-01 a 2021-01 la última fila es el **saldo en miles de S/**, no la morosidad | Descartar esa fila: esos 13 meses no tienen morosidad total publicada en B-2362 |
| E8 | El flujo de castigos es trimestral en 2015 | Los 4 archivos de 2015 dicen "Flujo Trimestral de castigos" | Marcar `flujo_trimestral` y excluirlos de la serie mensual |
| E9 | Notas y llamadas mezcladas con los datos | Filas de notas bajo el total; nombres con `*`, `**`, `1/` | Las entidades son las filas hasta "TOTAL BANCA MÚLTIPLE"; limpiar las llamadas del nombre |
| E10 | Nulos codificados | `-` significa "no aplica" | Se lee como vacío, no como cero |

## 2. Entidades

La SBS publica **32 nombres de banco distintos** (más la fila de total) que corresponden a
**22 bancos**. La tabla
[`data/reference/entidades.csv`](../data/reference/entidades.csv) asigna cada nombre a un id
estable y cita la resolución SBS que explica el cambio, tomada de las notas al pie de los propios
cuadros.

| Tipo de cambio | Casos |
|---|---|
| Cambio de denominación | B. Continental → BBVA (2019-06), B. Financiero → Pichincha (2018-08), B. Azteca → Alfin (2021-11), B. de Comercio → BANCOM (2023-09) |
| Variantes de escritura | "Scotiabank Perú (consucursales en el exterior)", "BCI Perú" / "B. BCI Perú" / "Banco BCI Perú", "B. Efectiva" / "Banco Efectiva" |
| Salidas | Deutsche Bank (liquidación, 2016-06), B. Cencosud (pasa a Caja CAT, 2019-02) |
| Entradas | Bank of China (2020-07), BCI (2022-07), Compartamos (2025-01), Santander Consumer (2025-06), Efectiva (2026-06) |

El número de bancos con cartera varía entre **15 y 20** según el mes. Deutsche Bank aparece en
los cuadros, pero con saldo cero en todos sus meses, así que no entra al modelo.

**Efecto composición.** Compartamos y Santander Consumer eran financieras especializadas en
microempresa y consumo. Su entrada en 2025 cambia el sistema "banca múltiple" por perímetro, no
por comportamiento. El análisis lo separa (ver [Fase 5](05_analisis.md)).

## 3. Consistencia entre cuadros

| # | Hallazgo | Decisión |
|---|---|---|
| C1 | Los archivos de castigos de 2024 ya incluyen a Compartamos y Santander Consumer, que ese año todavía no eran bancos. La SBS los republicó con el perímetro de 2025 | Solo se usan castigos de una entidad en los meses en que esa entidad tiene cartera en B-2334 |
| C2 | El total de deudores del sistema **no es la suma** de los bancos: la SBS cuenta una sola vez al deudor con créditos en varios bancos | El total publicado va a `fact_sistema_publicado` y el modelo lo usa cuando no hay filtro de banco |
| C3 | En abril de 2024, en Pichincha, la suma por tipo no coincide con el total (−1,01 %) | Nota SBS: un deudor no minorista quedó registrado como microempresa y la SBS usó la cifra de marzo en ese tipo. Se conserva tal como se publicó |
| C4 | En 2 meses, la morosidad de B-220512 no coincide con la de B-2334 y B-2362 | B-220512 sale del Reporte N° 14 y los otros dos del Balance de Comprobación. El proyecto calcula desde B-2334 |
| C5 | En B-230803, la columna de consumo tiene debajo el rótulo "Revolventes" | Se interpreta como todo el consumo: su magnitud (6,6 de 8,0 millones de deudores en 2026-07) no es compatible con solo tarjetas. Queda anotado como supuesto |

## 4. Valores

- **Negativos.** Hay 5 en toda la base: −S/ 3 mil en la cartera refinanciada de BBVA
  (2024-09, ajuste de redondeo) y 4 flujos de castigo negativos (probables reversiones). Se
  conservan como se publicaron.
- **Rupturas de serie** que el tablero marca como hitos en `dim_fecha`:
  - **Abril–agosto de 2020.** Se permitió reprogramar créditos al día y suspender el conteo de
    días de atraso. La morosidad de esos meses está contenida por regulación.
  - **Octubre de 2024.** La Res. SBS 2368-2023 cambió los criterios de tipificación de los
    créditos empresariales. La serie por tipo de crédito no es comparable antes y después.
  - **Diciembre de 2017.** BanBif reclasificó su cartera no minorista por tipo de crédito.

## 5. Validaciones automáticas

[`src/validate.py`](../src/validate.py) reconstruye cifras oficiales desde los datos procesados y
escribe [`reports/validaciones.csv`](../reports/validaciones.csv). Si alguna regla falla sin una
excepción documentada, el pipeline se detiene.

| Regla | Qué comprueba | Comparaciones | Resultado |
|---|---|---|---|
| V1 | Suma de bancos = total publicado en B-2334 | 3 058 | ✅ desvío máximo 0,0012 % |
| V2 | Suma por tipo = total de la entidad en B-2334 | 2 449 | ✅ 2 excepciones explicadas (C3) |
| V3 | Suma de bancos = total publicado en castigos | 908 | ✅ |
| V4 | Morosidad del sistema calculada = B-220512 | 139 | ✅ 2 excepciones explicadas (C4) |
| V5 | Morosidad por tipo calculada = B-2362 | 1 099 | ✅ desvío máximo 0,0085 pp |
| V6 | Todos los nombres de entidad tienen id | 33 | ✅ |
| V7 | La cartera tiene los 139 meses | 1 | ✅ |

V5 es la prueba más fuerte: los montos de B-2334, reordenados por el pipeline, reproducen la
morosidad que la SBS publica en otro cuadro para cada tipo de crédito y cada mes.
