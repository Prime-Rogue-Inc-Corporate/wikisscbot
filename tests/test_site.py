import json
import tempfile
import unittest
from pathlib import Path

from wikisscbot import site


class SiteTests(unittest.TestCase):
    def test_build_static_site(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            res = site.build(out)
            index = (out / "index.html").read_text()
            self.assertIn("window.WIKISSC_STATIC = true", index)
            self.assertIn('src="static/engine.js"', index)
            for f in ("static/app.js", "static/engine.js", "static/style.css", ".nojekyll", "404.html"):
                self.assertTrue((out / f).exists(), f)
            derived = json.loads((out / "derived.json").read_text())
            self.assertEqual(len(derived["files"]), res["files"])
            for f in derived["files"]:
                # Copied byte-for-byte so browser hashes match SHA256SUMS.
                self.assertEqual((out / f).read_bytes(), (site.ROOT / f).read_bytes())

    def test_crawlable_pages_and_discovery_files(self):
        import re
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            site.build(out)
            base = json.loads((site.ROOT / "config" / "site.json").read_text())["base_url"]
            index = (out / "index.html").read_text()
            self.assertIn(f'<link rel="canonical" href="{base}">', index)
            self.assertIn('class="prerender"', index)
            self.assertNotIn("<!--SEO-->", index)
            self.assertIn("noindex", (out / "404.html").read_text())
            self.assertEqual((out / "CNAME").read_text().strip(), base.split("//")[1].strip("/"))
            self.assertIn(f"Sitemap: {base}sitemap.xml", (out / "robots.txt").read_text())
            sitemap = (out / "sitemap.xml").read_text()
            years = sorted(p.parent.name for p in (site.ROOT / "data").glob("[0-9][0-9][0-9][0-9]/summary.json"))
            for rel in ["years.html", "faq.html", "methodology.html", "data.html", "coverage.html", "clusters.html", "llms.txt",
                        "static/og.png", "static/favicon.svg"] + [f"years/{y}.html" for y in years]:
                self.assertTrue((out / rel).exists(), rel)
                if rel.endswith(".html"):
                    self.assertIn(f"<loc>{base}{rel}</loc>", sitemap)
                    page = (out / rel).read_text()
                    self.assertIn(f'<link rel="canonical" href="{base}{rel}">', page)
                    # Every JSON-LD block must parse.
                    for block in re.findall(r'<script type="application/ld\+json">(.*?)</script>', page, re.S):
                        json.loads(block)
            for block in re.findall(r'<script type="application/ld\+json">(.*?)</script>', index, re.S):
                self.assertIn(json.loads(block)["@type"], ("WebSite", "Dataset"))


if __name__ == "__main__":
    unittest.main()
