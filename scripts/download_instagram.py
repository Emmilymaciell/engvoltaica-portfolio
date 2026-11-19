#!/usr/bin/env python
"""
download_instagram.py — Recupera as mídias originais do @engvoltaica.

Incremental, retomável e idempotente: o archive SQLite do gallery-dl guarda o
que já baixou, então reexecutar só pega o que falta. Seguro para interromper.

Uso:
    python scripts/download_instagram.py --browser chrome
    python scripts/download_instagram.py --browser chrome --limit 3      # teste
    python scripts/download_instagram.py --browser chrome --only 054,136,169
    python scripts/download_instagram.py --browser chrome --priority     # só relevância ALTA
    python scripts/download_instagram.py --status                        # sem baixar nada

A sessão do Instagram vem do navegador, em memória, via --cookies-from-browser.
Nenhum cookie é gravado, copiado ou registrado em log.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GDL = ROOT / ".venv" / "Scripts" / "gallery-dl.exe"
CONF = ROOT / "config" / "gallery-dl.conf"
POSTS = ROOT / "data" / "processed" / "posts_master.csv"
STAGING = ROOT / "data" / "raw" / "instagram" / "_staging"
META = ROOT / "data" / "raw" / "instagram" / "metadata"
STATE = ROOT / "state" / "instagram_download.json"
LOGDIR = ROOT / "logs"

BATCH = 25            # posts por chamada — permite parar limpo entre lotes
COOKIE_RE = re.compile(r"cookie|sessionid|csrftoken|ds_user", re.I)


def scrub(line: str) -> str:
    """Nada que pareça cookie/sessão entra em log."""
    return "[linha omitida: possível dado de sessão]" if COOKIE_RE.search(line) else line


def load_posts() -> list[dict]:
    if not POSTS.exists():
        sys.exit(f"ERRO: {POSTS} não existe. Rode scripts/parse_chrome_catalog.py antes.")
    with POSTS.open(encoding="utf-8-sig") as fh:
        return [r for r in csv.DictReader(fh) if r.get("url")]


def downloaded_shortcodes() -> set[str]:
    """O que já existe fisicamente em disco (staging ou raw organizado)."""
    found: set[str] = set()
    for base in (STAGING, ROOT / "data" / "raw" / "instagram" / "images",
                 ROOT / "data" / "raw" / "instagram" / "videos"):
        if not base.exists():
            continue
        for f in base.rglob("*"):
            if not f.is_file():
                continue
            m = re.search(r"([A-Za-z0-9_-]{11})_\d{2}\.", f.name) or \
                re.search(r"POST_\d{3}_([A-Za-z0-9_-]{11})_", f.name)
            if m:
                found.add(m.group(1))
    return found


def save_state(payload: dict) -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--browser", default="chrome",
                    help="navegador de onde ler a sessão (chrome/edge/firefox)")
    ap.add_argument("--limit", type=int, help="baixa no máximo N posts pendentes")
    ap.add_argument("--only", help="lista de post_number, ex.: 054,136,169")
    ap.add_argument("--priority", action="store_true", help="apenas relevância ALTA")
    ap.add_argument("--status", action="store_true", help="só relata o progresso")
    args = ap.parse_args()

    posts = load_posts()
    done = downloaded_shortcodes()

    sel = posts
    if args.only:
        want = {p.strip().zfill(3) for p in args.only.split(",")}
        sel = [p for p in posts if p["post_number"] in want]
    elif args.priority:
        sel = [p for p in posts if p["portfolio_relevance"] == "ALTA"]

    pending = [p for p in sel if p["shortcode"] not in done]

    print(f"Catálogo total : {len(posts)} posts")
    print(f"Seleção atual  : {len(sel)}")
    print(f"Já em disco    : {len(sel) - len(pending)}")
    print(f"Pendentes      : {len(pending)}")
    if args.status:
        return 0
    if not pending:
        print("Nada a baixar.")
        return 0
    if args.limit:
        pending = pending[: args.limit]
        print(f"Limitado a     : {len(pending)}")

    STAGING.mkdir(parents=True, exist_ok=True)
    META.mkdir(parents=True, exist_ok=True)
    LOGDIR.mkdir(parents=True, exist_ok=True)
    logfile = LOGDIR / f"instagram_download_{datetime.now():%Y-%m-%d}.log"

    ok = fail = 0
    stop_reason = ""
    with logfile.open("a", encoding="utf-8") as lg:
        lg.write(f"\n===== execução {datetime.now():%Y-%m-%d %H:%M:%S} · "
                 f"{len(pending)} pendentes · navegador={args.browser} =====\n")

        for i in range(0, len(pending), BATCH):
            lote = pending[i: i + BATCH]
            urlfile = ROOT / "tmp" / f"_batch_{i // BATCH:03d}.txt"
            urlfile.parent.mkdir(parents=True, exist_ok=True)
            # sem BOM: o gallery-dl trata BOM como parte da URL
            urlfile.write_text("\n".join(p["url"] for p in lote) + "\n",
                               encoding="utf-8", newline="\n")

            print(f"\n[lote {i // BATCH + 1}] {len(lote)} posts "
                  f"(POST {lote[0]['post_number']}…{lote[-1]['post_number']})")
            proc = subprocess.run(
                [str(GDL), "--config", str(CONF),
                 "--cookies-from-browser", args.browser,
                 "-i", str(urlfile)],
                cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace",
            )
            out = (proc.stdout or "") + (proc.stderr or "")
            for line in out.splitlines():
                lg.write(scrub(line) + "\n")

            low = out.lower()
            if "429" in low or "rate limit" in low or "please wait" in low:
                stop_reason = "RATE_LIMIT — Instagram pediu para esperar. Retome mais tarde."
            elif "login" in low and "redirect" in low:
                stop_reason = ("SESSAO_INVALIDA — o Instagram redirecionou para o login. "
                               "Feche o navegador (libera o banco de cookies) ou refaça o login nele.")
            elif "permission denied" in low and "cookies" in low:
                stop_reason = ("COOKIES_BLOQUEADOS — o navegador está aberto e mantém o banco de "
                               "cookies travado. Feche-o completamente e rode de novo.")
            elif "checkpoint" in low or "challenge" in low:
                stop_reason = "CHECKPOINT — o Instagram pediu verificação. Resolva no navegador."

            if stop_reason:
                print(f"\n!! PARADA SEGURA: {stop_reason}")
                lg.write(f"PARADA SEGURA: {stop_reason}\n")
                break

            if proc.returncode == 0:
                ok += len(lote)
            else:
                fail += len(lote)
                lg.write(f"lote retornou código {proc.returncode}\n")
            urlfile.unlink(missing_ok=True)

    agora = downloaded_shortcodes()
    save_state({
        "atualizado_em": datetime.now().isoformat(timespec="seconds"),
        "posts_no_catalogo": len(posts),
        "shortcodes_em_disco": len(agora),
        "pendentes": len([p for p in posts if p["shortcode"] not in agora]),
        "lotes_ok": ok, "lotes_com_falha": fail,
        "parada": stop_reason,
        "navegador": args.browser,
        "log": str(logfile.relative_to(ROOT)),
    })
    print(f"\nShortcodes em disco: {len(agora)} / {len(posts)}")
    print(f"Estado: {STATE.relative_to(ROOT)}")
    print(f"Log   : {logfile.relative_to(ROOT)}")
    print("\nPróximo passo: python scripts/build_media_manifest.py")
    return 2 if stop_reason else 0


if __name__ == "__main__":
    sys.exit(main())
