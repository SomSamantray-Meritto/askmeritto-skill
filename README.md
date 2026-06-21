# AskMeritto

A Claude skill that answers questions about **Meritto** (formerly NoPaperForms) — product, features,
guides, how-tos, releases, security, developer APIs, Mio AI, and company news — using **only Meritto's own
public sources**. Anything off-topic is politely declined.

Invoke with `/askmeritto <your question>`.

## What it can answer

- "How do I set up lead allocation in Meritto CRM?" (how-to, from the KB)
- "How does Mio AI Voice work and who is it for?" (feature explain, from getmio.ai + KB)
- "How does the Create Lead API work?" (developer API, from the Postman collection)
- "What's new in the latest Meritto release?" (newsletters + YouTube + LinkedIn)
- "What does Meritto offer?" (orientation)

It will NOT answer competitor comparisons, general CRM/edtech theory, or anything not about Meritto.

## Sources

KB (`help.meritto.com`), Security (`meritto.com/security`), YouTube (`@merittoofficial`), LinkedIn
(`company/meritto`), Developer API (`developer.nopaperforms.com` via Postman), Mio AI (`getmio.ai`), and
Meritto marketing pages (orientation only). See `references/source-policy.md` for the authority order.

## Setup

- **yt-dlp** is auto-installed on first run if missing (used only for the official YouTube channel). The
  skill tells you when it installs it.
- **LinkedIn** full-feed access is optional and requires session cookies. It is ToS-risky — read
  `references/linkedin-setup.md` before opting in. Without cookies, LinkedIn questions use public web
  search instead.

## Layout

```
SKILL.md                     the instructions Claude follows
scripts/meritto_fetch.py     youtube | linkedin | setup (the only code; everything else is WebFetch/MCP)
references/                  kb-map, source-policy, meritto-api (Postman fallback), linkedin-setup
hooks/                       SessionStart: ensure yt-dlp + save dir
```

Raw research trails are saved to `~/Documents/AskMeritto/`.
