# Company recommendation demo

Use Git and Python 3.12. From a fresh checkout containing the demo, run the commands below at the repository root.

```sh
python3.12 -m venv ../.next-bh-demo-venv
../.next-bh-demo-venv/bin/python -m pip install -r scripts/smoke-requirements.txt -r scripts/agent-smoke-requirements.txt
../.next-bh-demo-venv/bin/python -m pip check
../.next-bh-demo-venv/bin/python -B scripts/demo_recommendation.py
```

On success, the demo prints the selected product and draft status.

```text
Selected product: Synthetic Fleet Cover
Draft status: pending
```

The real FastAPI route selects the highest-scoring company from a two-row synthetic CSV. The real initial-message flow uses that recommendation to create a draft, and an in-memory substitute captures the subject, body, and pending-review status. The CSV and API output are written in a temporary directory and removed at the end. No live services, customer data, or credentials are needed, and the command sends no messages.

Run `scripts/smoke_recommendation_api.py` or `scripts/smoke_recommendation_draft.py` with the same Python interpreter to check either step on its own. A failed assertion or an unexpected response makes the demo exit with a nonzero status.

To verify how an approval and a rejection are recorded, follow the [synthetic draft review checks](DRAFT_REVIEW_DEMO.md).
