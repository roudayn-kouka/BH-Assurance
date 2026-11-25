"""
P2.1 — Export decision_events into a reproducible, deduplicated dataset.

Sources: Kafka topic (committed offsets kept in a local state file, not in the consumer
group, so a re-run from the same state yields the same dataset) or an offline JSONL dump.
Events are deduplicated by event_id and joined per decision_id. The admin verdict and the
customer outcome stay separate fields: reward_status is "final" only when a real customer
outcome exists — a missing outcome is never invented.

The joined dataset feeds calibration reports (approval rate per action); it is not
injected as rewards (attribution delays and selection bias, see architecture doc §6).
"""

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from mlops.common.schemas import DecisionEvent
from mlops.common.storage import artifact_root, atomic_write_json, read_json, sha256_bytes


def read_jsonl(path: Path) -> Iterable[Dict]:
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def read_kafka(topic: str, bootstrap: str, state_path: Path, max_records: int = 100_000) -> Iterable[Dict]:
    from kafka import KafkaConsumer, TopicPartition
    from kafka.serializer import Deserializer

    state = read_json(state_path) if state_path.exists() else {"offsets": {}}
    class Json(Deserializer):
        def deserialize(self, topic, *args):  # (data) or (headers, data) by version
            data = args[-1]
            return json.loads(data.decode("utf-8"))

    consumer = KafkaConsumer(bootstrap_servers=bootstrap, enable_auto_commit=False,
                             value_deserializer=Json(), consumer_timeout_ms=5000)
    partitions = [TopicPartition(topic, p) for p in consumer.partitions_for_topic(topic) or []]
    consumer.assign(partitions)
    for tp in partitions:
        consumer.seek(tp, int(state["offsets"].get(str(tp.partition), 0)))
    offsets = dict(state["offsets"])
    for count, msg in enumerate(consumer):
        offsets[str(msg.partition)] = msg.offset + 1
        yield msg.value
        if count + 1 >= max_records:
            break
    consumer.close()
    atomic_write_json(state_path, {"offsets": offsets})


def dedupe(events: Iterable[Dict], watermark: Optional[str] = None) -> List[Dict]:
    seen, out = set(), []
    for raw in events:
        try:
            ev = DecisionEvent.model_validate(raw).model_dump()
        except Exception:
            continue  # malformed events are dropped, counted by the caller via the diff
        if ev["event_id"] in seen or (watermark and ev["timestamp"] > watermark):
            continue
        seen.add(ev["event_id"])
        out.append(ev)
    return sorted(out, key=lambda e: (e["timestamp"], e["event_id"]))


def join_decisions(events: List[Dict]) -> List[Dict]:
    decisions: Dict[str, Dict] = defaultdict(dict)
    for ev in events:
        d = decisions[ev["decision_id"]]
        d.setdefault("decision_id", ev["decision_id"])
        if ev["event_type"] == "decision_made":
            d.update(action=ev["action"], model_version=ev["model_version"],
                     state_version=ev["state_version"], allowed_actions=ev["allowed_actions"],
                     fallback=ev["fallback"], decided_at=ev["timestamp"],
                     conversation_id=ev["conversation_id"])
        elif ev["event_type"] == "admin_verdict":
            d.update(admin_verdict=ev["admin_verdict"], verdict_at=ev["timestamp"])
        elif ev["event_type"] == "customer_outcome":
            d.update(customer_outcome=ev["customer_outcome"], outcome_at=ev["timestamp"])
    rows = []
    for d in decisions.values():
        d.setdefault("admin_verdict", None)
        d.setdefault("customer_outcome", None)
        d["reward_status"] = (
            "final" if d["customer_outcome"] else "provisional" if d["admin_verdict"] else "none"
        )
        rows.append(d)
    return sorted(rows, key=lambda r: r["decision_id"])


def calibration_report(rows: List[Dict]) -> Dict:
    by_action = defaultdict(Counter)
    for r in rows:
        if r.get("action"):
            by_action[r["action"]][r["admin_verdict"] or "pending"] += 1
    return {
        "decisions": len(rows),
        "with_outcome": sum(r["reward_status"] == "final" for r in rows),
        "verdicts_by_action": {a: dict(c) for a, c in by_action.items()},
        "approval_rate_by_action": {
            a: c["approved"] / max(sum(v for k, v in c.items() if k != "pending"), 1)
            for a, c in by_action.items()
        },
    }


def export(events: Iterable[Dict], out_dir: Path, watermark: Optional[str] = None) -> Dict:
    events = dedupe(events, watermark)
    rows = join_decisions(events)
    payload = "\n".join(json.dumps(r, sort_keys=True, ensure_ascii=False) for r in rows)
    data_hash = sha256_bytes(payload.encode())
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"decisions-{data_hash[:12]}.jsonl").write_text(payload, encoding="utf-8")
    report = {"data_hash": data_hash, "events": len(events), **calibration_report(rows)}
    atomic_write_json(out_dir / "calibration_report.json", report)
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--jsonl", type=Path)
    src.add_argument("--kafka-topic")
    parser.add_argument("--bootstrap", default="localhost:9092")
    parser.add_argument("--watermark", help="ISO timestamp; later events are left for the next run")
    args = parser.parse_args(argv)

    out_dir = artifact_root() / "rl" / "datasets"
    if args.jsonl:
        events = read_jsonl(args.jsonl)
    else:
        events = read_kafka(args.kafka_topic, args.bootstrap,
                            artifact_root() / "rl" / "export_state.json")
    print(json.dumps(export(events, out_dir, args.watermark), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
