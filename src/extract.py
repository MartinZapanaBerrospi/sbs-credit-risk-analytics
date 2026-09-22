"""Fase 1 — Descarga los archivos oficiales de la SBS y las series del BCRP.

Es idempotente: un archivo que ya está en data/raw no se vuelve a descargar (usar --force para
forzarlo). Cada archivo queda registrado en data/raw/manifest.csv con su URL, tamaño, formato
real y hash SHA-256, de modo que cualquier cambio posterior en la fuente sea detectable.

Uso:
    python -m src.extract            # todo lo que falte
    python -m src.extract --force    # vuelve a descargar todo
"""

import argparse
import csv
import hashlib
import time
from datetime import datetime, timezone

import requests

from src import config

MANIFEST_FIELDS = [
    "fuente", "cuadro", "periodo", "url", "archivo", "estado", "formato", "bytes", "sha256", "descargado_en",
]


def file_format(content: bytes) -> str:
    """Formato real según la firma del archivo: la extensión .XLS no es confiable."""
    if content[:4] == b"PK\x03\x04":
        return "xlsx"
    if content[:8] == bytes.fromhex("D0CF11E0A1B11AE1"):
        return "xls"
    if content.lstrip()[:1] in (b"{", b"["):
        return "json"
    return "desconocido"


def fetch(session: requests.Session, url: str, retries: int = 3) -> requests.Response:
    for attempt in range(1, retries + 1):
        try:
            resp = session.get(url, timeout=60)
            if resp.status_code in (200, 404):
                return resp
        except requests.RequestException:
            if attempt == retries:
                raise
        time.sleep(2 * attempt)
    return resp


def load_manifest() -> dict:
    if not config.MANIFEST.exists():
        return {}
    with config.MANIFEST.open(encoding="utf-8", newline="") as f:
        return {(r["fuente"], r["cuadro"], r["periodo"]): r for r in csv.DictReader(f)}


def save_manifest(rows: dict) -> None:
    config.MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    ordered = sorted(rows.values(), key=lambda r: (r["fuente"], r["cuadro"], r["periodo"]))
    with config.MANIFEST.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=MANIFEST_FIELDS)
        writer.writeheader()
        writer.writerows(ordered)


def record(content: bytes, **fields) -> dict:
    return {
        **fields,
        "formato": file_format(content) if content else "",
        "bytes": len(content),
        "sha256": hashlib.sha256(content).hexdigest() if content else "",
        "descargado_en": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def extract_sbs(session, manifest, force=False) -> tuple[int, int]:
    downloaded = missing = 0
    for code in config.SBS_TABLES:
        folder = config.RAW / "sbs" / code
        folder.mkdir(parents=True, exist_ok=True)
        for year, month in config.periods():
            period = f"{year}-{month:02d}"
            key = ("SBS", code, period)
            path = folder / f"{code}_{period}.xls"
            prev = manifest.get(key)
            if not force and prev and (prev["estado"] == "no_publicado" or path.exists()):
                continue

            url = config.sbs_url(code, year, month)
            resp = fetch(session, url)
            if resp.status_code == 404:
                manifest[key] = record(b"", fuente="SBS", cuadro=code, periodo=period, url=url,
                                       archivo="", estado="no_publicado")
                missing += 1
            else:
                path.write_bytes(resp.content)
                manifest[key] = record(resp.content, fuente="SBS", cuadro=code, periodo=period, url=url,
                                       archivo=path.relative_to(config.ROOT).as_posix(), estado="ok")
                downloaded += 1
            time.sleep(0.2)  # cortesía con el servidor de la SBS
        print(f"  {code}: listo")
    return downloaded, missing


def extract_bcrp(session, manifest) -> int:
    folder = config.RAW / "bcrp"
    folder.mkdir(parents=True, exist_ok=True)
    start = f"{config.START[0]}-{config.START[1]}"
    end = f"{config.END[0]}-{config.END[1]}"
    for code in config.BCRP_SERIES:
        url = config.BCRP_URL.format(code=code, start=start, end=end)
        resp = fetch(session, url)
        resp.raise_for_status()
        path = folder / f"{code}.json"
        # Las series se actualizan (revisiones del PBI, por ejemplo): siempre se vuelven a bajar
        # y el hash del manifiesto delata si cambió algo.
        path.write_bytes(resp.content)
        manifest[("BCRP", code, f"{start}..{end}")] = record(
            resp.content, fuente="BCRP", cuadro=code, periodo=f"{start}..{end}", url=url,
            archivo=path.relative_to(config.ROOT).as_posix(), estado="ok")
    return len(config.BCRP_SERIES)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--force", action="store_true", help="vuelve a descargar todos los archivos")
    args = parser.parse_args()

    session = requests.Session()
    session.headers["User-Agent"] = config.USER_AGENT
    manifest = load_manifest()

    print("SBS:")
    downloaded, missing = extract_sbs(session, manifest, force=args.force)
    print(f"  {downloaded} archivos nuevos, {missing} meses no publicados")
    print("BCRP:")
    print(f"  {extract_bcrp(session, manifest)} series")
    save_manifest(manifest)
    print(f"Manifiesto: {config.MANIFEST.relative_to(config.ROOT)} ({len(manifest)} filas)")


if __name__ == "__main__":
    main()
