#!/usr/bin/env python3
"""AskMeritto fetch helper.

Two sources need a script because WebFetch can't do them:
  - YouTube transcripts/listing (yt-dlp)
  - LinkedIn company feed (auth-cookie Voyager API, opt-in)

Everything else in the skill (KB, security, getmio.ai, marketing) is plain WebFetch,
and the developer API is the Postman MCP. So this stays small on purpose.

Subcommands:
  youtube --query Q [--transcripts] [--max N]
  linkedin [--count N]
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

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
