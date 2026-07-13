#!/usr/bin/env python3
"""Fetch and parse a YouTube interview's subtitles for English-study doc creation.

Downloads the ORIGINAL English track (the words actually spoken) plus, optionally,
a Chinese track, then parses YouTube's json3 caption format into:

  <out>/turns.txt  - subtitle grouped into speaker turns (split on ">>"), each line
                     prefixed with a [mm:ss] timestamp. This is the file to read when
                     planning sections and writing the study doc.
  <out>/full.txt   - every caption cue on its own [mm:ss] line (finer-grained backup).

Why a script: the json3 parsing + speaker-turn splitting is fiddly and gets rewritten
every time; the yt-dlp invocation needs specific flags and 429-retry handling.

Usage:
  # normal: fetch from a URL
  python get_transcript.py "https://www.youtube.com/watch?v=VIDEO_ID" --out ./work

  # parse an already-downloaded json3 file (no network)
  python get_transcript.py --from-json3 ./work/en.en-orig.json3 --out ./work

Notes:
  - English track preference order: en-orig (spoken English) > en. For a bilingual
    interview, en-orig is essential: it captures the guest's real English instead of a
    machine translation of a Chinese ASR track.
  - The YouTube timedtext endpoint frequently returns HTTP 429. This script retries with
    a long sleep (default 90s) which reliably clears it. Do NOT use the tv player_client
    (it hits DRM); the default client works.
  - Requires yt-dlp on PATH.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time


def run_ytdlp(url, langs, out_prefix, auto, retries, sleep_s):
    """Try each lang in order; return the path of the first json3 file written."""
    flag = "--write-auto-subs" if auto else "--write-subs"
    for lang in langs:
        for attempt in range(1, retries + 1):
            cmd = [
                "yt-dlp", "--skip-download", flag,
                "--sub-langs", lang, "--sub-format", "json3",
                "--no-update", "-o", out_prefix + ".%(ext)s", url,
            ]
            print(f"[fetch] lang={lang} ({'auto' if auto else 'manual'}) attempt {attempt}/{retries}", file=sys.stderr)
            proc = subprocess.run(cmd, capture_output=True, text=True)
            out = proc.stdout + proc.stderr
            written = re.search(r"Writing video subtitles to:\s*(.+\.json3)", out)
            # yt-dlp writes the file as <prefix>.<lang>.json3
            candidate = f"{out_prefix}.{lang}.json3"
            if os.path.exists(candidate):
                print(f"[fetch] got {candidate}", file=sys.stderr)
                return candidate
            if "429" in out:
                if attempt < retries:
                    print(f"[fetch] 429 rate-limited; sleeping {sleep_s}s then retrying", file=sys.stderr)
                    time.sleep(sleep_s)
                    continue
            else:
                # not a 429 and no file -> this lang unavailable, try next lang
                break
    return None


def parse_json3(path):
    """Return list of (seconds:int, text:str) cues, in order."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    cues = []
    for ev in data.get("events", []):
        segs = ev.get("segs")
        if not segs:
            continue
        t = ev.get("tStartMs", 0) // 1000
        text = "".join(s.get("utf8", "") for s in segs).replace("\n", " ").strip()
        if text:
            cues.append((t, text))
    return cues


def fmt(t):
    return f"{t // 60:02d}:{t % 60:02d}"


def write_full(cues, out_dir):
    lines = [f"[{fmt(t)}] {x}" for t, x in cues]
    p = os.path.join(out_dir, "full.txt")
    with open(p, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return p


def write_turns(cues, out_dir):
    """Split cues into speaker turns on the '>>' marker YouTube inserts."""
    turns = []
    cur = {"t": cues[0][0] if cues else 0, "text": ""}
    for t, x in cues:
        parts = re.split(r"(>>)", x)
        for p in parts:
            if p == ">>":
                if cur["text"].strip():
                    turns.append(cur)
                cur = {"t": t, "text": ""}
            else:
                chunk = p.strip()
                if chunk:
                    # separate cues/segments with a space to avoid gluing words
                    cur["text"] += (" " if cur["text"] else "") + chunk
    if cur["text"].strip():
        turns.append(cur)
    lines = []
    for tr in turns:
        txt = re.sub(r"\s+", " ", tr["text"]).strip()
        if not txt or txt == "[music]":
            continue
        lines.append(f"[{fmt(tr['t'])}] {txt}")
    p = os.path.join(out_dir, "turns.txt")
    with open(p, "w", encoding="utf-8") as f:
        f.write("\n\n".join(lines))
    return p, len(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url", nargs="?", help="YouTube video URL")
    ap.add_argument("--from-json3", help="Parse an existing json3 file instead of fetching")
    ap.add_argument("--out", default=".", help="Output directory (default: cwd)")
    ap.add_argument("--zh", action="store_true", help="Also fetch a Chinese track (reference)")
    ap.add_argument("--retries", type=int, default=4)
    ap.add_argument("--sleep", type=int, default=90, help="Seconds to sleep on HTTP 429")
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)

    if args.from_json3:
        en_path = args.from_json3
    else:
        if not args.url:
            ap.error("provide a URL or --from-json3")
        en_path = run_ytdlp(args.url, ["en-orig", "en"], os.path.join(args.out, "en"),
                            auto=True, retries=args.retries, sleep_s=args.sleep)
        if not en_path:
            print("ERROR: could not download an English track (en-orig/en).", file=sys.stderr)
            sys.exit(1)
        if args.zh:
            # manual zh first, then auto
            zh = run_ytdlp(args.url, ["zh-Hant", "zh-Hans", "zh"], os.path.join(args.out, "zh"),
                           auto=False, retries=args.retries, sleep_s=args.sleep)
            if not zh:
                run_ytdlp(args.url, ["zh-Hant", "zh-Hans"], os.path.join(args.out, "zh"),
                          auto=True, retries=args.retries, sleep_s=args.sleep)

    cues = parse_json3(en_path)
    if not cues:
        print("ERROR: no cues parsed from json3.", file=sys.stderr)
        sys.exit(1)
    full_p = write_full(cues, args.out)
    turns_p, n = write_turns(cues, args.out)
    dur = cues[-1][0]
    words = len(re.findall(r"\b\w+\b", " ".join(x for _, x in cues)))
    print(f"OK  cues={len(cues)}  turns={n}  duration={fmt(dur)}  english_words~={words}")
    print(f"    {turns_p}")
    print(f"    {full_p}")


if __name__ == "__main__":
    main()
