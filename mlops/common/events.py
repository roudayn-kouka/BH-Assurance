"""
Idempotent publication of decision_events, with a MongoDB outbox.

Every event is first upserted into the `event_outbox` collection (keyed by event_id) and
only then sent to Kafka; anything not acknowledged stays `pending` and is re-sent by
`relay_outbox()`. Event ids are derived from business keys, so publishing the same fact
twice produces the same event_id and consumers deduplicate it (export_events.dedupe).
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from .schemas import DecisionEvent

EVENT_NAMESPACE = uuid.UUID("6f1c2a8e-4d0b-4c7a-9f5e-2b1d3c4e5f60")
OUTBOX_COLLECTION = "event_outbox"


def event_id_for(event_type: str, *keys: Any) -> str:
    return str(uuid.uuid5(EVENT_NAMESPACE, ":".join([event_type, *map(str, keys)])))


def decision_made_event(decision: Dict, conversation_id: Optional[str],
                        message_id: Optional[str]) -> DecisionEvent:
    return DecisionEvent(
        event_id=event_id_for("decision_made", decision["decision_id"]),
        event_type="decision_made",
        decision_id=decision["decision_id"],
        conversation_id=str(conversation_id) if conversation_id else None,
        message_id=str(message_id) if message_id else None,
        model_version=decision.get("model_version"),
        state_version=decision.get("state_version", "v1"),
        action=decision.get("action"),
        allowed_actions=decision.get("allowed_actions") or [],
        fallback=decision.get("fallback"),
        reason_code=decision.get("fallback_reason"),
        trace_id=decision.get("trace_id"),
    )


def admin_verdict_event(decision: Dict, message_id: str, conversation_id: Optional[str],
                        verdict: str, reason_code: Optional[str] = None,
                        occurred_at: Optional[str] = None) -> DecisionEvent:
    return DecisionEvent(
        event_id=event_id_for("admin_verdict", decision["decision_id"], message_id, verdict),
        event_type="admin_verdict",
        decision_id=decision["decision_id"],
        conversation_id=str(conversation_id) if conversation_id else None,
        message_id=str(message_id),
        model_version=decision.get("model_version"),
        action=decision.get("action"),
        admin_verdict=verdict,
        reason_code=reason_code,
        # the verdict qualifies admissibility only; the business outcome is a separate event
        reward_status="provisional",
        trace_id=decision.get("trace_id"),
        **({"timestamp": occurred_at} if occurred_at else {}),
    )


def kafka_producer(bootstrap: str):
    from kafka import KafkaProducer
    from kafka.serializer import Serializer

    class Utf8(Serializer):
        def serialize(self, topic, *args):  # (value) or (headers, value) by version
            value = args[-1]
            return value.encode("utf-8")

    class Json(Serializer):
        def serialize(self, topic, *args):  # (value) or (headers, value) by version
            value = args[-1]
            return json.dumps(value, ensure_ascii=False).encode("utf-8")

    return KafkaProducer(
        bootstrap_servers=bootstrap, acks="all", retries=3,
        key_serializer=Utf8(), value_serializer=Json(),
    )


class EventPublisher:
    def __init__(self, outbox, topic: str, producer=None, send_timeout_s: float = 5.0):
        """`outbox` is a pymongo collection; `producer` a KafkaProducer (None = outbox only)."""
        self.outbox = outbox
        self.topic = topic
        self.producer = producer
        self.timeout = send_timeout_s

    def publish(self, event: DecisionEvent) -> bool:
        payload = event.model_dump()
        self.outbox.update_one(
            {"_id": event.event_id},
            {"$setOnInsert": {"payload": payload, "status": "pending", "attempts": 0,
                              "created_at": datetime.now(timezone.utc)}},
            upsert=True,
        )
        return self._send(event.event_id, payload)

    def _send(self, event_id: str, payload: Dict) -> bool:
        if self.producer is None:
            return False
        try:
            # key = decision_id keeps all events of a decision in one partition, in order
            self.producer.send(self.topic, key=payload["decision_id"], value=payload).get(
                timeout=self.timeout)
        except Exception as e:
            self.outbox.update_one({"_id": event_id},
                                   {"$inc": {"attempts": 1}, "$set": {"last_error": str(e)}})
            return False
        self.outbox.update_one({"_id": event_id},
                               {"$set": {"status": "sent", "sent_at": datetime.now(timezone.utc)}})
        return True

    def relay_outbox(self, limit: int = 500) -> int:
        sent = 0
        for doc in self.outbox.find({"status": "pending"}).limit(limit):
            sent += self._send(doc["_id"], doc["payload"])
        return sent
