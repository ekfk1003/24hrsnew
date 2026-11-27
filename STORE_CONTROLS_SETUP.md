# Store Control Center — Operational Setup
**Scope:** storefront and Business HQ at `ekfk1003/24hrsnew`, Render `two4hrsnew.onrender.com`, Supabase project `24hrsprinting-test`.

## What's implemented
- Admin-only **Store controls** page in Business HQ.
- Turn catalog, homepage sections, free-proof quotes and proof requests on or off.
- Create a product as **hidden**; publish/unpublish without deleting its historical order references.
- Reorder featured products, update descriptions, set a main photograph, add a public photo by URL, remove photos from public galleries (soft delete), and upload JPEG/PNG/WebP when storage is configured.
- Public storefront fetches its catalog and feature switches from Render, which reads Supabase. Visible product photos and features update after refreshing the customer site.
- Server blocks new quotes and proof orders when corresponding request switches are disabled. It also rejects requests for unpublished products.
- Initial eight sample photographic references seed **once** into product-media records. Removing an image does not re-create it on restart.
- Existing illustrative pricing, free digital proofs and manual approval remain. No paid checkout or real manufacturing is enabled.

## Deploying the latest code
1. GitHub Pages should deploy from `main` automatically.
2. Render → 24hrsnew → Manual Deploy → Deploy latest commit. Verify its commit equals the current GitHub head and service is Live.
3. Open `https://ekfk1003.github.io/24hrsnew/admin.html` and sign in.
4. Business HQ → **Store controls**. Changes persist in Supabase and appear on storefront after a browser refresh.
5. If the new page says HTTP 404, Render is running an older commit. If it says HTTP 503 at startup, inspect Render logs without exposing secrets.

## Adding an image from a URL
For an existing product, paste a direct public HTTPS image URL with explicit alt text. Provide appropriate rights and image credits. The preview is **not** proof artwork. After saving, refresh the customer storefront.

## Uploading actual product photographs
Product images must be **public**; never upload customer artwork or private documents to this bucket.

1. Supabase → Storage → **New bucket**.
2. Name exactly `product-media`; select **Public** (product marketing images are intended to be publicly viewable).
3. Set maximum upload size **5 MB** and allowed types `image/jpeg`, `image/png`, `image/webp`.
4. Render → 24hrsnew → Environment: add server-side `SUPABASE_URL` = `https://azglgvcsmqkfknuszqee.supabase.co`, `SUPABASE_SERVICE_ROLE_KEY` = **legacy service_role JWT** from the Supabase API settings. The service-role key is powerful and must NEVER be copied into GitHub files, frontend `config.js`, n8n public URLs or chat.
5. Save and deploy. Then use **Upload image** under a product in Business HQ. The server validates file signature/type/size and writes to Supabase Storage before recording its public URL.
6. If using new-generation Supabase keys instead of legacy JWT, the server adapter must be updated appropriately; don't put an `sb_secret_` key in a JWT Bearer field by guessing.
7. Production hardening: use scoped uploads/signed policies, malware/image decoding, image transforms, cleanup for orphaned files, file rights review, and stricter anti-abuse / request limits.

### Why no direct browser upload?
The admin credentials authorize a Render API endpoint; sensitive storage credentials stay on the server. Exposing a storage administrator key in a public HTML/JS site would compromise your database and files.

## Safety and known limitations
- External URLs are not checked for image rights or confirmed availability by the server; use only owned/licensed images.
- Soft-deleted media stays in the database for audit and is not automatically erased from remote Storage; add retention/purge controls for production.
- No versioned revision/rollback UI yet. Restore can be done through an authorized admin or database procedure.
- Visibility switches currently affect pages/requests listed in the feature registry; they do not yet manage *all* UI copy, individual navigation labels, prices, SEO metadata, promo offers, roles or integrations.
- Product categories newly created without an image appear with a photo placeholder. Custom product-option schemas are not yet editable.
- The existing public storefront is a prototype, not a complete multi-tenant SaaS commerce platform.
- Supabase flags disabled RLS in `app_private`; keep schema grants private and review RLS and least-privilege DB service accounts before adding real customers.
- Free Render may sleep when idle; scheduled automation later requires a reliable worker, not desktop n8n exposure.

## Acceptance test
1. Create unpublished `sample-bottle` and verify it **does not** appear on public catalog.
2. Add licensed image + description, then publish. It should appear after refresh.
3. Disable `quotes_enabled`; verify public quote route hides and backend rejects a new quote.
4. Reenable quotes, submit a synthetic quote. Reference appears in Business HQ.
5. Set product to hidden again; verify new quotes containing it are rejected and prior quote references remain.
6. Remove image; refresh to verify placeholder/no image. No deletion of historical order records.

**Do not hook up n8n until this foundation works end-to-end.**
