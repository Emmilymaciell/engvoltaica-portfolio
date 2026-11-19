#!/usr/bin/env python
"""
scan_onedrive.py — Indexa o OneDrive corporativo de forma FOCADA.

A árvore tem ~29 mil arquivos. Varrer tudo de novo não agrega: este script
indexa por nome/extensão e só calcula hash e dimensão do que interessa ao
portfólio (imagens grandes, documentos institucionais, projetos técnicos).

O OneDrive é READ-ONLY (docs/DECISIONS.md · DEC-002): aqui só se lê.

Saídas : data/indexes/onedrive_index.csv    — tudo que casou com os filtros
         data/indexes/onedrive_photos.csv   — só imagens, com dimensões
         logs/onedrive_scan.log
         state/onedrive_scan.json
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import sys
import unicodedata
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Pasta corporativa sincronizada (somente leitura). Configure ENGV_ONEDRIVE_DIR.
ONEDRIVE = Path(__import__("os").environ.get("ENGV_ONEDRIVE_DIR", r"C:\caminho\exemplo\PastaCorporativa\OneDrive"))
OUT_INDEX = ROOT / "data" / "indexes" / "onedrive_index.csv"
OUT_PHOTOS = ROOT / "data" / "indexes" / "onedrive_photos.csv"
LOG = ROOT / "logs" / "onedrive_scan.log"
STATE = ROOT / "state" / "onedrive_scan.json"

IMG_EXT = {".jpg", ".jpeg", ".png", ".heic", ".webp", ".tif", ".tiff"}
VID_EXT = {".mp4", ".mov", ".avi", ".mkv"}
DOC_EXT = {".pdf", ".docx", ".doc", ".xlsx", ".xls", ".pptx", ".ppt", ".dwg"}

# Termos de interesse. Casam contra o caminho inteiro, sem acento e minúsculo.
TERMS = [
    "engvoltaica", "usina", "solar", "fotovolt", "kwp", "mwp", "modulo", "painel",
    "placa", "inversor", "growatt", "jinko", "refusol", "solis", "drone", "dji",
    "memorial", "orcamento", "proposta", "contrato", "relatorio", "projeto",
    "art ", "parecer de acesso", "acervo", "cnpj", "crea", "logo", "marketing",
    "apresentacao", "portfolio", "case", "consorcio", "assinatura", "eletroposto",
    "carregamento", "atacarejo", "posto", "cliente b", "cliente e", "planalmira",
    "daia", "anapolis", "neropolis", "vianopolis", "serrinha", "aragoiania",
]
# Cases citados no Instagram — marcados para cruzamento posterior.
CASE_TERMS = {
    "atacarejo cliente a": "CASE_001", "atacarejo": "CASE_001",
    "80 modulos": "CASE_002",
    "cliente b": "CASE_003",
    "daia": "CASE_004", "anapolis": "CASE_004",
    "cliente c": "CASE_005",
    "posto cliente d": "CASE_006", "neropolis": "CASE_006",
    "cliente e": "CASE_007", "clientee": "CASE_007",
    "planalmira": "CASE_008",
    "eletroposto": "CASE_009", "carregamento": "CASE_009",
}
SKIP_DIRS = {"node_modules", ".git", "__pycache__", "bluestacks", "$recycle.bin"}
MIN_IMG_BYTES = 300_000          # abaixo disso não serve para página inteira em A4

_log: list[str] = []


def log(m: str) -> None:
    line = f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {m}"
    _log.append(line)
    print(line)


def sa(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if unicodedata.category(c) != "Mn").lower()


def sha256(p: Path, limit: int = 80 * 1024 * 1024) -> str:
    """Hash completo até `limit`; acima disso, hash das pontas + tamanho."""
    h = hashlib.sha256()
    size = p.stat().st_size
    with p.open("rb") as fh:
        if size <= limit:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                h.update(chunk)
        else:
            h.update(fh.read(1 << 22))
            fh.seek(-(1 << 22), os.SEEK_END)
            h.update(fh.read())
            h.update(str(size).encode())
    return h.hexdigest()


# Atributos NTFS de arquivo ainda "na nuvem" (Files On-Demand). Abrir um desses
# dispara download e trava a varredura por horas — por isso são pulados.
FILE_ATTRIBUTE_RECALL_ON_OPEN = 0x00040000
FILE_ATTRIBUTE_RECALL_ON_DATA_ACCESS = 0x00400000
FILE_ATTRIBUTE_OFFLINE = 0x00001000
CLOUD_MASK = (FILE_ATTRIBUTE_RECALL_ON_OPEN
              | FILE_ATTRIBUTE_RECALL_ON_DATA_ACCESS
              | FILE_ATTRIBUTE_OFFLINE)


def is_local(st: os.stat_result) -> bool:
    """False se o arquivo é placeholder de nuvem (conteúdo não está no disco)."""
    return not (getattr(st, "st_file_attributes", 0) & CLOUD_MASK)


def img_size(p: Path) -> tuple[int, int]:
    """Dimensões lendo só o cabeçalho. Nunca decodifica a imagem inteira."""
    try:
        from PIL import Image
        with Image.open(p) as im:          # Image.open é lazy: lê só o header
            return im.width, im.height
    except Exception:
        return 0, 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-hash", action="store_true",
                    help="pula SHA-256 (varredura muito mais rápida)")
    ap.add_argument("--no-dims", action="store_true",
                    help="não lê dimensão de imagem (evita qualquer acesso a conteúdo)")
    args = ap.parse_args()

    if not ONEDRIVE.exists():
        log(f"ERRO: OneDrive não encontrado em {ONEDRIVE}")
        return 1
    log(f"Varrendo (somente leitura): {ONEDRIVE}")

    rows, photos = [], []
    seen = matched = nuvem = 0
    for dirpath, dirnames, filenames in os.walk(ONEDRIVE):
        dirnames[:] = [d for d in dirnames if sa(d) not in SKIP_DIRS]
        for name in filenames:
            seen += 1
            p = Path(dirpath) / name
            ext = p.suffix.lower()
            if ext not in IMG_EXT | VID_EXT | DOC_EXT:
                continue
            rel = str(p.relative_to(ONEDRIVE)).replace("\\", "/")
            hay = sa(rel)
            hits = [t for t in TERMS if t in hay]
            if not hits:
                continue
            try:
                st = p.stat()
            except OSError:
                continue
            matched += 1

            cases = sorted({cid for term, cid in CASE_TERMS.items() if term in hay})
            kind = "image" if ext in IMG_EXT else ("video" if ext in VID_EXT else "doc")
            local = is_local(st)
            w = h = 0
            if (kind == "image" and st.st_size >= MIN_IMG_BYTES
                    and local and not args.no_dims):
                w, h = img_size(p)
            if not local:
                nuvem += 1

            row = {
                "rel_path": rel,
                "filename": name,
                "ext": ext,
                "kind": kind,
                "filesize": st.st_size,
                "modified": datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d"),
                "width": w, "height": h,
                "megapixels": round(w * h / 1e6, 2) if w and h else "",
                "no_disco": "sim" if local else "nao",
                "terms": "|".join(hits[:6]),
                "case_hint": "|".join(cases),
                "sha256": "" if args.no_hash or st.st_size > 200_000_000 else sha256(p),
            }
            rows.append(row)
            if kind == "image" and w and h:
                photos.append(row)

    OUT_INDEX.parent.mkdir(parents=True, exist_ok=True)
    cols = ["rel_path", "filename", "ext", "kind", "filesize", "modified",
            "width", "height", "megapixels", "no_disco", "terms", "case_hint", "sha256"]
    for path, data in ((OUT_INDEX, rows), (OUT_PHOTOS, photos)):
        with path.open("w", newline="", encoding="utf-8-sig") as fh:
            w = csv.DictWriter(fh, fieldnames=cols)
            w.writeheader()
            w.writerows(sorted(data, key=lambda r: (-(r["filesize"] or 0), r["rel_path"])))

    big = [r for r in photos if (r["megapixels"] or 0) >= 2]
    docs = sum(1 for r in rows if r["kind"] == "doc")
    vids = sum(1 for r in rows if r["kind"] == "video")
    with_case = sum(1 for r in rows if r["case_hint"])

    log(f"Arquivos percorridos : {seen}")
    log(f"Relevantes indexados : {matched}")
    log(f"  imagens={len(photos)}  (>=2 MP: {len(big)})  vídeos={vids}  documentos={docs}")
    log(f"  com pista de case    : {with_case}")
    log(f"  ainda só na nuvem    : {nuvem} (não hidratados — dimensão não lida)")
    log(f"-> {OUT_INDEX.relative_to(ROOT)} / {OUT_PHOTOS.relative_to(ROOT)}")

    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps({
        "varrido_em": datetime.now().isoformat(timespec="seconds"),
        "raiz": str(ONEDRIVE), "modo": "somente_leitura",
        "arquivos_percorridos": seen, "relevantes": matched,
        "imagens": len(photos), "imagens_2mp_ou_mais": len(big),
        "videos": vids, "documentos": docs, "com_case_hint": with_case, "apenas_na_nuvem": nuvem,
        "hash_calculado": not args.no_hash,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    LOG.parent.mkdir(parents=True, exist_ok=True)
    LOG.write_text("\n".join(_log) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
