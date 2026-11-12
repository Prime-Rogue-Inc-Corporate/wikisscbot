import importlib.util
import ipaddress
import unittest
from pathlib import Path
from unittest import mock

from wikisscbot import ranges

spec = importlib.util.spec_from_file_location(
    "ip_probe", Path(__file__).resolve().parent.parent / "tools" / "ip_probe.py")
ip_probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ip_probe)


class IpProbeTests(unittest.TestCase):
    def test_all_years_paginated_and_labelled_by_date(self):
        calls = []

        def fake(url, params, **kw):
            calls.append(dict(params))
            row = lambda rev, ts: {"revid": rev, "parentid": rev - 1, "timestamp": ts, "title": "Ottawa",
                                   "comment": "fix", "sizediff": 3}
            if "uccontinue" not in params:
                return {"query": {"usercontribs": [row(5, "2008-05-01T12:00:00Z")]},
                        "continue": {"uccontinue": "x", "continue": "-||"}}
            return {"query": {"usercontribs": [row(9, "2019-05-01T12:00:00Z")]}}

        lab = ranges.Labeller(ranges.load_confirmed() + [
            ranges.Range(ipaddress.ip_network("205.193.0.0/16"), "SSC bgp", "ssc-bgp")])
        with mock.patch.object(ip_probe, "get_json", side_effect=fake):
            r = ip_probe.probe_ip("205.193.51.200", [{"id": "enwiki", "host": "en.wikipedia.org"}], lab)
        self.assertEqual(r["total"], 2)
        self.assertNotIn("ucstart", calls[0])   # no date window: all years
        self.assertEqual(calls[0]["ucuser"], "205.193.51.200")
        self.assertEqual([e["label"] for e in r["edits"]],
                         ["SSC bgp", "Office of the Information Commissioner of Canada"])
        md = ip_probe.markdown([r], {}, [{"id": "enwiki", "host": "en.wikipedia.org"}], "now")
        self.assertIn("**2 edits**, 2008-05-01 to 2019-05-01", md)

    def test_sitematrix_and_niche_entries(self):
        matrix = {"sitematrix": {"count": 3, "0": {"code": "en", "site": [
            {"url": "https://en.wikipedia.org", "dbname": "enwiki"},
            {"url": "https://en.wikibooks.org", "dbname": "enwikibooks", "closed": True}]},
            "specials": [{"url": "https://office.wikimedia.org", "dbname": "officewiki", "private": True},
                         {"url": "https://species.wikimedia.org", "dbname": "specieswiki"}]}}
        with mock.patch.object(ip_probe, "get_json", return_value=matrix):
            wikis = ip_probe.all_wikimedia()
        self.assertEqual([w["id"] for w in wikis], ["enwiki", "enwikibooks", "specieswiki"])
        self.assertEqual(wikis[0]["api_url"], "https://en.wikipedia.org/w/api.php")
        fandom = ip_probe.norm({"id": "canada", "base": "https://canada.fandom.com", "genre": "canada"})
        self.assertEqual(fandom["api_url"], "https://canada.fandom.com/api.php")
        self.assertEqual(ip_probe.link(fandom, 9, 8), "https://canada.fandom.com/index.php?diff=9&oldid=8")

    def test_unreachable_wiki_does_not_stop_the_sweep(self):
        def fake(url, params, **kw):
            if "bad" in url:
                raise ip_probe.ApiError("HTTP 404")
            return {"query": {"usercontribs": []}}
        with mock.patch.object(ip_probe, "get_json", side_effect=fake):
            r = ip_probe.probe_ip("205.193.51.200", [{"id": "good", "host": "good.example"},
                                                      {"id": "bad", "host": "bad.example"}],
                                  ranges.Labeller([]), quick=True)
        self.assertEqual(r["wikis"], {"good": 0})
        self.assertIn("bad", r["errors"])

        # A wiki that fails in the fast sweep gets a second, slower attempt.
        seen = []
        def flaky(url, params, **kw):
            seen.append(kw)
            if len(seen) == 1:
                raise ip_probe.ApiError("HTTP 429")
            return {"query": {"usercontribs": []}}
        with mock.patch.object(ip_probe, "get_json", side_effect=flaky), mock.patch.object(ip_probe.time, "sleep"):
            r2 = ip_probe.probe_ip("205.193.51.200", [{"id": "slow", "host": "slow.example"}],
                                   ranges.Labeller([]), quick=True)
        self.assertEqual((r2["wikis"], r2["errors"]), ({"slow": 0}, {}))
        self.assertEqual(seen[1], {})
        self.assertIn("1 wikis could not be checked: bad.", ip_probe.markdown([r], {}, [{"id": "good", "host": "good.example"}, {"id": "bad", "host": "bad.example"}], "now"))

    def test_rejects_ranges(self):
        with self.assertRaises(ValueError):
            ip_probe.probe_ip("205.193.51.0/24", [], ranges.Labeller([]))


if __name__ == "__main__":
    unittest.main()
