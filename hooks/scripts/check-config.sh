#!/usr/bin/env bash
# AskMeritto SessionStart hook: ensure the save dir exists and yt-dlp is available.
# Quiet on the happy path; only speaks when it installs something or hits a problem.
set -u

SAVE_DIR="${HOME}/Documents/AskMeritto"
mkdir -p "$SAVE_DIR"

if command -v yt-dlp >/dev/null 2>&1; then
  exit 0
fi

# yt-dlp missing: try to install it (user authorized this in setup). pip -> pipx -> brew.
INSTALLED_VIA=""
if command -v python3 >/dev/null 2>&1 && python3 -m pip install --user yt-dlp >/dev/null 2>&1; then
  INSTALLED_VIA="pip --user"
elif command -v pipx >/dev/null 2>&1 && pipx install yt-dlp >/dev/null 2>&1; then
  INSTALLED_VIA="pipx"
elif command -v brew >/dev/null 2>&1 && brew install yt-dlp >/dev/null 2>&1; then
  INSTALLED_VIA="brew"
fi

if command -v yt-dlp >/dev/null 2>&1; then
  echo "AskMeritto installed yt-dlp (via ${INSTALLED_VIA}). It is used only to read titles and transcripts from Meritto's official YouTube channel (@merittoofficial) so video-based answers are grounded. Nothing is downloaded."
else
  echo "AskMeritto could not install yt-dlp on this host. YouTube questions will fall back to web search until yt-dlp is available."
fi
exit 0
