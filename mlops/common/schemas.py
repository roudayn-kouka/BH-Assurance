"""
Versioned contracts shared by the agent, the policy-service and the batch pipelines.

Any change to a field's meaning requires a new schema version: a policy trained on
state v1 / actions v1 must never be served with another feature or action space.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

STATE_SCHEMA_VERSION = "v1"
ACTION_SCHEMA_VERSION = "v1"
EVENT_SCHEMA_VERSION = "v1"


def new_id() -> str:
    return str(uuid.uuid4())


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------- Policy service ----------------


class PolicyActRequest(BaseModel):
    decision_id: str = Field(default_factory=new_id)
    client_id: str = Field(..., description="Identifiant client pseudonymisé")
    state_version: str = STATE_SCHEMA_VERSION
    features: Dict[str, Any] = Field(default_factory=dict)
    allowed_actions: Optional[List[str]] = Field(
        None, description="Restriction appelant ; intersectée avec le masque métier du service"
    )
    requested_policy_version: Optional[str] = None
    trace_id: Optional[str] = None


class PolicyActResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    decision_id: str
    action: str
    model_version: str
    fallback: bool
    fallback_reason: Optional[str] = None
    reason_codes: List[str] = Field(default_factory=list)
    allowed_actions: List[str]
    action_schema: str = ACTION_SCHEMA_VERSION
    inference_ms: float
    trace_id: Optional[str] = None


# ---------------- Kafka topic decision_events ----------------

EventType = Literal["decision_made", "admin_verdict", "customer_outcome"]
AdminVerdict = Literal["approved", "edited", "rejected"]


class DecisionEvent(BaseModel):
    """
    One schema for the three event types of topic `decision_events`.

    The admin verdict (message admissibility) and the customer outcome (business result)
    are separate events: a rejection is never turned into a negative conversion.
    """

    model_config = ConfigDict(protected_namespaces=())

    event_id: str = Field(default_factory=new_id)
    event_type: EventType
    schema_version: str = EVENT_SCHEMA_VERSION
    decision_id: str
    conversation_id: Optional[str] = None
    message_id: Optional[str] = None
    timestamp: str = Field(default_factory=utc_now)
    model_version: Optional[str] = None
    state_version: str = STATE_SCHEMA_VERSION
    action: Optional[str] = None
    allowed_actions: List[str] = Field(default_factory=list)
    fallback: Optional[bool] = None
    admin_verdict: Optional[AdminVerdict] = None
    reason_code: Optional[str] = None
    customer_outcome: Optional[str] = None
    attribution_window_days: Optional[int] = None
    reward_status: Literal["none", "provisional", "final"] = "none"
    trace_id: Optional[str] = None


# ---------------- Artifact manifests ----------------


class RagManifest(BaseModel):
    kind: Literal["rag"] = "rag"
    version: str = Field(..., description="index_version")
    artifact_uri: str
    collection_name: str
    embedding_model: str
    source_hash: str
    chunk_count: int
    evaluation_run_id: Optional[str] = None
    test_report: Dict[str, Any] = Field(default_factory=dict)
    approved: bool = False
    created_at: str = Field(default_factory=utc_now)


class RlManifest(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    kind: Literal["rl"] = "rl"
    version: str = Field(..., description="model_version")
    model_uri: str
    algorithm: str
    feature_schema: str = STATE_SCHEMA_VERSION
    action_schema: str = ACTION_SCHEMA_VERSION
    mlflow_run_id: Optional[str] = None
    data_hash: Optional[str] = None
    eval_report: Dict[str, Any] = Field(default_factory=dict)
    approved: bool = False
    created_at: str = Field(default_factory=utc_now)


class GateResult(BaseModel):
    value: Optional[float] = None
    threshold: Optional[float] = None
    passed: bool
    detail: Optional[str] = None


class ValidationRecord(BaseModel):
    kind: Literal["rag", "rl"]
    version: str
    gates: Dict[str, GateResult]
    approved: bool
    approved_by: Optional[str] = None
    approved_at: Optional[str] = None
    reasons: List[str] = Field(default_factory=list)
