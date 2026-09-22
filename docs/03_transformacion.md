# Fase 3 — Transformación

> Estado: **cerrada** (2026-09-22).

```bash
python -m src.transform   # raw → staging → curated
python -m src.validate    # compara lo procesado con las cifras oficiales
```

## Capas

| Capa | Qué contiene | Formato | ¿Se versiona? |
|---|---|---|---|
| `data/raw` | Archivos oficiales sin tocar + manifiesto | xls / xlsx / json | Solo el manifiesto |
| `data/staging` | Una tabla larga por cuadro: `periodo`, `entidad_raw`, `entidad_id`, concepto, valor, `es_total` | Parquet | No |
| `data/curated` | Modelo en estrella para Power BI | CSV (UTF-8, punto decimal) | **Sí** |

Staging conserva todo lo publicado, incluidas las filas de total y los flujos trimestrales, para
poder validar. Las reglas de negocio se aplican al pasar a curated.

## Reglas de staging → curated

1. **Sin totales en los hechos.** Las filas "TOTAL BANCA MÚLTIPLE" y la columna "Total créditos
   directos" solo sirven para validar. Los totales se recalculan en Power BI sumando bancos.
2. **Consumo en una sola fila.** Revolvente y no revolvente se suman.
3. **Filas sin saldo fuera.** Una combinación banco × tipo × mes con créditos directos = 0 no se
   guarda. Deudores y ratios vacíos tampoco.
4. **Un solo perímetro.** Castigos, deudores y ratios por días solo se guardan para una entidad
   en los meses en que tiene cartera en B-2334 (hallazgo C1 de la [Fase 2](02_calidad.md)). Así
   queda fuera, por ejemplo, Deutsche Bank, que figura en los cuadros con saldo cero. De castigos
   se usan solo los flujos mensuales (sin los trimestrales de 2015).
5. **Lo no aditivo, aparte.** El total de deudores del sistema y los ratios publicados por la SBS
   van a `fact_sistema_publicado`, porque no se pueden obtener sumando bancos. El total de
   deudores de cada banco tampoco se guarda: cuenta una sola vez al deudor que tiene créditos de
   varios tipos, así que no es la suma de los tipos.
6. **Fecha de fin de mes** en todas las tablas de hechos, para relacionarlas con `dim_fecha`.

## Diccionario de datos (`data/curated`)

Montos en **miles de soles**. Las fechas son el último día del mes.

### Hechos

| Tabla | Grano | Columnas |
|---|---|---|
| `fact_cartera` | mes × banco × tipo de crédito | `vigentes`, `refinanciados_reestructurados`, `atrasados`, `directos` (suma de las tres) |
| `fact_castigos` | mes × banco × tipo de crédito | `castigos`: flujo de créditos retirados del balance en el mes |
| `fact_deudores` | mes × banco × tipo de crédito | `deudores`: deudores con crédito directo en ese banco |
| `fact_morosidad_dias` | mes × banco | `mora_30d`, `mora_60d`, `mora_90d`, `mora_120d` (% de créditos con más de N días de atraso), `morosidad_contable` (%) |
| `fact_sistema_publicado` | mes × métrica × tipo de crédito | `valor`. Métricas: `deudores` (consolidado del sistema), `mora_30d` … `mora_120d`, `morosidad_contable`, `morosidad_publicada` (B-2362) |
| `fact_macro` | mes | `tasa_referencia` (%), `inflacion_12m` (%), `tipo_cambio` (S/ por US$), `pbi_indice` (2007 = 100), `pbi_var_12m` (%) |

### Dimensiones

| Tabla | Clave | Columnas |
|---|---|---|
| `dim_fecha` | `fecha` | `anio`, `mes`, `mes_nombre`, `periodo_etiqueta`, `trimestre`, `hito` (ruptura regulatoria o de perímetro de ese mes) |
| `dim_entidad` | `entidad_id` | `entidad`, `activa`, `primer_periodo` y `ultimo_periodo` con cartera, `tipo_predominante` y su `participacion_tipo_predominante` en el último mes, `evento` (resoluciones SBS) |
| `dim_tipo_credito` | `tipo_credito` | `tipo_credito_nombre`, `segmento` (Mayorista, MYPE, Personas), `orden` |

## Tamaño

| Tabla | Filas |
|---|---|
| fact_cartera | 11 599 |
| fact_deudores | 11 595 |
| fact_castigos | 4 327 |
| fact_sistema_publicado | 2 906 |
| fact_morosidad_dias | 1 983 |
| fact_macro, dim_fecha | 139 |
| dim_entidad | 21 |
| dim_tipo_credito | 7 |
