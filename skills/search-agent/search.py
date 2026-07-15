#!/usr/bin/env python3
"""search-agent helper — key-free academic search + citation verification.

Wraps three public APIs (arXiv, DBLP, OpenReview). No API key required.
Falls back gracefully: on any network error it prints a JSON error line so the
caller (Claude) knows to retry via the WebSearch / WebFetch tools.

Usage:
  search.py search "<query>" [--max N]          # arXiv full-text search
  search.py dblp   "<query>" [--max N]          # DBLP venue/acceptance lookup
  search.py verify --title T [--author A] [--year Y]
  search.py bib    path/to/references.bib       # audit every entry in a .bib
"""
import argparse
import json
import re
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from difflib import SequenceMatcher

UA = {"User-Agent": "search-agent/1.0 (academic citation verifier)"}
TIMEOUT = 20


def _get(url, retries=2):
    last = None
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                return r.read().decode("utf-8", "replace")
        except Exception as e:  # transient 5xx / timeout — back off and retry
            last = e
            if attempt < retries:
                time.sleep(1.5 * (attempt + 1))
    raise last


def _norm(s):
    return re.sub(r"[^a-z0-9 ]", "", (s or "").lower()).strip()


def _sim(a, b):
    return SequenceMatcher(None, _norm(a), _norm(b)).ratio()


# ---------------------------------------------------------------- arXiv
def arxiv_search(query, maxn=50, field="all"):
    # field="ti" restricts to the title — far more precise for verification.
    q = urllib.parse.quote(query)
    url = (
        "http://export.arxiv.org/api/query?"
        f"search_query={field}:{q}&start=0&max_results={maxn}"
        "&sortBy=relevance"
    )
    xml = _get(url)
    ns = {"a": "http://www.w3.org/2005/Atom"}
    root = ET.fromstring(xml)
    out = []
    for e in root.findall("a:entry", ns):
        aid = (e.findtext("a:id", "", ns) or "").rsplit("/", 1)[-1]
        title = " ".join((e.findtext("a:title", "", ns) or "").split())
        authors = [a.findtext("a:name", "", ns) for a in e.findall("a:author", ns)]
        published = e.findtext("a:published", "", ns) or ""
        out.append(
            {
                "title": title,
                "authors": authors,
                "year": published[:4],
                "arxiv_id": aid,
                "venue": "arXiv",
                "url": f"https://arxiv.org/abs/{aid}",
            }
        )
    return out


# ---------------------------------------------------------------- DBLP
def dblp_search(query, maxn=30):
    q = urllib.parse.quote(query)
    url = f"https://dblp.org/search/publ/api?q={q}&format=json&h={maxn}"
    data = json.loads(_get(url))
    hits = data.get("result", {}).get("hits", {}).get("hit", [])
    out = []
    for h in hits:
        info = h.get("info", {})
        authors = info.get("authors", {}).get("author", [])
        if isinstance(authors, dict):
            authors = [authors]
        names = [a.get("text") if isinstance(a, dict) else a for a in authors]
        out.append(
            {
                "title": info.get("title", "").rstrip("."),
                "authors": names,
                "year": info.get("year", ""),
                "venue": info.get("venue", ""),
                "type": info.get("type", ""),  # e.g. "Conference and Workshop Papers"
                "url": info.get("url", ""),
                "doi": info.get("doi", ""),
            }
        )
    return out


# ---------------------------------------------------------------- verify
def verify(title, author=None, year=None):
    """Return a verdict dict: verified | mismatch | not_found, with best match."""
    result = {"title": title, "verdict": "not_found", "match": None, "source": None}
    candidates = []
    # Folding the author into the query rescues exact matches that relevance
    # ranking otherwise buries under derivative "... is All You Need" titles.
    dblp_q = f"{title} {author}" if author else title
    try:
        candidates += [("dblp", c) for c in dblp_search(dblp_q, maxn=15)]
    except Exception as e:
        result["dblp_error"] = str(e)
    try:  # title-field query first — most precise for exact-title verification
        candidates += [("arxiv", c) for c in arxiv_search(title, maxn=15, field="ti")]
    except Exception as e:
        result["arxiv_error"] = str(e)

    best, best_score, best_src = None, 0.0, None
    for src, c in candidates:
        s = _sim(title, c["title"])
        if s > best_score:
            best, best_score, best_src = c, s, src

    if not best or best_score < 0.6:
        return result

    result["match"], result["source"], result["title_sim"] = best, best_src, round(best_score, 3)
    ok_title = best_score >= 0.9
    ok_author = True
    if author:
        ok_author = any(_norm(author) in _norm(a) for a in best.get("authors", []))
    ok_year = True
    if year and best.get("year"):
        try:
            ok_year = abs(int(year) - int(best["year"])) <= 1
        except ValueError:
            ok_year = False
    result["checks"] = {"title": ok_title, "author": ok_author, "year": ok_year}
    result["verdict"] = "verified" if (ok_title and ok_author and ok_year) else "mismatch"
    return result


# ---------------------------------------------------------------- .bib audit
def audit_bib(path):
    text = open(path, encoding="utf-8").read()
    entries = re.findall(r"@\w+\{[^@]*?\n\}", text, re.DOTALL)
    results = []
    for i, e in enumerate(entries):
        title = (re.search(r"title\s*=\s*[{\"]+(.+?)[}\"]+\s*,", e, re.DOTALL) or [None, ""])[1]
        title = " ".join(title.split())
        authorf = (re.search(r"author\s*=\s*[{\"]+(.+?)[}\"]+\s*,", e, re.DOTALL) or [None, ""])[1]
        author = authorf.split(" and ")[0].split(",")[0].strip()
        year = (re.search(r"year\s*=\s*[{\"]?(\d{4})", e) or [None, ""])[1]
        if not title:
            continue
        results.append(verify(title, author or None, year or None))
        time.sleep(0.5)  # be polite to the APIs
        # audit in batches of 20 — flush progress so a long run is observable
        if (i + 1) % 20 == 0:
            print(f"# audited {i+1} entries", file=sys.stderr)
    return results


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("search"); s.add_argument("query"); s.add_argument("--max", type=int, default=50)
    d = sub.add_parser("dblp");   d.add_argument("query"); d.add_argument("--max", type=int, default=30)
    v = sub.add_parser("verify")
    v.add_argument("--title", required=True); v.add_argument("--author"); v.add_argument("--year")
    b = sub.add_parser("bib");    b.add_argument("path")
    a = ap.parse_args()

    try:
        if a.cmd == "search":
            for row in arxiv_search(a.query, a.max):
                print(json.dumps(row, ensure_ascii=False))
        elif a.cmd == "dblp":
            for row in dblp_search(a.query, a.max):
                print(json.dumps(row, ensure_ascii=False))
        elif a.cmd == "verify":
            print(json.dumps(verify(a.title, a.author, a.year), ensure_ascii=False, indent=2))
        elif a.cmd == "bib":
            res = audit_bib(a.path)
            bad = [r for r in res if r["verdict"] != "verified"]
            for r in res:
                print(json.dumps(r, ensure_ascii=False))
            print(
                f"# {len(res)} entries: "
                f"{sum(1 for r in res if r['verdict']=='verified')} verified, "
                f"{sum(1 for r in res if r['verdict']=='mismatch')} mismatch, "
                f"{sum(1 for r in res if r['verdict']=='not_found')} not_found",
                file=sys.stderr,
            )
            sys.exit(1 if bad else 0)
    except Exception as e:
        # Signal the caller (Claude) to fall back to WebSearch/WebFetch.
        print(json.dumps({"error": str(e), "fallback": "use WebSearch/WebFetch tools"}))
        sys.exit(2)


if __name__ == "__main__":
    main()
