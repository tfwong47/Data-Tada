#!/usr/bin/env python3
import sys, argparse, gzip, urllib.request, urllib.parse, xml.etree.ElementTree as ET

NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}

# Default keywords that commonly indicate data endpoints/resources
DEFAULT_KEYWORDS = [
    # API / data endpoints
    "api", "apis", "graphql", "rest", "odata",
    # data nouns
    "data", "dataset", "datasets", "resources", "records", "entries",
    "feed", "stream", "datastore",
    # reporting / analytics
    "stats", "statistics", "report", "reports", "analytics", "metrics",
    # gov/open data
    "opendata", "catalog", "downloads", "ckan",
    # file-ish hints/extensions (as path substrings is fine)
    "json", "xml", "csv", "rdf", "geojson", "xlsx"
]

def fetch_bytes(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "sitemap-filter/1.0"})
    with urllib.request.urlopen(req) as r:
        data = r.read()
        enc = r.headers.get("Content-Encoding", "")
        if url.endswith(".gz") or "gzip" in enc.lower():
            try:
                import gzip as _gzip
                return _gzip.decompress(data)
            except OSError:
                pass  # not actually gzipped
        return data

def parse_xml_bytes(b: bytes) -> ET.Element:
    return ET.fromstring(b)

def collect_urls_from_sitemap(url: str) -> list[str]:
    """Returns all <loc> URLs from a sitemap or sitemap index (recursively, 1 level)."""
    root = parse_xml_bytes(fetch_bytes(url))
    urls = []

    # urlset
    for loc in root.findall(".//sm:url/sm:loc", NS):
        if loc.text:
            urls.append(loc.text.strip())

    # sitemapindex (one level deep)
    if not urls:
        for sm_loc in root.findall(".//sm:sitemap/sm:loc", NS):
            if sm_loc.text:
                try:
                    urls.extend(collect_urls_from_urlset(sm_loc.text.strip()))
                except Exception:
                    pass
    return urls

def collect_urls_from_urlset(url: str) -> list[str]:
    root = parse_xml_bytes(fetch_bytes(url))
    out = []
    for loc in root.findall(".//sm:url/sm:loc", NS):
        if loc.text:
            out.append(loc.text.strip())
    return out

def dedupe_preserve_order(items):
    seen = set()
    out = []
    for x in items:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out

def filter_by_keywords(urls: list[str], keywords: list[str]) -> list[str]:
    """Keep URLs whose *path* contains any of the keywords (case-insensitive)."""
    kws = [k.lower() for k in keywords]
    out = []
    for u in urls:
        try:
            path = urllib.parse.urlsplit(u).path.lower()
        except Exception:
            path = ""
        if any(k in path for k in kws):
            out.append(u)
    return out

def main():
    p = argparse.ArgumentParser(description="Filter sitemap URLs to those with data-related path keywords.")
    p.add_argument("sitemap_url", help="URL to sitemap.xml (or sitemap.xml.gz)")
    p.add_argument("--output", "-o", help="Write results to a file instead of stdout")
    p.add_argument("--limit", "-n", type=int, default=0, help="Maximum number of URLs to output (0 = no limit)")
    # Optional override (comma-separated) if you ever want to customize the keywords
    p.add_argument("--keywords", "-k", help="Comma-separated keywords to match in paths (default built-in list)")
    args = p.parse_args()

    try:
        urls = collect_urls_from_sitemap(args.sitemap_url)
        urls = dedupe_preserve_order(urls)

        keywords = DEFAULT_KEYWORDS
        if args.keywords:
            keywords = [s.strip() for s in args.keywords.split(",") if s.strip()]

        filtered = filter_by_keywords(urls, keywords)
        if args.limit and args.limit > 0:
            filtered = filtered[:args.limit]

        text = "\n".join(filtered) + ("\n" if filtered else "")
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(text)
        else:
            sys.stdout.write(text)
    except Exception as e:
        sys.stderr.write(f"Error: {e}\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
