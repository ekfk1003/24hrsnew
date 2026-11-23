# Live backend test: Supabase + Render

This is a **testing environment**, not a completed e-commerce checkout. The public site remains at https://ekfk1003.github.io/24hrsnew/ and a private API and database are hosted separately. No real payments are taken.

## 1. Create the Supabase database

1. Open https://supabase.com/dashboard and create a project (free tier if eligible).
2. In the project's **Connect** panel, choose the **Session pooler** connection URI, not the direct IPv6-only connection, unless your application host supports IPv6. SQLAlchemy maintains its own small pool. Keep the original URI secret and include the database password.
3. **Never** commit the connection URI, database password, or Supabase service-role key into GitHub or `config.js`.

The API creates tables in the PostgreSQL **app_private** schema, not the public schema. It requires permissions to create its schema and tables. Database migrations, backups and a dedicated least-privilege database user are required before production.

## 2. Deploy the Python API on Render

1. Connect Render at https://dashboard.render.com/ to the GitHub repository **ekfk1003/24hrsnew**.
2. Select **New → Blueprint** using the root `render.yaml` file, or create a Python web service with root directory `backend`, build `pip install -r requirements.txt`, and start `uvicorn app:app --host 0.0.0.0 --port $PORT`.
3. Supply secrets using **Render environment variables**, **never GitHub files**:
   - `DATABASE_URL`: full Supabase Session pooler connection string, including password
   - `ADMIN_EMAIL`: your test administrator email
   - `ADMIN_PASSWORD`: unique administrator password at least 14 characters long
   - `JWT_SECRET`: random, 32+ character secret (the Blueprint generates it)
   - `ALLOWED_ORIGINS`: `https://ekfk1003.github.io`
   - `APP_ENV`: `production`
4. Once Render reports live, open `https://YOUR-RENDER-HOST/health`. A healthy response is `{"status":"ok","payments_enabled":false}`; then verify product records using `/api/v1/products`. The `/health` route alone does **not** prove the DB is connected. Because this API initializes its tables at startup, a successful startup followed by products query proves the initial connection and catalog read.
5. Edit the **public-only** `config.js` in GitHub: `window.HP_API_BASE_URL = "https://YOUR-RENDER-HOST";`. This activates storefront requests. No credentials or keys belong there. GitHub Pages will redeploy.

## 3. End-to-end smoke test

1. Open storefront, choose a product, enter a test identity such as `Test Buyer` and `test-buyer@example.invalid`, and submit a proof request with valid minimum quantity (e.g. 100 lanyards).
2. The site must show a server-generated `Q-...` quote reference, not a demo summary.
3. Open `https://ekfk1003.github.io/24hrsnew/admin.html`; sign in with the ADMIN_EMAIL/ADMIN_PASSWORD configured on Render.
4. Verify the quote appears and status updates persist after refreshing the dashboard.
5. Test sample order with cart + checkout. It should create a `PR-...` **proof-request**, not a paid order. Verify it in the admin dashboard, without submitting payment information.

## Before accepting real customers
Add reliable event logging/alerts, SQL migrations, independent secure artwork uploads, malware scanning, transactional email, stronger per-user access controls, privacy policy/data retention, validated pricing/shipping/tax, payment provider integration and proof version approval. Free hosting can sleep and free Supabase databases can be paused or subject to usage quotas.

## Files
- `backend/app.py`: FastAPI API with schema-isolated Supabase Postgres support and local SQLite tests
- `backend/.env.example`: names of required variables
- `render.yaml`: optional Render Blueprint; secret values must be supplied interactively
- `config.js`: browser-safe API origin only, currently blank until the backend has a verified hostname
