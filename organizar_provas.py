"""
╔══════════════════════════════════════════════════════════════════╗
║         ORGANIZADOR DE PDFs POR CONTEÚDO — IA AUTOMÁTICO       ║
║  Lê cada PDF, analisa o conteúdo com IA e separa em pastas     ║
╚══════════════════════════════════════════════════════════════════╝

INSTALAÇÃO (rode uma vez):
    pip install pymupdf google-generativeai

USO:
    1. Coloque todos os seus PDFs em uma pasta
    2. Edite PASTA_ORIGEM abaixo com o caminho da sua pasta
    3. Execute: python organizar_pdfs.py

Os PDFs serão COPIADOS (não movidos) para subpastas organizadas.
"""

import os
import re
import json
import shutil
import logging
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# ──────────────────────────────────────────────
#  ⚙️  CONFIGURAÇÕES — EDITE AQUI
# ──────────────────────────────────────────────

# Pasta onde estão seus PDFs (pode ter subpastas)
PASTA_ORIGEM  = r"PROVAS_TI_BRASIL"

# Pasta de destino organizada (será criada automaticamente)
PASTA_DESTINO = r"PROVAS_ORGANIZADAS"

# Sua chave de API do Google Gemini (gratuita em aistudio.google.com)
# Deixe vazio "" para usar classificação apenas por nome de arquivo (sem IA)
GEMINI_API_KEY = ""

# Quantos PDFs processar em paralelo
WORKERS = 4

# Máximo de caracteres do PDF para enviar à IA (mais = mais preciso, mais lento)
MAX_CHARS_PDF = 3000

# ──────────────────────────────────────────────
#  📁  CATEGORIAS PARA PROVAS DE TI
#  Cada categoria vira uma pasta.
#  Adicione ou remova conforme sua necessidade.
# ──────────────────────────────────────────────
CATEGORIAS = {

    # ── BONSUCESSO / EBSERH ────────────────────
    "🏅 BONSUCESSO e EBSERH": [
        "bonsucesso", "ebserh", "hospital federal",
        "hucff", "hugg", "hgni", "into", "inca",
        "hospital universitario federal",
    ],

    # ── REDES E INFRAESTRUTURA ─────────────────
    "📡 Redes e Infraestrutura": [
        "redes", "tcp", "ip", "dns", "dhcp", "vlan", "vpn",
        "firewall", "roteador", "switch", "lan", "wan",
        "infraestrutura", "cabeamento", "wi-fi", "wireless",
        "protocolo", "osi", "topologia", "ipv4", "ipv6",
        "subnetting", "mascara de rede",
    ],

    # ── SEGURANÇA DA INFORMAÇÃO ────────────────
    "🔐 Segurança da Informação": [
        "segurança", "criptografia", "certificado digital",
        "autenticação", "vulnerabilidade", "exploit",
        "malware", "virus", "antivirus", "backup",
        "iso 27001", "lgpd", "gdpr", "pentest",
        "política de segurança", "controle de acesso",
        "confidencialidade", "integridade", "disponibilidade",
    ],

    # ── BANCO DE DADOS ─────────────────────────
    "🗄️ Banco de Dados": [
        "banco de dados", "sql", "select", "insert", "update",
        "delete", "join", "normalização", "chave primária",
        "chave estrangeira", "oracle", "mysql", "postgresql",
        "mongodb", "nosql", "acid", "transação", "índice",
        "stored procedure", "trigger", "modelagem",
    ],

    # ── DESENVOLVIMENTO DE SISTEMAS ────────────
    "💻 Desenvolvimento de Sistemas": [
        "programação", "algoritmo", "orientação a objetos",
        "java", "python", "javascript", "c#", ".net",
        "api", "rest", "soap", "web service", "microserviço",
        "git", "devops", "agile", "scrum", "kanban",
        "teste de software", "uml", "design pattern",
        "desenvolvimento", "framework",
    ],

    # ── SISTEMAS OPERACIONAIS ──────────────────
    "🖥️ Sistemas Operacionais": [
        "linux", "windows server", "active directory",
        "sistema operacional", "processo", "thread",
        "gerenciamento de memória", "escalonamento",
        "shell", "bash", "powershell", "virtualização",
        "hipervisor", "vmware", "container", "docker",
        "kubernetes", "permissões", "arquivo",
    ],

    # ── GOVERNANÇA E GESTÃO DE TI ──────────────
    "📋 Governança e Gestão de TI": [
        "itil", "cobit", "governança de ti", "pmbok",
        "gestão de projetos", "bsc", "sla", "acordo de nível",
        "cmmi", "iso 20000", "gerenciamento de mudança",
        "gerenciamento de incidente", "gerenciamento de problema",
        "continuidade", "plano de recuperação", "bcp", "drp",
        "contrato de ti", "licitação", "pregão",
    ],

    # ── CLOUD COMPUTING ────────────────────────
    "☁️ Cloud Computing": [
        "cloud", "nuvem", "aws", "azure", "google cloud",
        "iaas", "paas", "saas", "computação em nuvem",
        "escalabilidade", "elasticidade", "multicloud",
        "servidor em nuvem", "armazenamento em nuvem",
    ],

    # ── LEGISLAÇÃO E DIREITO DIGITAL ───────────
    "⚖️ Legislação e Direito Digital": [
        "lgpd", "lei geral de proteção", "decreto",
        "portaria", "instrução normativa", "norma",
        "tribunal de contas", "licitação", "lei de acesso",
        "lei 14.133", "lei 8.666", "pregão eletrônico",
        "dados pessoais", "titular de dados",
    ],

    # ── RACIOCÍNIO LÓGICO E MATEMÁTICA ─────────
    "🧮 Raciocínio Lógico e Matemática": [
        "raciocínio lógico", "lógica proposicional",
        "conjuntos", "probabilidade", "estatística",
        "porcentagem", "juros", "progressão",
        "análise combinatória", "geometria", "álgebra",
        "inferência", "silogismo",
    ],

    # ── GABARITOS ──────────────────────────────
    "✅ Gabaritos": [
        "gabarito", "resposta correta", "alternativa correta",
        "gabarito definitivo", "gabarito preliminar",
    ],

    # ── EDITAIS E DOCUMENTOS ───────────────────
    "📄 Editais e Documentos": [
        "edital", "cronograma", "inscrição", "homologação",
        "resultado final", "convocação", "resultado preliminar",
        "lista de aprovados", "classificação final",
    ],
}

PASTA_OUTROS = "📦 Outros"

# ──────────────────────────────────────────────
#  SETUP DE LOG
# ──────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("organizar_log.txt", encoding="utf-8"),
    ],
)
log = logging.getLogger(__name__)

# Cria pastas de destino
for nome_pasta in list(CATEGORIAS.keys()) + [PASTA_OUTROS]:
    pasta_limpa = re.sub(r'[\\/*?:"<>|]', "", nome_pasta).strip()
    os.makedirs(os.path.join(PASTA_DESTINO, pasta_limpa), exist_ok=True)


# ──────────────────────────────────────────────
#  EXTRAÇÃO DE TEXTO DO PDF
# ──────────────────────────────────────────────

def extrair_texto_pdf(caminho_pdf, max_chars=MAX_CHARS_PDF):
    """Extrai texto das primeiras páginas do PDF usando PyMuPDF."""
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(caminho_pdf)
        texto = ""
        for pagina in doc:
            texto += pagina.get_text()
            if len(texto) >= max_chars:
                break
        doc.close()
        return texto[:max_chars]
    except Exception as e:
        log.warning(f"  Não conseguiu extrair texto de {Path(caminho_pdf).name}: {e}")
        return ""


# ──────────────────────────────────────────────
#  CLASSIFICAÇÃO POR PALAVRAS-CHAVE (sem IA)
# ──────────────────────────────────────────────

def classificar_por_keywords(texto, nome_arquivo):
    """Classifica o PDF por correspondência de palavras-chave."""
    texto_lower = (texto + " " + nome_arquivo).lower()

    pontuacao = {}
    for categoria, keywords in CATEGORIAS.items():
        pontos = sum(1 for kw in keywords if kw in texto_lower)
        if pontos > 0:
            pontuacao[categoria] = pontos

    if not pontuacao:
        return PASTA_OUTROS, "sem correspondência"

    melhor = max(pontuacao, key=pontuacao.get)
    return melhor, f"{pontuacao[melhor]} palavras-chave"


# ──────────────────────────────────────────────
#  CLASSIFICAÇÃO COM IA (Google Gemini — grátis)
# ──────────────────────────────────────────────

gemini_model = None

def iniciar_gemini():
    global gemini_model
    if not GEMINI_API_KEY:
        return False
    try:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        gemini_model = genai.GenerativeModel("gemini-1.5-flash")
        log.info("  ✅ Google Gemini conectado — usando classificação por IA")
        return True
    except Exception as e:
        log.warning(f"  ⚠ Gemini não disponível: {e} — usando keywords")
        return False


def classificar_com_ia(texto, nome_arquivo):
    """Usa o Gemini para classificar o PDF em uma das categorias."""
    if not gemini_model:
        return None

    categorias_lista = "\n".join(f"- {c}" for c in CATEGORIAS.keys())
    prompt = f"""Você é um assistente que classifica provas de concurso público na área de TI.

Nome do arquivo: {nome_arquivo}

Trecho do conteúdo:
{texto[:2000]}

Categorias disponíveis:
{categorias_lista}
- {PASTA_OUTROS}

Responda APENAS com o nome exato de uma das categorias acima, sem explicação.
Se o conteúdo não se encaixar em nenhuma, responda: {PASTA_OUTROS}"""

    try:
        resp = gemini_model.generate_content(prompt)
        categoria_ia = resp.text.strip().strip('"').strip("'")

        # Valida se a categoria existe
        todas = list(CATEGORIAS.keys()) + [PASTA_OUTROS]
        for cat in todas:
            if cat.lower() in categoria_ia.lower() or categoria_ia.lower() in cat.lower():
                return cat

        return None  # Não reconheceu — fallback para keywords
    except Exception as e:
        log.warning(f"  IA falhou para {nome_arquivo}: {e}")
        time.sleep(2)
        return None


# ──────────────────────────────────────────────
#  PROCESSAR UM PDF
# ──────────────────────────────────────────────

def processar_pdf(caminho_pdf):
    nome = Path(caminho_pdf).name
    try:
        # 1. Extrai texto
        texto = extrair_texto_pdf(caminho_pdf)

        # 2. Classifica (IA se disponível, senão keywords)
        categoria = None
        metodo = ""

        if gemini_model and texto:
            categoria = classificar_com_ia(texto, nome)
            metodo = "IA"

        if not categoria:
            categoria, detalhe = classificar_por_keywords(texto, nome)
            metodo = f"keywords ({detalhe})"

        # 3. Define destino
        pasta_cat_limpa = re.sub(r'[\\/*?:"<>|]', "", categoria).strip()
        destino_dir = os.path.join(PASTA_DESTINO, pasta_cat_limpa)
        destino_arquivo = os.path.join(destino_dir, nome)

        # Evita sobrescrever se já existe com mesmo nome
        if os.path.exists(destino_arquivo):
            base, ext = os.path.splitext(nome)
            destino_arquivo = os.path.join(destino_dir, f"{base}_dup{ext}")

        # 4. Copia (não move — original fica intacto)
        shutil.copy2(caminho_pdf, destino_arquivo)

        emoji = next((c["emoji"] for c in [
            {"pasta": k, "emoji": k.split()[0]}
            for k in CATEGORIAS
        ] if c["pasta"] == categoria), "📦")

        log.info(f"  ✅ [{metodo}] {nome[:50]} → {pasta_cat_limpa}")
        return "ok", categoria

    except Exception as e:
        log.error(f"  ❌ ERRO em {nome}: {e}")
        return "erro", ""


# ──────────────────────────────────────────────
#  COLETAR TODOS OS PDFs RECURSIVAMENTE
# ──────────────────────────────────────────────

def coletar_pdfs(pasta_raiz):
    pdfs = []
    for root, dirs, files in os.walk(pasta_raiz):
        for f in files:
            if f.lower().endswith(".pdf"):
                pdfs.append(os.path.join(root, f))
    return sorted(pdfs)


# ──────────────────────────────────────────────
#  MAIN
# ──────────────────────────────────────────────

def main():
    log.info("=" * 60)
    log.info("  ORGANIZADOR DE PDFs POR CONTEÚDO")
    log.info("=" * 60)
    log.info(f"  Origem : {os.path.abspath(PASTA_ORIGEM)}")
    log.info(f"  Destino: {os.path.abspath(PASTA_DESTINO)}")
    log.info("")

    # Verifica se PyMuPDF está instalado
    try:
        import fitz
        log.info("  ✅ PyMuPDF instalado — extração de texto ativada")
    except ImportError:
        log.error("  ❌ PyMuPDF não encontrado!")
        log.error("     Instale com: pip install pymupdf")
        log.error("     Continuando apenas com classificação por nome de arquivo...")

    # Inicia Gemini se configurado
    usar_ia = iniciar_gemini()
    if not usar_ia:
        log.info("  ℹ️  Usando classificação por palavras-chave (sem IA)")
        log.info("     Para ativar IA: configure GEMINI_API_KEY no início do script")
        log.info("     Chave grátis em: https://aistudio.google.com/app/apikey")

    # Coleta PDFs
    log.info(f"\n  🔍 Buscando PDFs em: {PASTA_ORIGEM}")
    pdfs = coletar_pdfs(PASTA_ORIGEM)

    if not pdfs:
        log.error(f"  ❌ Nenhum PDF encontrado em '{PASTA_ORIGEM}'")
        log.error(f"     Verifique se o caminho está correto no topo do script.")
        return

    log.info(f"  📦 {len(pdfs)} PDFs encontrados\n")

    # Processa em paralelo
    log.info("━" * 50)
    log.info("  Classificando e copiando PDFs...")
    log.info("━" * 50)

    resultados = {"ok": 0, "erro": 0}
    contagem_cat = {}

    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futuros = {ex.submit(processar_pdf, pdf): pdf for pdf in pdfs}
        for i, fut in enumerate(as_completed(futuros), 1):
            status, categoria = fut.result()
            resultados[status] = resultados.get(status, 0) + 1
            if categoria:
                contagem_cat[categoria] = contagem_cat.get(categoria, 0) + 1
            if i % 20 == 0 or i == len(pdfs):
                log.info(f"  [{i}/{len(pdfs)}] OK: {resultados['ok']} | Erros: {resultados['erro']}")

    # Resumo final
    log.info("\n" + "=" * 60)
    log.info("  ✅ CONCLUÍDO!")
    log.info(f"  PDFs processados : {resultados['ok']}")
    log.info(f"  Erros            : {resultados['erro']}")
    log.info(f"\n  📊 Distribuição por categoria:")
    for cat, qtd in sorted(contagem_cat.items(), key=lambda x: -x[1]):
        pasta_limpa = re.sub(r'[\\/*?:"<>|]', "", cat).strip()
        log.info(f"    {pasta_limpa}: {qtd} PDFs")
    log.info(f"\n  📁 Resultado em: {os.path.abspath(PASTA_DESTINO)}")
    log.info("=" * 60)


if __name__ == "__main__":
    main()