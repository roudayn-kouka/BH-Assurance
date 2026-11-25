"""Run both synthetic review paths through the recommendation, agent, and decision code."""

import argparse
import sys
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from network_guard import is_socketpair_emulation
from pymongo import MongoClient
from smoke_recommendation_api import EXPECTED_PRODUCT, check_recommendation_api
from smoke_recommendation_draft import check_recommendation_draft

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "agent"))
from utils.draft_review import record_draft_decision


def check_review_paths(port):
    endpoint = ("127.0.0.1", port)
    outbound_attempts = []
    network_events = {
        "socket.connect", "socket.sendto", "socket.getaddrinfo",
        "socket.gethostbyname", "socket.gethostbyaddr", "socket.getnameinfo",
    }

    def prevent_outbound(event, args):
        if event not in network_events:
            return
        if event in {"socket.connect", "socket.sendto"} and args[1] == endpoint:
            return
        if event == "socket.connect" and is_socketpair_emulation(args[1]):
            return
        if event == "socket.getaddrinfo" and args[:2] == endpoint:
            return
        outbound_attempts.append(event)
        raise RuntimeError("The synthetic review demo attempted to use a non-demo connection")

    sys.addaudithook(prevent_outbound)

    recommendation = check_recommendation_api()
    draft = check_recommendation_draft(recommendation, EXPECTED_PRODUCT)
    print(f"Selected product: {recommendation['profile']['candidate_produit']}")
    print(f"Draft status: {draft['statut']}")

    with MongoClient(*endpoint, directConnection=True, tz_aware=True, serverSelectionTimeoutMS=3000) as client:
        database = client[f"bh_review_demo_{uuid4().hex}"]
        messages = database.messages
        try:
            for decision, reviewer, retry in (
                ("validated", "synthetic-approver", "rejected"),
                ("rejected", "synthetic-rejecter", "validated"),
            ):
                draft_id = messages.insert_one({
                    "status": draft["statut"],
                    "sender": draft["expediteur"],
                    "subject": draft["subject"],
                    "body": draft["corps"],
                }).inserted_id
                updated = record_draft_decision(messages, draft_id, decision, reviewer)
                if updated is None or (updated["status"], updated["reviewed_by"]) != (decision, reviewer):
                    raise RuntimeError(f"Missing {decision} decision or reviewer")
                if not isinstance(updated["reviewed_at"], datetime) or updated["reviewed_at"].tzinfo is None:
                    raise RuntimeError("Missing database decision timestamp")
                if record_draft_decision(messages, draft_id, retry, "synthetic-second-reviewer") is not None:
                    raise RuntimeError("A second decision was accepted")
                if messages.find_one({"_id": draft_id}) != updated:
                    raise RuntimeError("The recorded decision changed after rereading the draft")
                print(f"{decision}: {reviewer} at {updated['reviewed_at'].isoformat()}. First decision preserved.")
        finally:
            client.drop_database(database.name)

    if outbound_attempts:
        raise RuntimeError("The synthetic review demo attempted outbound network access")
    print("Outbound requests: 0")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, required=True, help="Disposable MongoDB port on localhost")
    check_review_paths(parser.parse_args().port)
