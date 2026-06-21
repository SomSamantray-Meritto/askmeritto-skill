# LinkedIn feed access (optional, opt-in)

LinkedIn's company feed is behind a login wall, so WebFetch cannot read it. To read the full
`linkedin.com/company/meritto` feed, AskMeritto can use your LinkedIn **session cookies**. This is
optional. If you skip it, AskMeritto answers LinkedIn questions from public Google-indexed posts instead
(partial coverage, but zero risk).

## ⚠️ Read this warning first

Using your LinkedIn session cookies to read the feed **violates LinkedIn's Terms of Service** and can get
the cookie-owner's personal account **rate-limited, restricted, or banned**. LinkedIn enforces this far
more aggressively than most sites. The underlying endpoint is also undocumented and breaks periodically.

Only opt in if you accept the account risk and keep usage to a low request rate. This is your personal
account on the line, not a service account.

## What you need (2 values)

- `li_at` — your LinkedIn session auth cookie.
- `JSESSIONID` — used as the CSRF token.

## How to get them

1. Log in to `https://www.linkedin.com` in a desktop browser.
2. Open DevTools (F12) → **Application** (Chrome) or **Storage** (Firefox) → **Cookies** →
   `https://www.linkedin.com`.
3. Copy the **Value** of `li_at`.
4. Copy the **Value** of `JSESSIONID`. Strip the surrounding double quotes.

## Where to put them

Add to `~/.config/askmeritto/.env` (create it if missing, then `chmod 600` it):

```
LI_AT=<your li_at value>
LI_JSESSIONID=<your JSESSIONID value, no quotes>
```

Or run `python3 scripts/meritto_fetch.py setup` and follow the prompt.

## Where they go

Stored locally only, in `~/.config/askmeritto/.env`. Never logged, never written to output files, never
sent anywhere except LinkedIn itself. Cookies expire every few days - if LinkedIn answers start failing,
re-copy them.
