# SBS Credit Risk Analytics

[![Datos: SBS](https://img.shields.io/badge/Datos-SBS%20Per%C3%BA-00457C)](https://www.sbs.gob.pe/app/stats_net/stats/estadisticaboletinestadistico.aspx?p=1)
[![Datos: BCRP](https://img.shields.io/badge/Datos-BCRPData-8C1D18)](https://estadisticas.bcrp.gob.pe/estadisticas/series/)
[![Power BI](https://img.shields.io/badge/Power%20BI-PBIP%20%2B%20TMDL-F2C811?logo=powerbi&logoColor=black)](https://learn.microsoft.com/power-bi/developer/projects/projects-overview)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

Análisis de la **calidad de la cartera de créditos de la banca múltiple peruana** entre enero
de 2015 y julio de 2026, construido de punta a punta con **datos públicos reales** de la
Superintendencia de Banca, Seguros y AFP (SBS) y del Banco Central de Reserva del Perú (BCRP):
desde la descarga de los archivos oficiales hasta un tablero en Power BI.

> **Estado:** Fase 0 cerrada. El repositorio documenta cada fase a medida que se completa.

## La pregunta

¿Cómo evolucionó la calidad de la cartera de la banca múltiple, qué tipos de crédito y qué
bancos explican sus cambios, y cuánto de ese deterioro no se ve en el indicador de morosidad
tradicional?

El detalle de las preguntas, los indicadores, el alcance y el reconocimiento de las fuentes
está en [docs/00_definicion.md](docs/00_definicion.md).

## Fases

| Fase | Qué se hace | Estado |
|---|---|---|
| 0. Definición | Problema, KPIs, alcance y verificación de las fuentes | ✅ [docs/00_definicion.md](docs/00_definicion.md) |
| 1. Adquisición | Descarga reproducible de 5 cuadros SBS × 139 meses y 4 series del BCRP | ⏳ |
| 2. Calidad | Perfilado, cambios de formato y diccionario de datos | ⏳ |
| 3. Transformación | raw → staging → curated, identidad estable de entidades | ⏳ |
| 4. Modelado | Modelo en estrella y medidas DAX (TMDL) | ⏳ |
| 5. Análisis | Respuestas cuantificadas a las preguntas P1–P5 | ⏳ |
| 6. Tablero | Power BI (PBIP) con capturas de cada página | ⏳ |
| 7. Hallazgos | Conclusiones y limitaciones | ⏳ |
| 8. Automatización | Pruebas y GitHub Actions | ⏳ |

## Fuentes

| Fuente | Qué aporta |
|---|---|
| SBS — Boletín estadístico de Banca Múltiple | Créditos por situación, castigos, deudores y ratios de morosidad por entidad y tipo de crédito |
| BCRP — BCRPData | Tasa de referencia, inflación, tipo de cambio y PBI |

Los datos son información pública de ambas instituciones. Cada visual del tablero indica su fuente.

## Licencia

Código bajo licencia [MIT](LICENSE). Los datos pertenecen a sus fuentes oficiales.
