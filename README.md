# 24hrsprinting LLC — Storefront preview

A stand-alone HTML/CSS/JavaScript storefront proof of concept with eight real-world promotional product reference photos, product filters, customization, artwork preview, illustrative bulk totals, cart, simulated checkout, local order history and an admin interface preview.

## Open locally
Open `index.html` in any modern browser. No installation or build step required. Photos require a network connection.

## Publish through GitHub Pages

1. Upload `index.html` and `.nojekyll` into the **root** of your `24hrsnew` repository, and commit them to the `main` branch.
2. In GitHub, go to **Settings → Pages** and select **Deploy from a branch → main → /(root)**, then save.
3. Once Pages deployment has completed, GitHub will show your live website URL. No custom domain is set in this preview.

**Deployment:** This repository is connected through the `ekfk1003` GitHub account.

## Preview-only limitations

- There is no real backend, authentication, payments, order submission, notifications, approvals, or email delivery.
- Cart and demo confirmation history persist only in localStorage for the current browser. Email/address entries are not saved by checkout and are never transmitted.
- Prices and example minimum quantities are illustrative UI data, not verified business pricing.
- Image URLs are real product **reference images sourced from third parties** for visual prototyping; image rights have **not** been verified. Replace them with owned or properly licensed images for a commercial release. External hosts may block hotlinking; missing photos use a neutral fallback.
- Product images are references and do not represent dynamically rendered customer artwork.

## Suggested next phase

Establish a proper product catalog with permissioned imagery and verified SKUs, authenticated backend, supplier pricing rules, artwork proof version control, Stripe/PayPal, secure uploads, and shipping/tax logic.