"""Exercise the decision rules against a disposable local MongoDB instance."""

import argparse
import sys
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from threading import Barrier
from uuid import uuid4

from bson import ObjectId
from pymongo import MongoClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "agent"))
from utils.draft_review import record_draft_decision


class DraftDecisionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        client = MongoClient(
            "127.0.0.1", cls.port, directConnection=True,
            tz_aware=True, serverSelectionTimeoutMS=3000,
        )
        cls.addClassCleanup(client.close)
        client.admin.command("ping")
        database = client[f"bh_review_test_{uuid4().hex}"]
        cls.addClassCleanup(client.drop_database, database.name)
        cls.messages = database.messages

    def add_message(self, status):
        return self.messages.insert_one({
            "status": status,
            "sender": "ai",
            "subject": "Synthetic draft",
            "body": "Synthetic review test message.",
        }).inserted_id

    def test_approve_and_reject_preserve_first_decision(self):
        for decision, second_decision in (("validated", "rejected"), ("rejected", "validated")):
            with self.subTest(decision=decision):
                draft_id = self.add_message("pending")
                updated = record_draft_decision(self.messages, str(draft_id), decision, "synthetic-reviewer")
                self.assertEqual(updated["status"], decision)
                self.assertEqual(updated["reviewed_by"], "synthetic-reviewer")
                self.assertIsInstance(updated["reviewed_at"], datetime)
                self.assertEqual(updated["reviewed_at"].utcoffset(), timezone.utc.utcoffset(None))
                self.assertEqual(updated["subject"], "Synthetic draft")
                self.assertEqual(updated["body"], "Synthetic review test message.")

                for retry in (decision, second_decision):
                    self.assertIsNone(record_draft_decision(self.messages, draft_id, retry, "second-reviewer"))
                self.assertEqual(self.messages.find_one({"_id": draft_id}), updated)

    def test_missing_or_non_pending_draft_is_unchanged(self):
        missing_id = ObjectId()
        self.assertIsNone(record_draft_decision(self.messages, missing_id, "validated", "reviewer"))
        self.assertIsNone(self.messages.find_one({"_id": missing_id}))
        draft_id = self.add_message("validated")
        before = self.messages.find_one({"_id": draft_id})
        self.assertIsNone(record_draft_decision(self.messages, draft_id, "rejected", "reviewer"))
        self.assertEqual(self.messages.find_one({"_id": draft_id}), before)

    def test_invalid_decision_reviewer_and_draft_id(self):
        draft_id = self.add_message("pending")
        before = self.messages.find_one({"_id": draft_id})
        for arguments in (
            (draft_id, "pending", "reviewer"),
            (draft_id, "validated", " "),
            (draft_id, "validated", None),
            ("invalid-id", "validated", "reviewer"),
        ):
            with self.subTest(arguments=arguments), self.assertRaises(ValueError):
                record_draft_decision(self.messages, *arguments)
        self.assertEqual(self.messages.find_one({"_id": draft_id}), before)

    def test_competing_reviewers_have_one_winner(self):
        draft_id = self.add_message("pending")
        ready = Barrier(2, timeout=5)

        def decide(decision, reviewer):
            ready.wait()
            return record_draft_decision(self.messages, draft_id, decision, reviewer)

        with ThreadPoolExecutor(max_workers=2) as pool:
            approval = pool.submit(decide, "validated", "approving-reviewer")
            rejection = pool.submit(decide, "rejected", "rejecting-reviewer")
            results = [approval.result(), rejection.result()]

        self.assertEqual(results.count(None), 1)
        winner = results[0] or results[1]
        self.assertEqual(self.messages.find_one({"_id": draft_id}), winner)
        self.assertIn((winner["status"], winner["reviewed_by"]), {
            ("validated", "approving-reviewer"),
            ("rejected", "rejecting-reviewer"),
        })
        self.assertIsInstance(winner["reviewed_at"], datetime)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, required=True, help="Disposable MongoDB port on localhost")
    DraftDecisionTests.port = parser.parse_args().port
    unittest.main(argv=[sys.argv[0]], verbosity=2)
