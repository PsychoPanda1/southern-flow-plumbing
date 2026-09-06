"""Source-level contrast and accessibility checks; not a browser accessibility audit."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
CSS = (ROOT / "site/styles.css").read_text(encoding="utf-8")
HTML = (ROOT / "site/index.html").read_text(encoding="utf-8")


def luminance(color):
    rgb = [int(color[index:index + 2], 16) / 255 for index in (1, 3, 5)]
    linear = [v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in rgb]
    return sum(value * weight for value, weight in zip(linear, (0.2126, 0.7152, 0.0722)))


def contrast(first, second):
    values = sorted((luminance(first), luminance(second)))
    return (values[1] + 0.05) / (values[0] + 0.05)


class AccessibilityChecks(unittest.TestCase):
    def test_solid_brand_text_colors_meet_normal_text_contrast(self):
        colors = dict(re.findall(r"--([\w-]+):\s*(#[0-9a-f]{6});", CSS))
        for foreground, background in (
            ("navy", "brass"), ("navy", "brass-hover"),
            ("brass-text", "paper"), ("brass-text", "cream"),
            ("muted", "paper"), ("muted", "cream"),
        ):
            with self.subTest(foreground=foreground, background=background):
                self.assertGreaterEqual(contrast(colors[foreground], colors[background]), 4.5)
        for selector in (".button", ".mobile-call-bar"):
            blocks = re.findall(re.escape(selector) + r"\s*\{([^}]+)\}", CSS)
            self.assertTrue(any("color: var(--navy);" in block for block in blocks))

    def test_skip_target_motion_and_focus_hooks_remain(self):
        self.assertIn('<main id="main" tabindex="-1">', HTML)
        self.assertIn('aria-controls="site-nav"', HTML)
        self.assertIn('role="status" aria-live="polite"', HTML)
        self.assertIn("prefers-reduced-motion: reduce", CSS)
        self.assertIn("a:focus-visible, button:focus-visible", CSS)
        self.assertIn("@media (forced-colors: active)", CSS)

    def test_feedback_is_not_presented_as_verified_customer_reviews(self):
        self.assertIn("Community feedback", HTML)
        self.assertNotIn("Customer reviews", HTML)
        self.assertNotIn("View original comment", HTML)
        self.assertNotIn('"aggregateRating"', HTML)


if __name__ == "__main__":
    unittest.main()
