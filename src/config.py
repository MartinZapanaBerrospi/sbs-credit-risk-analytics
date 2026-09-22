"""Parámetros del proyecto: periodo, cuadros de la SBS, series del BCRP y rutas."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
RAW = DATA / "raw"
STAGING = DATA / "staging"
CURATED = DATA / "curated"
MANIFEST = RAW / "manifest.csv"

# Periodo de análisis (inclusive). La SBS publica cada mes con ~1 mes de rezago.
START = (2015, 1)
END = (2026, 7)

# Carpeta de mes y abreviatura que usa la SBS en sus URLs
MONTHS = [
    ("Enero", "en"), ("Febrero", "fe"), ("Marzo", "ma"), ("Abril", "ab"),
    ("Mayo", "my"), ("Junio", "jn"), ("Julio", "jl"), ("Agosto", "ag"),
    ("Setiembre", "se"), ("Octubre", "oc"), ("Noviembre", "no"), ("Diciembre", "di"),
]

SBS_URL = "https://intranet2.sbs.gob.pe/estadistica/financiera/{year}/{month}/{code}-{abbr}{year}.XLS"

# Cuadros del boletín de Banca Múltiple
SBS_TABLES = {
    "B-2334": "Créditos directos según tipo de crédito y situación (miles de S/)",
    "B-2369": "Flujo de créditos castigados por tipo de crédito (miles de S/)",
    "B-230803": "Número de deudores según tipo de crédito",
    "B-220512": "Ratios de morosidad según días de incumplimiento (%)",
    "B-2362": "Morosidad por tipo y modalidad de crédito (%)",
}

BCRP_URL = "https://estadisticas.bcrp.gob.pe/estadisticas/series/api/{code}/json/{start}/{end}"

BCRP_SERIES = {
    "PD04722MM": "tasa_referencia",
    "PN01273PM": "inflacion_12m",
    "PN01210PM": "tipo_cambio",
    "PN01770AM": "pbi_indice",
}

USER_AGENT = "sbs-credit-risk-analytics/1.0 (+https://github.com/MartinZapanaBerrospi/sbs-credit-risk-analytics)"


def periods():
    """Lista de (año, mes) del periodo de análisis."""
    y, m = START
    out = []
    while (y, m) <= END:
        out.append((y, m))
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def sbs_url(code: str, year: int, month: int) -> str:
    folder, abbr = MONTHS[month - 1]
    return SBS_URL.format(year=year, month=folder, code=code, abbr=abbr)
