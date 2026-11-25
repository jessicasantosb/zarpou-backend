# 🛫 Fly Promo — Backend API (Python / FastAPI)

Complete, high-performance backend for the **Fly Promo** platform, built with **Python 3**, using a modern architecture based on **FastAPI**, **SQLAlchemy 2.0**, **Pydantic v2**, and **JWT** authentication.

The system provides a complete suite of 12 REST API modules connected 1:1 to the Next.js frontend (`the frontend project`), covering hotel search, flight and travel package listings, bookings with official booking references (**PNR** in the `ZRP-XXXXXX` format), Pix/card/bank slip payments, travel consulting CRM, and the **AI-powered Virtual Concierge**.

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
backend/
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
│   │   ├── companies/            # Fly Promo Business portal (B2B, employees, billing)
│   │   ├── customers/            # B2C customers and travelers (LGPD)
│   │   ├── destinations/         # Domestic and international tourist destinations
│   │   ├── flights/              # Airfares, segments, and connections
│   │   ├── hotels/               # Hotels, rooms, and availability
│   │   ├── inquiries/            # Personalized travel consulting CRM
│   │   ├── packages/             # Combined travel packages (flight + hotel)
│   │   ├── promotions/           # Flash deals, banners, and notifications
│   │   └── users/                # Administrators and Fly Promo dashboard staff
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

1. **`users`**: Fly Promo administrators and agents with role-based access control (RBAC).
2. **`customers`**: Agency travelers (CPF, email, phone).
3. **`companies`**: Companies enrolled in Fly Promo Business (CNPJ, credit limit, corporate discount).
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
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8008
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

### Local database commands (PowerShell)

Run these commands from the backend root with the virtual environment set up. Use the same `.env` and `DATABASE_URL` as the running API.

#### Check which database the backend uses

```powershell
.\venv\Scripts\python.exe -c 'from app.core.database import engine; print(engine.dialect.name); print(engine.url.database)'
```

The command prints the database engine and database name or path without printing the connection password.

#### Inspect the SQLite tables

These commands use the Python 3.12+ SQLite CLI. They resolve the configured file and stop if it does not exist.

```powershell
$dbPath = .\venv\Scripts\python.exe -c 'from pathlib import Path; from sys import argv; from app.core.database import engine; assert engine.dialect.name == argv[1]; print(Path(engine.url.database).resolve(strict=True))' sqlite
if ($LASTEXITCODE -eq 0) {
    .\venv\Scripts\python.exe -m sqlite3 $dbPath 'SELECT id, email, role, is_active FROM users ORDER BY email;'
    .\venv\Scripts\python.exe -m sqlite3 $dbPath 'SELECT count(*) AS customers FROM customers;'
}
```

`users` contains staff accounts for `/admin`. The public sign-up flow creates accounts in `customers`. An empty result from the first query means there are no staff accounts.

#### Create an administrator in local SQLite

Paste this block into PowerShell. It prompts for the name, email and password, then saves the account. Password input stays hidden. The command only creates accounts when the backend is configured for local SQLite in development.

```powershell
$adminScript = [System.IO.Path]::GetTempFileName()
try {
    @'
from getpass import getpass

from app.core.config import settings
from app.core.database import SessionLocal, engine
from app.core.security import get_password_hash
from app.main import prepare_database_schema
from app.models.user import User

if engine.dialect.name != "sqlite" or settings.ENVIRONMENT.strip().lower() != "development":
    raise SystemExit("This command requires SQLite in the development environment.")

print(f"SQLite database: {engine.url.database}")
name = input("Administrator name: ").strip()
email = input("Email: ").strip().lower()
if not name or not email:
    raise SystemExit("Enter a name and an email address.")

password = getpass("Password: ")
if password != getpass("Confirm password: "):
    raise SystemExit("The passwords do not match.")
if not password.strip() or len(password) < 8 or len(password.encode("utf-8")) > 72:
    raise SystemExit("Use at least 8 characters and at most 72 UTF-8 bytes.")

prepare_database_schema()
with SessionLocal() as db:
    if db.query(User.id).filter(User.email == email).first():
        raise SystemExit("A staff account already uses this email.")
    db.add(User(name=name, email=email, role="admin", password_hash=get_password_hash(password)))
    db.commit()

print(f"Administrator created: {email}")
'@ | Set-Content -LiteralPath $adminScript -Encoding utf8
    .\venv\Scripts\python.exe -c 'from runpy import run_path; from sys import argv; run_path(argv[1])' $adminScript
} finally {
    Remove-Item -LiteralPath $adminScript
}
```

Sign in at `/admin` with the email and the original password you entered.

If login returns HTTP 500 with a Redis connection error at `localhost:6379`, leave `RATE_LIMIT_STORAGE_URI=` blank in your local `.env` and restart Uvicorn. The rate limiter uses memory with this setting, so local login works without Redis.

#### Generate a bcrypt hash only

Use this command when you need to populate `users.password_hash` manually.

```powershell
.\venv\Scripts\python.exe -c 'from getpass import getpass; from app.core.security import get_password_hash; print(get_password_hash(getpass()))'
```

---

## 🌐 Connecting to Supabase in Production

To use Supabase PostgreSQL in production:

1. Copy the connection string URI from the Supabase dashboard.
2. Set `DATABASE_URL` in the `.env` file:

   ```env
   DATABASE_URL="postgresql+psycopg2://postgres:[YOUR_PASSWORD]@db.[YOUR_PROJECT].supabase.co:5432/postgres"
   ```

3. Let the FastAPI lifespan prepare the database, or run the schema preparation command in the deploy step. The reference [`schema.sql`](schema.sql) includes demonstration data for local use.

---

## 🔗 Integrating with the Next.js Frontend

To connect the frontend:

1. Add the following to the frontend `.env.local` file:

   ```env
   NEXT_PUBLIC_API_URL=http://localhost:8008/api/v1
   ```

2. All routes under `/api/v1` return data in the formats expected by the Zustand stores (`booking-store.ts`, `product-store.ts`, `auth-store.ts`, `config-store.ts`, `destination-store.ts`).

### Deploying administrative authentication

- Set `ENVIRONMENT=production` and a unique `SECRET_KEY` of at least 32 characters on Render. Set a separate `AUTH_SESSION_SECRET` of at least 32 characters on Vercel. Changing the backend key invalidates existing JWTs and affects TOTP secrets encrypted with the previous key, so plan re-enrollment or key migration if replacing an existing key.
- Deploy the frontend and backend together. If an account has MFA enabled, the admin login returns a challenge and the panel verifies it before starting the session. Set the public HTTPS `FRONTEND_URL` and configure `RESEND_API_KEY` and `RESEND_FROM_EMAIL` on Render. Use a sender address verified by Resend and set the real `CONTACT_EMAIL` and `PRIVACY_EMAIL` for Fly Promo.
- With multiple API instances, set `RATE_LIMIT_STORAGE_URI` to the same Redis URI on each instance. To run the existing schema updates once per release, run `python -c "from app.main import prepare_database_schema; prepare_database_schema()"` in the deploy step and set `SCHEMA_MIGRATIONS_ON_STARTUP=False` on the web instances after that step is configured.

---

## Geographic reference catalog

Import the [GeoNames data exports](https://www.geonames.org/export) into the database configured by `DATABASE_URL` before using the location endpoints.

```powershell
.\venv\Scripts\python.exe -m scripts.import_locations
```

To reuse downloaded files, pass `--source-dir` with a directory containing `countryInfo.txt`, `admin1CodesASCII.txt`, and `cities500.zip`. Run the import again to refresh the catalog. Each import replaces the three reference tables in one transaction. The city export covers populated places with more than 500 residents and selected administrative seats. The data is provided by GeoNames under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Include GeoNames attribution when displaying the data.

| Route | Result |
| --- | --- |
| `GET /api/v1/locations/countries` | Countries with their two-letter codes |
| `GET /api/v1/locations/countries/{country_code}/states` | First-level administrative divisions of the country |
| `GET /api/v1/locations/countries/{country_code}/cities` | Cities in the country with optional `state_code`, `q`, `limit`, and `offset` parameters |

Use the `code` returned by the states route as `state_code`. Omit it to search across a country, including places without a state code. The city search matches the start of a name regardless of accents or case. `limit` defaults to 50 and accepts up to 100, and `offset` defaults to 0.

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
