"""
Testes do pipeline Engvoltaica.

Cobrem o que quebra em silêncio: parsing, nomenclatura, integridade dos
manifestos e — o mais importante — as regras de publicabilidade.

    .venv\\Scripts\\python.exe -m pytest tests -q
"""
from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

PROC = ROOT / "data" / "processed"
POSTS = PROC / "posts_master.csv"
CASES = PROC / "cases_master.csv"
CLAIMS = PROC / "factual_claims.csv"
MANIFEST = PROC / "media_manifest.csv"
PDF = ROOT / "output" / "portfolio" / "v2" / "Portfolio_Engvoltaica_V2.pdf"

CNPJ_OK = "00.000.000/0001-00"
CNPJ_ERRADO = "00.000.100/0001-00"


def read(p: Path) -> list[dict]:
    if not p.exists():
        return []
    with p.open(encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


# ──────────────────────────── parsing ────────────────────────────

class TestParsing:
    def test_extratores_numericos(self):
        from parse_chrome_catalog import x_power, x_modules, x_generation, x_money, x_return_claim
        assert x_power("80 módulos · 40,00 KWP · 5.000 kWh/mês") == "40.00"
        assert x_modules("200 placas de 530W") == "200"
        assert x_generation("Produção ~10.000 kWh/mês") == "10.000 kWh/mês"
        assert x_money("Economia média anual R$ 100.000,00", "economia") == "R$ 100.000,00"
        assert x_return_claim("Rentabilidade >4% a.m.") == ">4% a.m."
        # ausência de dado nunca vira zero
        assert x_power("sem dado técnico") == ""
        assert x_modules("") == ""
        assert x_return_claim("payback de 2,7 anos") == ""

    def test_shortcode(self):
        from parse_chrome_catalog import shortcode_from_url
        assert shortcode_from_url("https://www.instagram.com/p/CfMEcPHu_wE/") == "CfMEcPHu_wE"
        assert shortcode_from_url("https://www.instagram.com/reel/C5TMPa3v8Sy/") == "C5TMPa3v8Sy"
        assert shortcode_from_url("https://www.instagram.com/engvoltaica/") == ""

    def test_data_iso(self):
        from parse_chrome_catalog import iso_date
        assert iso_date("08/01/2025") == "2025-01-08"
        assert iso_date("data inválida") == ""
        assert iso_date("32/13/2025") == ""

    def test_clean_nao_inventa(self):
        from parse_chrome_catalog import clean
        for ausente in ("—", "-", "Não informado", "Não informado na legenda", "N/A", ""):
            assert clean(ausente) == "", f"{ausente!r} deveria virar string vazia"
        assert clean("  Atacarejo   Cliente  A  ") == "Atacarejo Cliente A"

    def test_tipo_normalizado(self):
        from parse_chrome_catalog import norm_type
        assert norm_type("reel") == "reel"
        assert norm_type("Imagem/Carrossel") == "carousel_or_image"
        assert norm_type("post") == "carousel_or_image"


# ──────────────────────────── posts_master ────────────────────────────

@pytest.mark.skipif(not POSTS.exists(), reason="rode parse_chrome_catalog.py antes")
class TestPostsMaster:
    def test_245_posts(self):
        assert len(read(POSTS)) == 245

    def test_shortcodes_unicos_e_validos(self):
        rows = read(POSTS)
        scs = [r["shortcode"] for r in rows if r["shortcode"]]
        assert len(scs) == len(set(scs)), "shortcode duplicado quebra o elo com o Instagram"
        assert len(scs) == 245
        for sc in scs:
            assert re.fullmatch(r"[A-Za-z0-9_-]+", sc)

    def test_toda_linha_tem_url(self):
        for r in read(POSTS):
            assert r["url"].startswith("https://www.instagram.com/")

    def test_contagem_por_tipo(self):
        rows = read(POSTS)
        assert sum(1 for r in rows if r["type"] == "reel") == 63
        assert sum(1 for r in rows if r["type"] == "carousel_or_image") == 182

    def test_numeracao_sequencial(self):
        nums = sorted(int(r["post_number"]) for r in read(POSTS))
        assert nums == list(range(1, 246))

    def test_media_esperada_so_para_reel(self):
        """DEC-012: feed fica vazio até o download revelar o tamanho real."""
        for r in read(POSTS):
            if r["type"] == "reel" and r["download_status"] == "PENDENTE":
                assert r["media_count_expected"] == "1"


# ──────────────────────────── cases e claims ────────────────────────────

@pytest.mark.skipif(not CASES.exists(), reason="rode build_cases.py antes")
class TestCases:
    def test_case_id_unico(self):
        ids = [c["case_id"] for c in read(CASES)]
        assert len(ids) == len(set(ids))

    def test_publicabilidade_e_valor_conhecido(self):
        validos = {"PUBLICO_IG", "GENERICO_SEM_NOME", "INTERNO", "AUTORIZACAO_NEC"}
        for c in read(CASES):
            assert c["publishability"] in validos

    def test_case_principal_consolidado(self):
        c = next(c for c in read(CASES) if c["case_id"] == "CASE_001")
        assert c["nome_publico"] == "Atacarejo Cliente A"
        assert c["modulos"] == "200"
        assert "100.000" in c["economia"]
        assert c["publishability"] == "PUBLICO_IG"

    def test_posts_relacionados_sao_validos(self):
        for c in read(CASES):
            for p in filter(None, c["posts_relacionados"].split("|")):
                assert 1 <= int(p) <= 245


@pytest.mark.skipif(not CLAIMS.exists(), reason="rode build_cases.py antes")
class TestClaims:
    def test_toda_claim_tem_fonte(self):
        for c in read(CLAIMS):
            assert c["fonte_tipo"] and c["fonte_ref"], f"{c['claim_id']} sem fonte"

    def test_publicar_e_valor_conhecido(self):
        for c in read(CLAIMS):
            assert c["publicar"] in {"SIM", "SIM_COM_FRAMING", "NAO"}

    def test_rentabilidade_esta_bloqueada(self):
        """A regra que mais importa: promessa de rendimento nunca sai."""
        for c in read(CLAIMS):
            if re.search(r"\d+\s*%\s*a\.?\s*m", c["valor"] or "", re.I):
                assert c["publicar"] == "NAO", f"{c['claim_id']} deveria estar bloqueada"

    def test_financeiro_exige_enquadramento(self):
        for c in read(CLAIMS):
            if "conomia" in c["afirmacao"] or "nvestimento" in c["afirmacao"]:
                assert c["publicar"] in {"SIM_COM_FRAMING", "NAO"}
                if c["publicar"] == "SIM_COM_FRAMING":
                    assert c["observacao"], "faltou instrução de enquadramento"


# ──────────────────────────── mídia ────────────────────────────

@pytest.mark.skipif(not MANIFEST.exists(), reason="rode build_media_manifest.py antes")
class TestMedia:
    def test_nomenclatura(self):
        for r in read(MANIFEST):
            assert re.match(r"POST_\d{3}_[A-Za-z0-9_-]+_\d{2}\.\w+$", r["filename"])

    def test_sha256_valido(self):
        for r in read(MANIFEST):
            assert re.fullmatch(r"[0-9a-f]{64}", r["sha256"])

    def test_imagem_tem_dimensao(self):
        for r in read(MANIFEST):
            if r["media_type"] == "image" and r["download_status"] == "OK":
                assert r["width"] and r["height"]

    def test_arquivo_existe(self):
        for r in read(MANIFEST):
            assert (ROOT / r["local_raw_path"]).exists()

    def test_shortcode_do_nome_bate_com_a_coluna(self):
        for r in read(MANIFEST):
            assert r["shortcode"] in r["filename"]


# ──────────────────────────── PDF publicado ────────────────────────────

@pytest.mark.skipif(not PDF.exists(), reason="rode render_pdf.py antes")
class TestPDF:
    @staticmethod
    def texto() -> str:
        import pymupdf
        with pymupdf.open(PDF) as d:
            return "\n".join(p.get_text() for p in d)

    def test_cnpj_correto(self):
        t = self.texto()
        assert CNPJ_OK in t
        assert CNPJ_ERRADO not in t

    def test_sem_percentual_historico(self):
        t = self.texto()
        assert "25%" not in t
        assert "30%" not in t
        assert "20%" in t

    def test_sem_link_quebrado(self):
        assert "lps.engvoltaica.com.br" not in self.texto()

    def test_nenhum_dado_bloqueado_vazou(self):
        t = re.sub(r"\s", "", self.texto())
        for c in read(CLAIMS):
            if c["publicar"] == "NAO" and c["valor"]:
                for tok in re.findall(r"[><~]?\d{1,2}[.,]?\d*%a\.?m\.?",
                                      re.sub(r"\s", "", c["valor"]), re.I):
                    assert tok not in t, f"{c['claim_id']} vazou para o PDF"

    def test_tamanho_para_whatsapp(self):
        assert PDF.stat().st_size / 1048576 <= 8

    def test_contatos_presentes(self):
        t = self.texto()
        for esperado in ("00000-0000", "engvoltaica.com.br", "00000/RF"):
            assert esperado in t


# ──────────────────────────── segurança ────────────────────────────

class TestSeguranca:
    def test_nenhum_cookie_versionado(self):
        """A pergunta certa não é 'existe cookie no disco?' — o perfil headless do
        Edge cria um em tmp/, que é ignorado. É 'o Git levaria algum?'."""
        import subprocess
        try:
            r = subprocess.run(["git", "status", "--porcelain", "--untracked-files=all"],
                               cwd=ROOT, capture_output=True, text=True, timeout=60)
            tracked = subprocess.run(["git", "ls-files"], cwd=ROOT,
                                     capture_output=True, text=True, timeout=60)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pytest.skip("git indisponível")

        candidatos = [l[3:].strip().strip('"') for l in r.stdout.splitlines() if l.strip()]
        candidatos += [l.strip() for l in tracked.stdout.splitlines() if l.strip()]

        padrao = re.compile(r"cookie|session|credential|\.token|secret", re.I)
        suspeitos = sorted({c for c in candidatos if padrao.search(Path(c).name)})
        assert not suspeitos, (
            "o Git versionaria arquivos com cara de credencial: " + ", ".join(suspeitos))

    def test_gitignore_cobre_o_essencial(self):
        gi = (ROOT / ".gitignore").read_text(encoding="utf-8")
        for padrao in ("*cookie*", ".venv/", "tmp/", "credentials*"):
            assert padrao in gi

    def test_config_sem_segredo(self):
        for f in (ROOT / "config").glob("*"):
            if f.is_file():
                txt = f.read_text(encoding="utf-8", errors="ignore").lower()
                assert "sessionid" not in txt
                assert "password" not in txt
