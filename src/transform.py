"""Fase 3 — raw → staging → curated.

staging: una tabla larga por cuadro, tal como la publicó la SBS, con el id de entidad resuelto.
curated: hechos y dimensiones del modelo en estrella que lee Power BI.

Uso:
    python -m src.transform
"""

import json

import numpy as np
import pandas as pd

from src import config
from src.parse_sbs import TOTAL_LABEL, parse_table

REFERENCE = config.DATA / "reference"

CREDIT_TYPE_DIM = pd.DataFrame(
    [
        ("corporativo", "Corporativo", "Mayorista", 1),
        ("grandes_empresas", "Grandes empresas", "Mayorista", 2),
        ("medianas_empresas", "Medianas empresas", "Mayorista", 3),
        ("pequenas_empresas", "Pequeñas empresas", "MYPE", 4),
        ("microempresas", "Microempresas", "MYPE", 5),
        ("consumo", "Consumo", "Personas", 6),
        ("hipotecario", "Hipotecario", "Personas", 7),
    ],
    columns=["tipo_credito", "tipo_credito_nombre", "segmento", "orden"],
)

# Hitos regulatorios que cambian la lectura de las series (fuente: notas al pie de la SBS)
MILESTONES = {
    "2020-04": "COVID-19: reprogramaciones y suspensión del conteo de días de atraso (abr–ago 2020)",
    "2024-10": "Res. SBS 2368-2023: nuevos criterios de tipificación de créditos empresariales",
    "2025-01": "Compartamos Financiera se convierte en banco y entra al sistema",
    "2025-06": "Santander Consumer se convierte en banco y entra al sistema",
}

BCRP_MONTHS = {"Ene": 1, "Feb": 2, "Mar": 3, "Abr": 4, "May": 5, "Jun": 6,
               "Jul": 7, "Ago": 8, "Sep": 9, "Set": 9, "Oct": 10, "Nov": 11, "Dic": 12}


def month_end(period: pd.Series) -> pd.Series:
    return pd.PeriodIndex(period, freq="M").to_timestamp(how="end").normalize()


def map_entities(df: pd.DataFrame, aliases: dict) -> pd.DataFrame:
    unknown = sorted(set(df["entidad_raw"]) - set(aliases))
    if unknown:
        raise ValueError(f"Entidades sin mapear en data/reference/entidades.csv: {unknown}")
    return df.assign(entidad_id=df["entidad_raw"].map(aliases))


def build_staging() -> dict[str, pd.DataFrame]:
    ref = pd.read_csv(REFERENCE / "entidades.csv")
    aliases = dict(zip(ref["alias"], ref["entidad_id"]))
    staging = {}
    for code in config.SBS_TABLES:
        df = map_entities(parse_table(code, config.RAW / "sbs"), aliases)
        staging[code] = df
    config.STAGING.mkdir(parents=True, exist_ok=True)
    for code, df in staging.items():
        df.to_parquet(config.STAGING / f"{code}.parquet", index=False)
    return staging


def build_macro() -> pd.DataFrame:
    frames = []
    for code, name in config.BCRP_SERIES.items():
        payload = json.loads((config.RAW / "bcrp" / f"{code}.json").read_text(encoding="utf-8"))
        rows = []
        for p in payload["periods"]:
            month, year = p["name"].split(".")
            value = p["values"][0]
            rows.append((f"{year}-{BCRP_MONTHS[month]:02d}", pd.to_numeric(value, errors="coerce")))
        frames.append(pd.DataFrame(rows, columns=["periodo", name]).set_index("periodo"))
    macro = pd.concat(frames, axis=1).sort_index().reset_index()
    macro["pbi_var_12m"] = (macro["pbi_indice"] / macro["pbi_indice"].shift(12) - 1) * 100
    return macro


def build_curated(staging: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    out = {}

    # --- fact_cartera: montos por situación, sin la fila de total ni el tipo "total" ------------
    b2334 = staging["B-2334"]
    cartera = (
        b2334[(~b2334["es_total"]) & (b2334["tipo_credito"] != "total")]
        .pivot_table(index=["periodo", "entidad_id", "tipo_credito"], columns="situacion",
                     values="monto", aggfunc="sum")
        .reset_index()
    )
    cartera.columns.name = None
    for col in ["vigentes", "refinanciados_reestructurados", "atrasados"]:
        cartera[col] = cartera[col].fillna(0.0)
    cartera["directos"] = cartera[["vigentes", "refinanciados_reestructurados", "atrasados"]].sum(axis=1)
    # Una fila sin saldo no aporta nada al modelo
    cartera = cartera[cartera["directos"] != 0]
    out["fact_cartera"] = cartera

    perimeter = set(zip(cartera["periodo"], cartera["entidad_id"]))

    # --- fact_castigos: flujo mensual, dentro del perímetro de la cartera del mismo mes ----------
    b2369 = staging["B-2369"]
    castigos = b2369[(~b2369["es_total"]) & (b2369["tipo_credito"] != "total") & (~b2369["flujo_trimestral"])]
    in_perimeter = [(p, e) in perimeter for p, e in zip(castigos["periodo"], castigos["entidad_id"])]
    castigos = castigos[in_perimeter]
    castigos = castigos[castigos["monto"].fillna(0) != 0]
    out["fact_castigos"] = castigos[["periodo", "entidad_id", "tipo_credito", "monto"]].rename(
        columns={"monto": "castigos"})

    # --- fact_deudores: por banco y tipo. Los totales están consolidados (un deudor con varios
    # tipos cuenta una vez), así que no son la suma de los tipos: el del sistema va a
    # fact_sistema_publicado y el de cada banco no se usa.
    b230803 = staging["B-230803"]
    deudores = b230803[(~b230803["es_total"]) & (b230803["tipo_credito"] != "total")
                       & (b230803["deudores"].fillna(0) > 0)]
    deudores = deudores[[(p, e) in perimeter for p, e in zip(deudores["periodo"], deudores["entidad_id"])]]
    out["fact_deudores"] = deudores[["periodo", "entidad_id", "tipo_credito", "deudores"]]

    # --- fact_morosidad_dias: % por banco ------------------------------------------------------
    b220512 = staging["B-220512"]
    in_perimeter = np.array([(p, e) in perimeter for p, e in zip(b220512["periodo"], b220512["entidad_id"])])
    dias = (
        b220512[(~b220512["es_total"]) & in_perimeter]
        .pivot_table(index=["periodo", "entidad_id"], columns="metrica", values="valor", aggfunc="first")
        .reset_index()
    )
    dias.columns.name = None
    out["fact_morosidad_dias"] = dias

    # --- fact_sistema_publicado: cifras no aditivas que la SBS publica para el total -----------
    b2362 = staging["B-2362"]
    sistema = pd.concat([
        b230803[b230803["es_total"]].assign(metrica="deudores")[["periodo", "metrica", "tipo_credito", "deudores"]]
        .rename(columns={"deudores": "valor"}),
        b220512[b220512["es_total"]].assign(tipo_credito="total")[["periodo", "metrica", "tipo_credito", "valor"]],
        b2362[b2362["es_total"]].assign(metrica="morosidad_publicada")[["periodo", "metrica", "tipo_credito", "morosidad_pct"]]
        .rename(columns={"morosidad_pct": "valor"}),
    ], ignore_index=True)
    out["fact_sistema_publicado"] = sistema.dropna(subset=["valor"])

    # --- fact_macro ------------------------------------------------------------------------------
    periods = [f"{y}-{m:02d}" for y, m in config.periods()]
    out["fact_macro"] = build_macro().query("periodo in @periods")

    # --- dim_fecha -------------------------------------------------------------------------------
    fecha = pd.DataFrame({"periodo": periods})
    fecha["fecha"] = month_end(fecha["periodo"])
    fecha["anio"] = fecha["fecha"].dt.year
    fecha["mes"] = fecha["fecha"].dt.month
    fecha["mes_nombre"] = fecha["mes"].map(dict(zip(range(1, 13), [
        "Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Set", "Oct", "Nov", "Dic"])))
    fecha["periodo_etiqueta"] = fecha["mes_nombre"] + " " + fecha["anio"].astype(str)
    fecha["trimestre"] = "T" + fecha["fecha"].dt.quarter.astype(str)
    fecha["hito"] = fecha["periodo"].map(MILESTONES).fillna("")
    out["dim_fecha"] = fecha

    # --- dim_tipo_credito ------------------------------------------------------------------------
    out["dim_tipo_credito"] = CREDIT_TYPE_DIM

    # --- dim_entidad -----------------------------------------------------------------------------
    ref = pd.read_csv(REFERENCE / "entidades.csv").query("entidad_id != 'SISTEMA'")
    names = ref.groupby("entidad_id")["nombre_corto"].first()
    events = ref.dropna(subset=["evento"]).groupby("entidad_id")["evento"].agg(" | ".join)
    span = cartera.groupby("entidad_id")["periodo"].agg(primer_periodo="min", ultimo_periodo="max")
    last = cartera[cartera["periodo"] == cartera["periodo"].max()]
    share = last.groupby(["entidad_id", "tipo_credito"])["directos"].sum()
    main_type = share.groupby(level=0).idxmax().map(lambda t: t[1])
    main_share = share.groupby(level=0).max() / share.groupby(level=0).sum()
    # Para entidades que ya salieron, el tipo predominante se mide en su último mes
    for ent, row in span.iterrows():
        if ent not in main_type.index:
            snap = cartera[(cartera["entidad_id"] == ent) & (cartera["periodo"] == row["ultimo_periodo"])]
            s = snap.groupby("tipo_credito")["directos"].sum()
            main_type[ent], main_share[ent] = s.idxmax(), s.max() / s.sum()
    dim = span.reset_index()
    dim["entidad"] = dim["entidad_id"].map(names)
    dim["activa"] = dim["ultimo_periodo"] == max(periods)
    dim["tipo_predominante"] = dim["entidad_id"].map(main_type)
    dim["participacion_tipo_predominante"] = dim["entidad_id"].map(main_share).round(4)
    dim["evento"] = dim["entidad_id"].map(events).fillna("")
    out["dim_entidad"] = dim[["entidad_id", "entidad", "activa", "primer_periodo", "ultimo_periodo",
                              "tipo_predominante", "participacion_tipo_predominante", "evento"]]

    # Fecha real (fin de mes) en todas las tablas de hechos, para relacionarlas con dim_fecha
    for name in list(out):
        if name.startswith("fact_"):
            df = out[name].copy()
            df.insert(0, "fecha", month_end(df["periodo"]))
            keys = [c for c in ("fecha", "entidad_id", "tipo_credito", "metrica") if c in df.columns]
            out[name] = df.drop(columns="periodo").sort_values(keys).reset_index(drop=True)
    return out


def write_curated(tables: dict[str, pd.DataFrame]) -> None:
    config.CURATED.mkdir(parents=True, exist_ok=True)
    for name, df in tables.items():
        df = df.copy()
        for col in df.select_dtypes("datetime").columns:
            df[col] = df[col].dt.strftime("%Y-%m-%d")
        df.to_csv(config.CURATED / f"{name}.csv", index=False, float_format="%.6f")


def main() -> None:
    staging = build_staging()
    print("staging:", {k: len(v) for k, v in staging.items()})
    curated = build_curated(staging)
    write_curated(curated)
    for name, df in curated.items():
        print(f"  {name:24s} {len(df):7d} filas")


if __name__ == "__main__":
    main()
