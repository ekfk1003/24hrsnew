# 24hrsprinting · AI Brain & Site Design Studio

## Current milestone — 27 November 2026

**Objective:** Ask for website design changes in ordinary English from **Business HQ → AI Design Studio**, preview and approve, publish a safe change to Supabase, and roll back if necessary. A designer/developer must still review new components, product configurators, payment logic, navigation, external integrations, and changes to executable code.

This is an **allow-listed content-management and page theme system**, not unrestricted agentic code editing or a fully interactive visual builder. The AI can only propose which allowed text, color or layout fields to change. It cannot directly change GitHub source, bypass approvals, send messages, access customer data, or enable unsafe functions.

### Supported pages and controls

| Page | Editable via prompt or manual draft |
|---|---|
| Global design | Announcement copy, tagline, primary/accent colors, rounded/pill/square button style |
| Homepage | Hero eyebrow/headline/description, call-to-action labels, category/featured headings, split/centered/editorial hero layouts |
| Catalog | Heading, introduction and 2/3/4-column desktop grid |
| Product page | Reference-photo disclaimer and customization guidance |
| Quote | Page heading and intro |
| Cart | Page heading and info |
| Checkout (proof requests only) | Page heading and explicit non-payment explanation |

The existing **Store controls** tab separately manages product publication, images, product information and enabled website sections. They are not AI-generated changes in this milestone.

### Deploying and enabling AI

1. GitHub Pages deploys from `ekfk1003/24hrsnew` main automatically.
2. Render service `24hrsnew` must deploy the same current GitHub commit. It will create the new `app_private.site_pages`, `app_private.site_page_revisions`, and `app_private.site_design_drafts` tables on startup.
3. In **Render → 24hrsnew → Environment**, add `OPENAI_API_KEY` as a secret environment variable. Obtain it from your authorized OpenAI API Platform project; do **not** put it in GitHub, the frontend, Supabase public settings, or any screenshots. API billing is separate from ChatGPT subscription and will be charged when generating proposals.
4. Optional `OPENAI_MODEL` defaults to `gpt-4.1-mini`. Use a model enabled for your API project and compatible with Responses API structured output.
5. Save and deploy, then sign in at `https://ekfk1003.github.io/24hrsnew/admin.html`.
6. **AI Design Studio** → select page → type prompt → Generate AI proposal. Review proposed fields in the simulated section preview. Click **Approve & publish changes**, then refresh the customer storefront to verify.
7. Open **Published version history** to restore an earlier version. Rollback itself creates a new audited version, rather than erasing history.

### Test without an AI API key

In AI Design Studio, expand **Manual draft**. Choose page and field, enter a new allowed value, and save. It will use the *same* draft, preview, approval, publish and rollback pipeline. This is a useful functional test of the CMS before enabling paid AI generation.

### Example prompts

- "Make the homepage feel luxurious for U.S. corporate event buyers. Use an emerald accent, a concise professional headline and a centered hero. Keep the free-proof message."
- "Rewrite the custom-socks product-page guidance with a clear note that the photo is illustrative and designs require approval." (Product-specific SKU copy editing still belongs to **Store controls**.)
- "Simplify the checkout page explanation; clarify that this is a proof request and no payment is collected."
- "Change global buttons to pill shape and use dark teal as the main brand color."
- "Make the catalog more elegant and display three products per row on desktop."

### Safety and rollback rules

- Proposed text and style values are schema-checked and never execute HTML/CSS/JS from a user prompt.
- The AI cannot change checkout or payment logic, add scripts, edit API keys, or directly publish.
- Only administrators can propose, publish or roll back. Viewer/sales/ops users can inspect design drafts and history.
- Every draft is pinned to its base page version. If another version publishes first, stale drafts cannot overwrite later work.
- The backend records actor and history; public site only reads published settings.
- AI requests use `store:false` with the OpenAI Responses API; the prompt and existing public page copy are sent to the selected API provider, not customer records or secrets.
- Do not place personal customer data or credentials in design prompts.
- Simulation previews show a representative composition, **not** a pixel-perfect interactive screenshot. Always open and inspect the real storefront before accepting design changes.
- If Render is still on an old commit, AI Design Studio will report HTTP 404. Deploy updated API first.
- If no API key exists, prompting reports an informative configuration error; manual draft mode remains usable.

### Pending foundation work

See [Business HQ gap audit](BUSINESS_HQ_AUDIT_2026-11-27.md), [Store controls setup](STORE_CONTROLS_SETUP.md), and [SaaS integrations research](SAAS_INTEGRATIONS_RESEARCH_2026-11-27.md).

Priority: true product configuration, secure private customer artwork, finalized quotes/payment approval, supplier and shipping jobs, backup/restore and MFA, real social/store connectors, and a future hosted n8n worker. Desktop n8n is already installed but **not yet connected**.

### Self-test and release check

1. Automated API tests validate create draft, unchanged public content until approval, publish, rollback, stale version conflict and restricted fields.
2. Frontend integrity tests validate JS syntax, linked public content script and Business HQ navigation.
3. Manually verify in live browser: demo/manual draft → publish → refresh homepage → verify exact published change → roll back → verify original. Test mobile and desktop.
4. Use GitHub Actions, Render deployment logs and Supabase table records. Passing code tests **does not** prove the currently deployed Render service has updated.
