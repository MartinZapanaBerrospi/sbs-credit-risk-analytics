# Fase 1 — Adquisición

> Estado: **cerrada** (2026-09-22).

## Qué se descarga

| Fuente | Qué | Cantidad | Destino |
|---|---|---|---|
| SBS | 5 cuadros del boletín de Banca Múltiple × 139 meses (2015-01 a 2026-07) | 687 archivos (31 MB) | `data/raw/sbs/{cuadro}/{cuadro}_{AAAA-MM}.xls` |
| BCRP | 4 series mensuales vía BCRPData | 4 JSON | `data/raw/bcrp/{serie}.json` |

Los 8 archivos que faltan son los meses sin cierre trimestral de 2015 del cuadro de castigos
(B-2369). La SBS publicaba ese cuadro solo por trimestre, y el servidor responde 404; quedan en el
manifiesto con estado `no_publicado`.

## Cómo se ejecuta

```bash
pip install -r requirements.txt
python -m src.extract          # descarga solo lo que falta
python -m src.extract --force  # vuelve a bajar todo
```

- **Idempotente.** Un archivo ya descargado no se vuelve a pedir, y un mes que respondió 404 no
  se reintenta. Las series del BCRP sí se bajan siempre, porque el BCRP las revisa (el PBI, por
  ejemplo).
- **Cortés con la fuente.** Hace una pausa de 0,2 s entre peticiones, identifica el proyecto en
  el `User-Agent` y reintenta con espera creciente ante errores de red.
- **Sin evadir controles.** El portal de consulta de la SBS tiene un desafío antibots, pero no se
  usa: los enlaces del portal apuntan a archivos estáticos públicos en `intranet2.sbs.gob.pe`, y
  esos son los que se descargan.

## Manifiesto

`data/raw/manifest.csv` es el único archivo de `data/raw` que se versiona. Tiene una fila por
archivo:

| Campo | Para qué sirve |
|---|---|
| `fuente`, `cuadro`, `periodo`, `url` | Trazabilidad hasta el archivo oficial |
| `estado` | `ok` o `no_publicado` |
| `formato` | Formato **real**, detectado por la firma de los primeros bytes (`xls`, `xlsx`, `json`) |
| `bytes`, `sha256` | Detectar si la SBS corrige un archivo ya publicado: el hash cambiaría |
| `descargado_en` | Fecha y hora UTC de la descarga |

## Lo que la descarga ya reveló

Todos los archivos terminan en `.XLS`, pero **38 de 687 son en realidad xlsx** (zip). Por
ejemplo, 26 de los 131 archivos de castigos son xlsx. Por eso el formato se detecta por
contenido y no por extensión.

Además, **18 archivos de deudores (B-230803)** hacen fallar a `xlrd`, el lector habitual de
`.xls`, con un `UnicodeDecodeError` en un bloque interno de referencias externas. El proyecto usa **`python-calamine`** como lector único: abre xls y
xlsx por igual y leyó sin errores los 687 archivos. El detalle está en la
[Fase 2](02_calidad.md).
