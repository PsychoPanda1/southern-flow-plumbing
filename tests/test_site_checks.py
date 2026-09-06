"""Regression checks for mistakes that must prevent production deployment."""
import shutil
import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from check_site import inspect_site, Page, INDEXABLE_ROUTES, ORIGIN


class DeploymentChecks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.site = Path(self.temp.name) / "site"
        files, errors = inspect_site(ROOT / "site")
        self.assertEqual(errors, [])
        for file in files:
            dest = self.site / file.relative_to(ROOT / "site")
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(file, dest)

    def replace_home(self, before, after):
        home = self.site / "index.html"
        source = home.read_text(encoding="utf-8")
        self.assertIn(before, source)
        home.write_text(source.replace(before, after, 1), encoding="utf-8")

    def test_missing_responsive_image_is_rejected(self):
        self.replace_home("public/bathroom-finish-640.webp 640w", "public/missing-image.webp 640w")
        _, errors = inspect_site(self.site)
        self.assertTrue(any("missing-image.webp" in error for error in errors))

    def test_broken_section_and_wrong_phone_are_rejected(self):
        self.replace_home('href="#services"', 'href="#missing-section"')
        self.replace_home('href="tel:+18437938806"', 'href="tel:+15555555555"')
        _, errors = inspect_site(self.site)
        self.assertTrue(any("Broken section" in error for error in errors))
        self.assertTrue(any("Unexpected phone" in error for error in errors))

    def test_invalid_structured_data_is_rejected(self):
        self.replace_home('"@type": "Plumber",', '"@type": "Plumber" BROKEN,')
        _, errors = inspect_site(self.site)
        self.assertTrue(any("Invalid business structured data" in error for error in errors))

    def test_private_files_are_not_collected(self):
        private = self.site / "app" / "private-notes.txt"
        private.parent.mkdir()
        private.write_text("private")
        files, errors = inspect_site(self.site)
        self.assertEqual(errors, [])
        self.assertNotIn(private, files)

    def test_crawl_block_and_path_escape_are_rejected(self):
        (self.site / "robots.txt").write_text("User-agent: *\nDisallow: /\n")
        self.replace_home('href="styles.css"', 'href="../private.txt"')
        _, errors = inspect_site(self.site)
        self.assertTrue(any("Robots file" in error for error in errors))
        self.assertTrue(any("leaves public site" in error for error in errors))

    def test_nested_error_page_links_resolve_from_root(self):
        refs = Page((self.site / "404.html").read_text(encoding="utf-8")).refs
        self.assertTrue(all(ref.startswith(("/", "#", "tel:", "https:")) for ref in refs))

    def replace_service(self, before, after):
        file = self.site / "services/water-heaters/index.html"
        source = file.read_text(encoding="utf-8")
        self.assertIn(before, source)
        file.write_text(source.replace(before, after, 1), encoding="utf-8")

    def test_all_declared_pages_are_packaged(self):
        files, errors = inspect_site(self.site)
        self.assertEqual(errors, [])
        for relative in INDEXABLE_ROUTES.values():
            self.assertIn(self.site / relative, files)

    def test_missing_service_page_is_rejected(self):
        (self.site / "services/water-heaters/index.html").unlink()
        _, errors = inspect_site(self.site)
        self.assertTrue(any("Missing file: services" in error for error in errors))

    def test_service_canonical_and_social_url_must_match_route(self):
        self.replace_service('rel="canonical" href="' + ORIGIN + '/services/water-heaters/"',
                             'rel="canonical" href="' + ORIGIN + '/"')
        self.replace_service('property="og:url" content="' + ORIGIN + '/services/water-heaters/"',
                             'property="og:url" content="' + ORIGIN + '/"')
        _, errors = inspect_site(self.site)
        self.assertTrue(any("canonical URL: /services/water-heaters/" in e for e in errors))
        self.assertTrue(any("social metadata: /services/water-heaters/" in e for e in errors))

    def test_service_title_and_description_must_be_unique(self):
        home = Page((self.site / "index.html").read_text(encoding="utf-8"))
        self.replace_service("Water Heater Replacement | Southern Flow Plumbing | Charleston", home.title)
        service = Page((self.site / "services/water-heaters/index.html").read_text(encoding="utf-8"))
        self.replace_service(service.meta["description"], home.meta["description"])
        _, errors = inspect_site(self.site)
        self.assertTrue(any("duplicate page title" in e for e in errors))
        self.assertTrue(any("duplicate page description" in e for e in errors))

    def test_sitemap_rejects_missing_duplicate_and_unexpected_routes(self):
        file = self.site / "sitemap.xml"
        original = file.read_text(encoding="utf-8")
        location = f"<loc>{ORIGIN}/services/water-heaters/</loc>"
        for replacement in ("", location + location, f"<loc>{ORIGIN}/404.html</loc>"):
            with self.subTest(replacement=replacement):
                file.write_text(original.replace(location, replacement), encoding="utf-8")
                _, errors = inspect_site(self.site)
                self.assertTrue(any("Sitemap must match" in e for e in errors))

    def test_metadata_cannot_hide_orphaned_service_pages(self):
        self.replace_home('href="/services/water-heaters/"', 'href="#services"')
        self.replace_home('href="/services/renovations/"', 'href="#services"')
        _, errors = inspect_site(self.site)
        self.assertEqual(sum("not reachable" in e for e in errors), 2)

    def test_nested_assets_and_fragments_are_checked(self):
        self.replace_service('href="/styles.css"', 'href="../../styles.css"')
        self.replace_service('href="/#work"', 'href="/#missing-work"')
        _, errors = inspect_site(self.site)
        self.assertTrue(any("Nested page assets" in e for e in errors))
        self.assertTrue(any("Broken section" in e for e in errors))

    def test_page_needs_one_h1_and_must_be_indexable(self):
        self.replace_service('<h1 id="service-title">', '<h2 id="service-title">')
        self.replace_service('</head>', '<meta name="robots" content="noindex" /></head>')
        _, errors = inspect_site(self.site)
        self.assertTrue(any("exactly one h1" in e for e in errors))
        self.assertTrue(any("must not be marked noindex" in e for e in errors))


if __name__ == "__main__":
    unittest.main()
