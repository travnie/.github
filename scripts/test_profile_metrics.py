"""Offline smoke checks for profile metrics."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import update_profile_metrics as metrics


class ProfileMetricsTests(unittest.TestCase):
    def test_upkeep_sources(self):
        workflow = (
            "          README_FEED_URLS: >-\n"
            "            ${{ vars.README_FEED_URLS || 'https://example.com/a.xml' }},\n"
            "            https://example.com/b.xml,\n"
            "          README_FEED_MAX_ENTRIES: 6\n"
        )
        self.assertEqual(metrics.upkeep_sources(workflow), [
            "https://example.com/a.xml", "https://example.com/b.xml"
        ])

    def test_atom(self):
        xml = (
            '<feed xmlns="http://www.w3.org/2005/Atom"><title>Test</title>'
            '<entry><title>Hello</title><published>2026-11-06T12:00:00Z</published>'
            '<link href="https://example.com/post" rel="alternate"/></entry></feed>'
        )
        items = metrics.entries(xml.encode(), "https://example.com/atom")
        self.assertEqual(items[0][1:], ("[Test] Hello", "https://example.com/post"))

    def test_rss(self):
        xml = (
            '<rss version="2.0"><channel><title>News</title>'
            '<item><title>Item</title><link>https://example.com/item</link>'
            '<pubDate>Fri, 06 Nov 2026 12:00:00 +0000</pubDate></item>'
            '</channel></rss>'
        )
        self.assertEqual(metrics.entries(xml.encode(), "https://example.com/rss")[0][1], "[News] Item")


    def test_newest_item_selected(self):
        xml = (
            '<rss><channel><title>Sorted</title>'
            + "".join(f'<item><title>{i}</title><link>https://example.com/{i}</link><pubDate>Fri, 06 Nov 2026 0{i}:00:00 +0000</pubDate></item>' for i in range(1, 5))
            + '</channel></rss>'
        )
        names = [entry[1] for entry in metrics.entries(xml.encode(), "https://example.com")]
        self.assertEqual(names, ["[Sorted] 4", "[Sorted] 3", "[Sorted] 2"])

    def test_rdf(self):
        xml = (
            '<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">'
            '<channel><title>RDF News</title></channel>'
            '<item><title>Entry</title><link>https://example.com/rdf</link></item>'
            '</rdf:RDF>'
        )
        self.assertEqual(len(metrics.entries(xml.encode(), "https://example.com/rdf")), 1)

    def test_reject_entities(self):
        xml = b'<!DOCTYPE rss [<!ENTITY bomb "AAAAAAAA">]><rss><channel><title>&bomb;</title></channel></rss>'
        with self.assertRaises(metrics.DefusedXmlException):
            metrics.entries(xml, "https://example.com/rss")

    def test_endpoint_schema(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(metrics, "OUT", Path(tmp)):
            metrics.badge("pr.json", "merged PRs", "3,399", "8250df", "pr")
            badge = json.loads(Path(tmp, "pr.json").read_text(encoding="utf-8"))
            self.assertEqual(badge["schemaVersion"], 1)
            self.assertEqual(badge["message"], "3,399")
            self.assertIn("<svg", badge["logoSvg"])


if __name__ == "__main__":
    unittest.main()
