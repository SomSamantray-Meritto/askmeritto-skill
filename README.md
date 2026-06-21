# AskMeritto

**Your Meritto guide, as an agent skill.** AskMeritto answers questions about **Meritto** (formerly
NoPaperForms) - product, features, guides, how-tos, releases, security, developer APIs, Mio AI, and
company news - using **only Meritto's own public sources**. Anything off-topic is politely declined.

Invoke it with `/askmeritto <your question>` (or however your agent runtime triggers a skill - see
[Installation](#installation)).

It is built as a portable [Agent Skill](https://docs.claude.com/en/docs/claude-code/skills): a single
`SKILL.md` instruction file (the "brain") plus a small Python helper for the two sources a browser-style
fetch cannot read (YouTube transcripts and the LinkedIn feed). No server, no build step.

---

## Table of contents

- [What it can answer](#what-it-can-answer)
- [What it refuses](#what-it-refuses)
- [The 12 sources and their authority order](#the-12-sources-and-their-authority-order)
- [How it works - the pipeline](#how-it-works---the-pipeline)
- [Feature highlights](#feature-highlights)
- [Installation](#installation)
  - [Claude Code](#claude-code-native)
  - [Codex CLI](#codex-cli)
  - [OpenCode](#opencode)
  - [GitHub Copilot CLI](#github-copilot-cli)
  - [Gemini CLI](#gemini-cli)
  - [Any other agent / generic](#any-other-agent-generic)
- [Setup and dependencies](#setup-and-dependencies)
- [Repo layout](#repo-layout)
- [Security and privacy](#security-and-privacy)

---

## What it can answer

- "How do I set up lead allocation in Meritto CRM?" - a how-to, from the KB
- "How does Mio AI Voice work and who is it for?" - a feature explainer, from getmio.ai + KB
- "How does the Create Lead API work?" - a developer-API answer, from the Postman collection
- "What's new in the latest Meritto release?" - release news, from newsletters + YouTube + LinkedIn
- "What does Meritto offer?" - an orientation overview, KB-led
- "Is Meritto SOC 2 / GDPR compliant?" - a security answer, from meritto.com/security

## What it refuses

By design, AskMeritto declines and stops on:

- **Competitor comparisons** ("Meritto vs Salesforce", "best CRM for admissions") - it will answer the
  Meritto half of a mixed question and decline the competitor half
- **Generic theory** (general CRM / edtech / marketing advice not specific to Meritto)
- **General programming or world knowledge**
- **Your tenant's private data** ("why is *my* lead missing") - it has no access to your account; it
  points you to the Meritto Helpdesk instead
- **Pricing / sales / demos** - not in the docs; it points you to meritto.com

It never answers from general knowledge. Every fact it states comes from a Meritto source it actually
fetched.

---

## The 12 sources and their authority order

| # | Source | Where | How it is read |
|---|--------|-------|----------------|
| 1 | Getting Started (KB) | help.meritto.com/portal/en/kb/getting-started | WebFetch hub → article |
| 2 | Product Guide (KB) | …/kb/product-guide | WebFetch hub → article |
| 3 | How-To's (KB) | …/kb/how-to-s | WebFetch hub → article |
| 4 | Business Cases (KB) | …/kb/solutioning-business-cases | WebFetch hub → article |
| 5 | FAQs / Troubleshooting (KB) | …/kb/faqs-troubleshooting | WebFetch hub → article |
| 6 | Product Newsletters (KB) | …/kb/product-newsletters | WebFetch hub → article |
| 7 | Security | meritto.com/security/ | WebFetch direct |
| 8 | YouTube | youtube.com/@merittoofficial | `meritto_fetch.py youtube` (yt-dlp) |
| 9 | LinkedIn | linkedin.com/company/meritto/posts | `meritto_fetch.py linkedin` (opt-in) or WebSearch |
| 10 | Developer API | developer.nopaperforms.com | Postman MCP `getCollection` (the SPA cannot be fetched) |
| 11 | Mio AI | getmio.ai | WebFetch |
| 12 | Marketing | meritto.com (page-sitemap.xml) | WebFetch, filtered, complement-only |

**Authority order (higher wins on any conflict):**

```
KB article = Postman API collection (1.0)
  > getmio.ai for Mio AI            (0.9)
  > YouTube transcript              (0.7)
  > Newsletter                      (0.6)
  > LinkedIn / WebSearch            (0.4)
  > Marketing pages                 (0.2)  complement only, never primary
```

The knowledge base is the source of truth. Marketing pages never override it, are never a primary source
for any question, and are only touched as last-resort filler when the KB genuinely does not cover
something - always framed as "Meritto describes…".

---

## How it works - the pipeline

When you ask a question, the skill runs an ordered gauntlet. Nothing is fetched until the gates pass.

**STEP 0 - Topic Guard.** Is this about Meritto / NoPaperForms? If not, it declines politely and stops.
This is the single most important rule. NoPaperForms (the legacy brand) and `api.nopaperforms.io` count
as in-scope; competitors and generic theory do not.

**STEP 1 - Classify.** The question is sorted into one of 12 query types: `ORIENTATION`,
`GETTING_STARTED`, `HOW_TO`, `FEATURE_EXPLAIN`, `MIO_AI`, `PRODUCT_GUIDE`, `RELEASE_NEWS`,
`FAQ_TROUBLESHOOT`, `SECURITY`, `BUSINESS_CASE`, `DEVELOPER_API`, `COMPANY_NEWS`. The type decides which
sources to reach for.

**STEP 2 - Keyword-Trap check.** Catches questions the docs cannot answer well before wasting a fetch:
- **M2 tenant data** ("my lead is missing") → routes to the Helpdesk, does not pretend to fix your instance
- **M3 too vague** ("help me with Meritto") → asks one clarifying question naming real modules
- **M4 ambiguous / legacy name** (bare "forms", "AI", "app", "NoPaperForms") → normalizes to the real
  module name ("AI" → "Mio AI") before fetching
- **M5 pricing / sales** → points to meritto.com, skips the KB walk

**STEP 3 - Sub-Category Sweep with a parallel Haiku research fan-out (the exhaustive search).** Google
does not index the Meritto KB, so the skill walks it live. Critically, the KB is **three levels deep** -
a hub page (e.g. Product Guide) lists ~26 **sub-categories** (Leads, Webhook, Automations, MIO AI, ...)
and *no articles*; the real articles live one level down inside each sub-category; articles then
cross-link to each other. A hub page alone will make you wrongly conclude a feature does not exist (this
is exactly how "Smart Capture", which lives under Product Guide -> Leads, was missed).
- **Phase A** - fetch the relevant hub(s) and treat the result as a *sub-category index*, not an article
  list.
- **Phase B** - dispatch **5-6 Haiku subagents in parallel** (`meritto-researcher`), partitioning all the
  sub-categories among them. Each worker opens its sub-categories, lists every article, deep-reads the
  query-relevant ones, follows cross-links, and returns a structured **linkage map** (articles, key
  terms, cross-document mentions). Coverage is exhaustive because sub-category names do not reliably
  reveal where a feature lives.
- **Phase C** - the main model merges all linkage maps into one network, dedupes, ranks, and fills any
  reported gap with a follow-up worker.
- **Phase D** - hands the strongest articles to synthesis. On runtimes that cannot spawn subagents, the
  same sweep runs sequentially instead.
Budgets keep it bounded: sub-category *listing* is exhaustive (cheap), but article *body* reads are
ranked and capped (~3 per worker, ~8 merged).

**STEP 3F - Feature traversal** (for `FEATURE_EXPLAIN`). Seeds from the ranked sweep, then follows the
inline cross-links inside articles via a bounded breadth-first search (at most 6 articles, depth at most
2, with URL dedupe and a cycle guard) to assemble the complete picture. The answer must give: what it is,
who can use it (only if the docs say so), step-by-step how to operate or enable it, related features, and
a complete "Sources used" link list.

**STEP 3D - Developer API** (for `DEVELOPER_API`). `developer.nopaperforms.com` is a Postman SPA that a
plain fetch cannot read, so the skill calls the **Postman MCP** `getCollection` to pull the live endpoint
map and per-endpoint detail: method, URL (base `api.nopaperforms.io`), mandatory vs optional params,
example curl, response shape, error codes, and the auth model. If no Postman MCP is connected, it falls
back to a cached snapshot (`references/meritto-api.md`) plus the live portal link.

**STEP 3M - Mio AI** (for `MIO_AI`). getmio.ai is authoritative for what Mio AI is, its capabilities, and
who it is for; the KB is authoritative for how to set it up. Both are cited; case-study metrics are
attributed, never stated as bare fact.

**STEP 3O - Orientation** (for `ORIENTATION`). Runs the full KB sweep first. Marketing pages are touched
only if the KB is still insufficient, and then only filtered (competitor `*-vs-*`, e-book, event, and
policy pages are hard-excluded) and claims-framed.

**STEP 4 - Source Plan.** The skill decides which sources to actually read and in what priority, following
the authority order above.

**STEP 5 - Fetch, with fallbacks everywhere.** Each source has a graceful degradation path: a 404 article
re-ranks to the next candidate; a failed hub falls back to site-scoped web search; missing yt-dlp falls
back to a YouTube web search; missing LinkedIn cookies fall back to indexed-post search; a missing Postman
MCP falls back to the cached snapshot. The global rule: **never fabricate** - if nothing yields an answer,
it says so and points to the Helpdesk.

**STEP 6 - Synthesize (docs-concierge voice).** Answers lead with a `🎓 AskMeritto · {date}` badge, give
the direct answer first, cite sources as inline links, avoid em-dashes, and ground every claim in fetched
content. Each query type has its own answer shape (numbered steps for how-tos, full API contract for
developer questions, and so on).

**STEP 7 - Raw save.** The fetched sources and the answer are appended to
`~/Documents/AskMeritto/{slug}-raw.md` so every answer is auditable back to its Meritto source.

**STEP 8 - Expert mode.** Follow-up questions are answered from already-fetched content without
re-fetching, until you move to a genuinely new topic. The Topic Guard still applies to every follow-up.

---

## Feature highlights

- **Exhaustive multi-hub KB search** - every relevant KB section is swept before an answer is formed, not
  just one
- **Knowledge base outranks marketing** - marketing copy is demoted to a 0.2-weight, last-resort
  complement and never overrides the docs
- **Feature traversal with full citations** - cross-linked articles are followed and every source used is
  listed
- **Real developer-API detail** - live endpoint specs via the Postman collection, with a cached fallback
- **Mio AI authority split** - product site for "what/who", KB for "how"
- **Topic Guard** - stays strictly inside the Meritto sphere, declines everything else
- **Keyword traps** - reroutes tenant-data, vague, ambiguous, and pricing questions before fetching
- **Raw audit trail** - every answer is saved with its sources
- **Graceful fallbacks** - every source can fail without breaking the answer

---

## Installation

Clone the repo first:

```bash
git clone https://github.com/SomSamantray-Meritto/askmeritto-skill.git
```

> **Portability note.** The skill is authored with Claude Code tool names (`WebFetch`, `WebSearch`,
> `Bash`, `Read`, `Write`, `AskUserQuestion`). On other runtimes these map to the host's equivalents
> (most agents have a web-fetch, a web-search, and a shell tool). The developer-API path is richest when a
> **Postman MCP** is connected, but it still works without one via the cached snapshot. The YouTube helper
> installs `yt-dlp` itself on first use, so it does not depend on the SessionStart hook.

### Claude Code (native)

This is the home format. Copy the folder into your skills directory:

```bash
mkdir -p ~/.claude/skills/askmeritto
cp -r askmeritto-skill/* ~/.claude/skills/askmeritto/
# the parallel Haiku research worker must live where Claude Code discovers subagents:
mkdir -p ~/.claude/agents
cp askmeritto-skill/agents/meritto-researcher.md ~/.claude/agents/
```

The skill is `user-invocable`, so it is immediately available as `/askmeritto <question>`. The
`meritto-researcher` agent (copied above) is what STEP 3 fans out 5-6 of in parallel on Haiku - without it
in `~/.claude/agents/`, the skill falls back to a slower sequential sweep. To wire the `/askmeritto` slash
command and the optional yt-dlp SessionStart hook, also add a command file at
`~/.claude/commands/askmeritto.md` that invokes the skill, and register
`hooks/scripts/check-config.sh` as a `SessionStart` hook in `~/.claude/settings.json`.

For the developer-API path, connect a Postman MCP:

```bash
claude mcp add postman -- npx -y @postman/mcp-server
```

You can also package the folder (it ships a `.claude-plugin/plugin.json`) and install it from a plugin
marketplace.

### Codex CLI

Codex has no native skill format, so reference `SKILL.md` as a standing instruction or a custom prompt.

**Option A - as a slash command.** Create `~/.codex/prompts/askmeritto.md`:

```markdown
Follow the AskMeritto protocol in ~/path/to/askmeritto-skill/SKILL.md exactly.
Answer this Meritto question: $ARGUMENTS
```

Codex exposes files in `~/.codex/prompts/` as `/askmeritto`.

**Option B - always on.** Add a section to `~/.codex/AGENTS.md` (or a project `AGENTS.md`) pointing at the
absolute path of `SKILL.md` and instructing Codex to follow it for Meritto questions.

For the developer-API path, add the Postman MCP to `~/.codex/config.toml`:

```toml
[mcp_servers.postman]
command = "npx"
args = ["-y", "@postman/mcp-server"]
```

Run the YouTube / LinkedIn helper directly with `python3 scripts/meritto_fetch.py youtube --query "..."`.

### OpenCode

OpenCode supports the skill format natively (its `opencode.json` already grants the `skill` permission).
Drop the folder into the global skills directory:

```bash
mkdir -p ~/.config/opencode/skill/askmeritto
cp -r askmeritto-skill/* ~/.config/opencode/skill/askmeritto/
```

(Use `.opencode/skill/askmeritto/` for a project-local install.) The `SKILL.md` frontmatter is read as-is.

Add the Postman MCP to the `mcp` block in `~/.config/opencode/opencode.json`:

```json
{
  "mcp": {
    "postman": {
      "type": "local",
      "enabled": true,
      "command": ["npx", "-y", "@postman/mcp-server"]
    }
  }
}
```

### GitHub Copilot CLI

Copilot CLI auto-discovers skills from installed plugins and exposes a `skill` tool equivalent to Claude's.
Place the folder where your Copilot setup looks for skills/plugins, and the `SKILL.md` is picked up. Map
the Claude tool names to Copilot's equivalents if your version does not alias them automatically.

### Gemini CLI

Gemini CLI loads skill metadata at session start and activates the full content via `activate_skill`.
Reference the skill from your `GEMINI.md` (point at the absolute `SKILL.md` path and instruct Gemini to
follow it for Meritto questions), or place it where your Gemini skills are discovered. Tool names map to
Gemini's web-fetch / web-search / shell equivalents.

### Any other agent (generic)

The skill is just a Markdown instruction file plus a Python script, so any capable agent can run it:

1. **Load the brain.** Paste the contents of `SKILL.md` into the agent's system prompt, rules file, or
   custom-instructions field. That alone gives you the full Topic Guard → classify → sweep → synthesize
   behaviour.
2. **Give it a web-fetch and a web-search tool.** The KB walk, security, getmio.ai, and marketing paths
   need an HTTP fetch; the fallbacks need a web search.
3. **Run the helper for YouTube / LinkedIn** when needed:
   ```bash
   python3 scripts/meritto_fetch.py youtube --query "lead allocation" --transcripts
   python3 scripts/meritto_fetch.py linkedin        # opt-in; see linkedin-setup.md
   ```
4. **Optional Postman MCP** for the richest developer-API answers; otherwise the skill uses
   `references/meritto-api.md`.

---

## Setup and dependencies

- **Python 3** - required only for the YouTube / LinkedIn helper (`scripts/meritto_fetch.py`). Pure
  standard library plus yt-dlp.
- **yt-dlp** - auto-installed on first use (tries `pip --user` → `pipx` → `brew`). Used only to read
  titles and transcripts from Meritto's official YouTube channel. If every install path fails, YouTube
  questions fall back to web search; nothing breaks.
- **Postman MCP** - optional but recommended. Without it, developer-API answers come from the cached
  snapshot plus the live portal link.
- **LinkedIn cookies** - fully optional and **opt-in**. The full company feed is login-walled, so reading
  it requires your `li_at` and `JSESSIONID` session cookies. **This violates LinkedIn's Terms of Service
  and can get your personal account rate-limited, restricted, or banned** - read
  `references/linkedin-setup.md` before opting in. Without cookies, LinkedIn questions use public web
  search instead. Cookies are stored locally only in `~/.config/askmeritto/.env`, never logged, never
  sent anywhere except LinkedIn.

Run the one-time setup helper at any time:

```bash
python3 scripts/meritto_fetch.py setup
```

It creates the save directory, verifies yt-dlp, and reports whether LinkedIn cookies are present.

---

## Repo layout

```
askmeritto-skill/
├── SKILL.md                      the brain - the full instruction contract the agent follows
├── README.md                     this file
├── .claude-plugin/plugin.json    plugin metadata (name, version, description)
├── agents/
│   └── meritto-researcher.md     Haiku KB research worker (5-6 spawned in parallel for the sweep)
├── scripts/
│   └── meritto_fetch.py          youtube | linkedin | setup  (the only code; everything else is fetch/MCP)
├── references/
│   ├── kb-map.md                 KB category hubs + module names (link-resolution seed)
│   ├── meritto-api.md            cached Postman collection snapshot (developer-API fallback)
│   ├── source-policy.md          authority order + marketing exclusion rules
│   └── linkedin-setup.md         how to get li_at + JSESSIONID, with the ToS / ban warning
└── hooks/
    ├── hooks.json                SessionStart hook registration (Claude Code)
    └── scripts/check-config.sh   ensure yt-dlp + create the save dir on session start
```

Raw research trails are saved to `~/Documents/AskMeritto/`.

---

## Security and privacy

- AskMeritto only **reads public Meritto data** and **documents** the API. It never executes tenant API
  calls, and never posts or modifies anything.
- LinkedIn cookies, if you choose to provide them, live only in `~/.config/askmeritto/.env` (chmod 600),
  are never logged, and are sent only to LinkedIn.
- Every answer is saved with its sources to `~/Documents/AskMeritto/` so it can be audited back to the
  Meritto page it came from.

---

Canonical repository: **https://github.com/SomSamantray-Meritto/askmeritto-skill**
