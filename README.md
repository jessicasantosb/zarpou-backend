# 🛫 Zarpou Viagens e Turismo — Backend API (Python / FastAPI)

Backend completo e de alta performance da plataforma **Zarpou Viagens e Turismo**, desenvolvido em **Python 3** com arquitetura moderna baseada em **FastAPI**, **SQLAlchemy 2.0**, **Pydantic v2** e autenticação **JWT**.

O sistema fornece uma suíte completa de 12 módulos de APIs RESTful conectadas 1:1 ao frontend Next.js (`C:\Users\jessicabandeira\dev\freelance-zarpou`), abrangendo busca de hotéis, emissão de voos e pacotes, geração de reservas com localizador oficial (**PNR** no padrão `ZRP-XXXXXX`), faturamento corporativo para empresas (**Zarpou Empresas B2B**), pagamentos Pix/Cartão/Boleto, CRM de consultoria de viagens e o **Concierge Virtual com Inteligência Artificial**.

---

## 🛠️ Tecnologias e Arquitetura

- **Linguagem:** Python 3.10+ (testado no Python 3.14)
- **Framework Web:** FastAPI (alta performance, tipagem estática e documentação OpenAPI/Swagger interativa)
- **Servidor ASGI:** Uvicorn com suporte a reload automático
- **ORM / Banco de Dados:** SQLAlchemy 2.0 & SQLite (local zero-setup) / PostgreSQL (Supabase em produção)
- **Validação e Serialização:** Pydantic v2 com `ConfigDict(from_attributes=True)` e aliases camelCase
- **Segurança & Criptografia:** Bcrypt (hashing de senhas seguro) e PyJWT (tokens de acesso Bearer)
- **Testes Automatizados:** Pytest e FastAPI TestClient com 100% de aprovação end-to-end
- **Integrações de Terceiros:**
  - **IA Concierge:** OpenAI / Groq com fallback nativo inteligente em português e ações contextuais recomendadas
  - **E-mails Transacionais:** Resend API via background tasks assíncronas
  - **Gateways de Pagamento:** MercadoPago / Asaas / Stripe com geração de QR Code Pix e boleto
  - **WhatsApp API:** Meta Cloud API e links de redirecionamento dinâmico

---

## 📁 Estrutura do Projeto

```text
zarpou-backend/
├── app/
│   ├── api/
│   │   ├── deps.py               # Injeção de dependências e proteção JWT (Admin, Cliente, Empresa)
│   │   └── router.py             # Roteador central unificado que agrega todas as features
│   ├── features/                 # Módulos de negócio (Clean Architecture: domain, app, infra)
│   │   ├── addons/               # Adicionais (seguro viagem, bagagem, traslados)
│   │   ├── agency/               # Configurações da agência, Hero e métricas
│   │   ├── auth/                 # Autenticação JWT, 2FA e recuperação
│   │   ├── bookings/             # Checkout, PNR (ZRP-XXXXXX), Pix QR Code, Faturamento PJ
│   │   ├── chat/                 # Concierge Virtual de Viagens com IA e histórico
│   │   ├── companies/            # Portal Zarpou Empresas (B2B, Colaboradores, Faturamento)
│   │   ├── customers/            # Clientes e viajantes B2C (LGPD)
│   │   ├── destinations/         # Destinos turísticos nacionais e internacionais
│   │   ├── flights/              # Passagens aéreas, trechos e conexões
│   │   ├── hotels/               # Hotéis, quartos e disponibilidades
│   │   ├── inquiries/            # CRM de consultoria de viagens personalizada
│   │   ├── packages/             # Pacotes turísticos integrados (Aéreo + Hotel)
│   │   ├── promotions/           # Ofertas relâmpago, banners e notificações
│   │   └── users/                # Administradores e equipe do painel Zarpou
│   ├── core/
│   │   ├── config.py             # Variáveis de ambiente e Pydantic BaseSettings
│   │   ├── database.py           # Engine SQLAlchemy, sessões e Base
│   │   └── security.py           # Bcrypt e criação/decodificação de tokens JWT
│   ├── models/                   # Re-exports unificados ORM SQLAlchemy
│   ├── schemas/                  # Schemas de validação e serialização Pydantic v2
│   ├── seeds/
│   │   └── seed_data.py          # Carga automática de dados do catálogo
│   └── main.py                   # Inicialização da aplicação, CORS e lifespan
├── tests/                        # Suíte completa de testes automatizados end-to-end
├── schema.sql                    # Modelagem SQL DDL de 21 tabelas e dados iniciais
├── ESPECIFICACOES_BACKEND.md     # Especificação técnica detalhada de arquitetura
├── requirements.txt              # Dependências Python instaladas
├── .env.example                  # Variáveis de ambiente de referência
├── .env                          # Configurações ativas para ambiente local
└── README.md                     # Documentação do projeto
```

---

## 🗄️ Modelagem de Dados (`schema.sql` — 21 Tabelas)

O arquivo [`schema.sql`](file:///c:/Users/jessicabandeira/dev/zarpou-backend/schema.sql) contém o script DDL ANSI-SQL completo e otimizado para PostgreSQL (Supabase) e SQLite:

1. **`users`**: Administradores e agentes da Zarpou com controle de acesso (RBAC).
2. **`customers`**: Viajantes registrados na agência (CPF, e-mail, telefone).
3. **`companies`**: Empresas conveniadas no Zarpou Empresas (CNPJ, limite de crédito, desconto PJ).
4. **`company_employees`**: Colaboradores autorizados a emitir viagens corporativas por centro de custo.
5. **`company_invoices`**: Faturas quinzenais/mensais com boletos consolidados para faturamento PJ.
6. **`destinations`**: Destinos turísticos nacionais e internacionais com preços a partir de.
7. **`hero_configs`**: Configurações dinâmicas de títulos, vídeo de fundo e CTA da Home.
8. **`hotels`**: Hotéis, resorts e pousadas, estrelas, avaliação e fotos.
9. **`rooms`**: Categorias de quartos, capacidade de adultos/crianças, camas, cancelamento grátis e café da manhã.
10. **`flights`**: Tarifas aéreas, destaques, regiões (EUA, Europa, América do Sul).
11. **`flight_segments`**: Trechos de voo (ida e volta) com código de companhia aérea, horários e aeroportos IATA.
12. **`packages`**: Combinação de hospedagem + aéreo com cálculo de parcelas em até 12x.
13. **`promotions`**: Campanhas comerciais ("Oferta Relâmpago", "Nordeste dos Sonhos").
14. **`addons`**: Serviços adicionais (Seguro Viagem, Bagagem Extra 23kg, Transfer VIP).
15. **`bookings`**: Pedidos completos com localizador PNR único (ex: `ZRP-849201`), discriminação de valores e prazos.
16. **`booking_travelers`**: Dados dos passageiros da reserva (CPF, data de nascimento, responsável).
17. **`booking_addons`**: Serviços extras contratados em cada compra.
18. **`payments`**: Registro de transações com gateways (Pix, Cartão de Crédito com parcelas, Boleto).
19. **`contact_inquiries`**: Consultorias de roteiros solicitadas através do formulário interativo de múltiplos passos.
20. **`agency_settings`**: Dados legais da empresa (CNPJ, Cadastur, WhatsApp, chaves de API dinâmicas).
21. **`chat_logs`**: Histórico das interações do viajante com o Concierge Virtual.

---

## 🔐 Gerenciamento Dinâmico de Credenciais

Conforme diretriz do projeto, as chaves e credenciais sensíveis de integrações externas **não precisam ser fixadas em código nem no `.env`**:
- Elas são inseridas e gerenciadas diretamente pelo administrador na tela de configurações do frontend (`/admin/configuracoes`).
- São persistidas no banco de dados na tabela `agency_settings` via endpoint `PUT /api/v1/agency/settings`.
- O backend carrega essas chaves em tempo de execução para:
  - **`RESEND_API_KEY`**: Disparo de e-mails de confirmação e cotações.
  - **`MERCADOPAGO_ACCESS_TOKEN`**: Processamento de pagamentos transparentes.
  - **`WHATSAPP_API_TOKEN`**: Integração oficial de mensagens do WhatsApp Cloud.
  - **`OPENAI_API_KEY` / `GROQ_API_KEY`**: Motor do Concierge Virtual inteligente.

---

## 🚀 Como Executar o Backend

### 1. Iniciar o Servidor FastAPI
No terminal (PowerShell no Windows):
```powershell
.\venv\Scripts\uvicorn app.main:app --reload --port 8000
```

### 2. Acessar a Documentação Interativa
- **Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **Health Check:** [http://localhost:8000/health](http://localhost:8000/health)

### 3. Executar os Testes Automatizados
```powershell
.\venv\Scripts\python.exe -m pytest tests\test_e2e_full.py -v
```
Todos os testes cobrem:
- Health check e catálogo público de destinos, hotéis, voos, pacotes e promoções.
- Autenticação e perfil de Administrador e Clientes B2C.
- Fluxo corporativo B2B (cadastro de empresa, aprovação backoffice, colaboradores).
- Checkout B2C com geração de PNR e Pix QR code.
- Checkout B2B com faturamento à prazo (`corporate_invoice`), desconto PJ e dedução de crédito.
- Envio e listagem de formulários de consultoria (CRM Leads).
- Configurações da agência e métricas consolidadas do dashboard.
- Concierge Virtual com respostas contextuais, links de ação e histórico de sessão.


---

## 🌐 Conexão com Supabase em Produção

Para utilizar o Supabase PostgreSQL em ambiente de produção:
1. No painel do Supabase, copie a connection string no formato URI.
2. Defina no arquivo `.env`:
   ```env
   DATABASE_URL="postgresql+psycopg2://postgres:[SUA_SENHA]@db.[SEU_PROJETO].supabase.co:5432/postgres"
   ```
3. Execute o script [`schema.sql`](file:///c:/Users/jessicabandeira/dev/zarpou-backend/schema.sql) diretamente no SQL Editor do Supabase ou deixe o lifespan do FastAPI criar automaticamente as 21 tabelas.

---

## 🔗 Integração com o Frontend Next.js

Para conectar o frontend (`C:\Users\jessicabandeira\dev\freelance-zarpou`):
1. No arquivo `.env.local` do frontend:
   ```env
   NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
   ```
2. Todas as rotas expostas em `/api/v1` respondem nos formatos das stores Zustand (`booking-store.ts`, `product-store.ts`, `auth-store.ts`, `config-store.ts`, `destination-store.ts`).
