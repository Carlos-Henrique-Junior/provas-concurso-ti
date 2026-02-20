# 📚 Provas Concurso TI — Crawler & Organizador

> Ferramentas automáticas para baixar e organizar provas de concurso público na área de **Tecnologia da Informação**, com foco no concurso do **Hospital de Bonsucesso / EBSERH**.

---

## 🎯 Objetivo

Este projeto automatiza duas tarefas essenciais para quem está se preparando para concursos de TI:

1. **Baixar** todas as provas de TI disponíveis no PCI Concursos
2. **Organizar** os PDFs automaticamente por conteúdo/assunto

---

## 📁 Estrutura do Projeto

```
provas-concurso-ti/
│
├── main.py                  # Crawler — baixa as provas do PCI Concursos
├── Organizar_Pdf_Provas_TI.py  # Organizador — separa PDFs por conteúdo
├── .gitignore
└── README.md
```

---

## ⚙️ Como Usar

### 1. Clone o repositório

```bash
git clone https://github.com/Carlos-Henrique-Junior/provas-concurso-ti.git
cd provas-concurso-ti
```

### 2. Instale as dependências

```bash
pip install requests beautifulsoup4 pymupdf
```

### 3. Baixe as provas

```bash
python main.py
```

As provas serão salvas em `PROVAS_TI_BRASIL/` separadas por categoria.

### 4. Organize os PDFs por conteúdo

```bash
python Organizar_Pdf_Provas_TI.py
```

Os PDFs serão copiados para `PROVAS_ORGANIZADAS/` com a seguinte estrutura:

```
PROVAS_ORGANIZADAS/
├── 🏅 BONSUCESSO e EBSERH/
├── 📡 Redes e Infraestrutura/
├── 🔐 Segurança da Informação/
├── 🗄️ Banco de Dados/
├── 💻 Desenvolvimento de Sistemas/
├── 🖥️ Sistemas Operacionais/
├── 📋 Governança e Gestão de TI/
├── ☁️ Cloud Computing/
├── ⚖️ Legislação e Direito Digital/
├── 🧮 Raciocínio Lógico e Matemática/
├── ✅ Gabaritos/
├── 📄 Editais e Documentos/
└── 📦 Outros/
```

> ✅ Após confirmar que tudo foi copiado corretamente, a pasta `PROVAS_TI_BRASIL/` pode ser deletada.

---

## 🚀 Funcionalidades

### `main.py` — Crawler
- Varre automaticamente todas as páginas de provas de TI do PCI Concursos
- Detecta fim das páginas automaticamente
- Retry automático em caso de falha de conexão
- Downloads paralelos (5 simultâneos)
- Separa provas do Bonsucesso/EBSERH com prioridade
- Log completo salvo em `download_log.txt`

### `Organizar_Pdf_Provas_TI.py` — Organizador
- Lê o conteúdo interno de cada PDF com PyMuPDF
- Classifica por palavras-chave (funciona offline)
- Suporte opcional a IA (Google Gemini) para classificação mais precisa
- Processamento paralelo
- Não apaga os originais (faz cópia)
- Log salvo em `organizar_log.txt`

---

## 🔑 Classificação com IA (opcional)

Para ativar classificação ainda mais precisa com Google Gemini (gratuito):

1. Acesse [aistudio.google.com](https://aistudio.google.com/app/apikey) e gere uma chave grátis
2. No arquivo `Organizar_Pdf_Provas_TI.py`, configure:

```python
GEMINI_API_KEY = "sua-chave-aqui"
```

---

## 📦 Dependências

| Biblioteca | Uso |
|---|---|
| `requests` | Requisições HTTP para o crawler |
| `beautifulsoup4` | Parser HTML das páginas |
| `pymupdf` | Extração de texto dos PDFs |
| `google-generativeai` | Classificação por IA (opcional) |

---

## 📊 Resultados

- **+7.700 provas** baixadas do PCI Concursos
- Organizadas em **12 categorias** por conteúdo
- Prioridade para provas do **Hospital de Bonsucesso / EBSERH**

---

## 👤 Autor

**Carlos Henrique Junior**
- GitHub: [@Carlos-Henrique-Junior](https://github.com/Carlos-Henrique-Junior)

---

## ⚠️ Aviso Legal

Este projeto é para fins exclusivamente educacionais e de estudo para concursos públicos. Os PDFs baixados são de domínio público e disponibilizados gratuitamente pelo PCI Concursos.

---

⭐ Se este projeto te ajudou nos estudos, deixa uma estrela no repositório!
