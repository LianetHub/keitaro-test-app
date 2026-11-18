import unittest

from app.services.campaign_edit import stream_update_body
from app.services.weights import ShareError, redistribute_shares


def _shares(items: list[dict]) -> list[int]:
    return [i["share"] for i in items]


class RedistributeSharesTest(unittest.TestCase):
    def test_unpinned_split_including_remainder(self):
        items = [
            {"share": 0, "is_pinned": False, "status": "active"},
            {"share": 0, "is_pinned": False, "status": "active"},
            {"share": 0, "is_pinned": False, "status": "active"},
        ]
        redistribute_shares(items)
        self.assertEqual(_shares(items), [34, 33, 33])
        self.assertEqual(sum(_shares(items)), 100)

    def test_pinned_keeps_share_and_free_split_rest(self):
        items = [
            {"share": 25, "is_pinned": True, "status": "active"},
            {"share": 0, "is_pinned": False, "status": "active"},
            {"share": 0, "is_pinned": False, "status": "active"},
        ]
        redistribute_shares(items)
        self.assertEqual(items[0]["share"], 25)
        self.assertEqual(_shares(items), [25, 38, 37])
        self.assertEqual(sum(_shares(items)), 100)

    def test_all_pinned_at_100_stays(self):
        items = [
            {"share": 40, "is_pinned": True, "status": "active"},
            {"share": 60, "is_pinned": True, "status": "active"},
        ]
        redistribute_shares(items)
        self.assertEqual(_shares(items), [40, 60])

    def test_single_unpinned_becomes_100(self):
        items = [{"share": 0, "is_pinned": False, "status": "active"}]
        redistribute_shares(items)
        self.assertEqual(_shares(items), [100])

    def test_removed_is_zero_and_excluded_from_split(self):
        items = [
            {"share": 50, "is_pinned": False, "status": "active"},
            {"share": 50, "is_pinned": False, "status": "removed"},
            {"share": 50, "is_pinned": False, "status": "active"},
        ]
        redistribute_shares(items)
        self.assertEqual(_shares(items), [50, 0, 50])

    def test_all_pinned_not_100_raises(self):
        items = [{"share": 40, "is_pinned": True, "status": "active"}]
        with self.assertRaises(ShareError):
            redistribute_shares(items)
        self.assertEqual(items[0]["share"], 40)

    def test_pinned_100_plus_free_offer_raises(self):
        items = [
            {"share": 100, "is_pinned": True, "status": "active"},
            {"share": 0, "is_pinned": False, "status": "active"},
        ]
        with self.assertRaises(ShareError):
            redistribute_shares(items)

    def test_pinned_over_100_raises_without_scaling(self):
        items = [
            {"share": 60, "is_pinned": True, "status": "active"},
            {"share": 50, "is_pinned": True, "status": "active"},
            {"share": 0, "is_pinned": False, "status": "active"},
        ]
        with self.assertRaises(ShareError):
            redistribute_shares(items)
        self.assertEqual(_shares(items), [60, 50, 0])

    def test_no_active_only_clears_removed(self):
        items = [{"share": 40, "is_pinned": True, "status": "removed"}]
        redistribute_shares(items)
        self.assertEqual(_shares(items), [0])


class StreamUpdateBodyTest(unittest.TestCase):
    def test_replaces_offers_and_keeps_filter_payload(self):
        remote = {
            "id": 9,
            "stream_id": 9,
            "created_at": "t",
            "updated_at": "t",
            "name": "Google",
            "schema": "redirect",
            "action_payload": "https://www.google.com",
            "filters": [
                {
                    "id": 1,
                    "oid": 2,
                    "stream_id": 9,
                    "name": "country",
                    "mode": "accept",
                    "payload": ["AU"],
                }
            ],
            "landings": [{"id": 3, "landing_id": 15, "share": 100, "state": "active"}],
            "offers": [{"id": 4, "offer_id": 7, "share": 100}],
            "triggers": [],
            "comments": "keep",
        }
        body = stream_update_body(
            remote,
            [{"offer_id": 8, "share": 100, "state": "active"}],
        )
        self.assertNotIn("id", body)
        self.assertEqual(body["name"], "Google")
        self.assertEqual(body["comments"], "keep")
        self.assertEqual(body["action_payload"], "https://www.google.com")
        self.assertEqual(
            body["filters"],
            [{"name": "country", "mode": "accept", "payload": ["AU"]}],
        )
        self.assertEqual(body["landings"], [{"landing_id": 15, "share": 100, "state": "active"}])
        self.assertEqual(body["offers"], [{"offer_id": 8, "share": 100, "state": "active"}])


if __name__ == "__main__":
    unittest.main()
