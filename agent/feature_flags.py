"""
Feature flags for the Next-BH 2.0 migration.

Every new behaviour is off by default so the legacy flow (SalesAgent.respond /
agent_initiate) keeps working unchanged until a flag is explicitly enabled.
"""

import os


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


# Route SalesAgent.respond() through AgentOrchestrator (graph) instead of the legacy sequence
USE_ORCHESTRATOR = _env_bool("NEXTBH_USE_ORCHESTRATOR")

# off: policy-service never called | shadow: called and logged, legacy decision kept |
# active: policy decision applied
POLICY_MODE = os.getenv("NEXTBH_POLICY_MODE", "off").strip().lower()
if POLICY_MODE not in ("off", "shadow", "active"):
    POLICY_MODE = "off"

POLICY_SERVICE_URL = os.getenv("POLICY_SERVICE_URL", "http://localhost:8010")
POLICY_TIMEOUT_S = float(os.getenv("POLICY_TIMEOUT_S", "2.0"))

# Path to rag/latest.json; when unset query_rag uses the legacy "legal_docs" collection
RAG_INDEX_MANIFEST = os.getenv("RAG_INDEX_MANIFEST", "")

# Publish decision_made events (Kafka, with MongoDB outbox fallback)
PUBLISH_EVENTS = _env_bool("NEXTBH_PUBLISH_EVENTS")
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
DECISION_EVENTS_TOPIC = os.getenv("DECISION_EVENTS_TOPIC", "decision_events")
