"""Publish the decision_made event of a persisted AI message (flag NEXTBH_PUBLISH_EVENTS)."""

import os
import sys

import feature_flags

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.append(REPO_ROOT)

from mlops.common.events import (  # noqa: E402
    OUTBOX_COLLECTION,
    EventPublisher,
    decision_made_event,
    kafka_producer,
)

_publisher = None


def _get_publisher() -> EventPublisher:
    global _publisher
    if _publisher is None:
        from pymongo import MongoClient

        from utils.mongodb_conn import MONGODB_URI

        db = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000).get_database()
        try:
            producer = kafka_producer(feature_flags.KAFKA_BOOTSTRAP_SERVERS)
        except Exception as e:
            print(f"[events] Kafka unavailable ({e}); events kept in the outbox")
            producer = None
        _publisher = EventPublisher(db[OUTBOX_COLLECTION], feature_flags.DECISION_EVENTS_TOPIC, producer)
    return _publisher


def publish_decision(decision, conversation_id, message_id, publisher=None) -> bool:
    """Never raises: a publishing problem must not break message generation."""
    if not feature_flags.PUBLISH_EVENTS or not decision or not message_id:
        return False
    try:
        publisher = publisher or _get_publisher()
        return publisher.publish(decision_made_event(decision, conversation_id, message_id))
    except Exception as e:
        print(f"[events] decision_made not published for {decision.get('decision_id')}: {e}")
        return False
