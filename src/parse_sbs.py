"""Lectura de los cuadros de la SBS a tablas largas (una fila por entidad × concepto × mes).

Cada archivo mensual es una hoja de Excel pensada para imprimir: título, fecha, encabezados en
varias filas, una fila por entidad, una fila de total y notas al pie. Las reglas que aplican
todos los lectores son:

- El formato se ignora: python-calamine abre xls y xlsx por igual.
- El encabezado se ubica por su texto ("Empresas" o "Concepto"), nunca por posición, porque
  algunos meses tienen filas o columnas de más.
- Las entidades son las filas entre el encabezado y la fila "TOTAL BANCA MÚLTIPLE". Lo que
  queda debajo son notas. El total publicado se conserva aparte para validar.
- "-" significa "no aplica" y se guarda como vacío.
"""

import re
from pathlib import Path

import numpy as np
import pandas as pd

TOTAL_LABEL = "TOTAL BANCA MÚLTIPLE"

# Tipo de crédito canónico, reconocido por palabras clave en el encabezado de cada cuadro
CREDIT_TYPES = [
    ("corporativo", r"corporativ"),
    ("grandes_empresas", r"grandes"),
    ("medianas_empresas", r"medianas"),
    ("pequenas_empresas", r"peque"),
    ("microempresas", r"micro"),
    ("consumo", r"consumo"),
    ("hipotecario", r"hipotecari"),
    ("total", r"^total"),
]


def clean(value) -> str:
    """Texto sin espacios repetidos ni llamadas finales (*, **, 1/, 2/)."""
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return ""
    text = re.sub(r"\s+", " ", str(value)).strip()
    while True:
        stripped = re.sub(r"\s*(\*+|\d/)$", "", text).strip()
        if stripped == text:
            return text
        text = stripped


def credit_type(label: str) -> str | None:
    low = clean(label).lower()
    for key, pattern in CREDIT_TYPES:
        if re.search(pattern, low):
            return key
    return None


def to_number(value):
    if value is None:
        return np.nan
    if isinstance(value, (int, float, np.number)):
        return float(value)
    text = str(value).strip().replace(",", "")
    if text in ("", "-", "--", "n.d.", "nan"):
        return np.nan
    try:
        return float(text)
    except ValueError:
        return np.nan


def period_of(path: Path) -> str:
    return re.search(r"_(\d{4}-\d{2})\.xls$", path.name).group(1)


def read_sheet(path: Path) -> pd.DataFrame:
    return pd.read_excel(path, header=None, engine="calamine", dtype=object)


def locate(df: pd.DataFrame, pattern: str) -> tuple[int, int]:
    """Fila y columna de la primera celda cuyo texto coincide con `pattern`."""
    for col in range(min(3, df.shape[1])):
        texts = df.iloc[:, col].map(clean)
        hits = texts[texts.str.match(pattern)]
        if len(hits):
            return hits.index[0], col
    raise ValueError(f"No se encontró el encabezado {pattern!r}")


def entity_rows(df: pd.DataFrame, header_row: int, col: int) -> list[tuple[int, str]]:
    """Filas de entidades (incluida la del total) debajo del encabezado."""
    rows = []
    for r in range(header_row + 1, len(df)):
        name = clean(df.iat[r, col])
        if not name:
            continue
        numeric = [to_number(v) for v in df.iloc[r, col + 1:]]
        if all(np.isnan(numeric)) and not name.upper().startswith("TOTAL"):
            continue
        rows.append((r, name))
        if name.upper().startswith("TOTAL"):
            break
    if not rows or not rows[-1][1].upper().startswith("TOTAL"):
        raise ValueError("No se encontró la fila de total")
    return rows


def ffill_row(values) -> list[str]:
    out, last = [], ""
    for v in values:
        text = clean(v)
        last = text or last
        out.append(last)
    return out


def _long(records, columns) -> pd.DataFrame:
    df = pd.DataFrame.from_records(records, columns=columns)
    df["es_total"] = df["entidad_raw"].str.upper().str.startswith("TOTAL")
    return df


# ---------------------------------------------------------------------------------------------
# Un lector por cuadro
# ---------------------------------------------------------------------------------------------

SITUATIONS = {"vigentes": "vigentes", "refinanc": "refinanciados_reestructurados", "atrasad": "atrasados"}


def parse_b2334(path: Path) -> pd.DataFrame:
    """Créditos directos por tipo y situación (miles de S/).

    Consumo viene partido en revolvente y no revolvente (6 columnas); ambas mitades quedan con
    tipo "consumo" y se suman al pivotar. La última columna es el total de créditos directos de
    la entidad, sin situación: se guarda como tipo "total", situación "directos", para validar.
    """
    df = read_sheet(path)
    h, c = locate(df, r"^Empresas")
    types = ffill_row(df.iloc[h, c + 1:])
    situations = [clean(v).lower() for v in df.iloc[h + 2, c + 1:]]
    columns = []
    for j, (t, s) in enumerate(zip(types, situations), start=c + 1):
        tipo = credit_type(t)
        sit = next((v for k, v in SITUATIONS.items() if s.startswith(k)), None)
        if tipo and sit:
            columns.append((j, tipo, sit))
        elif tipo == "total" and clean(df.iat[h, j]):
            columns.append((j, "total", "directos"))
    if len(columns) != 25:
        raise ValueError(f"B-2334 esperaba 24 columnas tipo × situación y 1 de total, encontró {len(columns)}")

    period = period_of(path)
    records = [
        (period, name, tipo, sit, to_number(df.iat[r, j]))
        for r, name in entity_rows(df, h, c)
        for j, tipo, sit in columns
    ]
    return _long(records, ["periodo", "entidad_raw", "tipo_credito", "situacion", "monto"])


def parse_b2369(path: Path) -> pd.DataFrame:
    """Flujo de créditos castigados por tipo (miles de S/). En 2015 el flujo es trimestral."""
    df = read_sheet(path)
    h, c = locate(df, r"^Empresas")
    header = " ".join(clean(v) for v in df.iloc[h, c + 1:])
    quarterly = "trimestral" in header.lower()
    top = [clean(v) for v in df.iloc[h, c + 1:]]
    sub = [clean(v) for v in df.iloc[h + 1, c + 1:]]
    columns = []
    for j, (a, b) in enumerate(zip(top, sub), start=c + 1):
        tipo = credit_type(b) or (credit_type(a) if a.lower() == "total" else None)
        if tipo:
            columns.append((j, tipo))
    if len(columns) != 8:
        raise ValueError(f"B-2369 esperaba 8 columnas, encontró {len(columns)}")

    period = period_of(path)
    records = [
        (period, name, tipo, to_number(df.iat[r, j]), quarterly)
        for r, name in entity_rows(df, h, c)
        for j, tipo in columns
    ]
    return _long(records, ["periodo", "entidad_raw", "tipo_credito", "monto", "flujo_trimestral"])


def parse_b230803(path: Path) -> pd.DataFrame:
    """Número de deudores por tipo. El total del sistema consolida deudores repetidos."""
    df = read_sheet(path)
    h, c = locate(df, r"^Empresas")
    columns = []
    for j in range(c + 1, df.shape[1]):
        label = clean(df.iat[h, j])
        tipo = "total" if label.lower().startswith("total") else credit_type(label.replace("Deudores", ""))
        if tipo:
            columns.append((j, tipo))
    if len(columns) != 8:
        raise ValueError(f"B-230803 esperaba 8 columnas, encontró {len(columns)}")

    period = period_of(path)
    records = [
        (period, name, tipo, to_number(df.iat[r, j]))
        for r, name in entity_rows(df, h, c)
        for j, tipo in columns
    ]
    return _long(records, ["periodo", "entidad_raw", "tipo_credito", "deudores"])


DAYS = {"30": "mora_30d", "60": "mora_60d", "90": "mora_90d", "120": "mora_120d"}


def parse_b220512(path: Path) -> pd.DataFrame:
    """Porcentaje de créditos con más de N días de atraso y morosidad contable (%)."""
    df = read_sheet(path)
    h, c = locate(df, r"^Empresas")
    columns = []
    for j in range(c + 1, df.shape[1]):
        top, sub = clean(df.iat[h, j]).lower(), clean(df.iat[h + 1, j]).lower()
        days = re.search(r"más de (\d+) días", sub)
        if days and days.group(1) in DAYS:
            columns.append((j, DAYS[days.group(1)]))
        elif "criterio contable" in top:
            columns.append((j, "morosidad_contable"))
    if len(columns) != 5:
        raise ValueError(f"B-220512 esperaba 5 columnas, encontró {len(columns)}")

    period = period_of(path)
    records = [
        (period, name, metric, to_number(df.iat[r, j]))
        for r, name in entity_rows(df, h, c)
        for j, metric in columns
    ]
    return _long(records, ["periodo", "entidad_raw", "metrica", "valor"])


def parse_b2362(path: Path) -> pd.DataFrame:
    """Morosidad por tipo de crédito (%), solo las filas de tipo (no las modalidades).

    Es el único cuadro con entidades en columnas. Se usa para validar la morosidad que se
    calcula desde los montos de B-2334.
    """
    df = read_sheet(path)
    h, c = locate(df, r"^Concepto")
    entities = []
    for j in range(c + 1, df.shape[1]):
        name = clean(df.iat[h, j])
        if name:
            entities.append((j, name))
    period = period_of(path)
    records = []
    for r in range(h + 1, len(df)):
        label = clean(df.iat[r, c])
        if not re.match(r"^(Créditos|Total Créditos Directo)", label):
            continue
        # Algunos meses publican en esa fila el saldo en miles de S/, no la morosidad
        if "miles" in label.lower():
            continue
        tipo = credit_type(label)
        for j, name in entities:
            records.append((period, name, tipo, to_number(df.iat[r, j])))
    out = _long(records, ["periodo", "entidad_raw", "tipo_credito", "morosidad_pct"])
    if set(out["tipo_credito"]) - {"total"} != {k for k, _ in CREDIT_TYPES} - {"total"}:
        raise ValueError("B-2362 debía tener los 7 tipos de crédito")
    return out


PARSERS = {
    "B-2334": parse_b2334,
    "B-2369": parse_b2369,
    "B-230803": parse_b230803,
    "B-220512": parse_b220512,
    "B-2362": parse_b2362,
}


def parse_table(code: str, raw_dir: Path) -> pd.DataFrame:
    frames = []
    for path in sorted((raw_dir / code).glob(f"{code}_*.xls")):
        try:
            frames.append(PARSERS[code](path))
        except Exception as exc:  # el nombre del archivo es indispensable para depurar
            raise RuntimeError(f"{path.name}: {exc}") from exc
    return pd.concat(frames, ignore_index=True)
