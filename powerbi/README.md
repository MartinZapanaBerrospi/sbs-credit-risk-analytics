# Tablero de Power BI (PBIP)

El informe se guarda como **Power BI Project**: el modelo en TMDL y el informe en PBIR (JSON),
todo en texto. Se puede leer y revisar en GitHub sin abrir Power BI.

## Cómo abrirlo

1. Clona el repositorio. Los datos que lee el tablero (`data/curated/*.csv`) vienen incluidos:
   no hace falta ejecutar el pipeline.
2. Abre `sbs_credit_risk.pbip` con **Power BI Desktop** (se construyó con la versión 2.157; necesita soporte para el formato de informe PBIR).
3. Si clonaste en otra carpeta, ve a *Inicio → Transformar datos → Editar parámetros* y cambia
   **`RutaDatos`** por la ruta de tu copia de `data/curated/`, con la barra final.
4. *Inicio → Actualizar*. El repositorio no guarda la caché de datos (`.pbi/cache.abf`), así que
   el primer refresco es obligatorio.

## Qué hay en cada carpeta

```
powerbi/
├── sbs_credit_risk.pbip                    # Lo que se abre en Power BI Desktop
├── sbs_credit_risk.SemanticModel/
│   └── definition/
│       ├── model.tmdl                      # Cultura, opciones y orden de consultas
│       ├── expressions.tmdl                # Parámetro RutaDatos
│       ├── relationships.tmdl              # 14 relaciones
│       └── tables/                         # 3 dimensiones, 6 hechos y _Medidas (28 medidas DAX)
└── sbs_credit_risk.Report/
    ├── definition/pages/                   # 6 páginas, un visual por carpeta
    └── StaticResources/RegisteredResources/SBS_Risk.json   # Tema: paleta y tipografía
```

## Páginas

| Página | Pregunta |
|---|---|
| 1. Sistema | ¿Cómo evolucionaron la morosidad y la CAR entre 2015 y 2026? |
| 2. Tipos de crédito | ¿Qué tipos de crédito explican los cambios? |
| 3. Bancos | ¿Qué bancos se desvían del sistema, y cuánto pesan? (con segmentadores de mes y tipo) |
| 4. Mora oculta | ¿Cuánto deterioro dejan de mostrar los castigos? |
| 5. Contexto macro | ¿Cómo se mueve la morosidad frente a la tasa de referencia y la inflación? |
| 6. Notas | Definiciones, fuentes, rupturas de serie y validaciones |

Las decisiones del modelo y de las medidas están en [docs/04_modelado.md](../docs/04_modelado.md).
