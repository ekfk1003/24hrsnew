# 24hrsprinting / Business HQ — Gap audit and implementation roadmap
Date: 2026-11-27 | Repository: ekfk1003/24hrsnew | Scope: current deployed prototype and user's earlier Business HQ/order-flow brief

## Executive verdict

This is a connected **test prototype**, not a complete selling/fulfillment ERP. The API and PostgreSQL product records, quote and proof-request intake, basic admin login, contacts, product edits, and admin status updates exist. Current catalog = 8 sample products with unapproved illustrative prices. No real payment, customer artwork upload, vendor purchasing, or shipment integration is implemented. Do not advertise those as operational.

The biggest gap is a **single durable order/job model** shared by buyer, sales, design, supplier, payments, shipping and support. The existing app has quotes and proof requests but lacks finalized order/quote versions, approvals, line-level vendor costing and verified fulfillment.

## Source requirements carried forward

From the 24hrsprinting Business HQ brief and order-flow research (2026-11-07 / 2026-11-22):
- A mobile-first lanyard buyer chooses width, material, print sides, attachment, quantity; a wristband buyer chooses size, color, imprint, quantities per artwork design.
- Buyers upload files, preview, enter delivery ZIP and required date, see exactly what is included, and receive one reliable reference through reorders, proofs, price, checkout, production and shipment.
- Staff must view the same ordered specification, artwork revision, approved amount, vendor, fulfillment state and support history.
- Future business scope: CRM, vendor quotes/POs, margin checks, payment links/deposits, GetResponse, social and WhatsApp approvals, marketing research, website monitoring, and AI-assisted operations.
- Acceptance tests must cover pricing consistency, no duplicate submissions, stale proof approval rejection, recoverable missing artwork, resume-on-mobile, rollback without altering accepted records.

## Audit by category

| Area | Current implementation | Missing / risks | Priority |
|---|---|---|---|
| Site structure and navigation | One HTML storefront + separate admin; responsive admin shell | Stable product-specific routes, SEO metadata, accessibility audit, URL previews, consistent navigation/search/filters | P1 |
| Visual system | Brand palette and photographic references; new Material-inspired admin density/nav | Verified commercially licensed product images per exact SKU, cohesive photo art direction, design token library, accessibility/contrast tests | P1 |
| Catalog | Eight DB records with name, category, minimum and illustrative cents | Product families/SKUs, inventory, published status, product options, material, print areas, dimensions, tier pricing, imagery/media and vendor mappings | P0 |
| Pricing | Illustrative prices; editable name/minimum/unit estimate | Pricing versions, approved quote lines, qty breaks, freight/rush/tax/discount calculation, margin gates, shared server totals | P0 |
| Configuration | Simple product-specific fields on frontend | Schema-driven configuration per product and valid-combination rules; save/resume; rendered proof mockup tied to selections | P0 |
| Inquiry and cart | API quote and proof-request order storage | Server idempotency, draft recovery, revisions, order line schema, structured address, timeline, clear customer confirmation email | P0 |
| Artwork | Browser-only preview; filename stored in order | Private signed uploads, virus scanning, versioned proofs, technical checks, explicit latest-version approval | P0 |
| CRM | Contacts and admin list | Lead source, history, tags, consent/opt-outs, opportunities, assignments, reminders, duplicate resolution, email threading | P1 |
| Customer portal | Demo history in localStorage | Verified email/order access, shared status, secure order/resume, historical approved assets, reorders | P0 |
| Vendor/PO | Reference specifications only | Vendor records, quote request, price book, production purchase orders, QC, dispatch and dispute/returns workflow | P1 |
| Production and shipping | Missing | Job tickets, status transition rules, handoffs, ship-by SLA, carrier APIs, tracking, delay alerts | P1 |
| Payments | Explicitly off | Stripe/PayPal sandbox checkout after approval, signed webhooks, idempotency, taxes, invoicing, deposit/balance/refund | P1 |
| AI/marketing | Reference modules only | Human approval, campaign drafts, permission-based audiences, GetResponse sync, scheduling, analytics, audit of AI suggestions | P2 |
| Admin permissions | PBKDF2 login, JWT, role checks | MFA, password recovery, user management, session revocation, SSO, fine-grained audit events, privacy rules | P0 security |
| Database | Supabase Postgres in app_private | Formal migrations, versioned backups, restore exercises, least-privilege DB account, row-level security review | P0 security |
| Reliability | FastAPI tests + frontend static CI; free Render | Browser E2E, load testing, caching, incident monitoring, restart/drift alerts, staged deployment rollback | P0 |
| Mobile UX | Responsive admin/sidebar plus storefront | Device matrix, cart/forms progress and input validation, large tap targets, save/resume, poor network handling | P1 |
| Analytics | None verified | Privacy-aware conversion funnel, quote-to-order, source attribution, product interest, slow-route/error tracking | P2 |

## Work completed in this improvement pass

1. Added `hq-experience.css`: responsive sidebar/density, accessible focus states, Material-inspired surfaces/cards, mobile navigation.
2. Added `hq-experience.js`: live-vs-planned navigation; quick actions; browser-read-only health/catalog diagnostic page; clearly labeled reference modules for artwork, vendors, production, payments, marketing and security.
3. Integrated both assets into `admin.html`, plus the authenticated activity/audit view already backed by API.
4. Added static frontend integrity CI to check linked resources, required navigation IDs, browser script syntax and public config hygiene.
5. Existing API tests exercise product lookup, quote, proof request, login, status changes, product updates and contact retrieval.

## Recommended architecture (incrementally, **not** a wholesale rewrite)

Keep GitHub Pages + Render FastAPI + Supabase Postgres during test phase, while isolating UI/backend services by stable REST contracts.

- **UI now:** small, dependency-free Material-inspired custom components and CSS design tokens. Material Web (`@material/web`) is an option for selected controls after component-level accessibility and bundle-size review, not an installed dependency.
- **Data:** Supabase PostgreSQL with Alembic migrations; private artwork storage via Supabase Storage signed URLs and strict policy controls; separate database roles and reviewed RLS.
- **Order model:** orders, line_items, configurations, quote_versions, artwork_assets, proof_versions, approvals, events, payments and vendor jobs with immutable revisions and idempotency keys.
- **Testing:** Python API contract/security tests in GitHub Actions; Playwright browser E2E with mobile and desktop Chromium/WebKit/Firefox; seeded synthetic test users only.
- **Observability:** structured server logs, error tracking (e.g. Sentry), OpenTelemetry traces, uptime/error budget and automated alerts; no secrets logged.
- **Payments:** Stripe Checkout / PayPal only in sandbox first, with verified webhook signatures and duplicate-event resistance.
- **Marketing:** existing GetResponse and social integrations through scoped APIs with **draft → user approval → publish**, consent and opt-out enforcement.
- **Publishing:** `main` for explicitly approved/verified work, staging previews for changes and rollback capability; never replace working flows with mockup widgets.
- **AI:** role-scoped research/draft assistants; no autonomous payment, supplier purchase, live price revision or mass publishing without approval.

## Critical test sequence (must pass before first customer pilot)

1. Deployment: code on GitHub matches Render and GitHub Pages revisions; health and DB product read both succeed.
2. Admin login: valid admin succeeds; invalid password and unauthenticated admin routes fail.
3. Catalog: change sample name/minimum/price in admin; verify exact same values on refreshed storefront and API.
4. Quote: submit synthetic quote from storefront; preserve server reference; match it and buyer details in admin + database.
5. Order: configure two different products, checkout as proof-request only; verify items/quantities and the same reference in admin.
6. Status: change status; refresh admin and check persistent audit event; invalid role/status rejected.
7. Edge cases: minimum quantity, invalid product, unsafe HTML in notes, mobile form, offline/network retry, double-click/re-submit, slow/free Render wake-up.
8. Security: RLS/permissions/DB grants and backups reviewed, secrets absent from public files and logs, MFA and privacy disclosures before real use.

Do not call a fake confirmation an order placement. The system currently acknowledges **quote** and **proof request**, not a paid or scheduled manufacturing job.

## Definition of done for first real pilot

A buyer can configure one complete product, upload artwork to private storage, receive a durable shared reference, review an explicit price and proof, approve the exact proof version, pay via verified sandbox (then approved live) checkout, and track production/delivery. Business HQ shows the identical immutable record with audit trail and human override controls.

### Research links
- Material Web components: https://github.com/material-components/material-web
- Playwright E2E: https://playwright.dev/docs/intro
- Supabase private storage/security: https://supabase.com/docs/guides/storage/security/access-control
- Supabase signed uploads: https://supabase.com/docs/reference/javascript/file-buckets-createsigneduploadurl
- OWASP webhook security: https://cheatsheetseries.owasp.org/cheatsheets/Webhook_Security_Cheat_Sheet.html
