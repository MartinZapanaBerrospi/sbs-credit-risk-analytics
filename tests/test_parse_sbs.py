"""Pruebas del lector de cuadros SBS con archivos reales que representan cada caso difícil.

Los archivos de tests/fixtures son copias sin modificar de la descarga oficial.
"""

from pathlib import Path

import numpy as np
import pytest

from src.parse_sbs import (
    clean, credit_type, parse_b220512, parse_b230803, parse_b2334, parse_b2362, parse_b2369, to_number,
)

FIX = Path(__file__).parent / "fixtures"


@pytest.mark.parametrize("raw, expected", [
    ("  Interbank (con sucursales en el exterior)  ", "Interbank (con sucursales en el exterior)"),
    ("B. Efectiva*", "B. Efectiva"),
    ("Compartamos Banco**", "Compartamos Banco"),
    ("TOTAL BANCA MÚLTIPLE 1/", "TOTAL BANCA MÚLTIPLE"),
    ("Deudores  Medianas Empresas", "Deudores Medianas Empresas"),
    (np.nan, ""),
])
def test_clean(raw, expected):
    assert clean(raw) == expected


@pytest.mark.parametrize("label, expected", [
    ("Créditos pequeñas empresas", "pequenas_empresas"),
    ("Hipotecarios para Vivienda", "hipotecario"),
    ("Corporativo*", "corporativo"),
    ("Total Créditos Directos", "total"),
    ("Tarjetas de crédito", None),
])
def test_credit_type(label, expected):
    assert credit_type(label) == expected


def test_to_number_treats_dash_as_missing():
    assert np.isnan(to_number("-"))
    assert to_number("1,234.5") == 1234.5
    assert to_number(0) == 0.0


def test_b2334_reads_24_type_situation_columns_plus_total():
    df = parse_b2334(FIX / "B-2334_2026-07.xls")
    banks = df[~df["es_total"]]
    assert banks["entidad_raw"].nunique() == 20
    assert set(df["situacion"]) == {"vigentes", "refinanciados_reestructurados", "atrasados", "directos"}
    # Consumo aparece dos veces por situación (revolvente y no revolvente)
    bbva = df[(df["entidad_raw"] == "B. BBVA Perú") & (df["tipo_credito"] == "consumo")]
    assert len(bbva) == 6


def test_b2334_sum_of_banks_matches_published_total():
    df = parse_b2334(FIX / "B-2334_2026-07.xls")
    banks = df[~df["es_total"]].groupby(["tipo_credito", "situacion"])["monto"].sum()
    total = df[df["es_total"]].groupby(["tipo_credito", "situacion"])["monto"].sum()
    assert np.allclose(banks, total.loc[banks.index], rtol=1e-4)


def test_b2334_pichincha_april_2024_keeps_published_figures():
    """La SBS reemplazó un tipo de Pichincha con la cifra de marzo sin tocar su total."""
    df = parse_b2334(FIX / "B-2334_2024-04.xls")
    pich = df[df["entidad_raw"] == "B. Pichincha"]
    by_type = pich[pich["tipo_credito"] != "total"]["monto"].sum()
    total = pich[pich["tipo_credito"] == "total"]["monto"].sum()
    assert by_type / total == pytest.approx(1 - 0.010144, abs=1e-5)


def test_b230803_finds_header_in_second_column():
    """En 2015 hay una columna extra de códigos a la izquierda, y xlrd no abre el archivo."""
    df = parse_b230803(FIX / "B-230803_2015-01.xls")
    assert "B. Continental" in set(df["entidad_raw"])
    assert set(df["tipo_credito"]) == {
        "corporativo", "grandes_empresas", "medianas_empresas", "pequenas_empresas",
        "microempresas", "consumo", "hipotecario", "total"}


def test_b2369_flags_quarterly_flow_in_2015():
    df = parse_b2369(FIX / "B-2369_2015-03.xls")
    assert df["flujo_trimestral"].all()


def test_b220512_reads_xlsx_disguised_as_xls():
    assert (FIX / "B-220512_2015-01.xls").read_bytes()[:4] == b"PK\x03\x04"
    df = parse_b220512(FIX / "B-220512_2015-01.xls")
    assert set(df["metrica"]) == {"mora_30d", "mora_60d", "mora_90d", "mora_120d", "morosidad_contable"}
    total = df[df["es_total"] & (df["metrica"] == "morosidad_contable")]["valor"].iloc[0]
    assert 2 < total < 4


def test_b2362_skips_total_row_published_in_thousands():
    """De 2020-01 a 2021-01 la fila de total trae el saldo en miles de S/, no la morosidad."""
    df = parse_b2362(FIX / "B-2362_2020-01.xls")
    assert "total" not in set(df["tipo_credito"])
    assert df["morosidad_pct"].max() <= 100
