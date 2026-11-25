import copy

from mlops.common.events import EventPublisher, decision_made_event
from mlops.feedback.verdict_relay import relay_verdicts, verdict_of
from mlops.rl.export_events import dedupe, join_decisions


def _match(doc, query):
    for key, cond in query.items():
        value = doc
        for part in key.split("."):
            value = value.get(part) if isinstance(value, dict) else None
        if isinstance(cond, dict):
            if "$exists" in cond and (value is not None) != cond["$exists"]:
                return False
            if "$in" in cond and value not in cond["$in"]:
                return False
        elif value != cond:
            return False
    return True


class Cursor(list):
    def limit(self, n):
        return Cursor(self[:n])


class FakeCollection:
    """The subset of pymongo used by the outbox and the relay."""

    def __init__(self, docs=()):
        self.docs = {d["_id"]: copy.deepcopy(d) for d in docs}

    def find(self, query):
        return Cursor(copy.deepcopy(d) for d in self.docs.values() if _match(d, query))

    def update_one(self, query, update, upsert=False):
        target = next((d for d in self.docs.values() if _match(d, query)), None)
        if target is None:
            if not upsert:
                return
            target = {"_id": query["_id"]}
            self.docs[target["_id"]] = target
            target.update(update.get("$setOnInsert", {}))
        target.update(update.get("$set", {}))
        for k, v in update.get("$inc", {}).items():
            target[k] = target.get(k, 0) + v


class FakeProducer:
    def __init__(self, fail=False):
        self.sent, self.fail = [], fail

    def send(self, topic, key, value):
        producer = self

        class Future:
            def get(self, timeout):
                if producer.fail:
                    raise TimeoutError("broker down")
                producer.sent.append((topic, key, value))
        return Future()


DECISION = {"decision_id": "d-1", "action": "recommend_product", "model_version": "rl-1",
            "allowed_actions": ["wait", "recommend_product"], "fallback": False, "trace_id": "t-1"}


def test_outbox_keeps_event_until_kafka_acknowledges():
    outbox = FakeCollection()
    down = EventPublisher(outbox, "decision_events", FakeProducer(fail=True))
    event = decision_made_event(DECISION, "conv-1", "msg-1")
    assert down.publish(event) is False
    assert outbox.docs[event.event_id]["status"] == "pending"

    producer = FakeProducer()
    up = EventPublisher(outbox, "decision_events", producer)
    assert up.relay_outbox() == 1
    assert outbox.docs[event.event_id]["status"] == "sent"
    assert producer.sent[0][1] == "d-1"
    # publishing the same fact again yields the same event_id: no duplicate row
    up.publish(decision_made_event(DECISION, "conv-1", "msg-1"))
    assert len(outbox.docs) == 1


def test_verdict_mapping():
    assert verdict_of({"status": "validated"}) == "approved"
    assert verdict_of({"status": "validated", "is_modified": True}) == "edited"
    assert verdict_of({"status": "rejected"}) == "rejected"
    assert verdict_of({"status": "pending"}) is None


def test_relay_publishes_each_verdict_once():
    messages = FakeCollection([
        {"_id": "m1", "status": "validated", "is_modified": True, "conversation_id": "c1",
         "decision": DECISION},
        {"_id": "m2", "status": "pending", "decision": {**DECISION, "decision_id": "d-2"}},
        {"_id": "m3", "status": "rejected"},  # legacy message without decision: ignored
    ])
    producer = FakeProducer()
    publisher = EventPublisher(FakeCollection(), "decision_events", producer)

    assert relay_verdicts(messages, publisher) == 1
    assert relay_verdicts(messages, publisher) == 0
    event = producer.sent[0][2]
    assert event["event_type"] == "admin_verdict" and event["admin_verdict"] == "edited"
    assert event["customer_outcome"] is None and event["reward_status"] == "provisional"
    assert messages.docs["m1"]["verdict_event_id"] == event["event_id"]

    rows = join_decisions(dedupe([decision_made_event(DECISION, "c1", "m1").model_dump(), event]))
    assert rows[0]["action"] == "recommend_product" and rows[0]["admin_verdict"] == "edited"


def test_relay_uses_review_timestamp_from_draft_review():
    from datetime import datetime, timezone

    reviewed = datetime(2026, 11, 20, 9, 30, tzinfo=timezone.utc)
    # shape written by agent/utils/draft_review.record_draft_decision and the review pilot
    messages = FakeCollection([{
        "_id": "m1", "status": "validated", "reviewed_by": "reviewer-1", "reviewed_at": reviewed,
        "updated_at": datetime(2026, 11, 21, tzinfo=timezone.utc), "decision": DECISION,
    }])
    producer = FakeProducer()
    relay_verdicts(messages, EventPublisher(FakeCollection(), "decision_events", producer))
    event = producer.sent[0][2]
    assert event["admin_verdict"] == "approved"
    assert event["timestamp"] == reviewed.isoformat()
    assert "reviewer-1" not in str(event)  # reviewer identity stays out of the event stream


def test_relay_marks_naive_mongo_dates_as_utc():
    from datetime import datetime

    # pymongo returns naive datetimes (UTC) unless tz_aware=True
    messages = FakeCollection([{"_id": "m1", "status": "rejected", "decision": DECISION,
                                "reviewed_at": datetime(2026, 11, 25, 1, 0)}])
    producer = FakeProducer()
    relay_verdicts(messages, EventPublisher(FakeCollection(), "decision_events", producer))
    assert producer.sent[0][2]["timestamp"] == "2026-11-25T01:00:00+00:00"
