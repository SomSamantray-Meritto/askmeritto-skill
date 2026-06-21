# KB Map (link-resolution seed)

The Meritto help center is a Zoho Desk portal at `https://help.meritto.com/portal/en/kb`. It has **no
sitemap and is not indexed by Google**, so the skill discovers articles by tree-walk: WebFetch a category
hub, read the article links it returns, then fetch the relevant article(s). This file is just the seed -
always trust the live hub over this list.

## Category hubs (query-type → hub)

| Category | Hub URL | Use for |
|----------|---------|---------|
| Getting Started | `/portal/en/kb/getting-started` | onboarding, first setup, ORIENTATION/GETTING_STARTED |
| Product Guide | `/portal/en/kb/product-guide` | feature/module docs, FEATURE_EXPLAIN, PRODUCT_GUIDE |
| How-To's | `/portal/en/kb/how-to-s` | step-by-step tasks, HOW_TO |
| Solutioning & Business Cases | `/portal/en/kb/solutioning-business-cases` | BUSINESS_CASE |
| FAQs & Troubleshooting | `/portal/en/kb/faqs-troubleshooting` | FAQ_TROUBLESHOOT |
| Product Newsletters | `/portal/en/kb/product-newsletters` | RELEASE_NEWS |

Prefix all paths with `https://help.meritto.com`.

## Modules seen in Product Guide / Getting Started (for trap M3/M4 normalization)

Leads / CRM, Opportunities, Application Manager, Communication, Campaign Management, QMS, Reports &
Dashboards, Connectors / Integrations, Automations, Telephony, Mobile Application, Field Force, **Mio AI**,
Account Setup, Security, User Management.

Normalize ambiguous words to these: "AI" → "Mio AI"; "forms" → the relevant module (Application / Lead
capture); "the app" → "Mobile Application".

## Article URL shapes

- `https://help.meritto.com/portal/en/kb/articles/{slug}` (most common)
- `https://help.meritto.com/portal/en/kb/{category}/{sub-slug}`

Examples confirmed live: `/kb/articles/all-about-mio-ai`,
`/kb/articles/lead-allocation-in-meritto-crm-11-3-2025`,
`/kb/articles/how-to-raise-a-ticket-through-meritto-helpdesk`.

## Non-KB sources

- Security: `https://www.meritto.com/security/` (WebFetch direct)
- Mio AI: `https://getmio.ai/` (+ `/mio-ai-voice/`, `/mio-ai-chatbot-for-education/`,
  `/mio-ai-sales-coaching-agent/`)
- Developer API: Postman MCP (see `meritto-api.md`)
