# Fase 5 — Análisis

> Estado: **cerrada** (2026-09-22). Cada cifra sale de [`src/analysis.py`](../src/analysis.py),
> que lee solo `data/curated`, lo mismo que el tablero. Las tablas completas están en
> [`reports/analisis/`](../reports/analisis/).

**Definiciones.** *Morosidad* = créditos atrasados / créditos directos. *CAR* (cartera de alto
riesgo) = (atrasados + refinanciados y reestructurados) / directos. *Morosidad ajustada* =
(atrasados + castigos de 12 meses) / (directos + castigos de 12 meses).

## P1 — ¿Cómo evolucionó la calidad de la cartera del sistema?

| Corte | Créditos directos (S/ miles de millones) | Morosidad | CAR |
|---|---|---|---|
| Ene 2015 | 195,6 | 2,58 % | 3,57 % |
| Dic 2019 | 286,1 | 3,02 % | 4,46 % |
| Dic 2021 | 350,0 | 3,77 % | 5,65 % |
| **May 2024 (máximo)** | 351,1 | **4,49 %** | 6,61 % |
| Jul 2026 | 395,9 | 2,85 % | 4,41 % |

La serie tiene cuatro etapas:

1. **2015–2019: deterioro lento.** La morosidad sube de 2,58 % a 3,02 % mientras la cartera
   crece 46 %.
2. **2020: una morosidad contenida por regulación.** Entre febrero y agosto de 2020 la morosidad
   no se mueve (3,09 % → 3,10 %) aunque la cartera crece 13 %: en esos meses se permitió
   reprogramar créditos y suspender el conteo de días de atraso. Cuando termina la suspensión,
   la morosidad salta a 3,75 % en marzo de 2021. La de consumo llega a 6,38 % en diciembre de
   2020, el doble que antes de la pandemia.
3. **2022–mayo 2024: segundo deterioro**, hasta el máximo del periodo (4,49 %). La CAR llega a
   6,62 % en marzo de 2024.
4. **Junio 2024–julio 2026: recuperación.** La morosidad baja 1,64 pp y termina en 2,85 %, cerca
   de su nivel de 2015–2019.

**Los bancos nuevos no explican la caída.** Compartamos, Santander Consumer y Efectiva entraron
al sistema en 2025–2026 como bancos especializados en microempresa y consumo. Sin ellos, la
morosidad de julio de 2026 sería 2,81 % en vez de 2,85 %: el efecto de perímetro está entre
+0,02 y +0,04 pp en todos los meses desde su entrada.

## P2 — ¿Qué tipos de crédito explican los cambios?

El cambio de la morosidad del sistema entre dos cortes se descompone en un **efecto tasa** (la
morosidad de cada tipo cambió) y un **efecto mezcla** (cambió el peso de cada tipo en la cartera).

| Tramo | Δ morosidad | Tasa | Mezcla | Qué lo explica |
|---|---|---|---|---|
| Ene 2015 → Dic 2019 | +0,44 pp | +0,65 | −0,21 | Medianas empresas (+0,24 pp: su morosidad pasa de 5,2 % a 8,0 %) e hipotecario (+0,26 pp: de 1,4 % a 3,0 %) |
| Dic 2019 → Dic 2021 | +0,75 pp | +0,43 | +0,33 | Medianas empresas (+0,66 pp): su peso sube de 14,8 % a 19,5 % de la cartera con una morosidad de 9,5 % |
| Dic 2021 → May 2024 | +0,72 pp | +1,14 | −0,42 | **Consumo** (+0,48 pp: su morosidad pasa de 2,5 % a 4,2 % y su peso de 15,9 % a 20,7 %) |
| May 2024 → Set 2024 | −0,34 pp | −0,29 | −0,04 | Baja generalizada, liderada por consumo (−0,15 pp) |
| Oct 2024 → Jul 2026 | −1,22 pp | −1,27 | +0,05 | Medianas empresas (−0,44 pp: de 16,6 % a 6,8 %), pequeñas empresas (−0,37 pp) y consumo (−0,17 pp) |

El segundo deterioro no fue empresarial: lo llevó el crédito de consumo. La recuperación es casi
toda efecto tasa: los tipos de crédito mejoraron, no cambió la composición de la cartera.

### La ruptura de octubre de 2024

Septiembre → octubre de 2024 se deja fuera de la tabla a propósito: su descomposición (tasa
+0,57, mezcla −0,65) no describe un cambio de riesgo, sino de clasificación. En ese mes entraron en
vigor los nuevos criterios de tipificación de la Res. SBS 2368-2023, y la cartera se reordenó
entre tipos **en un solo mes**:

| Tipo | Participación set-2024 | Participación oct-2024 |
|---|---|---|
| Corporativo | 24,8 % | 30,4 % |
| Grandes empresas | 15,3 % | 10,8 % |
| Medianas empresas | 14,1 % | 4,7 % |
| Pequeñas empresas | 6,0 % | 13,7 % |

La morosidad total casi no cambió, pero la de medianas empresas pasó de 13,4 % a 16,6 % y la de
pequeñas de 9,8 % a 11,7 %, solo por la reclasificación. **Las series por tipo de crédito
empresarial no son comparables antes y después de octubre de 2024.** El tablero marca ese mes.

## P3 — ¿Qué bancos se desvían del sistema? (julio de 2026)

Una brecha solo importa si el banco pesa en el tipo de crédito. Casos con más de 10 % de
participación en el tipo:

| Banco | Tipo | Participación en el tipo | Morosidad | Sistema | Brecha |
|---|---|---|---|---|---|
| Scotiabank | Medianas empresas | 12,7 % | 17,89 % | 6,84 % | **+11,05 pp** |
| Scotiabank | Pequeñas empresas | 11,5 % | 11,76 % | 8,99 % | +2,76 pp |
| Interbank | Grandes empresas | 11,4 % | 3,23 % | 1,90 % | +1,33 pp |
| BCP | Pequeñas empresas | 39,0 % | 10,32 % | 8,99 % | +1,33 pp |
| BBVA | Grandes empresas | 31,1 % | 2,71 % | 1,90 % | +0,80 pp |
| Mibanco | Pequeñas empresas | 22,1 % | 3,87 % | 8,99 % | −5,12 pp |
| BCP | Medianas empresas | 37,0 % | 1,98 % | 6,84 % | −4,86 pp |

Con un 12,7 % de la cartera de medianas empresas, Scotiabank concentra el 33 % de los atrasados
de ese tipo en el sistema. En pequeñas empresas, BCP aporta el 45 % de los atrasados porque tiene
el 39 % de la cartera.

## P4 — ¿Cuánto deterioro no se ve en la morosidad?

Castigar un crédito lo saca del balance, y con él sale de la morosidad. Sumar los castigos de
los últimos 12 meses muestra el deterioro que el indicador tradicional ya no ve.

| Corte | Morosidad | Castigos 12 m (S/ miles de millones) | Morosidad ajustada | Brecha |
|---|---|---|---|---|
| Dic 2016 | 2,80 % | 3,9 | 4,37 % | 1,57 pp |
| Dic 2019 | 3,02 % | 4,4 | 4,50 % | 1,48 pp |
| Dic 2021 | 3,77 % | 7,2 | 5,71 % | 1,94 pp |
| May 2024 | 4,49 % | 10,2 | 7,19 % | 2,70 pp |
| **Nov 2024 (brecha máxima)** | 3,92 % | **11,0** | 6,83 % | **2,92 pp** |
| Jul 2026 | 2,85 % | 7,1 | 4,57 % | 1,72 pp |

- **La brecha se duplicó** entre 2019 y fines de 2024: los bancos castigaron cerca de
  S/ 11 000 millones en los 12 meses a noviembre de 2024, 2,5 veces lo de 2019.
- **La recuperación es real, no un efecto de los castigos.** Entre mayo de 2024 y julio de 2026
  la morosidad ajustada cae 2,62 pp, más que la tradicional (1,64 pp).

La serie ajustada empieza en diciembre de 2016, porque en 2015 la SBS publicaba los castigos por
trimestre y no por mes (ver [Fase 2](02_calidad.md)).

## P5 — ¿Cómo se mueve con el contexto macroeconómico?

Se correlaciona la **variación de 12 meses de la morosidad** con variables del BCRP adelantadas
varios meses. Se excluye abril 2020 – diciembre 2021, cuando la regulación de emergencia
desconectó la morosidad del ciclo.

| Variable del BCRP | Sin rezago | 6 meses antes | 12 meses antes | 18 meses antes |
|---|---|---|---|---|
| Tasa de referencia (variación 12 m) | 0,32 | 0,59 | **0,71** | 0,47 |
| Inflación (variación 12 m) | −0,20 | 0,28 | 0,69 | **0,80** |
| PBI (variación 12 m) | −0,21 | −0,25 | 0,09 | 0,15 |

La morosidad sube entre 12 y 18 meses después de que suben la tasa de referencia y la
inflación. Es coherente con el ciclo 2021–2024: la inflación llegó a 8,81 % en junio de 2022, la
tasa de referencia subió de 0,25 % a 7,75 % entre 2021 y enero de 2023, y la morosidad hizo su
máximo en mayo de 2024.

**Límites de esta lectura.** Son correlaciones, no efectos causales. Las variaciones de 12 meses
se solapan, así que las observaciones no son independientes y el valor real de la muestra (unas
90) es menor de lo que parece. Además, el periodo tiene un solo ciclo completo de tasas. Sirve
como señal de alerta temprana, no como modelo de pronóstico.
