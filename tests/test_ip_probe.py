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

        def fake(url, params):
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

    def test_rejects_ranges(self):
        with self.assertRaises(ValueError):
            ip_probe.probe_ip("205.193.51.0/24", [], ranges.Labeller([]))


if __name__ == "__main__":
    unittest.main()
