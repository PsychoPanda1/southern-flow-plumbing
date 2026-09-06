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
ENTRIES = ("index.html", "404.html", "robots.txt", "sitemap.xml", "CNAME", ".nojekyll")
ASSET_TYPES = {".html", ".css", ".js", ".png", ".jpg", ".jpeg", ".webp", ".svg", ".ico", ".woff", ".woff2"}


class Page(HTMLParser):
    def __init__(self, source):
        super().__init__(convert_charrefs=True)
        self.ids, self.refs, self.errors, self.meta = set(), [], [], {}
        self.canonical = None
        self.feed(source)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
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
    home = pages.get(site / "index.html")
    if home:
        if home.canonical != ORIGIN + "/":
            errors.append("Incorrect or missing homepage canonical URL")
        if "noindex" in home.meta.get("robots", "").lower():
            errors.append("Homepage must not be marked noindex")
        if not home.meta.get("description") or not home.meta.get("og:image"):
            errors.append("Homepage description or social-preview image is missing")
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
        if locations != [ORIGIN + "/"]:
            errors.append("Sitemap must identify the current single-page site only")
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
