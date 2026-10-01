# Assessor pessoal com IA

Aplicação acadêmica de inteligência artificial para auxiliar na organização financeira e no gerenciamento de compromissos. O projeto reúne uma API em FastAPI e uma interface de conversa no navegador.

As mensagens são encaminhadas a agentes especializados por meio do LangGraph. Cada agente utiliza ferramentas para consultar ou registrar informações nos bancos de dados.

## Funcionalidades

- Registro, consulta e atualização de transações financeiras.
- Consulta de saldo e organização de gastos por categoria.
- A agenda não está habilitada nesta versão; comentários sobre viagens podem ser mantidos como contexto da conversa.
- Respostas a perguntas frequentes com base em um documento PDF.
- Histórico de conversas e resumos de sessões para consultas posteriores.
- Verificações de entrada e saída das mensagens por meio de guardrails.
- Interface web e documentação interativa da API.

## Tecnologias

| Tecnologia | Uso no projeto |
| --- | --- |
| Python e FastAPI | Implementação da API |
| Uvicorn | Execução do servidor |
| LangChain e LangGraph | Integração com modelos e coordenação dos agentes |
| Google Gemini e Groq | Modelos de linguagem |
| PostgreSQL | Dados financeiros |
| MongoDB | Sessões e histórico das conversas |
| Qdrant | Busca semântica de FAQ e memórias |
| HTML, CSS e JavaScript | Interface do usuário |

## Estrutura

```text
migracao_fastAPI/
├── app/
│   ├── routes/         # Rotas de chat e sessões
│   ├── tools/          # Ferramentas utilizadas pelos agentes
│   ├── config.py       # Configuração e variáveis de ambiente
│   ├── graph.py        # Fluxo de execução dos agentes
│   ├── guardrail.py    # Verificações de mensagens
│   ├── ingest_faq.py   # Indexação do PDF no Qdrant
│   ├── llms.py         # Integração com os modelos
│   ├── main.py         # Inicialização da API e interface
│   ├── memory.py       # Memória das conversas
│   ├── prompts.py      # Instruções dos agentes
│   ├── schemas.py      # Contratos de entrada e saída
│   └── vectorstore.py  # Integração com o banco vetorial
├── data/
│   └── FAQ_assessor_v1.1.pdf
├── frontend/           # Interface de conversa
├── requirements.txt
└── README.md
```

## Como executar no Windows

Execute os comandos no terminal, dentro da pasta `migracao_fastAPI`.

### 1. Preparar o ambiente Python

Utilize Python 3.11 ou superior. Crie o ambiente virtual e instale as dependências:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Os comandos usam diretamente o Python do ambiente virtual; não é necessário ativá-lo no PowerShell. Caso a pasta `.venv` tenha sido copiada de outro projeto e não funcione, recrie o ambiente nesta pasta.

### 2. Configurar as variáveis de ambiente

Crie um arquivo chamado `.env` na raiz do projeto, no mesmo nível de `requirements.txt`, com os seguintes campos:

```dotenv
GEMINI_API_KEY=sua_chave_gemini
GROQ_API_KEY=sua_chave_groq
DATABASE_URL=postgresql://usuario:senha@localhost:5432/assessor
MONGODB_URI=mongodb://localhost:27017
QDRANT_URL=https://seu_cluster.qdrant.io
QDRANT_API_KEY=sua_chave_qdrant
FAQ_PDF_PATH=data/FAQ_assessor_v1.1.pdf
```

Substitua os exemplos pelos dados dos seus serviços. O arquivo `.env` contém credenciais e não deve ser compartilhado ou publicado.

PostgreSQL, MongoDB e Qdrant precisam estar configurados e acessíveis. A instalação das dependências Python não instala esses serviços nem prepara o esquema financeiro. As ferramentas financeiras esperam tabelas como `transactions`, `transaction_types` e `categories` no PostgreSQL, com estrutura compatível com o código.

### 3. Indexar o documento de perguntas frequentes

Antes da primeira consulta ao FAQ, execute:

```powershell
.\.venv\Scripts\python.exe -m app.ingest_faq
```

O comando lê o PDF em `data/`, gera embeddings e armazena os trechos no Qdrant. Ele depende da configuração dos serviços de embeddings e do Qdrant. A rotina não apaga pontos existentes; ao trocar o PDF, trechos antigos podem permanecer no índice.

### 4. Iniciar o servidor

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Com o servidor em execução, acesse:

- [Conversa com o assistente](http://localhost:8000)
- [Documentação interativa da API](http://localhost:8000/docs)
- [Diagnóstico dos serviços](http://localhost:8000/health)

Para encerrar o servidor, pressione `Ctrl + C` no terminal.

## Rotas da API

| Método | Rota | Finalidade |
| --- | --- | --- |
| `POST` | `/chat` | Enviar uma mensagem ao assistente |
| `POST` | `/sessions/{session_id}/encerrar` | Encerrar uma sessão e solicitar seu resumo |
| `GET` | `/health` | Verificar configuração e conectividade dos serviços |

### Enviar uma mensagem

Exemplo de corpo para `POST /chat`:

```json
{
  "session_id": "sessao-01",
  "user_id": "usuario_teste",
  "pergunta": "Gastei 50 reais no mercado hoje."
}
```

A resposta contém `resposta`, com o texto do assistente, e `agentes_chamados`, com a lista de agentes acionados. Mantenha o mesmo `session_id` durante uma conversa e o mesmo `user_id` para identificar o usuário entre sessões.

## Memória das conversas

O MongoDB armazena as informações das sessões. Ao encerrar uma sessão, a aplicação gera um resumo, que pode ser indexado no Qdrant e recuperado por semelhança de significado em consultas futuras. O FAQ utiliza uma base própria de trechos extraídos do PDF.
