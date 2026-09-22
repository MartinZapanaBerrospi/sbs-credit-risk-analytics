"""Integridad del modelo en estrella que se versiona en data/curated."""

import pandas as pd
import pytest

from src import config

C = config.CURATED


@pytest.fixture(scope="module")
def t():
    return {p.stem: pd.read_csv(p) for p in C.glob("*.csv")}


def test_all_tables_present(t):
    assert set(t) == {
        "fact_cartera", "fact_castigos", "fact_deudores", "fact_morosidad_dias", "fact_sistema_publicado",
        "fact_macro", "dim_fecha", "dim_entidad", "dim_tipo_credito"}


@pytest.mark.parametrize("table, keys", [
    ("fact_cartera", ["fecha", "entidad_id", "tipo_credito"]),
    ("fact_castigos", ["fecha", "entidad_id", "tipo_credito"]),
    ("fact_deudores", ["fecha", "entidad_id", "tipo_credito"]),
    ("fact_morosidad_dias", ["fecha", "entidad_id"]),
    ("fact_sistema_publicado", ["fecha", "metrica", "tipo_credito"]),
    ("fact_macro", ["fecha"]),
    ("dim_fecha", ["fecha"]),
    ("dim_entidad", ["entidad_id"]),
    ("dim_tipo_credito", ["tipo_credito"]),
])
def test_keys_are_unique_and_complete(t, table, keys):
    df = t[table]
    assert not df[keys].isna().any().any()
    assert not df.duplicated(keys).any()


@pytest.mark.parametrize("table", ["fact_cartera", "fact_castigos", "fact_deudores", "fact_morosidad_dias"])
def test_facts_reference_existing_dimensions(t, table):
    df = t[table]
    assert set(df["fecha"]) <= set(t["dim_fecha"]["fecha"])
    assert set(df["entidad_id"]) <= set(t["dim_entidad"]["entidad_id"])
    if "tipo_credito" in df:
        assert set(df["tipo_credito"]) <= set(t["dim_tipo_credito"]["tipo_credito"])


def test_period_is_complete(t):
    assert t["dim_fecha"]["fecha"].min() == "2015-01-31"
    assert t["dim_fecha"]["fecha"].max() == "2026-07-31"
    assert t["fact_cartera"]["fecha"].nunique() == 139
    assert t["fact_macro"]["fecha"].nunique() == 139


def test_directos_is_sum_of_situations(t):
    c = t["fact_cartera"]
    parts = c["vigentes"] + c["refinanciados_reestructurados"] + c["atrasados"]
    assert (parts - c["directos"]).abs().max() < 1e-3


def test_system_npl_ratio_is_plausible(t):
    """Morosidad de la banca múltiple entre 2 % y 6 % en todo el periodo."""
    g = t["fact_cartera"].groupby("fecha")[["atrasados", "directos"]].sum()
    ratio = g["atrasados"] / g["directos"] * 100
    assert ratio.between(2, 6).all()


def test_castigos_only_inside_portfolio_perimeter(t):
    cart = set(zip(t["fact_cartera"]["fecha"], t["fact_cartera"]["entidad_id"]))
    cast = set(zip(t["fact_castigos"]["fecha"], t["fact_castigos"]["entidad_id"]))
    assert cast <= cart
