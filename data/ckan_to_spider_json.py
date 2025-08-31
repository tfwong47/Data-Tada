#!/usr/bin/env python3
import sys, json, argparse, re
from pathlib import Path
from urllib.parse import urlparse, urlencode, urlsplit, urlunsplit, parse_qs
import urllib.request

YEAR_RE = re.compile(r"\b(19|20|21)\d{2}\b")

def clean(s):
    if not s:
        return ""
    return " ".join(str(s).split()).strip()

def ext_from_url(u: str) -> str | None:
    try:
        path = urlparse(u).path.lower()
        if "." in path:
            ext = path.rsplit(".", 1)[-1]
            if 1 <= len(ext) <= 5 and ext.isalnum():
                return ext
    except Exception:
        pass
    return None

def collect_data_types(resources):
    types = set()
    for r in resources or []:
        fmt = clean(r.get("format", "")).lower()
        if fmt:
            types.add(fmt)
        url = r.get("url") or r.get("download_url")
        if url:
            ext = ext_from_url(url)
            if ext:
                types.add(ext)
    norm = {t.lower() for t in types if t}
    alias = {
        "xls": "xls", "xlsx": "xlsx", "csv": "csv", "json": "json", "xml": "xml",
        "zip": "zip", "pdf": "pdf", "doc": "doc", "docx": "docx",
        "ppt": "ppt", "pptx": "pptx", "geojson": "geojson", "tsv": "tsv",
        # mild HTML normalization (optional)
        "htm": "html"
    }
    out = set(alias.get(t, t) for t in norm)
    return ", ".join(sorted(out))

def guess_year(title, temporal_from, resources):
    m = YEAR_RE.search(clean(title))
    if m:
        return m.group(0)
    if temporal_from:
        m = YEAR_RE.search(str(temporal_from))
        if m:
            return m.group(0)
    years = []
    for r in resources or []:
        for key in ("last_modified", "created", "metadata_modified"):
            v = r.get(key)
            if v:
                m = YEAR_RE.search(str(v))
                if m:
                    years.append(int(m.group(0)))
    return str(max(years)) if years else ""

def guess_owner(pkg):
    org = (pkg.get("organization") or {}).get("title") or (pkg.get("organization") or {}).get("name")
    if org:
        return clean(org)
    if pkg.get("author"):
        return clean(pkg["author"])
    if pkg.get("maintainer"):
        return clean(pkg["maintainer"])
    return ""

def guess_topic(pkg):
    groups = pkg.get("groups") or []
    names = []
    for g in groups:
        t = clean(g.get("title") or g.get("display_name") or g.get("name"))
        if t:
            names.append(t)
    # de-dup preserving order
    seen, out = set(), []
    for n in names:
        ln = n.lower()
        if ln not in seen:
            seen.add(ln)
            out.append(n)
    return ", ".join(out)

def guess_coverage(pkg):
    cov = clean(pkg.get("spatial_coverage"))
    if cov:
        return cov
    spatial = pkg.get("spatial")
    if isinstance(spatial, str) and spatial:
        s = clean(spatial)
        if len(s) <= 120:
            return s
    return ""

def sample_preview_from_notes(notes):
    return clean(notes)[:280]

def guess_description(pkg):
    return clean(pkg.get("notes") or pkg.get("description") or "")

def guess_license(pkg):
    return clean(pkg.get("license_title") or pkg.get("license_url") or "")

def guess_source_url(pkg):
    if pkg.get("original_harvest_source") and pkg["original_harvest_source"].get("href"):
        return clean(pkg["original_harvest_source"]["href"])
    name = pkg.get("name") or pkg.get("id")
    if name:
        return f"https://data.gov.au/data/dataset/{name}"
    return ""

def transform_package(pkg, *, drop_if_empty_types=True, row_id=None):
    title = clean(pkg.get("title") or pkg.get("name"))
    description = guess_description(pkg)
    owner = guess_owner(pkg)
    topic = guess_topic(pkg)
    year = guess_year(title, pkg.get("temporal_coverage_from"), pkg.get("resources"))
    license_text = guess_license(pkg)
    coverage = guess_coverage(pkg)
    sample_preview = sample_preview_from_notes(pkg.get("notes", ""))
    source_url = guess_source_url(pkg)
    data_types = collect_data_types(pkg.get("resources"))

    if drop_if_empty_types and not data_types:
        return None

    # NOTE: id assigned here at creation time
    return {
        "id": row_id if row_id is not None else "",
        "title": title or "",
        "description": description or "",
        "owner": owner or "",
        "topic": topic or "",
        "year": year or "",
        "license": license_text or "",
        "coverage": coverage or "",
        "sample_preview": sample_preview or "",
        "source_url": source_url or "",
        "data_types": data_types or "",
    }

def fetch_url(u: str) -> str:
    req = urllib.request.Request(u, headers={"User-Agent": "ckan2spider/1.0"})
    with urllib.request.urlopen(req) as r:
        return r.read().decode("utf-8", errors="replace")

def load_json_any(path_or_dash: str):
    # Supports stdin, http(s), or local file
    if path_or_dash == "-":
        text = sys.stdin.read()
    elif path_or_dash.startswith("http://") or path_or_dash.startswith("https://"):
        text = fetch_url(path_or_dash)
    else:
        text = Path(path_or_dash).read_text(encoding="utf-8")
    return json.loads(text)

def ckan_results_from_page(data: dict) -> tuple[list[dict], int | None]:
    if not isinstance(data, dict) or "result" not in data or "results" not in data["result"]:
        raise ValueError("Input is not a CKAN package_search response")
    if not data.get("success", True):
        raise ValueError("CKAN API success=false")
    return data["result"]["results"], data["result"].get("count", None)

def update_query(url: str, **params) -> str:
    parts = urlsplit(url)
    q = parse_qs(parts.query, keep_blank_values=True)
    for k, v in params.items():
        q[k] = [str(v)]
    new_query = urlencode(q, doseq=True)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, new_query, parts.fragment))

def fetch_all_pages(base_url: str) -> list[dict]:
    """Fetch all pages given a package_search URL containing rows & start."""
    data = load_json_any(base_url)
    results, total = ckan_results_from_page(data)
    if total is None:
        return results

    parts = urlsplit(base_url)
    params = parse_qs(parts.query, keep_blank_values=True)
    rows = int(params.get("rows", ["100"])[0])
    start = int(params.get("start", ["0"])[0])

    got = len(results)
    while got < total:
        start += rows
        page_url = update_query(base_url, start=start)
        page_data = load_json_any(page_url)
        page_results, _ = ckan_results_from_page(page_data)
        if not page_results:
            break
        results.extend(page_results)
        got += len(page_results)
    return results

def main():
    ap = argparse.ArgumentParser(description="Convert CKAN package_search JSON (URL/file/stdin) to spider-style JSON.")
    ap.add_argument("input", help="URL to CKAN package_search, local file path, or '-' for stdin")
    ap.add_argument("-o", "--output", default="ckan_output.json", help="Output JSON file")
    ap.add_argument("--keep-empty", action="store_true", help="Keep entries with empty data_types")
    ap.add_argument("--all", action="store_true", help="If input is a CKAN URL, page through all results (uses rows/start)")
    ap.add_argument("--start-id", type=int, default=1, help="Starting ID value for records")
    args = ap.parse_args()

    # Get package list
    if args.input.startswith("http://") or args.input.startswith("https://"):
        if args.all:
            pkgs = fetch_all_pages(args.input)
        else:
            data = load_json_any(args.input)
            pkgs, _ = ckan_results_from_page(data)
    else:
        data = load_json_any(args.input)
        if isinstance(data, dict) and "result" in data and "results" in data["result"]:
            pkgs = data["result"]["results"]
        elif isinstance(data, list):
            pkgs = data
        else:
            print("Unrecognized input structure: expected CKAN package_search JSON.", file=sys.stderr)
            sys.exit(2)

    out = []
    current_id = args.start_id
    for pkg in pkgs:
        row = transform_package(pkg, drop_if_empty_types=not args.keep_empty, row_id=current_id)
        if row is not None:
            out.append(row)
            current_id += 1  # increment only when kept

    Path(args.output).write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {len(out)} records to {args.output}")

if __name__ == "__main__":
    main()
