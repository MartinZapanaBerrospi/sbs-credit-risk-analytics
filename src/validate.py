"""Validaciones del pipeline contra las cifras que la propia SBS publica.

Cada regla compara algo que el proyecto calcula con algo que la SBS ya publicó. Si la
reconstrucción desde montos coincide con los totales y ratios oficiales, el parser y el mapa de
entidades son correctos.

Uso:
    python -m src.validate     # escribe reports/validaciones.csv y falla si alguna regla no pasa
"""

import sys

import numpy as np
import pandas as pd

from src import config

REPORTS = config.ROOT / "reports"

REL_TOL = 1e-4   # 0,01 % en montos
PP_TOL = 0.01    # 0,01 puntos porcentuales en ratios

# Diferencias investigadas y explicadas: no se relaja la tolerancia, se documenta el caso.
KNOWN_EXCEPTIONS = {
    ("V4", "2017-04"): "B-220512 publica 3,00 %; B-2334 y B-2362 coinciden en 3,0589 %. B-220512 sale de otro "
                       "reporte (Reporte N° 14) y difiere de los cuadros basados en el Balance de Comprobación.",
    ("V4", "2024-09"): "B-220512 publica 4,17 %; B-2334 y B-2362 coinciden en 4,1556 %. Misma causa que 2017-04.",
    ("V2", "('2024-04', 'B. Pichincha')"): "Nota SBS: Pichincha registró un deudor no minorista como microempresa; "
                                          "la SBS usó la cifra de marzo en ese tipo sin alterar el total (-1,01 %).",
    ("V2", "('2024-04', 'TOTAL BANCA MÚLTIPLE')"): "Arrastre del caso Pichincha 2024-04 en el total del sistema (-0,025 %).",
}


def load_staging() -> dict[str, pd.DataFrame]:
    return {code: pd.read_parquet(config.STAGING / f"{code}.parquet") for code in config.SBS_TABLES}


def rel_diff(a: pd.Series, b: pd.Series) -> pd.Series:
    return (a - b).abs() / b.abs().where(b.abs() > 0, 1)


def v_sum_equals_total(df: pd.DataFrame, keys: list[str], value: str) -> pd.DataFrame:
    banks = df[~df["es_total"]].groupby(keys)[value].sum(min_count=1)
    total = df[df["es_total"]].groupby(keys)[value].sum(min_count=1)
    cmp = pd.concat({"calculado": banks, "publicado": total}, axis=1).dropna()
    cmp["dif"] = rel_diff(cmp["calculado"], cmp["publicado"])
    return cmp


def morosidad_sistema(b2334: pd.DataFrame, tipo: str | None = None) -> pd.Series:
    df = b2334[(~b2334["es_total"]) & (b2334["tipo_credito"] != "total")]
    if tipo:
        df = df[df["tipo_credito"] == tipo]
    pv = df.pivot_table(index="periodo", columns="situacion", values="monto", aggfunc="sum")
    return pv["atrasados"] / pv.sum(axis=1) * 100


def run() -> pd.DataFrame:
    st = load_staging()
    results = []

    def add(rule, detail, cmp, tol, column="dif"):
        worst = cmp[column].max() if len(cmp) else np.nan
        failing = cmp[cmp[column] > tol]
        explained = [str(k) for k in failing.index if (rule, str(k)) in KNOWN_EXCEPTIONS]
        results.append({
            "regla": rule, "detalle": detail, "comparaciones": len(cmp),
            "fallas": len(failing) - len(explained), "explicadas": len(explained),
            "peor_diferencia": worst, "tolerancia": tol,
        })

    b2334 = st["B-2334"]
    add("V1", "B-2334: suma de bancos = TOTAL BANCA MÚLTIPLE (tipo × situación × mes)",
        v_sum_equals_total(b2334, ["periodo", "tipo_credito", "situacion"], "monto"), REL_TOL)

    keys = ["periodo", "entidad_raw"]
    by_type = b2334[b2334["tipo_credito"] != "total"].groupby(keys)["monto"].sum()
    total_col = b2334[b2334["tipo_credito"] == "total"].groupby(keys)["monto"].sum()
    cmp = pd.concat({"calculado": by_type, "publicado": total_col}, axis=1).dropna()
    cmp["dif"] = rel_diff(cmp["calculado"], cmp["publicado"])
    add("V2", "B-2334: suma de tipos × situación = columna 'Total créditos directos' (entidad × mes)", cmp, REL_TOL)

    b2369 = st["B-2369"]
    add("V3", "B-2369: suma de bancos = TOTAL en castigos (tipo × mes)",
        v_sum_equals_total(b2369, ["periodo", "tipo_credito"], "monto"), REL_TOL)

    calc = morosidad_sistema(b2334)
    b220512 = st["B-220512"]
    pub = b220512[b220512["es_total"] & (b220512["metrica"] == "morosidad_contable")].set_index("periodo")["valor"]
    cmp = pd.concat({"calculado": calc, "publicado": pub}, axis=1).dropna()
    cmp["dif"] = (cmp["calculado"] - cmp["publicado"]).abs()
    # B-220512 publica la morosidad con 2 decimales: el redondeo admite hasta 0,005 pp
    add("V4", "Morosidad del sistema calculada desde B-2334 = morosidad contable publicada en B-220512 (pp)",
        cmp, PP_TOL)

    b2362 = st["B-2362"]
    pub = b2362[b2362["es_total"]].pivot_table(index="periodo", columns="tipo_credito", values="morosidad_pct")
    diffs = []
    for tipo in pub.columns:
        c = morosidad_sistema(b2334, None if tipo == "total" else tipo)
        both = pd.concat({"calculado": c, "publicado": pub[tipo]}, axis=1).dropna()
        both["dif"] = (both["calculado"] - both["publicado"]).abs()
        diffs.append(both.assign(tipo=tipo))
    add("V5", "Morosidad por tipo de crédito calculada desde B-2334 = publicada en B-2362 (pp)",
        pd.concat(diffs), PP_TOL)

    ref = pd.read_csv(config.DATA / "reference" / "entidades.csv")
    names = pd.concat([df["entidad_raw"] for df in st.values()]).unique()
    unmapped = pd.DataFrame({"dif": [float(n not in set(ref["alias"])) for n in names]})
    add("V6", "Todos los nombres de entidad publicados tienen id en data/reference/entidades.csv", unmapped, 0)

    cartera = pd.read_csv(config.CURATED / "fact_cartera.csv")
    months = pd.DataFrame({"dif": [float(cartera["fecha"].nunique() != len(config.periods()))]})
    add("V7", "fact_cartera tiene los 139 meses del periodo", months, 0)

    return pd.DataFrame(results)


def main() -> None:
    report = run()
    REPORTS.mkdir(exist_ok=True)
    report.to_csv(REPORTS / "validaciones.csv", index=False, float_format="%.6g")
    with pd.option_context("display.width", 200, "display.max_colwidth", 90):
        print(report.to_string(index=False))
    if report["fallas"].sum():
        sys.exit("Hay validaciones con fallas")


if __name__ == "__main__":
    main()
