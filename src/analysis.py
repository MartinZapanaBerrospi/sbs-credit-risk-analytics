"""Fase 5 — Respuestas cuantificadas a las preguntas P1–P5.

Lee solo data/curated (lo mismo que ve Power BI) y escribe las tablas de soporte en
reports/analisis/. Las cifras de docs/05_analisis.md salen de aquí.

Uso:
    python -m src.analysis
"""

import numpy as np
import pandas as pd

from src import config

OUT = config.ROOT / "reports" / "analisis"
NEW_ENTRANTS = ["COMPARTAMOS", "SANTANDER_CONSUMER", "EFECTIVA"]


def load():
    read = lambda n: pd.read_csv(config.CURATED / f"{n}.csv", parse_dates=["fecha"] if n != "dim_entidad" and n != "dim_tipo_credito" else None)
    return {n: read(n) for n in ["fact_cartera", "fact_castigos", "fact_macro", "dim_entidad", "dim_tipo_credito"]}


def ratios(df: pd.DataFrame, by: list[str]) -> pd.DataFrame:
    g = df.groupby(by)[["vigentes", "refinanciados_reestructurados", "atrasados", "directos"]].sum()
    g["morosidad"] = g["atrasados"] / g["directos"] * 100
    g["car"] = (g["atrasados"] + g["refinanciados_reestructurados"]) / g["directos"] * 100
    return g


def p1_sistema(t) -> pd.DataFrame:
    s = ratios(t["fact_cartera"], ["fecha"])
    s["directos_miles_millones"] = s["directos"] / 1e6
    s["morosidad_var_12m_pp"] = s["morosidad"] - s["morosidad"].shift(12)
    return s[["directos_miles_millones", "morosidad", "car", "morosidad_var_12m_pp"]]


def p1_perimetro(t) -> pd.DataFrame:
    """Morosidad del sistema con y sin los bancos que entraron por conversión en 2025–2026."""
    c = t["fact_cartera"]
    full = ratios(c, ["fecha"])["morosidad"]
    const = ratios(c[~c["entidad_id"].isin(NEW_ENTRANTS)], ["fecha"])["morosidad"]
    return pd.DataFrame({"morosidad": full, "morosidad_sin_nuevos": const, "efecto_pp": full - const})


def p2_descomposicion(t, cortes: list[str]) -> pd.DataFrame:
    """Cambio de la morosidad entre cortes = efecto tasa + efecto mezcla, por tipo de crédito.

    mora = Σ w_i m_i  (w: participación del tipo en la cartera, m: morosidad del tipo)
    Δmora = Σ w̄_i Δm_i  (tasa)  +  Σ m̄_i Δw_i  (mezcla),  con w̄, m̄ promedios de ambos cortes.
    """
    by = ratios(t["fact_cartera"], ["fecha", "tipo_credito"])
    w = (by["directos"] / by.groupby(level=0)["directos"].transform("sum")).unstack()
    m = by["morosidad"].unstack()
    rows = []
    for a, b in zip(cortes[:-1], cortes[1:]):
        a, b = pd.Timestamp(a), pd.Timestamp(b)
        dm, dw = m.loc[b] - m.loc[a], w.loc[b] - w.loc[a]
        wbar, mbar = (w.loc[a] + w.loc[b]) / 2, (m.loc[a] + m.loc[b]) / 2
        for tipo in m.columns:
            rows.append({
                "desde": a.strftime("%Y-%m"), "hasta": b.strftime("%Y-%m"), "tipo_credito": tipo,
                "morosidad_desde": m.loc[a, tipo], "morosidad_hasta": m.loc[b, tipo],
                "participacion_desde": w.loc[a, tipo] * 100, "participacion_hasta": w.loc[b, tipo] * 100,
                "efecto_tasa_pp": wbar[tipo] * dm[tipo], "efecto_mezcla_pp": mbar[tipo] * dw[tipo],
            })
    out = pd.DataFrame(rows)
    out["aporte_total_pp"] = out["efecto_tasa_pp"] + out["efecto_mezcla_pp"]
    return out


def p3_bancos(t, fecha: str) -> pd.DataFrame:
    """Morosidad de cada banco frente al sistema dentro de cada tipo, en un corte."""
    c = t["fact_cartera"][t["fact_cartera"]["fecha"] == pd.Timestamp(fecha)]
    bank = ratios(c, ["entidad_id", "tipo_credito"])
    system = ratios(c, ["tipo_credito"])
    bank = bank.join(system[["morosidad", "directos"]], on="tipo_credito", rsuffix="_sistema")
    bank["brecha_pp"] = bank["morosidad"] - bank["morosidad_sistema"]
    bank["participacion_tipo"] = bank["directos"] / bank["directos_sistema"] * 100
    # Contribución a la morosidad del tipo: cuánto de los atrasados del sistema aporta el banco
    bank["aporte_atrasados_pct"] = bank["atrasados"] / bank.groupby(level="tipo_credito")["atrasados"].transform("sum") * 100
    return bank[["directos", "participacion_tipo", "morosidad", "morosidad_sistema", "brecha_pp", "aporte_atrasados_pct"]]


def p4_mora_oculta(t) -> pd.DataFrame:
    s = ratios(t["fact_cartera"], ["fecha"])
    cast = t["fact_castigos"].groupby("fecha")["castigos"].sum().reindex(s.index)
    c12 = cast.rolling(12, min_periods=12).sum()
    out = pd.DataFrame({
        "morosidad": s["morosidad"],
        "castigos_12m_miles_millones": c12 / 1e6,
        "morosidad_ajustada": (s["atrasados"] + c12) / (s["directos"] + c12) * 100,
    })
    out["brecha_pp"] = out["morosidad_ajustada"] - out["morosidad"]
    return out


def p5_macro(t, sistema: pd.DataFrame) -> pd.DataFrame:
    """Correlación de la morosidad con variables macro a distintos rezagos (en meses).

    Se correlacionan variaciones de 12 meses para no confundir dos tendencias con una relación.
    Excluye abr-2020 a dic-2021, cuando las reprogramaciones y el congelamiento de días de atraso
    desconectaron la morosidad del ciclo económico.
    """
    macro = t["fact_macro"].set_index("fecha")
    y = sistema["morosidad"].diff(12)
    covid = (y.index >= "2020-04-01") & (y.index <= "2021-12-31")
    rows = []
    for var, transform in [("tasa_referencia", "diff"), ("inflacion_12m", "diff"), ("pbi_var_12m", "level")]:
        x = macro[var].diff(12) if transform == "diff" else macro[var]
        for lag in [0, 6, 12, 18]:
            pair = pd.concat({"y": y, "x": x.shift(lag)}, axis=1)[~covid].dropna()
            rows.append({"variable": var, "transformacion": "variación 12m" if transform == "diff" else "nivel",
                         "rezago_meses": lag, "correlacion": pair["y"].corr(pair["x"]), "n": len(pair)})
    return pd.DataFrame(rows)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    t = load()
    s = p1_sistema(t)
    tables = {
        "p1_sistema": s,
        "p1_perimetro": p1_perimetro(t),
        # 2024-09 → 2024-10 es la reclasificación de la Res. SBS 2368-2023: se aísla en su propio
        # tramo para que no contamine la lectura de los demás.
        "p2_descomposicion": p2_descomposicion(
            t, ["2015-01-31", "2019-12-31", "2021-12-31", "2024-05-31", "2024-09-30", "2024-10-31", "2026-07-31"]),
        "p3_bancos": p3_bancos(t, "2026-07-31"),
        "p4_mora_oculta": p4_mora_oculta(t),
        "p5_macro": p5_macro(t, s),
    }
    for name, df in tables.items():
        df.to_csv(OUT / f"{name}.csv", float_format="%.4f")
    print(f"{len(tables)} tablas en {OUT.relative_to(config.ROOT)}")


if __name__ == "__main__":
    main()
