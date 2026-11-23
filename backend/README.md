# 24hrsprinting backend (API prototype)

This FastAPI/SQLAlchemy application is not hosted on GitHub Pages. It must be deployed to a separate HTTPS backend host with a persistent database.

## Local test

In the `backend` directory:

```sh
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env: secure ADMIN_EMAIL, ADMIN_PASSWORD, JWT_SECRET (32+ chars).
set -a; . ./.env; set +a
uvicorn app:app --host 127.0.0.1 --port 8000 --reload
```

Check `/health`, `/docs`, and `/api/v1/products`. In production, supply PostgreSQL `DATABASE_URL`, long random secrets, a persistent database/backup, TLS, edge rate limiting, and exact frontend origin in `ALLOWED_ORIGINS`. Set only the public API origin (not secrets) in the root `config.js`.

## Implemented scope

* Products, deduplicated contacts, quote requests, proof-request orders, and administrative status updates.
* Salted PBKDF2 passwords, 2-hour JWT authentication, admin/sales/ops/viewer role enforcement and basic audit entries.
* Server-side validation of quantities and product IDs. Estimates are illustrative only.

## Not yet implemented

No live payment, actual production order acceptance, artwork file storage or antivirus scanning, proof version approval, transactional emails, vendor purchasing, shipping, tax, migrations, audit compliance, hosted infrastructure, or full CRM/ERP. No production orders should be accepted until these are implemented and tested.
