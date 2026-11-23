# 24hrsprinting LLC — storefront + CRM backend foundation

Repo target: `ekfk1003/24hrsnew`. A light, mobile-first eight-product storefront with real reference photography and a proof-request journey. The source is **not yet a live purchasing or payment system**.

## What's in this repository

| File | Purpose |
| --- | --- |
| `index.html` | Homepage, category catalog, product customization, illustrative cart, free proof request form, sample order journey |
| `admin.html` | Protected API-connected login screen and quote/order management dashboard; no credentials hardcoded |
| `config.js` | Public HTTPS backend origin; blank means safe local demo mode |
| `PHOTO_SOURCES.md` | Source/license attribution for each real photograph |
| `backend/app.py` | FastAPI + SQLAlchemy API: products, customers, quotes, proof-request orders, admin auth and statuses |
| `backend/requirements.txt` | Python runtime dependencies |
| `backend/.env.example` | Environment variable names (not secret values) |
| `backend/Dockerfile` | Deployment image for an independent Python host |

## Storefront (GitHub Pages)

Under repository **Settings → Pages**, choose **Deploy from a branch → main → /(root)**. The storefront should appear at https://ekfk1003.github.io/24hrsnew/ after deployment succeeds. The admin client page is `https://ekfk1003.github.io/24hrsnew/admin.html` but is **not usable until the API is deployed**.

## Photo usage

All eight product photos are real photographic references from Pexels and Wikimedia Commons rather than unlicensed supplier/marketplace product listings. Pexels has a commercially reusable photo license; Wikimedia Commons images have CC BY-SA 4.0 credit obligations. See [`PHOTO_SOURCES.md`](PHOTO_SOURCES.md) before any commercial use. **Do not represent these as actual manufactured 24hrsprinting product photos.** Some examples show related products rather than exact material, printing method or SKU. The image URLs remain hosted externally.

## Backend (local first; separate deployment needed)

From the `backend` directory:

```sh
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Fill in ADMIN_EMAIL, a strong ADMIN_PASSWORD, and a long random JWT_SECRET.
set -a; . ./.env; set +a
uvicorn app:app --host 127.0.0.1 --port 8000 --reload
```

Local docs: `http://127.0.0.1:8000/docs`. Health: `/health`. For production, use managed PostgreSQL (`DATABASE_URL=postgresql+psycopg://...`), TLS-enabled HTTPS API hosting, long unique admin password and JWT secret, restrict CORS to the real storefront origin and configure backups. Read [`backend/README.md`](backend/README.md).

When hosted, change **only** the public origin in `config.js` (e.g. `window.HP_API_BASE_URL = "https://api.example.com";`). This enables real lead/proof-request submission to the API without exposing secrets.

## Important current boundaries

- GitHub Pages **does not host Python, databases, admin API, email or payment processing**.
- With `config.js` empty, `index.html` intentionally displays a demo. Forms do not transmit customer data. The cart and demonstration orders live in the browser's localStorage.
- After API is connected, contacts/quote requests/proof requests save to the database. An admin can log in and review/update statuses. This is **not** customer payment, confirmed manufacturing, approval-ready artwork, email, tracking, tax, shipping or full ERP.
- Prices/MOQs are **illustrative**, not verified vendor costs or customer quotes; pricing must be reviewed before any sale.
- Customer artwork input is **local preview only**. The API stores an artwork *filename reference* at most, not the artwork file itself. Add a secured upload service, malware scanning and versioned proof approval before offering artwork submission.
- Production hardening is still needed: migrations, full audit history, backups, delivery emails, monitoring, edge rate limiting, opt-outs, privacy rules, RBAC user management, Stripe/PayPal webhooks, vendor management and workflow automation.

## Developer quick tests

```sh
node --check /tmp/checkfront.js   # use extracted inline JS from index.html, see backend tests for API
cd backend && pytest -q
```