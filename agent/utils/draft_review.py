"""Record human review on the agent's MongoDB message documents."""

from bson import ObjectId
from pymongo import ReturnDocument


def record_draft_decision(messages, draft_id, decision, reviewer_id):
    """Record a decision using the reviewer's authenticated identity.

    The caller supplies the messages collection and trusted reviewer ID. Return
    the updated draft, or None if the ID is missing or the draft is no longer
    pending. The database records the timestamp in the same write as the decision.
    """
    if decision not in ("validated", "rejected"):
        raise ValueError("Decision must be validated or rejected")
    if not isinstance(reviewer_id, str) or not reviewer_id.strip():
        raise ValueError("A reviewer ID is required")
    if not ObjectId.is_valid(draft_id):
        raise ValueError("A valid draft ID is required")

    return messages.find_one_and_update(
        {"_id": ObjectId(draft_id), "status": "pending"},
        {
            "$set": {"status": decision, "reviewed_by": reviewer_id},
            "$currentDate": {"reviewed_at": True},
        },
        return_document=ReturnDocument.AFTER,
    )
