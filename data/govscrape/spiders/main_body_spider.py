# govscrape/spiders/main_body_spider.py
from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urljoin, urlparse

import scrapy
from parsel import Selector
from w3lib.html import remove_tags, replace_entities


YEAR_RE = re.compile(r"\b(19|20|21)\d{2}\b")
# Common downloadable extensions we care about
KNOWN_EXTS = {
    "csv", "tsv", "xlsx", "xls", "json", "xml", "rdf", "geojson",
    "zip", "pdf", "doc", "docx", "ppt", "pptx"
}


class MainBodySpider(scrapy.Spider):
    name = "main_body"

    custom_settings = {
        # Keep smallish default concurrency; obey robots from settings.py/run script
        "DOWNLOAD_TIMEOUT": 30,
        "FEED_EXPORT_ENCODING": "utf-8",
        # Avoid being blocked by trivial duplicate filtering when anchors differ
        "DUPEFILTER_DEBUG": False,
    }

    def __init__(self, urls_file: str | None = None, start_id: int | str = 1, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.urls_file = urls_file
        try:
            self._id_counter = int(start_id)
        except Exception:
            self._id_counter = 1

        # No default page; if urls_file missing/empty, we just don't crawl anything.
        if self.urls_file:
            p = Path(self.urls_file)
            if p.exists():
                self.start_urls = [u.strip() for u in p.read_text(encoding="utf-8").splitlines() if u.strip()]
            else:
                self.logger.warning("urls_file not found: %s", self.urls_file)
                self.start_urls = []
        else:
            self.start_urls = []

    # --------------------
    # Helpers
    # --------------------
    def _sel(self, response: scrapy.http.Response) -> Selector | None:
        """
        Return a Selector scoping to the main content area if possible.
        Try typical main containers seen on gov sites/Drupal.
        """
        sel = response.selector
        # Prefer explicit main content region
        for css in [
            "main#main-content",
            "#main-content",
            "main[role='main']",
            "article.node",
            "article[role='article']",
            "article",
            "div[role='main']",
            "section.section .region-content",
            ".region.region-content",
        ]:
            nodes = sel.css(css)
            if nodes:
                return nodes
        return sel  # fallback to full page

    @staticmethod
    def _clean_text(html_text: str) -> str:
        # Remove tags/entities, collapse whitespace
        if not html_text:
            return ""
        t = replace_entities(remove_tags(html_text))
        return " ".join(t.split()).strip()

    @staticmethod
    def _first_nonempty(*values: str) -> str:
        for v in values:
            if v and v.strip():
                return v.strip()
        return ""

    @staticmethod
    def _ext_from_href(href: str) -> str | None:
        try:
            path = urlparse(href).path.lower()
            if "." in path:
                ext = path.rsplit(".", 1)[-1]
                # Strip trailing punctuation or query-styled remnants
                ext = re.sub(r"[^a-z0-9]+$", "", ext)
                if 1 <= len(ext) <= 5 and ext.isalnum():
                    return ext
        except Exception:
            pass
        return None

    @staticmethod
    def _collect_data_types_from_links(container: Selector, base_url: str) -> set[str]:
        exts: set[str] = set()

        # 1) <a class="file type-xlsx"> pattern
        for a in container.css("a.file"):
            classes = " ".join(a.attrib.get("class", "").lower().split())
            # Class may contain "type-xxx"
            for m in re.finditer(r"type-([a-z0-9]+)", classes):
                exts.add(m.group(1))

            href = a.attrib.get("href")
            if href:
                abs_url = urljoin(base_url, href)
                ext = MainBodySpider._ext_from_href(abs_url)
                if ext:
                    exts.add(ext)

        # 2) Any links that look like files by extension
        for a in container.css("a[href]"):
            href = a.attrib.get("href")
            if not href:
                continue
            abs_url = urljoin(base_url, href)
            ext = MainBodySpider._ext_from_href(abs_url)
            if ext:
                exts.add(ext)

        # Normalize known ext aliases
        norm_map = {
            "htm": "html",
        }
        out = set()
        for e in exts:
            e = e.lower()
            e = norm_map.get(e, e)
            out.add(e)
        # Keep only known data-ish types if you want to exclude plain html
        # (If you prefer to include html/aspx too, comment next line out)
        # return {e for e in out if e in KNOWN_EXTS}
        return out

    @staticmethod
    def _extract_title(container: Selector, fallback_sel: Selector) -> str:
        title = container.css("h1::text").get()
        if not title:
            title = fallback_sel.css("title::text").get()
        return (title or "").strip()

    @staticmethod
    def _extract_description(container: Selector) -> str:
        # Common Drupal intro field
        intro = container.css(".field--name-field-intro, .node-intro").get()
        if intro:
            return MainBodySpider._clean_text(intro)

        # Meta description fallback if present outside container
        return ""

    @staticmethod
    def _extract_owner(container: Selector) -> str:
        # Try details: Creator / Publisher fields
        # <dt>Creator</dt><dd>...</dd> etc.
        owner = ""
        dls = container.css("dl.details")
        if dls:
            # Map dt text -> dd text
            for dl in dls:
                dts = [MainBodySpider._clean_text(x) for x in dl.css("dt").getall()]
                dds = [MainBodySpider._clean_text(x) for x in dl.css("dd").getall()]
                mapping = dict(zip(dts, dds))
                owner = mapping.get("Creator") or mapping.get("Publisher") or ""
                if owner:
                    break
        # Other common selector (publisher text blocks)
        if not owner:
            owner = MainBodySpider._clean_text(" ".join(container.css(".field--name-field-publication-publisher ::text").getall()))
        return owner

    @staticmethod
    def _extract_topic(container: Selector) -> str:
        # Drupal taxonomy tags often live in .field--name-field-tags or breadcrumbs
        tags = [t.strip() for t in container.css(".field--name-field-tags a::text").getall() if t.strip()]
        if tags:
            # dedupe preserving order
            seen, out = set(), []
            for t in tags:
                tl = t.lower()
                if tl not in seen:
                    seen.add(tl)
                    out.append(t)
            return ", ".join(out)
        return ""

    @staticmethod
    def _extract_year(title: str, container: Selector) -> str:
        # 1) From title
        m = YEAR_RE.search(title or "")
        if m:
            return m.group(0)

        # 2) From details (Creation Date / Published)
        for dl in container.css("dl.details"):
            dts = [MainBodySpider._clean_text(x) for x in dl.css("dt").getall()]
            dds = [MainBodySpider._clean_text(x) for x in dl.css("dd").getall()]
            mapping = dict(zip(dts, dds))
            for key in ("Creation Date", "Published", "Publication date", "Date"):
                val = mapping.get(key)
                if val:
                    mm = YEAR_RE.search(val)
                    if mm:
                        return mm.group(0)

        # 3) From any time tags
        for time in container.css("time::attr(datetime), time::text").getall():
            mm = YEAR_RE.search(time)
            if mm:
                return mm.group(0)

        return ""

    @staticmethod
    def _extract_license(container: Selector) -> str:
        # Many pages won’t expose a license—leave blank if unknown
        # Try common license fields if present
        lic = MainBodySpider._clean_text(" ".join(container.css(".field--name-field-license ::text").getall()))
        return lic

    @staticmethod
    def _extract_coverage(container: Selector) -> str:
        for dl in container.css("dl.details"):
            dts = [MainBodySpider._clean_text(x) for x in dl.css("dt").getall()]
            dds = [MainBodySpider._clean_text(x) for x in dl.css("dd").getall()]
            mapping = dict(zip(dts, dds))
            cov = mapping.get("Coverage") or ""
            if cov:
                return cov
        # Alt field name
        cov = MainBodySpider._clean_text(" ".join(container.css(".field--name-field-publication-coverage ::text").getall()))
        return cov

    @staticmethod
    def _extract_sample_preview(container: Selector) -> str:
        # Prefer intro/description; else grab first paragraph-ish text from main content
        intro = container.css(".field--name-field-intro, .node-intro, .summary, .description").get()
        text = MainBodySpider._clean_text(intro) if intro else ""
        if not text:
            # fallback to first meaningful paragraph
            para_html = container.css("p").get()
            text = MainBodySpider._clean_text(para_html) if para_html else ""
        return text[:280]

    # --------------------
    # Parse
    # --------------------
    def parse(self, response: scrapy.http.Response):
        base = response.url
        container = self._sel(response)

        title = self._extract_title(container, response.selector)
        description = self._extract_description(container)
        owner = self._extract_owner(container)
        topic = self._extract_topic(container)
        year = self._extract_year(title, container)
        license_text = self._extract_license(container)
        coverage = self._extract_coverage(container)
        sample_preview = self._extract_sample_preview(container)

        # Data types from links within the main content area only
        data_types_set = self._collect_data_types_from_links(container, base)
        # If you want to strictly exclude HTML-only pages, filter here:
        # data_types_set = {e for e in data_types_set if e in KNOWN_EXTS}

        item = {
            "id": self._id_counter,
            "title": title or "",
            "description": description or "",
            "owner": owner or "",
            "topic": topic or "",
            "year": year or "",
            "license": license_text or "",
            "coverage": coverage or "",
            "sample_preview": sample_preview or "",
            "source_url": response.url,
            "data_types": ", ".join(sorted(data_types_set)) if data_types_set else "",
        }

        # Drop entries that have empty data_types (as requested)
        if not item["data_types"]:
            return

        # Increment only when yielding a kept item
        self._id_counter += 1
        yield item
