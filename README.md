# thecurltapes.com, without Squarespace

This folder is a self-hosted static copy of **www.thecurltapes.com**, rebuilt from the live site on Nov 12, 2026. It has the same pages, URLs, copy, photos, videos, fonts, layout and interactions. It has no Squarespace code, CDN, badge, cookies or hosting.

```
public/            ← the website (this is what gets deployed)
functions/api/     ← Cloudflare Pages Functions for the forms (/api/subscribe, /api/contact, /api/order)
netlify/functions/ ← the same three endpoints for Netlify
lib/forms.js       ← shared form/email/newsletter logic used by both
serve.py           ← local preview server
tools/             ← convert.py (rebuilds public/*.html from _source), build-css.mjs, check-links.py
_source/           ← raw capture of the old site (HTML, JSON, CSS, original images, 1080p video masters)
_reference/        ← screenshots of the live site (desktop 1440px + mobile 390px) and rebuild/ screenshots of this copy
```

## Preview locally

```bash
python3 serve.py            # http://localhost:8080
python3 serve.py --no-api   # simulate "forms not configured", to see the fallback messages
```

`serve.py` behaves like the real hosts. `/aboutpage` serves `aboutpage/index.html`, and unknown URLs get `404.html`. It applies `_redirects`, and it fakes the `/api/*` endpoints by writing each submission to `preview-submissions.jsonl`, so you can see exactly what would be sent.

A plain `python3 -m http.server -d public` also works for browsing. Forms will then show their "couldn't send, email us instead" fallback, because there is no `/api`.

## What's included

| URL | What it is |
|---|---|
| `/` (also `/thecurltapes`) | Home: full-screen hover menu (Music / The Hayloft) + newsletter |
| `/thecurltapes/project-one-h346n-gjtmc` | Music (albums, "Click To Listen") |
| `/thecurltapes/hayloft` | The Hayloft (galleries, slideshows, carousels, 3 videos) |
| `/aboutpage`, `/aboutpage/colemanmartin`, `/aboutpage/blakezuniga`, `/aboutpage/mics-and-tape-machines` | About section |
| `/contact-6`, `/cole-contact`, `/cole-contact-1` | Contact forms (both of you / Coleman / Blake) |
| `/blake-gg`, `/blake-gg/project-two-…-ldeaf`, `/portfolio`, `/portfolio/new-portfolio-item` | Blake's & Coleman's gear pages |
| `/cole-bio`, `/blake-bio` | Bio photo pages |
| `/store`, `/store/p/the-curl-tapes-and-friends-sparrow-nest-theater`, `/cart` | Ticket store + cart |
| `/joon` and its 3 sub-pages | Joon & Madison wedding photo share (not in the menu, same as before) |
| `/welcome?name=First+Last` | The personalised "Hey, {name}" welcome splash (all easter eggs kept) |
| `/404.html` | Not-found page |

Everything is plain HTML/CSS/vanilla JS:
- `assets/css/theme.css` is the site's original theme styles, cut down to the rules these pages use.
- `custom.css` is the Times New Roman custom CSS from the old site, copied as-is.
- `site.css` and `site.js` cover the parts that used to need Squarespace's scripts: the header and mobile menu, the home hover, galleries, slideshows, carousels, the lightbox, film grain, forms, cart and checkout.
- Images are local, with 750px and 1500px versions added for speed.
- Fonts (Newsreader and Instrument Serif) are self-hosted.
- Videos are local MP4s. The Landry's video was re-encoded to 22 MB so it fits the 25 MB per-file limit on Cloudflare Pages. The original is in `_source/video-masters/`.
- Page titles, descriptions, Open Graph/Twitter cards, alt text, captions and structured data (JSON-LD) are all kept.

Analytics: the old site loaded Google Tag Manager `GTM-PMH3HDKV`, which also fires an AppLovin pixel. This copy keeps it so tracking doesn't change. To turn it off, set `gtmId: ''` in `public/assets/js/config.js`.

## Deploy

The site is static; deploy the `public/` folder.

**Cloudflare Pages (recommended; free, and the form functions work)**
1. Put this folder in a GitHub repo, or use `npx wrangler pages deploy public --project-name thecurltapes`. Upload via wrangler from this folder so that `functions/` is included.
2. In the dashboard: *Workers & Pages → Create → Pages → connect repo*. Set build command: none. Set output directory: `public`. Cloudflare detects `functions/` automatically.
3. *Settings → Environment variables*: add the form variables (see below), then redeploy.

**Netlify**: connect the repo. `netlify.toml` already sets `publish = "public"` and the functions folder. Add the same environment variables under *Site configuration → Environment variables*.

**GitHub Pages**: works for the site itself. Point Pages at `public/`, or copy it to a `gh-pages` branch. GitHub Pages can't run the `/api` functions, so forms fall back to "email us at thecurltapes@gmail.com" links. One file is close to GitHub's limits: the Landry's mp4 is 22 MB, which is fine. The repo is about 250 MB in total.

## DNS cutover (moving www.thecurltapes.com off Squarespace)

Do this only after the new host is live and you've checked it on its preview URL (e.g. `thecurltapes.pages.dev`).

Current public DNS (checked Nov 12, 2026, read-only):
- Nameservers are `dns1–4.p01.nsone.net`, which is Squarespace Domains DNS.
- Apex `A` records: 198.185.159.144/145 and 198.49.23.144/145.
- `www` CNAME: `ext-sq.squarespace.com`.
- **Email is on Zoho Mail.** MX records are `mx.zoho.com` (10), `mx2.zoho.com` (20) and `mx3.zoho.com` (50). There is also an SPF TXT record and a `zoho-verification` TXT record.
- **Those mail records must survive the move**, or @thecurltapes.com email stops working. Also look for a Zoho DKIM record (e.g. `zmail._domainkey`).

1. **Find where the domain is registered.** Squarespace → *Settings → Domains*. If it says "Squarespace Domains" (or ex-Google Domains), Squarespace is the registrar.
2. **Add the custom domain on the new host first.**
   - Cloudflare Pages: *Custom domains → Set up a domain*, adding `www.thecurltapes.com` and `thecurltapes.com`.
   - Netlify: *Domain management → Add domain*.
   - The host shows the exact DNS records it wants.
3. **Change the DNS records.** In Squarespace's DNS settings, or at whoever runs the domain's DNS:
   - Delete the Squarespace defaults: the `www` CNAME to `ext-sq.squarespace.com`, and the four `A` records `198.185.159.144/145`, `198.49.23.144/145`.
   - Add `www` CNAME → `thecurltapes.pages.dev` (or `<site>.netlify.app`).
   - Root/apex `@`:
     - Netlify: `A 75.2.60.5`.
     - Cloudflare Pages: apex needs the domain's DNS on Cloudflare. The simplest option is to move the domain's nameservers to Cloudflare (free). Cloudflare then imports the records and handles apex + www.
   - **Keep the Zoho MX, SPF/verification TXT and any DKIM records exactly as they are.** If you move nameservers to Cloudflare, check that the import copied all of them before switching.
4. Wait for HTTPS to issue (minutes to a few hours), then check www, the bare domain, a form, and the store.
5. **Only then** cancel the Squarespace *website* plan. If the domain is registered at Squarespace, either keep paying for just the domain there or transfer it (unlock + get the auth code in *Domains → Transfer*) to Cloudflare Registrar or another registrar. Don't let the domain lapse when cancelling the site plan.
6. Before cancelling, export anything Squarespace stores that this copy doesn't: form submissions (Squarespace *Contacts / Marketing → Profiles*), order history, and newsletter contacts.

## Forms & newsletter

Every form shows the same success text as before when it works. If the backend isn't set up or fails, the visitor sees an error with a pre-filled email link to thecurltapes@gmail.com. Nothing fails silently. All forms have validation and a hidden spam honeypot.

| Form | Sends to | Needs |
|---|---|---|
| "We Don't Have Social Media" newsletter (every page footer) | `/api/subscribe` → your email list (+ a copy to you) | `BUTTONDOWN_API_KEY` **or** `MAILCHIMP_API_KEY` + `MAILCHIMP_LIST_ID`; optional Resend for a notification email |
| Contact (`/contact-6`, `/cole-contact`, `/cole-contact-1`), store "Have Questions?" | `/api/contact` → email | `RESEND_API_KEY` + `MAIL_FROM` |
| Ticket order request (cart checkout without Stripe) | `/api/order` → email | `RESEND_API_KEY` + `MAIL_FROM` |

Environment variables:
- `RESEND_API_KEY`: free at resend.com. Verify the domain thecurltapes.com there; it gives you 3 DNS records to add.
- `MAIL_FROM`: e.g. `The Curl Tapes <site@thecurltapes.com>`.
- `MAIL_TO`: default `thecurltapes@gmail.com`.
- `MAIL_TO_COLEMAN` and `MAIL_TO_BLAKE`: optional, so the "Message Coleman" and "Message Blake" forms go to each of you.
- `BUTTONDOWN_API_KEY` or `MAILCHIMP_API_KEY`/`MAILCHIMP_LIST_ID`: the mailing list.

> ⚠️ On the live Squarespace site the newsletter block has **no storage connected** (Squarespace shows "needs a storage option" only to editors). Signups there are probably **not being saved anywhere**. Connecting Buttondown or Mailchimp here fixes that.

## Store / tickets

- The store page, product page, quantity picker, "Ticket Information" form (Names to Add to List, Email, Phone) and cart all match the original: same product, $25.00, same copy and images.
- The cart lives in the visitor's browser (localStorage) and the cart icon shows in the header when it has items, as before.
- **Checkout**: Squarespace Commerce can't come with you, so there are two options:
  1. **Stripe Payment Link (real payments).** Create a $25 "Sparrow Nest Theater ticket" Payment Link in Stripe, with adjustable quantity and a custom field for guest names. Paste the URL into `public/assets/js/config.js` → `store.paymentLinks['the-curl-tapes-and-friends-sparrow-nest-theater']`. Checkout then sends buyers to Stripe and pre-fills their email. Note: guest names typed on the site aren't passed to Stripe, so add a Stripe custom field for them.
  2. **No Stripe (default).** Checkout sends an *order request* (items, names, email, total) to your email via `/api/order` and tells the buyer you'll confirm and arrange payment. No card is charged. If email isn't configured either, the buyer gets a pre-filled email to you.
- ⚠️ The only product is the **Saturday, April 25th 2026** Sparrow Nest Theater show, which has already happened, but the old site still shows it "in stock" (75 left). It's kept as-is. You may want to remove it or mark it sold out. Product data is embedded in the product HTML (`data-ct-product`) and comes from `_source/json/store_p_*.json`.

## Pages left out

| URL | Why |
|---|---|
| `/code-test` | Empty test page |
| `/about`, `/contact`, `/home`, `/music` | Already 404 on the live site (the real pages are `/aboutpage`, `/contact-6`, `/`, `/thecurltapes/project-one-…`) |
| `/search`, `/s/*`, `/config/*` | Squarespace system URLs; redirect to `/` via `public/_redirects` |

## Decisions & notes

- **Rebuilt, not mirrored.** The pages are generated from the rendered pages of the live site (`tools/convert.py`) with all Squarespace scripts and attributes stripped. That's why layout and spacing match closely. A section-by-section height comparison against the live site matches within a few pixels at 1440px and 390px on every page.
- `/thecurltapes` is the same page as `/` on the old site. It's kept, with its canonical link pointing to `/`.
- `/welcome` kept its exact text, timings and easter eggs. Names are now inserted as text, not HTML, which fixes an injection bug in the original.
- Kept as written:
  - The "Message Blake" form's success text says "Thanks for reaching out to Coleman" (that's what the live site says).
  - `/joon` pages link to a Google Drive folder.
  - External links: YouTube (@TheCurlTapes), carrd.co, an Instagram photo credit.
- No search page (the old site had none either).
- Rebuild workflow if you edit content:
  - Change the HTML in `public/` directly.
  - Or re-run `python3 tools/convert.py`, which overwrites public HTML from `_source/`.
  - Then run `node tools/build-css.mjs` (needs `cd tools && npm install`) and `python3 tools/check-links.py`.
