"""
╔══════════════════════════════════════════════════════════╗
║   CRAWLER DE PROVAS TI — HOSPITAL BONSUCESSO / EBSERH   ║
║   URLs corrigidas com base na estrutura real do site    ║
╚══════════════════════════════════════════════════════════╝
Uso: python crawler_provas_ti.py
"""

import requests
from bs4 import BeautifulSoup
import os
import re
import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urljoin

# ─────────────────────────────────────────────────────────
#  CATEGORIAS DE PROVAS TI — URLs REAIS DO SITE
#  Cada categoria tem seu próprio slug e número de páginas
# ─────────────────────────────────────────────────────────
CATEGORIAS_BUSCA = [
    # (slug_url,                                    paginas_max, descricao)
    ("analista-de-tecnologia-da-informacao",        25,  "Analista TI"),
    ("tecnico-de-tecnologia-da-informacao",         16,  "Tecnico TI"),
    ("tecnico-em-tecnologia-da-informacao",         16,  "Tecnico em TI"),
    ("analista-de-tecnologia-de-informacao",        10,  "Analista Tecnologia Info"),
    ("analista-de-sistemas",                        15,  "Analista de Sistemas"),
    ("analista-de-infraestrutura",                  10,  "Analista Infraestrutura"),
    ("tecnico-de-suporte",                          10,  "Tecnico Suporte"),
    ("analista-de-suporte",                         10,  "Analista Suporte"),
    ("desenvolvedor",                               10,  "Desenvolvedor"),
    ("seguranca-da-informacao",                     10,  "Seguranca da Informacao"),
    ("banco-de-dados",                              10,  "Banco de Dados"),
    ("redes-de-computadores",                       10,  "Redes"),
    ("analista-de-ti",                              10,  "Analista de TI"),
    ("tecnico-de-ti",                               10,  "Tecnico de TI"),
    ("analista-de-tecnologia",                      10,  "Analista de Tecnologia"),
    ("ti",                                          30,  "TI Geral"),
]

BASE_URL        = "https://www.pciconcursos.com.br"
PASTA_RAIZ      = "PROVAS_TI_BRASIL"
DOWNLOADS_SIMULT = 5
DELAY_PAGINAS   = 1.2   # Entre páginas de listagem
MAX_RETRIES     = 3

# ─────────────────────────────────────────────────────────
#  SEPARAÇÃO AUTOMÁTICA EM PASTAS
# ─────────────────────────────────────────────────────────
PASTAS = [
    {
        "pasta": "1_BONSUCESSO_EBSERH",
        "emoji": "🏅",
        "termos": [
            "bonsucesso", "ebserh", "hospital federal",
            "hgni", "hucff", "hugg", "into", "inca",
            "hospital universitario federal", "husm", "hupaa",
        ],
    },
    {
        "pasta": "2_Hospitais_Saude",
        "emoji": "🏥",
        "termos": [
            "hospital", "saude", "sus", "ministerio da saude",
            "fiocruz", "anvisa", "secretaria de saude",
            "unidade de saude", "ubs", "upa",
        ],
    },
    {
        "pasta": "3_TI_Federal",
        "emoji": "💻",
        "termos": [
            "federal", "uniao", "mpu", "tcu", "trt", "tst",
            "mec", "cnu", "anatel", "aneel", "bacen",
            "banco central", "receita federal", "ministerio",
        ],
    },
    {
        "pasta": "4_TI_Estadual_Municipal",
        "emoji": "🖥️",
        "termos": [
            "prefeitura", "camara", "estado", "municipio",
            "governo do estado", "secretaria",
        ],
    },
]
PASTA_OUTROS = "5_Outros"

# ─────────────────────────────────────────────────────────
#  SETUP
# ─────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("download_log.txt", encoding="utf-8"),
    ],
)
log = logging.getLogger(__name__)

# Cria pastas
for p in PASTAS:
    os.makedirs(os.path.join(PASTA_RAIZ, p["pasta"]), exist_ok=True)
os.makedirs(os.path.join(PASTA_RAIZ, PASTA_OUTROS), exist_ok=True)

session = requests.Session()
session.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9",
})

urls_vistas = set()
nomes_baixados = set()


# ─────────────────────────────────────────────────────────
#  AUXILIARES
# ─────────────────────────────────────────────────────────

def limpar_nome(nome):
    nome = re.sub(r'[\\/*?:"<>|]', "", nome)
    nome = re.sub(r'\s+', " ", nome).strip()
    return nome[:180]


def classificar(nome):
    nl = nome.lower()
    for cat in PASTAS:
        if any(t in nl for t in cat["termos"]):
            return cat["pasta"], cat["emoji"]
    return PASTA_OUTROS, "📄"


def get_retry(url, stream=False, timeout=20):
    for tentativa in range(1, MAX_RETRIES + 1):
        try:
            r = session.get(url, stream=stream, timeout=timeout)
            r.raise_for_status()
            return r
        except Exception as e:
            if tentativa == MAX_RETRIES:
                raise
            espera = 2 ** tentativa
            log.warning(f"  Retry {tentativa}/{MAX_RETRIES} ({espera}s) | {e}")
            time.sleep(espera)


# ─────────────────────────────────────────────────────────
#  DOWNLOAD DE UM PDF
# ─────────────────────────────────────────────────────────

def baixar_pdf(url, nome_bonito):
    pasta_cat, emoji = classificar(nome_bonito)
    nome_arquivo = limpar_nome(nome_bonito) + ".pdf"

    if nome_arquivo in nomes_baixados:
        return "ja_existe"
    nomes_baixados.add(nome_arquivo)

    caminho = os.path.join(PASTA_RAIZ, pasta_cat, nome_arquivo)

    if os.path.exists(caminho):
        return "ja_existe"

    try:
        r = get_retry(url, stream=True, timeout=30)
        ct = r.headers.get("Content-Type", "").lower()
        if "html" in ct:
            return "nao_pdf"

        with open(caminho, "wb") as f:
            for chunk in r.iter_content(chunk_size=512 * 1024):
                if chunk:
                    f.write(chunk)

        tamanho = os.path.getsize(caminho)
        if tamanho < 3000:
            os.remove(caminho)
            return "vazio"

        kb = tamanho // 1024
        log.info(f"  {emoji} [{kb:>5} KB] [{pasta_cat}] {nome_bonito[:65]}")
        return "ok"

    except Exception as e:
        log.error(f"  ERRO: {nome_bonito[:60]} | {e}")
        if os.path.exists(caminho):
            os.remove(caminho)
        return "erro"


# ─────────────────────────────────────────────────────────
#  EXTRAI PDFs DE UMA PÁGINA DE CONCURSO ESPECÍFICO
#  Ex: /provas/download/analista-ti-tcu-cespe-2024
# ─────────────────────────────────────────────────────────

def extrair_pdfs_do_concurso(url_concurso):
    try:
        res = get_retry(url_concurso, timeout=15)
        soup = BeautifulSoup(res.text, "html.parser")

        h1 = soup.find("h1")
        titulo = h1.get_text(" ", strip=True) if h1 else "Prova"

        encontrados = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if ".pdf" not in href.lower():
                continue

            if href.startswith("//"):
                url_final = "https:" + href
            elif href.startswith("/"):
                url_final = BASE_URL + href
            elif href.startswith("http"):
                url_final = href
            else:
                url_final = urljoin(url_concurso, href)

            if url_final in urls_vistas:
                continue
            urls_vistas.add(url_final)

            # Só pega links de "Baixar" (não "Ver")
            texto = a.get_text(" ", strip=True)
            if "baixar" in texto.lower() or ".pdf" in texto.lower():
                nome = f"{titulo} - {texto}"
                encontrados.append((url_final, nome))

        # Fallback: pega TODOS os PDFs se não encontrou com "Baixar"
        if not encontrados:
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if ".pdf" not in href.lower():
                    continue
                if href.startswith("/"):
                    url_final = BASE_URL + href
                elif href.startswith("http"):
                    url_final = href
                else:
                    continue
                if url_final in urls_vistas:
                    continue
                urls_vistas.add(url_final)
                texto = a.get_text(" ", strip=True) or "arquivo"
                nome = f"{titulo} - {texto}"
                encontrados.append((url_final, nome))

        return encontrados

    except Exception as e:
        log.warning(f"  Falha ao ler: {url_concurso[:70]} | {e}")
        return []


# ─────────────────────────────────────────────────────────
#  VARRE UMA CATEGORIA (EX: analista-de-tecnologia-da-informacao)
#  Página de listagem real: /provas/analista-de-tecnologia-da-informacao
#  Com paginação:          /provas/analista-de-tecnologia-da-informacao/2
# ─────────────────────────────────────────────────────────

def varrer_categoria(slug, max_pag, descricao):
    links_concurso = []
    vistos_local = set()

    for p in range(1, max_pag + 1):
        if p == 1:
            url_pag = f"{BASE_URL}/provas/{slug}"
        else:
            url_pag = f"{BASE_URL}/provas/{slug}/{p}"

        try:
            res = get_retry(url_pag, timeout=15)
            soup = BeautifulSoup(res.text, "html.parser")

            # Links de concursos específicos ficam em /provas/download/...
            novos = 0
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if "/provas/download/" in href:
                    full = BASE_URL + href if href.startswith("/") else href
                    if full not in vistos_local:
                        vistos_local.add(full)
                        links_concurso.append(full)
                        novos += 1

            log.info(f"  [{descricao}] Pag {p}/{max_pag}: +{novos} concursos (total: {len(links_concurso)})")

            if novos == 0:
                log.info(f"  [{descricao}] Sem novos — encerrando categoria.")
                break

            time.sleep(DELAY_PAGINAS)

        except Exception as e:
            # 404 significa que acabaram as páginas
            if "404" in str(e) or "Not Found" in str(e):
                log.info(f"  [{descricao}] Fim na pag {p} (404).")
                break
            log.error(f"  [{descricao}] Erro pag {p}: {e}")
            time.sleep(2)

    return links_concurso


# ─────────────────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────────────────

def main():
    log.info("=" * 60)
    log.info("  CRAWLER PROVAS TI - BONSUCESSO / EBSERH")
    log.info("=" * 60)
    log.info(f"  Destino: {os.path.abspath(PASTA_RAIZ)}")
    log.info(f"  Categorias a varrer: {len(CATEGORIAS_BUSCA)}")
    log.info("")

    # ── ETAPA 1: Mapeia todos os links de concurso ────────
    log.info("━" * 50)
    log.info("  ETAPA 1 — Mapeando concursos por categoria")
    log.info("━" * 50)

    todos_links_concurso = []
    vistos_global = set()

    for slug, max_pag, desc in CATEGORIAS_BUSCA:
        log.info(f"\n  >> Categoria: {desc}")
        links = varrer_categoria(slug, max_pag, desc)
        novos = [l for l in links if l not in vistos_global]
        vistos_global.update(novos)
        todos_links_concurso.extend(novos)
        log.info(f"     {len(novos)} concursos únicos nesta categoria")

    log.info(f"\n  Total de concursos únicos: {len(todos_links_concurso)}")

    # ── ETAPA 2: Extrai PDFs de cada concurso ────────────
    log.info("\n" + "━" * 50)
    log.info("  ETAPA 2 — Extraindo links de PDF")
    log.info("━" * 50)

    todos_pdfs = []
    with ThreadPoolExecutor(max_workers=8) as ex:
        futuros = {ex.submit(extrair_pdfs_do_concurso, url): url
                   for url in todos_links_concurso}
        for i, fut in enumerate(as_completed(futuros), 1):
            todos_pdfs.extend(fut.result())
            if i % 100 == 0 or i == len(todos_links_concurso):
                log.info(f"  [{i}/{len(todos_links_concurso)}] PDFs encontrados: {len(todos_pdfs)}")

    log.info(f"\n  Total de PDFs para baixar: {len(todos_pdfs)}")

    # Contagem por pasta
    contagem = {p["pasta"]: 0 for p in PASTAS}
    contagem[PASTA_OUTROS] = 0
    for _, nome in todos_pdfs:
        pasta, _ = classificar(nome)
        contagem[pasta] = contagem.get(pasta, 0) + 1

    log.info("\n  Distribuicao:")
    for p in PASTAS:
        log.info(f"    {p['emoji']}  {p['pasta']}: {contagem[p['pasta']]} PDFs")
    log.info(f"    -  {PASTA_OUTROS}: {contagem[PASTA_OUTROS]} PDFs")

    # ── ETAPA 3: Baixa (prioridade primeiro) ─────────────
    log.info("\n" + "━" * 50)
    log.info("  ETAPA 3 — Baixando PDFs")
    log.info("━" * 50)

    def prioridade(item):
        _, nome = item
        pasta, _ = classificar(nome)
        for i, p in enumerate(PASTAS):
            if p["pasta"] == pasta:
                return i
        return len(PASTAS)

    todos_pdfs.sort(key=prioridade)

    resultados = {"ok": 0, "ja_existe": 0, "erro": 0, "nao_pdf": 0, "vazio": 0}

    with ThreadPoolExecutor(max_workers=DOWNLOADS_SIMULT) as ex:
        futuros = {ex.submit(baixar_pdf, url, nome): nome
                   for url, nome in todos_pdfs}
        for i, fut in enumerate(as_completed(futuros), 1):
            status = fut.result()
            resultados[status] = resultados.get(status, 0) + 1
            if i % 25 == 0 or i == len(todos_pdfs):
                log.info(
                    f"  {i}/{len(todos_pdfs)} | "
                    f"Baixados: {resultados['ok']} | "
                    f"Ja existiam: {resultados['ja_existe']} | "
                    f"Erros: {resultados['erro']}"
                )

    # ── Resumo final ──────────────────────────────────────
    log.info("\n" + "=" * 60)
    log.info("  CONCLUIDO!")
    log.info(f"  Baixados com sucesso : {resultados['ok']}")
    log.info(f"  Ja existiam          : {resultados['ja_existe']}")
    log.info(f"  Erros                : {resultados['erro']}")
    log.info(f"  Pasta                : {os.path.abspath(PASTA_RAIZ)}")
    log.info("=" * 60)


if __name__ == "__main__":
    main()