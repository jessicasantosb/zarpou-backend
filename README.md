# 🛫 Zarpou Travel and Tourism — Backend API (Python / FastAPI)

Complete, high-performance backend for the **Zarpou Travel and Tourism** platform, built with **Python 3**, using a modern architecture based on **FastAPI**, **SQLAlchemy 2.0**, **Pydantic v2**, and **JWT** authentication.

The system provides a complete suite of 12 REST API modules connected 1:1 to the Next.js frontend (`C:\Users\jessicabandeira\dev\freelance-zarpou`), covering hotel search, flight and travel package listings, bookings with official booking references (**PNR** in the `ZRP-XXXXXX` format), Pix/card/bank slip payments, travel consulting CRM, and the **AI-powered Virtual Concierge**.

---

## 🛠️ Technology Stack and Architecture

- **Language:** Python 3.10+ (tested with Python 3.14)
- **Web framework:** FastAPI (high performance, type hints, and interactive OpenAPI/Swagger documentation)
- **ASGI server:** Uvicorn with automatic reload support
- **ORM / Database:** SQLAlchemy 2.0 & SQLite (zero-setup local development) / PostgreSQL (Supabase in production)
- **Validation and serialization:** Pydantic v2 with `ConfigDict(from_attributes=True)` and camelCase aliases
- **Security and cryptography:** Bcrypt (secure password hashing) and PyJWT (Bearer access tokens)
- **Automated tests:** Pytest and FastAPI TestClient with end-to-end coverage
- **Third-party integrations:**
  - **AI Concierge:** OpenAI / Groq with an intelligent built-in fallback in Portuguese and recommended contextual actions
  - **Transactional email:** Resend API via asynchronous background tasks
  - **Payment gateways:** MercadoPago / Asaas / Stripe with Pix QR code and bank slip generation
  - **WhatsApp API:** Meta Cloud API and dynamic redirect links

---

## 📁 Project Structure

```text
zarpou-backend/
├── app/
│   ├── api/
│   │   ├── deps.py               # Dependency injection and JWT protection (Admin, Customer, Company)
│   │   └── router.py             # Unified central router that aggregates all features
│   ├── features/                 # Business modules (Clean Architecture: domain, app, infra)
│   │   ├── addons/               # Add-ons (travel insurance, baggage, transfers)
│   │   ├── agency/               # Agency settings, hero section, and metrics
│   │   ├── auth/                 # JWT authentication, 2FA, and account recovery
│   │   ├── bookings/             # Checkout, PNR (ZRP-XXXXXX), Pix QR code, corporate billing
│   │   ├── chat/                 # AI-powered Virtual Travel Concierge and history
│   │   ├── companies/            # Zarpou Business portal (B2B, employees, billing)
│   │   ├── customers/            # B2C customers and travelers (LGPD)
│   │   ├── destinations/         # Domestic and international tourist destinations
│   │   ├── flights/              # Airfares, segments, and connections
│   │   ├── hotels/               # Hotels, rooms, and availability
│   │   ├── inquiries/            # Personalized travel consulting CRM
│   │   ├── packages/             # Combined travel packages (flight + hotel)
│   │   ├── promotions/           # Flash deals, banners, and notifications
│   │   └── users/                # Administrators and Zarpou dashboard staff
│   ├── core/
│   │   ├── config.py             # Environment variables and Pydantic BaseSettings
│   │   ├── database.py           # SQLAlchemy engine, sessions, and Base
│   │   └── security.py           # Bcrypt and JWT token creation/decoding
│   ├── models/                   # Unified SQLAlchemy ORM re-exports
│   ├── schemas/                  # Pydantic v2 validation and serialization schemas
│   ├── seeds/
│   │   └── seed_data.py          # Automatic catalog data loading
│   └── main.py                   # Application startup, CORS, and lifespan
├── tests/                        # Automated end-to-end test suite
├── schema.sql                    # SQL DDL schema for 21 tables and initial data
├── requirements.txt              # Python dependencies
├── .env.example                  # Reference environment variables
├── .env                          # Active local environment configuration
└── README.md                     # Project documentation
```

---

## 🗄️ Data Schema (`schema.sql` — 21 Tables)

The [`schema.sql`](schema.sql) file contains the complete ANSI SQL DDL script, optimized for PostgreSQL (Supabase) and SQLite:

1. **`users`**: Zarpou administrators and agents with role-based access control (RBAC).
2. **`customers`**: Agency travelers (CPF, email, phone).
3. **`companies`**: Companies enrolled in Zarpou Business (CNPJ, credit limit, corporate discount).
4. **`company_employees`**: Employees authorized to book corporate travel by cost center.
5. **`company_invoices`**: Biweekly/monthly invoices with consolidated corporate billing slips.
6. **`destinations`**: Domestic and international destinations with starting prices.
7. **`hero_configs`**: Dynamic home page title, background video, and CTA settings.
8. **`hotels`**: Hotels, resorts, and inns, including star ratings, reviews, and photos.
9. **`rooms`**: Room categories, adult/child capacity, beds, free cancellation, and breakfast.
10. **`flights`**: Airfares, featured deals, and regions (US, Europe, South America).
11. **`flight_segments`**: Outbound and return flight segments with airline codes, times, and IATA airports.
12. **`packages`**: Flight + accommodation bundles with installment calculations of up to 12 payments.
13. **`promotions`**: Marketing campaigns ("Flash Deal", "Dream Northeast").
14. **`addons`**: Additional services (travel insurance, extra 23 kg baggage, VIP transfer).
15. **`bookings`**: Complete orders with a unique PNR (e.g. `ZRP-849201`), itemized amounts, and deadlines.
16. **`booking_travelers`**: Passenger details for each booking (CPF, date of birth, responsible party).
17. **`booking_addons`**: Extra services purchased with each booking.
18. **`payments`**: Payment gateway transactions (Pix, credit card installments, bank slip).
19. **`contact_inquiries`**: Travel consulting requests submitted through the multi-step interactive form.
20. **`agency_settings`**: Legal company information (CNPJ, Cadastur, WhatsApp, dynamic API keys).
21. **`chat_logs`**: Traveler interactions with the Virtual Concierge.

---

## 🔐 Dynamic Credential Management

According to the project guidelines, sensitive third-party integration keys and credentials do **not** need to be hard-coded or stored in `.env`:

- Administrators enter and manage them directly on the frontend settings page (`/admin/configuracoes`).
- They are stored in the database in the `agency_settings` table via `PUT /api/v1/agency/settings`.
- The backend loads these keys at runtime for:
  - **`RESEND_API_KEY`**: Sending confirmation emails and quotes.
  - **`MERCADOPAGO_ACCESS_TOKEN`**: Processing transparent payments.
  - **`WHATSAPP_API_TOKEN`**: Official WhatsApp Cloud messaging integration.
  - **`OPENAI_API_KEY` / `GROQ_API_KEY`**: Intelligent Virtual Concierge engine.

---

## 🚀 Running the Backend

### 1. Start the FastAPI Server

In a terminal (PowerShell on Windows):

```powershell
.\venv\Scripts\uvicorn app.main:app --reload --port 8008
```

### 2. Open the Interactive Documentation

- **Swagger UI:** [http://localhost:8008/docs](http://localhost:8008/docs)
- **ReDoc:** [http://localhost:8008/redoc](http://localhost:8008/redoc)
- **Health check:** [http://localhost:8008/health](http://localhost:8008/health)

### 3. Run the Automated Tests

```powershell
.\venv\Scripts\python.exe -m pytest tests\test_e2e_full.py -v
```

The tests cover:

- Health check and public catalogs for destinations, hotels, flights, packages, and promotions.
- Authentication and Admin and B2C Customer profiles.
- B2B corporate flow (company registration, back-office approval, employees).
- B2C checkout with PNR generation and Pix QR code.
- B2B checkout with deferred billing (`corporate_invoice`), corporate discount, and credit deduction.
- Submitting and listing consulting forms (CRM leads).
- Agency settings and consolidated dashboard metrics.
- Virtual Concierge contextual responses, action links, and session history.

---

## 🌐 Connecting to Supabase in Production

To use Supabase PostgreSQL in production:

1. Copy the connection string URI from the Supabase dashboard.
2. Set `DATABASE_URL` in the `.env` file:

   ```env
   DATABASE_URL="postgresql+psycopg2://postgres:[YOUR_PASSWORD]@db.[YOUR_PROJECT].supabase.co:5432/postgres"
   ```

3. Run [`schema.sql`](schema.sql) in the Supabase SQL Editor, or let the FastAPI lifespan create all 21 tables automatically.

---

## 🔗 Integrating with the Next.js Frontend

Frontend repository: [freelance-zarpou](https://github.com/jessicasantosb/freelance-zarpou).

To connect the frontend (`C:\Users\jessicabandeira\dev\freelance-zarpou`):

1. Add the following to the frontend `.env.local` file:

   ```env
   NEXT_PUBLIC_API_URL=http://localhost:8008/api/v1
   ```

2. All routes under `/api/v1` return data in the formats expected by the Zustand stores (`booking-store.ts`, `product-store.ts`, `auth-store.ts`, `config-store.ts`, `destination-store.ts`).

---

## 📦 Bulk Catalog Import (CSV/Excel + Celery)

The admin dashboard supports large-scale catalog imports and updates (accommodations, destinations, flights, promotions, and coupons) from CSV/XLSX spreadsheets:

1. The upload (`POST /api/v1/imports/{resource}`) only saves the file and creates an `ImportJob`; the response is immediate, avoiding 504 timeouts for large files.
2. Processing runs in the background with **Celery + Redis** (row-by-row validation, type coercion, and upsert by code; failures do not stop the import).
3. The final report (`GET /api/v1/imports/{resource}/jobs`) shows how many rows were imported and which rows failed, including the reason for each failure.

To run locally, Redis and a Celery worker are required:

```bash
# Redis (Docker, port 6379)
docker run -d -p 6379:6379 redis:alpine

# Celery worker (Windows: --pool=solo)
celery -A app.core.celery_app.celery_app worker -l info --pool=solo
```

Configure with `.env`: `REDIS_URL=redis://localhost:6379/0` (use `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND` to override).

Spreadsheet templates (CSV/XLSX) are available at `GET /api/v1/imports/{resource}/template`. Jobs interrupted by a server restart are marked as failed at startup.
