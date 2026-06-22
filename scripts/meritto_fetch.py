#!/usr/bin/env python3
"""AskMeritto fetch helper.

Subcommands:
  youtube --query Q [--transcripts] [--max N]
  linkedin [--count N]
  kb hub-deep <hub-url>   -- concurrent KB listing (97% token savings vs WebFetch)
  setup

Output is always a single JSON object on stdout so the calling model can branch on
"status". The script never raises uncaught - failures become {"status": "..."}.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import urllib.request
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed

CHANNEL = "https://www.youtube.com/@merittoofficial/videos"
ENV_PATH = os.path.expanduser("~/.config/askmeritto/.env")
SAVE_DIR = os.path.expanduser("~/Documents/AskMeritto")
COMPANY_VANITY = "meritto"


def out(obj):
    print(json.dumps(obj, ensure_ascii=False, indent=2))
    sys.exit(0)


def load_env():
    """Read ~/.config/askmeritto/.env into a dict (KEY=VALUE lines). Env vars win."""
    env = {}
    if os.path.exists(ENV_PATH):
        with open(ENV_PATH) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    env[k.strip()] = v.strip()
    env.update({k: v for k, v in os.environ.items() if k in ("LI_AT", "LI_JSESSIONID")})
    return env


# ponytail: install order pip->pipx->brew covers the hosts we care about; no detection matrix.
def ensure_ytdlp():
    """Return path to yt-dlp, installing it if missing. None if every method fails."""
    found = shutil.which("yt-dlp")
    if found:
        return found, None
    attempts = [
        ([sys.executable, "-m", "pip", "install", "--user", "yt-dlp"], "pip --user"),
        (["pipx", "install", "yt-dlp"], "pipx"),
        (["brew", "install", "yt-dlp"], "brew"),
    ]
    for cmd, label in attempts:
        if cmd[0] == "pipx" and not shutil.which("pipx"):
            continue
        if cmd[0] == "brew" and not shutil.which("brew"):
            continue
        try:
            subprocess.run(cmd, capture_output=True, timeout=300, check=True)
        except Exception:
            continue
        found = shutil.which("yt-dlp")
        if found:
            return found, label
    return None, None


def cmd_youtube(args):
    ytdlp, installed_via = ensure_ytdlp()
    if not ytdlp:
        out({"status": "no_ytdlp",
             "note": "yt-dlp not installed and auto-install failed; caller should WebSearch youtube instead."})
    # Flat playlist listing is cheap and needs no per-video network calls.
    try:
        r = subprocess.run(
            [ytdlp, "--flat-playlist", "--print", "%(title)s\t%(id)s", CHANNEL],
            capture_output=True, text=True, timeout=120, check=True)
    except Exception as e:
        out({"status": "ytdlp_error", "error": str(e), "installed_via": installed_via})

    q = (args.query or "").lower()
    videos = []
    for line in r.stdout.splitlines():
        if "\t" not in line:
            continue
        title, vid = line.split("\t", 1)
        if not q or q in title.lower():
            videos.append({"title": title,
                           "url": f"https://www.youtube.com/watch?v={vid}",
                           "id": vid})
    videos = videos[: args.max]

    if args.transcripts:
        for v in videos:
            v["transcript"] = _transcript(ytdlp, v["id"])

    out({"status": "ok", "installed_via": installed_via,
         "count": len(videos), "videos": videos})


def _transcript(ytdlp, vid):
    """Best-effort auto-sub fetch as plain text. Empty string if none."""
    import tempfile
    import glob
    with tempfile.TemporaryDirectory() as d:
        try:
            subprocess.run(
                [ytdlp, "--skip-download", "--write-auto-subs", "--sub-langs", "en.*,en",
                 "--sub-format", "vtt", "-o", os.path.join(d, "%(id)s.%(ext)s"),
                 f"https://www.youtube.com/watch?v={vid}"],
                capture_output=True, timeout=120, check=True)
        except Exception:
            return ""
        import re
        tag = re.compile(r"<[^>]+>")  # inline <00:00.400><c> timing tags
        text = []
        for fn in glob.glob(os.path.join(d, "*.vtt")):
            with open(fn, errors="ignore") as f:
                for line in f:
                    line = tag.sub("", line).strip()
                    if (not line or "-->" in line or line.startswith("WEBVTT")
                            or line.isdigit() or line.startswith("Kind:")
                            or line.startswith("Language:")):
                        continue
                    if line not in text[-3:]:  # vtt repeats lines; cheap de-dupe
                        text.append(line)
        return " ".join(text)[:5000]


def _voyager_get(url, env):
    csrf = env["LI_JSESSIONID"].strip('"')
    req = urllib.request.Request(url, headers={
        "csrf-token": csrf,
        "x-restli-protocol-version": "2.0.0",
        "x-li-lang": "en_US",
        "accept": "application/vnd.linkedin.normalized+json+2.1",
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
        "cookie": f'li_at={env["LI_AT"]}; JSESSIONID="{csrf}"',
    })
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def cmd_linkedin(args):
    env = load_env()
    if not env.get("LI_AT") or not env.get("LI_JSESSIONID"):
        out({"status": "no_cookies",
             "note": "No LinkedIn cookies set; caller should WebSearch indexed posts. See references/linkedin-setup.md."})
    try:
        org = _voyager_get(
            "https://www.linkedin.com/voyager/api/organization/companies"
            f"?q=universalName&universalName={COMPANY_VANITY}"
            "&decoration=(entityUrn,name,universalName)", env)
    except Exception as e:
        out({"status": "auth_failed", "error": str(e),
             "note": "Cookies likely expired/blocked; caller should WebSearch. LinkedIn use is ToS-risky (see references/linkedin-setup.md)."})
    out({"status": "ok",
         "note": "Org resolved. Post-feed endpoint is reverse-engineered and fragile; "
                 "if it breaks, fall back to WebSearch.",
         "organization": org})


# ---------------------------------------------------------------------------
# KB API — Zoho Desk public JSON endpoints (discovered via Chrome DevTools)
# No auth required. portalId is a static public token for help.meritto.com.
# ---------------------------------------------------------------------------

_KB_BASE = "https://help.meritto.com"
_PORTAL_ID = "edbsn8127bb5cac1d2a212fbb1af1c6fa309cbeb94b497f26f282f6ccf192729bea61"
_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
       "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36")
_KB_HEADERS = {
    "User-Agent": _UA,
    "X-Requested-With": "XMLHttpRequest",
    "Accept": "*/*",
}

# Hub permalink → slug mapping (add more if Meritto adds new hubs)
_HUB_SLUGS = {
    "product-guide": "product-guide",
    "getting-started": "getting-started",
    "how-to-s": "how-to-s",
    "faqs-troubleshooting": "faqs-troubleshooting",
    "solutioning-business-cases": "solutioning-business-cases",
    "product-newsletters": "product-newsletters",
}


def _kb_get(path, params, timeout=15):
    """GET a Zoho Desk KB API endpoint, return parsed JSON. Raises on HTTP error."""
    import ssl
    qs = urllib.parse.urlencode({"portalId": _PORTAL_ID, **params})
    url = f"{_KB_BASE}{path}?{qs}"
    req = urllib.request.Request(url, headers=_KB_HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except ssl.SSLError:
        ctx = ssl._create_unverified_context()
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code in (429, 503):
            import time; time.sleep(2)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8"))
        raise


def _fetch_category_articles(cat_id, cat_name, cat_url):
    """Fetch all articles for one sub-category. Returns dict, never raises."""
    try:
        # limit=100 covers any sub-category; Reports & Dashboards has ~33, the most observed
        data = _kb_get("/portal/api/kbArticles", {
            "categoryId": cat_id, "from": "1", "limit": "100", "locale": "en"
        })
        articles = [
            {
                "title": a["title"],
                "url": a["webUrl"],
                "summary": (a.get("summary") or "").strip()[:300],
                "modified": a.get("modifiedTime", ""),
            }
            for a in data.get("data", [])
        ]
        return {"status": "ok", "name": cat_name, "url": cat_url,
                "id": cat_id, "articles": articles}
    except Exception as e:
        return {"status": "error", "name": cat_name, "url": cat_url,
                "id": cat_id, "articles": [], "error": str(e)}


def _hub_permalink_from_url(hub_url):
    """Extract the slug from a KB hub URL, e.g. '.../kb/product-guide' → 'product-guide'."""
    return hub_url.rstrip("/").split("/")[-1]


def cmd_kb_hub_deep(args):
    hub_url = args.url.rstrip("/")
    permalink = _hub_permalink_from_url(hub_url)

    # 1. Get category tree — ONE API call returns all sub-categories with IDs
    try:
        tree = _kb_get("/portal/api/kbRootCategories/categoryTreeByPermalink", {
            "permalink": permalink,
            "include": "sectionsCount,articlesCount,followersCount",
            "locale": "en",
        })
    except Exception as e:
        out({"status": "fetch_error", "hub_url": hub_url,
             "error": str(e), "fallback": "WebFetch the hub URL directly"})

    sub_cats = tree.get("child", [])

    # Flat hub (e.g. product-newsletters): no sub-categories, articles live on root category
    if not sub_cats:
        root_id = tree.get("id") or tree.get("rootCategoryId")
        root_name = tree.get("translatedName", permalink)
        if not root_id:
            out({"status": "fetch_error", "hub_url": hub_url,
                 "error": "No sub-categories and no root category ID found",
                 "fallback": "WebFetch the hub URL directly"})
        result = _fetch_category_articles(root_id, root_name, hub_url)
        out({
            "status": "ok",
            "hub": permalink,
            "hub_url": hub_url,
            "flat": True,
            "sub_categories": [result],
            "total_articles": len(result["articles"]),
            "failed_sub_categories": [] if result["status"] == "ok" else [root_name],
        })

    # 2. Concurrently fetch articles for every sub-category
    results = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {
            pool.submit(
                _fetch_category_articles,
                sc["id"], sc["translatedName"], sc["webUrl"]
            ): sc for sc in sub_cats
        }
        for fut in as_completed(futures):
            results.append(fut.result())

    results.sort(key=lambda x: x["name"])

    failed = [r["name"] for r in results if r["status"] == "error"]
    total_articles = sum(len(r["articles"]) for r in results)

    # Strip internal keys from output
    sub_category_list = [
        {k: v for k, v in r.items() if k != "id"} for r in results
    ]

    out({
        "status": "ok",
        "hub": permalink,
        "hub_url": hub_url,
        "sub_categories": sub_category_list,
        "total_articles": total_articles,
        "failed_sub_categories": failed,
    })


def cmd_setup(_args):
    os.makedirs(SAVE_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(ENV_PATH), exist_ok=True)
    ytdlp, via = ensure_ytdlp()
    out({"status": "ok",
         "save_dir": SAVE_DIR,
         "ytdlp": bool(ytdlp),
         "ytdlp_installed_via": via,
         "linkedin_cookies_present": bool(load_env().get("LI_AT")),
         "next": "To enable LinkedIn feed access, add LI_AT and LI_JSESSIONID to "
                 f"{ENV_PATH} (chmod 600). Read references/linkedin-setup.md FIRST - it is ToS-risky."})


def main():
    p = argparse.ArgumentParser(prog="meritto_fetch")
    sub = p.add_subparsers(dest="cmd", required=True)

    yt = sub.add_parser("youtube")
    yt.add_argument("--query", default="")
    yt.add_argument("--transcripts", action="store_true")
    yt.add_argument("--max", type=int, default=8)
    yt.set_defaults(func=cmd_youtube)

    li = sub.add_parser("linkedin")
    li.add_argument("--count", type=int, default=10)
    li.set_defaults(func=cmd_linkedin)

    st = sub.add_parser("setup")
    st.set_defaults(func=cmd_setup)

    kb = sub.add_parser("kb", help="KB listing tools (token-efficient)")
    kb_sub = kb.add_subparsers(dest="kb_cmd", required=True)
    hd = kb_sub.add_parser("hub-deep", help="fetch hub + all sub-categories concurrently")
    hd.add_argument("url", help="KB hub URL, e.g. https://help.meritto.com/portal/en/kb/product-guide")
    hd.set_defaults(func=cmd_kb_hub_deep)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
