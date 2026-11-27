# 24hrsprinting AI Commerce OS — SaaS API and Growth Integration Research
**Research date:** 2026-11-27  
**Target repository:** `ekfk1003/24hrsnew`  
**Scope:** Full promotional-products storefront + CRM + product syndication + lead intelligence + marketing + AI approval operating system.

## Status warning (read first)

The currently deployed **working** platform is GitHub Pages storefront, Render Python FastAPI and Supabase PostgreSQL. The catalog, quote/proof-request API, admin login, product edits, CRM contact list and status updates have been tested in API CI. **External social, store and lead-provider OAuth accounts have not been integrated into Render.** Creating a registry entry or internal approved draft does not connect, publish, message or sync. GetResponse is accessible as a separate ChatGPT integration but its API connection *inside Business HQ* has not been established; the attempted GetResponse contact-list read was not authorized in this session. Likewise GitHub and Supabase connected inside ChatGPT are separate from provider credentials in the hosted application.

## API integration feasibility and authorization matrix

| Platform | Proposed value | Supported technical path | Required permission / constraint | Phase |
|---|---|---|---|---|
| Facebook Pages | Public promotions + comments | Meta Graph API Page publishing and insights | Facebook Page manager grant, eligible app review and Page token | 1 |
| Instagram professional | Brand reels/carousels | Instagram Platform / Graph API content publishing | Authorized professional account, Meta app review/scopes and media compliance | 1 |
| LinkedIn organization | U.S. business campaigns | LinkedIn Posts API | Company-admin identity, `w_organization_social`, approved developer access, current version | 1 |
| Pinterest | Product inspiration + Pins | Pinterest API | Developer app and authorized business account | 1 |
| YouTube | Product demonstrations/shorts | YouTube Data API | Google OAuth, upload scope, quotas and possible app review | 2 |
| X | Announcements + buyer engagement | X Developer API | OAuth and consumption-based API costs; recheck actual plan before purchase | 2 |
| TikTok | Product use-case videos | Content Posting API | Creator/account authorization, compliance audit; unreviewed apps may have visibility restrictions | 2 |
| Reddit | Authentic participation, research | Official Reddit API and community posts | API terms, community-specific rules, commercial access where necessary; **no unsolicited mass posting** | 3 |
| Telegram channels | Approved channel updates | Telegram Bot API | Bot token and channel administrator role | 1 |
| WhatsApp Business | Opted-in customer service and order updates | WhatsApp Business Platform | Meta business onboarding, templates, consent, conversation rules | 2 |
| WhatsApp Channels | Public one-way updates | Manual publishing until verified official channel-post API exists | Do not mistake Business messaging API for Channels posting | Manual |
| Google Business Profile | Local presence and updates | Business Profile APIs | Verified eligible location, Google project and restricted access | 2 |
| Google Merchant Center | Shopping catalog | Merchant API | Merchant account, feed rules, OAuth/approval | 1 |
| RSS | Blogs/news distribution | First-party feed generator | Own content URLs and canonical URLs | 1 |
| Craigslist / Yelp / BBB / Alignable | Appropriate listings | Manual / provider-approved routes | Do not simulate generic public auto-post APIs | Manual |
| GetResponse | Email marketing, segmentation, journey analytics | GetResponse API or separately connected plugin | Approved sender identity, compliant audience and opt-out suppression | 1 |
| Shopify | Product/order synchronization | Admin GraphQL API + webhooks | Installed app, per-store OAuth and proper access scopes | 1 |
| WooCommerce | Product/order sync | WC REST API + webhooks | Store-owned authorized keys, per-shop webhook signature | 1 |
| osCommerce (24hrsprinting.com) | Existing store catalog/migration | Version-specific custom server connector | Confirm osCommerce version, database/plugin model, test checkout integrity | 1 |
| Etsy | Listings/inventory/orders | Etsy Open API v3 | Registered app, OAuth 2.0, seller scopes and listing compliance | 2 |
| eBay | Inventory, offers, orders | eBay Sell Inventory/Fulfillment APIs | Authorized seller, marketplace category mapping and offer publication rights | 2 |
| Faire | Wholesale channel | Authorized brand/partner API | Supplier credentials, access eligibility | 3 |
| Amazon SP-API | Conditional marketplace channel | Selling Partner API | Selling account, approved application and restricted data access | Optional |
| TikTok Shop | Social commerce | Shop partner APIs | Approved seller account, regional availability | 3 |
| ASI / PPAI / SAGE | Promotional product sourcing | Approved supplier/distributor data feeds | Membership/vendor licensing, catalog rights and mapping | 2 |

### Lead engine: user-defined B2B market

Target relevant U.S. **schools, colleges, companies, nonprofits, corporate marketing teams, trade associations, advertising agencies, event organizers, wedding planners, funeral/memorial services, hospitality and retailers, and verified ASI/PPAI distributors**. Sources must be traceable, and any email or phone number must be properly verified and used lawfully. A purchase intent score is not proof that contact is lawful.

**Pipeline:** category/ZIP/industry searches → source URL and business identity → duplicate detection → public company facts → authorized business email enrichment → validation and opt-out checks → human qualification → permission-appropriate personalized draft → internal approval → provider delivery when connected → event/reply tracking → quote/order opportunity.

Do not scrape LinkedIn profiles, Google Maps, social DMs or restricted directories against provider rules. Avoid collecting unnecessary personal data. A search-result screenshot, public business website or social profile does not prove an email address is deliverable. Never assert verification without actually checking.

### Key product differentiator: commercial AI, not generic social scheduling

1. **Product-to-audience graph:** connect product features, quantities, deadlines and use-cases (lanyards → conferences/schools; wristbands → festivals/venues; can coolers → events; totes → nonprofits/retail).
2. **AI-assisted contextual offers:** Generate drafts tied to *approved actual product terms*, not invented price/deadlines. User can set buy-100-get-100 or other promotions subject to accurate margins and fulfillment capacity.
3. **Cross-channel approval studio:** One draft can have unique versions for LinkedIn, Facebook, X, email and Pinterest with human review and consent checks.
4. **Store syndication hub:** One SKU and media library mapped to each store's field, variant, product taxonomies and policy constraints; record sync state and error.
5. **Lead-to-order single record:** Each approved lead, reply, campaign, quote, design proof, vendor PO, invoice and shipment shares persistent references.
6. **AI reliability agent:** Monitors build status, API errors, marketplace listing failures and vendor lead times; suggests action but does not autonomously spend, post or purchase.
7. **Seller-grade economics:** Real supplier quote → quantity price break → margin + rush freight + proof revision → customer-approved price → payment → production.

## Built into test environment in this phase

- Authenticated `GET /api/v1/admin/integrations`: documented provider registry; every external hosted-app connection correctly reports `not_connected`, `not_run`.
- Authenticated `GET/POST /api/v1/admin/leads` and `PATCH /api/v1/admin/leads/{id}`: source-based company lead intake, duplicate checking, review workflow.
- Authenticated `GET/POST /api/v1/admin/content-drafts` and `PATCH /api/v1/admin/content-drafts/{reference}`: draft → approved/rejected **internal** state. Never sends anything.
- New Business HQ navigation sections: Social & API connections, B2B lead research, Drafts & approvals. Each responds to the private backend only after Render deploys the latest commit.
- Automated API tests cover unauthorized access, registry honesty, duplicate lead, status approval and guarantees `published=false`.

**Not built yet:** Provider OAuth callback flows, token storage/rotation, connected-account health checks, outbound posting, scheduled publishing, store bidirectional sync, email validation purchase/lookup, automated lead discovery, bulk outreach, social metrics or a multi-tenant SaaS subscription layer.

## SaaS production architecture

1. **Authentication and tenants:** Define organizations, users, memberships, roles, per-organization data scopes, MFA and billing.
2. **Postgres (Supabase):** Organization-keyed normalized records for accounts, integrations, leads, consent/suppression, audience groups, campaign drafts, publishing attempts, product variants, store mappings, order lines, provider webhooks, logs.
3. **Secrets:** Token encryption, per-provider OAuth consent, least-privilege scopes; never store private API secrets in GitHub Pages `config.js`.
4. **Worker layer:** Scheduled/queued sync, retries with exponential backoff, provider rate limits and signing verification; avoid relying on free Render wake-ups for reliable recurring jobs.
5. **Gatekeeping:** Draft → review → approve → schedule → publish → verify ID → analytics, with action actor and audit. Separate **approval** from **successful publication**.
6. **Product data:** Product, SKU/variant, options, imagery rights, MOQ, quantity breaks, supplier/vendor, inventory/capacity, region, terms, versions.
7. **Observability:** Uptime, connector error dashboards, token expiry warnings, consent ledger, dead-letter queue and reliable test suites.
8. **Isolation:** Avoid giving external lead/contact providers access to user chat history or unrelated CRM records.

## Acceptance checks before calling a channel 'Live'

- OAuth or credential connection belongs to this Business HQ tenant, not only a ChatGPT plugin.
- Minimal permissions verified against provider introspection or direct API read.
- Publish tests only with an expressly approved test post to an owned channel; record returned provider ID and confirm live visibility.
- Store product sync includes upstream mapping, webhook signature verification, an idempotent resync and an explicit dry-run mode.
- Lead provider lookup reports source, extraction timestamp, verified email/phone status, opt-out/legal basis, duplicate matching and user approval.
- GetResponse draft can be found in the actual intended account before any recipient send; final audience is reviewed and no email is sent without approval.
- Failure state is visible and not mislabeled as success. Every connector exposes configured / authorized / tested / live / degraded / disabled statuses.

## Suggested staged delivery

**Phase A (test integration foundation):** Integrations list and permissions, provenance-based lead inbox, draft approval studio (this commit); test all internal endpoints on Render.
**Phase B (first production providers):** GetResponse account + Shopify/WooCommerce/osCommerce + LinkedIn/Pinterest/Facebook as authorized; OAuth and webhook tests; exportable channel reports.
**Phase C (growth engine):** Apollo/Hunter/approved B2B sources, consent and suppression, lead-to-order pipeline, AI-assisted campaign copy, mobile alerts and tracking.
**Phase D (SaaS):** Multi-tenancy, self-service provider connection, subscriptions, per-tenant billing, background workers, reliability/security reviews and enterprise logs.

### Source references (official docs)
- LinkedIn Posts: https://learn.microsoft.com/en-us/linkedin/marketing/community-management/shares/posts-api
- TikTok Content Posting: https://developers.tiktok.com/docs/en/content-posting-api-get-started
- Etsy OAuth 2: https://developer.etsy.com/documentation/essentials/oauth2/
- Shopify GraphQL: https://shopify.dev/docs/api/admin-graphql/latest
- eBay Inventory: https://developer.ebay.com/api-docs/sell/static/inventory/managing-inventory-and-offers.html
- YouTube Data API: https://developers.google.com/youtube/v3/docs/videos/insert
- Pinterest API: https://developers.pinterest.com/
- WooCommerce REST: https://developer.woocommerce.com/docs/apis/rest-api/
- Merchant API: https://developers.google.com/merchant/api
- CAN-SPAM: https://www.ftc.gov/business-guidance/resources/can-spam-act-compliance-guide-business
- Supabase RLS: https://supabase.com/docs/guides/database/postgres/row-level-security

**Cost reminder:** API access varies across providers, and many require approved developer accounts or paid tiers. Full multi-channel auto-posting is not achievable reliably with zero credentials or zero platform costs.
