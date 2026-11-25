# Wave 2 dashboard pilot

This pilot uses the [historical dashboard source](../../docs/DASHBOARD_SOURCE.md). It reuses the existing React layout, Express authentication, and MongoDB message model. A loopback-only Express entry point serves the review page and stores decisions in disposable MongoDB.

Use Git, Python 3.12, Node.js 22 or later, npm, and Docker. From the repository root, install the [recommendation demo dependencies](../../docs/RECOMMENDATION_DEMO.md), then run:

```sh
bash scripts/run_dashboard_review_pilot.sh ../.next-bh-demo-venv/bin/python
```

Open the local URL printed by the command and sign in using the temporary account displayed with it. Open draft A and select **Approuver**, then open draft B and select **Rejeter**. Reload the validation page and reopen each draft. A shows `validated`, B shows `rejected`, and each includes the recorded reviewer and UTC timestamp. Both drafts were generated from the synthetic recommendation demo. The pilot exposes only sign-in and review actions and uses no production credentials or email delivery routes. Press Ctrl-C to remove the disposable database and source directory.

The patch is applied only to the verified historical revision in a temporary directory. The current dashboard pin is tracked separately in [BH-8](https://maiteai.atlassian.net/browse/BH-8).
