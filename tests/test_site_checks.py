"""Regression checks for mistakes that must prevent production deployment."""
import shutil
import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from check_site import inspect_site, Page


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


if __name__ == "__main__":
    unittest.main()
