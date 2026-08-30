# Deploying the Dispute Tracker

The site is a **pure static build** — no server, no database, no API keys. The
dataset is bundled into the JS at build time from the canonical CSV.

## Build

```bash
python3 scripts/site_data/build_site_data.py   # canonical CSV → site JSON (+ /disputes.csv download)
cd site
npm install        # first time only
npm run build      # typechecks, bundles → site/dist/
```

`site/dist/` is the whole site (~600 KB, ~130 KB gzipped over the wire).

## Verify locally (do this before first deploy)

```bash
cd site && npm run dev        # http://localhost:5173
```

What to check:

- Stat band numbers match gut checks (195 disputes, 74 still out of network, ~6.7M patients).
- Map: dots sit on the right states; click a dot → detail drawer with working source links; click a state → filters to it; wheel/buttons zoom.
- Timeline: bars start 2021-era, ongoing bars run to today with a ▸; "Longest first" sort brings Kootenai vs Regence to the top.
- Filters: pick UnitedHealth Group → everything (map, timeline, table, stat band) narrows together.
- Table: "source ↗" links open the right articles; the `*` estimate footnote shows.
- Download the full dataset (CSV) link works.
- Phone-width window: stat band 2-up, filters wrap, map/timeline still usable.

## The one deploy step

Proposed home: **disputes.healthisotherpeople.com** (confirm the subdomain at
review — `tracker.` and `standoffs.` are the alternates).

Using Vercel (matches the HIOP site's hosting):

```bash
cd site && npx vercel deploy dist --prod
```

First run creates the Vercel project; then in the Vercel dashboard → project →
Domains, add `disputes.healthisotherpeople.com` and add the CNAME record it
prints (`disputes` → `cname.vercel-dns.com`) wherever healthisotherpeople.com's
DNS lives. That's the whole deployment — subsequent updates are the same one
command after each monthly `apply`.

(Any static host works identically — Netlify `netlify deploy --prod --dir dist`,
Cloudflare Pages, or an S3 bucket. Nothing in the build assumes Vercel.)

## Update cycle

Monthly job refreshes the data (see `scripts/monthly_update/README.md`), then:

```bash
cd site && npm run build && npx vercel deploy dist --prod
```
