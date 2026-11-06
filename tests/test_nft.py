import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "nft"))

import cards  # noqa: E402


def edit(revid, ip, title, ts, label="Shared Services Canada", comment="", ns=0, tags=None, sizediff=10):
    return {"wiki": "enwiki", "revid": revid, "parentid": revid - 1, "timestamp": ts, "title": title, "ns": ns,
            "comment": comment, "sizediff": sizediff, "ip": ip, "range": "x", "label": label,
            "label_source": "gccaedits", "url": f"https://en.wikipedia.org/w/index.php?diff={revid}",
            "tags": tags or []}


class CardTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        (root / "data" / "2025").mkdir(parents=True)
        rows = [
            edit(3, "205.193.239.44", "List of prime ministers of Canada", "2025-01-14T15:19:55Z",
                 comment="Removed vandalism", sizediff=-1028, tags=["mw-reverted"]),
            edit(1, "207.35.15.25", "2019 Canadian federal election", "2019-09-05T19:46:55Z",
                 label="Canadian House of Commons", comment="/* Electoral reform */ partisan", sizediff=-4882),
            edit(2, "207.35.15.27", "Don Davies", "2020-02-04T19:32:00Z", label="Canadian House of Commons",
                 comment="Undid revision 5 by [[Special:Contributions/1.2.3.4|1.2.3.4]]"),
            edit(4, "205.193.1.1", "User talk:Someone", "2025-02-01T10:00:00Z", ns=3),
            edit(5, "205.193.1.2", "Skipped page", "2025-02-02T10:00:00Z"),
        ]
        (root / "data" / "2025" / "edits.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
        (root / "data" / "topics.json").write_text(json.dumps(
            {"pages": {"enwiki|Don Davies": [{"topic": "Culture: Biography", "score": 0.9}]}, "labels": {}}))
        self.root = root
        self.nft = root / "nft"
        self.nft.mkdir()
        for f in ("config.json", "characters.json"):
            (self.nft / f).write_text((ROOT / "nft" / f).read_text())
        (self.nft / "skip.txt").write_text("# test\nenwiki|page:Skipped page\n")
        self.patch = mock.patch.object(cards, "NFT", self.nft)
        self.patch.start()

    def tearDown(self):
        self.patch.stop()
        self.tmp.cleanup()

    def run_build(self, ahead=100):
        return cards.build(root=self.root, out=self.root / "out", registry=self.nft / "registry.jsonl",
                           ahead=ahead)

    def test_guardrails_and_numbering(self):
        res = self.run_build()
        reg = cards.read_registry(self.nft / "registry.jsonl")
        keys = [r["key"] for r in reg]
        # oldest first; HoC biography, user-talk page and skip-listed page excluded
        self.assertEqual(keys, ["enwiki|1", "enwiki|3"])
        self.assertEqual([r["n"] for r in reg], [1, 2])
        self.assertEqual(res["written"], 2)
        meta = json.loads((self.root / "out" / "2.json").read_text())
        self.assertEqual(meta["name"], "GC Edit #00002")
        attrs = {a["trait_type"]: a["value"] for a in meta["attributes"]}
        self.assertEqual(attrs["Character"], "The Gunner")
        self.assertEqual(attrs["Rarity"], "Legendary")
        self.assertLessEqual(len(meta["name"].encode()), 32)

    def test_no_ip_anywhere(self):
        self.run_build()
        for p in (self.root / "out").iterdir():
            text = p.read_text()
            for ip in ("205.193.239.44", "207.35.15.25", "1.2.3.4"):
                self.assertNotIn(ip, text, p.name)

    def test_registry_is_stable_and_withdrawal_removes_files(self):
        self.run_build()
        self.run_build()
        self.assertEqual(len(cards.read_registry(self.nft / "registry.jsonl")), 2)
        (self.nft / "skip.txt").write_text("enwiki|3\n")
        res = self.run_build()
        self.assertEqual(res["withdrawn"], 1)
        self.assertFalse((self.root / "out" / "2.json").exists())
        self.assertTrue((self.root / "out" / "1.json").exists())

    def test_horizon_limits_files(self):
        res = self.run_build(ahead=1)
        self.assertEqual(res["written"], 1)
        self.assertFalse((self.root / "out" / "2.svg").exists())

    def test_clean_summary(self):
        self.assertEqual(cards.clean_summary("/* Federal politics */ "), "§ Federal politics")
        self.assertEqual(
            cards.clean_summary("Undid revision 9 by [[Special:Contributions/10.0.0.1|10.0.0.1]] ([[User talk:10.0.0.1|talk]])"),
            "Undid revision 9 by [address] (talk)")


if __name__ == "__main__":
    unittest.main()
