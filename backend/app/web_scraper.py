"""
web_scraper.py — polite, robots-respecting datasheet collector for NIRACONCHEM AI.

Design principles (ToS-safe by default):
  * WHITELIST ONLY. Nothing is fetched unless the manufacturer is explicitly
    listed in MANUFACTURERS below AND you set `allow_scrape=True`.
  * Honors robots.txt for every host (urllib.robotparser).
  * Never parses/scrapes HTML product prose. Instead it finds the LINKED
    datasheet PDF (TDS/MSDS) on each product page and downloads that binary
    into raw_manufacturer_docs/<brand>/ — exactly the input the booster ingests.
  * Throttled (min delay between requests), identifies via a contact User-Agent.
  * All HTML text stays on disk; the AI is trained only on the datasheet PDFs.

This module only COLLECTS datasheets. To turn them into the AI dataset, run:
    python -m app.ingest_booster --source ../raw_manufacturer_docs --rewrite

WARNING: verify each manufacturer's ToS/robots.txt permits datasheet retrieval
before enabling allow_scrape. Default is OFF.
"""
from __future__ import annotations

import argparse
import time
import urllib.robotparser
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

# ---- configuration -------------------------------------------------------
USER_AGENT = "NIRACONCHEM-AI-DatasetBuilder/1.0 (+contact: founder@niraconchem.ai)"
REQUEST_DELAY = 2.0  # seconds between requests to the same host
TIMEOUT = 30

# Whitelist. Add a manufacturer only after confirming ToS/robots permission.
# `product_index` = a page listing products; `pdf_hint` helps find datasheet links.
MANUFACTURERS = {
    # Example shape — DO NOT enable scraping until you have permission + a real URL:
    # "Saveto": {
    #     "base": "https://www.saveto.example.com",
    #     "product_index": "https://www.saveto.example.com/products",
    #     "pdf_hint": "datasheet",
    # },
}

PDF_EXT = (".pdf", ".PDF")
_session = requests.Session()
_session.headers.update({"User-Agent": USER_AGENT})


def _can_fetch(url: str) -> bool:
    parsed = urlparse(url)
    rp = urllib.robotparser.RobotFileParser()
    rp.set_url(f"{parsed.scheme}://{parsed.netloc}/robots.txt")
    try:
        rp.read()
    except Exception:  # noqa: BLE001
        return False  # be conservative: if we can't read robots, don't fetch
    return rp.can_fetch(USER_AGENT, url)


def _get(url: str) -> str | None:
    if not _can_fetch(url):
        print(f"  robots disallow: {url}")
        return None
    try:
        resp = _session.get(url, timeout=TIMEOUT)
        resp.raise_for_status()
        return resp.text
    except Exception as exc:  # noqa: BLE001
        print(f"  fetch failed {url}: {exc}")
        return None


def _find_pdf_links(html: str, base: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        text = (a.get_text() or "").lower()
        if href.lower().endswith(PDF_EXT) or any(h in text for h in ("datasheet", "tds", "pdf", "download")):
            if href.lower().endswith(PDF_EXT):
                links.append(urljoin(base, href))
    # de-dup
    seen, out = set(), []
    for l in links:
        if l not in seen:
            seen.add(l); out.append(l)
    return out


def collect_manufacturer(name: str, cfg: dict, out_root: Path, allow_scrape: bool) -> int:
    if not allow_scrape:
        print(f"[skip] {name}: scraping disabled (pass --allow-scrape to enable)")
        return 0
    index_url = cfg.get("product_index")
    if not index_url:
        print(f"[skip] {name}: no product_index URL configured")
        return 0
    if not _can_fetch(index_url):
        print(f"[skip] {name}: robots disallow index")
        return 0

    dest = out_root / name
    dest.mkdir(parents=True, exist_ok=True)

    print(f"[collect] {name} <- {index_url}")
    html = _get(index_url)
    if not html:
        return 0
    pdf_links = _find_pdf_links(html, cfg.get("base", index_url))
    print(f"  found {len(pdf_links)} datasheet PDF links")

    downloaded = 0
    for link in pdf_links:
        if not _can_fetch(link):
            continue
        try:
            r = _session.get(link, timeout=TIMEOUT)
            r.raise_for_status()
            if r.headers.get("Content-Type", "").lower().startswith("application"):
                fname = dest / Path(urlparse(link).path).name
                if not fname.suffix:
                    fname = fname.with_suffix(".pdf")
                fname.write_bytes(r.content)
                downloaded += 1
                print(f"  saved {fname.name} ({len(r.content)} bytes)")
        except Exception as exc:  # noqa: BLE001
            print(f"  pdf fail {link}: {exc}")
        time.sleep(REQUEST_DELAY)
    return downloaded


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--allow-scrape", action="store_true",
                    help="REQUIRED to actually fetch. Off by default (ToS-safe).")
    ap.add_argument("--out", default="../raw_manufacturer_docs",
                    help="where datasheet PDFs are saved")
    args = ap.parse_args()

    out_root = Path(args.out)
    out_root.mkdir(parents=True, exist_ok=True)
    total = 0
    for name, cfg in MANUFACTURERS.items():
        total += collect_manufacturer(name, cfg, out_root, args.allow_scrape)
    print(f"\n[done] downloaded {total} datasheet PDFs into {out_root}")
    if total and args.allow_scrape:
        print("Next: python -m app.ingest_booster --source ../raw_manufacturer_docs --rewrite")


if __name__ == "__main__":
    main()
