#!/usr/bin/env python3
import sys
from pathlib import Path
import tempfile
import json

from sitemap_filter import (
    collect_urls_from_sitemap,
    dedupe_preserve_order,
    filter_by_keywords,
    DEFAULT_KEYWORDS,
)

# Reuse your CKAN converter functions
from ckan_to_spider_json import (
    fetch_all_pages,
    load_json_any,
    ckan_results_from_page,
    transform_package,
)

from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from govscrape.spiders.main_body_spider import MainBodySpider


def _read_api_links(path: Path) -> list[str]:
    """Read non-empty, non-comment lines from api_links.txt"""
    lines = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        s = raw.strip()
        if not s or s.startswith("#"):
            continue
        lines.append(s)
    return lines


def _ckan_collect_all(api_urls: list[str], start_id: int) -> tuple[list[dict], int]:
    """
    For each CKAN package_search URL, fetch all pages (respects rows/start in URL),
    transform into target schema, and assign IDs starting from start_id.
    Returns (rows, next_id).
    """
    out = []
    current_id = start_id
    for url in api_urls:
        try:
            # If it's clearly a CKAN URL, fetch pages; else try to load once.
            if url.startswith("http://") or url.startswith("https://"):
                # Prefer full pagination if URL has rows/start (works either way)
                pkgs = fetch_all_pages(url)
            else:
                data = load_json_any(url)
                if isinstance(data, dict):
                    pkgs, _ = ckan_results_from_page(data)
                elif isinstance(data, list):
                    pkgs = data
                else:
                    print(f"[ckan] Skipping unrecognized structure from: {url}")
                    continue

            for pkg in pkgs:
                row = transform_package(pkg, drop_if_empty_types=True, row_id=current_id)
                if row is not None:
                    out.append(row)
                    current_id += 1
        except Exception as e:
            print(f"[ckan] Error processing {url}: {e}")
            continue

    return out, current_id


def run_pipeline(
    sitemap_url: str,
    *,
    item_limit: int = 0,
    page_limit: int = 0,
    keywords=None,
    output: str = "datasets.json",
    api_links_file: str = "api_links.txt",
):
    # -------------------------------
    # 0) CKAN side: collect + transform with sequential IDs
    # -------------------------------
    api_file = Path(api_links_file)
    ckan_rows = []
    next_id = 1
    if api_file.exists():
        api_urls = _read_api_links(api_file)
        if api_urls:
            print(f"[ckan] Found {len(api_urls)} API URLs in {api_file}")
            ckan_rows, next_id = _ckan_collect_all(api_urls, start_id=1)
            print(f"[ckan] Kept {len(ckan_rows)} records; next_id = {next_id}")
        else:
            print(f"[ckan] {api_file} is empty; skipping CKAN step.")
    else:
        print(f"[ckan] {api_file} not found; skipping CKAN step.")

    # -------------------------------
    # 1) Sitemap filter for spider URLs
    # -------------------------------
    urls = collect_urls_from_sitemap(sitemap_url)
    urls = dedupe_preserve_order(urls)
    kws = keywords or DEFAULT_KEYWORDS
    filtered = filter_by_keywords(urls, kws)

    if not filtered:
        print("No matching URLs found after filtering.")
        # Even if no spider URLs, still write CKAN output if any
        Path(output).write_text(json.dumps(ckan_rows, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[final] Wrote {len(ckan_rows)} records to {output}")
        return

    # Write start URLs for spider
    tmp_urls_file = Path(tempfile.mkstemp(suffix=".txt")[1])
    tmp_urls_file.write_text("\n".join(filtered), encoding="utf-8")

    # Temporary spider output
    tmp_spider_json = Path(tempfile.mkstemp(suffix=".json")[1])

    # -------------------------------
    # 2) Configure Scrapy run (spider continues IDs from next_id)
    # -------------------------------
    settings = get_project_settings()
    # Feed: overwrite tmp spider file (we'll merge with CKAN afterward)
    settings.set(
        "FEEDS",
        {
            str(tmp_spider_json): {
                "format": "json",
                "encoding": "utf8",
                "overwrite": True,
            }
        },
        priority="cmdline",
    )

    # Apply scraper-side limits at crawler level
    if item_limit and item_limit > 0:
        settings.set("CLOSESPIDER_ITEMCOUNT", item_limit, priority="cmdline")
    if page_limit and page_limit > 0:
        settings.set("CLOSESPIDER_PAGECOUNT", page_limit, priority="cmdline")

    # Sensible defaults
    settings.set("ROBOTSTXT_OBEY", True, priority="cmdline")
    settings.set("FEED_EXPORT_ENCODING", "utf-8", priority="cmdline")

    process = CrawlerProcess(settings)
    # Pass urls_file and start_id so the spider can assign IDs
    process.crawl(MainBodySpider, urls_file=str(tmp_urls_file), start_id=next_id)
    process.start()

    # -------------------------------
    # 3) Merge CKAN rows + spider rows into final output
    # -------------------------------
    spider_rows = []
    try:
        if tmp_spider_json.exists():
            spider_rows = json.loads(tmp_spider_json.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[merge] Could not read spider output: {e}")

    combined = ckan_rows + (spider_rows or [])
    Path(output).write_text(json.dumps(combined, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[final] Wrote {len(combined)} records to {output}")


def _parse_args(argv):
    import argparse

    p = argparse.ArgumentParser(
        description="Run: (1) CKAN package_search from api_links.txt, (2) sitemap filter, (3) Scrapy spider; then merge outputs."
    )
    p.add_argument("sitemap_url", help="URL to sitemap.xml (or .gz)")
    p.add_argument(
        "--item-limit",
        type=int,
        default=0,
        help="Stop after N items scraped (post-pipeline). 0 = no limit.",
    )
    p.add_argument(
        "--page-limit",
        type=int,
        default=0,
        help="Stop after N pages fetched. 0 = no limit.",
    )
    p.add_argument(
        "--keywords",
        help="Comma-separated keyword overrides for filtering (default list used if omitted).",
    )
    p.add_argument(
        "--output",
        default="datasets.json",
        help="Final merged JSON filename (default: datasets.json)",
    )
    p.add_argument(
        "--api-links",
        default="api_links.txt",
        help="Path to a file containing CKAN package_search URLs (default: api_links.txt)",
    )
    return p.parse_args(argv)


if __name__ == "__main__":
    args = _parse_args(sys.argv[1:])
    kws = (
        [s.strip() for s in args.keywords.split(",") if s.strip()]
        if args.keywords
        else None
    )
    run_pipeline(
        args.sitemap_url,
        item_limit=args.item_limit,
        page_limit=args.page_limit,
        keywords=kws,
        output=args.output,
        api_links_file=args.api_links,
    )
