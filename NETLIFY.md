# Netlify for thecurltapes.com

This repository is the full site source: the static files in `public/` plus the form functions. It is separate from [bpz82/thecurltapes-site](https://github.com/bpz82/thecurltapes-site), the GitHub Pages static export. Do not delete either repository.

## Build settings

`netlify.toml` already sets these. Confirm the same values in the Netlify UI if you connect the repo by hand:

- Base directory: (empty; repository root)
- Build command: (none / empty)
- Publish directory: `public`
- Functions directory: `netlify/functions`
- Node bundler: `esbuild`

## Environment variables

Set these under *Site configuration → Environment variables*. Do not put keys in this repository or in client code.

Required for contact and order emails:

- `RESEND_API_KEY` — from the Resend account (Netlify UI only)
- `MAIL_FROM` = `The Curl Tapes <site@thecurltapes.com>`
- `MAIL_TO` = `thecurltapes@gmail.com`

Optional:

- `MAIL_TO_COLEMAN` / `MAIL_TO_BLAKE` — if the "Message Coleman" and "Message Blake" forms should go to different inboxes (otherwise they use `MAIL_TO`)
- `MAIL_TO_BLAKEZUNIGA` — inbox for the blakezuniga.com contact form at `POST /api/bz-contact`. If unset, mail goes to `bpz82bear@gmail.com` (the blake@blakezuniga.com mailbox is still being set up). Set this to `blake@blakezuniga.com` once that mailbox is ready. The function is called from blakezuniga.com / www and the surge preview; CORS allows only `https://blakezuniga.com`, `https://www.blakezuniga.com`, and `https://bpz-guitar-versions.surge.sh`.
- `BUTTONDOWN_API_KEY` or `MAILCHIMP_API_KEY` + `MAILCHIMP_LIST_ID` — to save newsletter signups to a list (otherwise a signup still emails `MAIL_TO` when Resend is configured)

## CORS for form functions

`/api/contact`, `/api/order`, and `/api/subscribe` answer OPTIONS preflight and echo `Access-Control-Allow-Origin` only for `https://thecurltapes.com`, `https://www.thecurltapes.com`, and `https://bpz82.github.io`. Same-origin requests (no `Origin`, or the Netlify site itself) still work and do not get that header. `/api/bz-contact` keeps its own allow-list (`blakezuniga.com`, `www`, and the surge preview).

Verify `thecurltapes.com` in Resend and add the DNS records Resend shows before relying on `MAIL_FROM`.

## Rollback

A bad Netlify deploy is rolled back in the Netlify dashboard by publishing the previous successful deploy, or by pushing (or redeploying) the previous good commit on `main`. Do not delete this repository or `bpz82/thecurltapes-site`.

To take the custom domain off Netlify and show the GitHub Pages copy again, point DNS back to the GitHub Pages records in `DOMAIN.md` (apex A records `185.199.108.153`–`185.199.111.153`, `www` CNAME to `bpz82.github.io`) and keep every Zoho mail record exactly as listed there. To show the old Squarespace site again, use the Squarespace rollback in `DOMAIN.md` instead.

What a rollback cannot undo:

- DNS and certificate changes take time and cannot be snapped back instantly.
- Form emails already sent via Resend stay in the inboxes they were delivered to. That includes `/api/bz-contact` messages, which go to `MAIL_TO_BLAKEZUNIGA` or, if that variable is unset, to `bpz82bear@gmail.com`.
- If Zoho MX, SPF, verification, or DKIM records are dropped during a DNS change, @thecurltapes.com mail can stop until those records are put back.
- Do not cancel the Squarespace website plan without Blake's OK. That is a billing change.
