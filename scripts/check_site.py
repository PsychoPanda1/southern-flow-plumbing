"""Validate and optionally package the static site using only Python's standard library."""
import argparse
import json
import re
import shutil
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit
import xml.etree.ElementTree as ET

ORIGIN = "https://southernflowplumbingllc.com"
PHONE = "tel:+18437938806"
INDEXABLE_ROUTES = {
    "/": "index.html",
    "/services/water-heaters/": "services/water-heaters/index.html",
    "/services/renovations/": "services/renovations/index.html",
}
ENTRIES = (*INDEXABLE_ROUTES.values(), "404.html", "robots.txt", "sitemap.xml", "CNAME", ".nojekyll")
ASSET_TYPES = {".html", ".css", ".js", ".png", ".jpg", ".jpeg", ".webp", ".svg", ".ico", ".woff", ".woff2"}


class Page(HTMLParser):
    def __init__(self, source):
        super().__init__(convert_charrefs=True)
        self.ids, self.refs, self.errors, self.meta = set(), [], [], {}
        self.canonical = None
        self.title_parts, self.links, self.assets = [], [], []
        self.in_title, self.h1_count = False, 0
        self.feed(source)

    @property
    def title(self):
        return "".join(self.title_parts).strip()

    def handle_data(self, data):
        if self.in_title:
            self.title_parts.append(data)

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "title":
            self.in_title = True
        if tag == "h1":
            self.h1_count += 1
        if tag == "a" and attrs.get("href"):
            self.links.append(attrs["href"])
        if tag in {"img", "script", "source"} and attrs.get("src"):
            self.assets.append(attrs["src"])
        if tag == "link" and attrs.get("rel") == "stylesheet":
            self.assets.append(attrs.get("href", ""))
        if attrs.get("id"):
            if attrs["id"] in self.ids:
                self.errors.append(f"Duplicate id: {attrs['id']}")
            self.ids.add(attrs["id"])
        if tag == "img" and "alt" not in attrs:
            self.errors.append(f"Missing image alternative text: {attrs.get('src')}")
        for key in ("src", "href"):
            if attrs.get(key):
                self.refs.append(attrs[key])
        if attrs.get("srcset"):
            self.refs.extend(item.strip().split()[0] for item in attrs["srcset"].split(",") if item.strip())
        if tag == "link" and attrs.get("rel") == "canonical":
            self.canonical = attrs.get("href")
        if tag == "meta":
            name = attrs.get("name", attrs.get("property"))
            self.meta[name] = attrs.get("content", "")
            if name in {"og:image", "og:image:secure_url", "twitter:image"}:
                self.refs.append(attrs.get("content", ""))
        if tag == "a" and attrs.get("target") == "_blank" and "noopener" not in attrs.get("rel", "").split():
            self.errors.append("External new-tab link missing noopener")
        if attrs.get("href", "").startswith("tel:") and attrs["href"] != PHONE:
            self.errors.append(f"Unexpected phone destination: {attrs['href']}")
        if attrs.get("data-mobile-call") and attrs["data-mobile-call"] != PHONE:
            self.errors.append("Mobile call destination does not match the business number")


def inspect_site(site):
    site = site.resolve()
    files, errors, pages = set(), [], {}

    def local_file(ref, parent):
        parts = urlsplit(ref)
        if parts.scheme or parts.netloc:
            if parts.netloc != urlsplit(ORIGIN).netloc:
                return None
            if parts.scheme != "https":
                errors.append(f"Non-HTTPS site URL: {ref}")
        if not parts.path:
            return parent
        path = unquote(parts.path)
        target = (site / path.lstrip("/") if path.startswith("/") else parent.parent / path).resolve()
        if target.is_dir() or path.endswith("/"):
            target /= "index.html"
        if not target.is_relative_to(site):
            errors.append(f"Reference leaves public site: {ref}")
            return None
        if target.suffix not in ASSET_TYPES:
            errors.append(f"Unexpected public file type: {ref}")
            return None
        return target

    def visit(file):
        if file in files:
            return
        if not file.is_file():
            errors.append(f"Missing file: {file.relative_to(site)}")
            return
        files.add(file)
        if file.suffix not in {".html", ".css"}:
            return
        source = file.read_text(encoding="utf-8")
        if file.suffix == ".css":
            refs = re.findall(r'url\([\s\"\x27]*([^\)\"\x27\s]+)', source)
        else:
            page = pages[file] = Page(source)
            errors.extend(f"{file.name}: {e}" for e in page.errors)
            refs = list(page.refs)
            for block in re.findall(r'<script\b[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', source, re.S):
                try:
                    data = json.loads(block)
                    if data.get("@type") == "Plumber":
                        if data.get("url") != ORIGIN + "/" or data.get("telephone") != "+1-843-793-8806":
                            errors.append("Business structured data has a mismatched URL or phone")
                        refs.extend(data[key] for key in ("logo", "image") if key in data)
                except (ValueError, TypeError, AttributeError) as exc:
                    errors.append(f"Invalid business structured data: {exc}")
        for ref in refs:
            target = local_file(ref, file)
            if target:
                visit(target)
                fragment = unquote(urlsplit(ref).fragment)
                if fragment and target.suffix == ".html" and target in pages and fragment not in pages[target].ids:
                    errors.append(f"Broken section link in {file.name}: {ref}")

    for entry in ENTRIES:
        visit(site / entry)
    titles, descriptions = set(), set()
    for route, relative in INDEXABLE_ROUTES.items():
        page = pages.get(site / relative)
        if not page:
            continue  # Missing file already reported during traversal.
        if page.canonical != ORIGIN + route:
            errors.append(f"Incorrect or missing canonical URL: {route}")
        if "noindex" in page.meta.get("robots", "").lower():
            errors.append(f"Indexable page must not be marked noindex: {route}")
        if not page.title or page.title in titles:
            errors.append(f"Missing or duplicate page title: {route}")
        titles.add(page.title)
        description = page.meta.get("description")
        if not description or description in descriptions:
            errors.append(f"Missing or duplicate page description: {route}")
        descriptions.add(description)
        if page.h1_count != 1:
            errors.append(f"Page must have exactly one h1: {route}")
        if page.meta.get("og:url") != ORIGIN + route or not page.meta.get("og:image"):
            errors.append(f"Missing or mismatched social metadata: {route}")
        if route != "/" and any(not ref.startswith(("/", "https:", "data:")) for ref in page.assets):
            errors.append(f"Nested page assets must use root-relative or HTTPS URLs: {route}")

    # Reachability uses actual navigation links, never canonical/social metadata.
    reachable, pending = set(), [site / "index.html"]
    while pending:
        current = pending.pop()
        if current in reachable or current not in pages:
            continue
        reachable.add(current)
        for ref in pages[current].links:
            target = local_file(ref, current)
            if target in pages and target not in reachable:
                pending.append(target)
    for route, relative in INDEXABLE_ROUTES.items():
        if site / relative not in reachable:
            errors.append(f"Indexable page is not reachable from homepage links: {route}")
    declared_html = {site / file for file in INDEXABLE_ROUTES.values()} | {site / "404.html"}
    for file in pages.keys() - declared_html:
        errors.append(f"Undeclared public HTML page: {file.relative_to(site)}")
    error_page = pages.get(site / "404.html")
    if error_page and "noindex" not in error_page.meta.get("robots", ""):
        errors.append("Error page must be marked noindex")
    try:
        if (site / "CNAME").read_text().strip() != urlsplit(ORIGIN).netloc:
            errors.append("Custom domain does not match the canonical domain")
        robots = (site / "robots.txt").read_text()
        if f"Sitemap: {ORIGIN}/sitemap.xml" not in robots or re.search(r"^Disallow:\s*/\s*$", robots, re.M):
            errors.append("Robots file must permit crawling and identify the sitemap")
        sitemap = ET.parse(site / "sitemap.xml")
        locations = [e.text for e in sitemap.findall(".//{*}loc")]
        expected = {ORIGIN + route for route in INDEXABLE_ROUTES}
        if len(locations) != len(set(locations)) or set(locations) != expected:
            errors.append("Sitemap must match declared indexable routes without duplicates")
    except (OSError, ET.ParseError) as exc:
        errors.append(f"Search metadata unreadable: {exc}")
    return files, errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", type=Path, default=Path(__file__).resolve().parents[1] / "site")
    parser.add_argument("--output", type=Path, help="Optional empty directory for the validated public artifact")
    args = parser.parse_args()
    site = args.site.resolve()
    files, errors = inspect_site(site)
    if errors:
        print("Site check failed:\n" + "\n".join(f"- {e}" for e in errors), file=sys.stderr)
        return 1
    if args.output:
        output = args.output.resolve()
        if output == site or output.is_relative_to(site) or site.is_relative_to(output):
            parser.error("Output must be separate from the site directory")
        if output.exists() and any(output.iterdir()):
            parser.error("Output directory must be empty; choose a new directory")
        for file in sorted(files):
            destination = output / file.relative_to(site)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(file, destination)
    print(f"PASS: {len(files)} public files; links, image variants, phone links and search metadata checked.")
    if args.output:
        print(f"Public artifact: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
