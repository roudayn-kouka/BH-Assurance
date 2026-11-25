# Wave 3 sales recommendation pilot

This pilot follows a synthetic company opportunity through the existing FastAPI company recommendation route, Chroma product retrieval, the LangChain recommendation scenario, and review in the existing dashboard. The isolated launcher uses a fresh MongoDB database and a temporary sign-in. It serves review and sign-in only. It starts no delivery, inbound-message, or reinforcement-learning services.

## Pin the inputs

| Input | Revision |
| --- | --- |
| Approved synthetic catalog | [`scripts/fixtures/wave3-catalog.json`](../scripts/fixtures/wave3-catalog.json) at [`0a8c2dd9f75882fe24fddb3914442a5e5232e135`](https://github.com/naderite/Next-BH/blob/0a8c2dd9f75882fe24fddb3914442a5e5232e135/scripts/fixtures/wave3-catalog.json) |
| Catalog revision and SHA-256 | `wave3-synthetic-fixture-1`, `d121baca9ecb41d985e4a1d30372253c1a87ed8f7dff72f31c6c264832ffe1e2` |
| Approved dashboard pilot source | `a18e1e0fc402af64d63a16fba5532bc357d077e1` |
| Dashboard gitlink | `394df01b2ce3fb5575a828049928885c76f3c31a` |
| Configured Gemma model | `gemma3n:e4b`. Record the local Ollama manifest digest and runtime version from the run output. |

Mohamed Kallel approved the catalog for this synthetic pilot. The evaluation covers the synthetic workflow and its fictional materials.

## Run and review

1. From a clean checkout, install the dependencies and confirm the dedicated loopback Ollama process has the configured model. [Staging setup](STAGING_SETUP.md)
2. Run the pilot below. Set `pilot_gemma_digest` to the full digest for `gemma3n:e4b` returned by the provisioning check. Enter the authorized reviewer's email when prompted. The launcher prints the case outcomes, counts, model, catalog digest, and loopback dashboard URL. Keep the temporary password private.

   ```sh
   pilot_python=../.next-bh-wave3-venv/bin/python
   pilot_catalog_sha=d121baca9ecb41d985e4a1d30372253c1a87ed8f7dff72f31c6c264832ffe1e2
   read -r -p 'Pilot reviewer email: ' pilot_reviewer_email
   read -r -p 'Full Gemma digest: ' pilot_gemma_digest
   bash scripts/run_dashboard_review_pilot.sh "$pilot_python" --staging "$pilot_reviewer_email" \
     --catalog "$PWD/scripts/fixtures/wave3-catalog.json" --catalog-sha256 "$pilot_catalog_sha" \
     --ollama-url http://127.0.0.1:11434 --ollama-digest "$pilot_gemma_digest"
   ```

3. Sign in to the dashboard. In **Validation**, open `CLEAR-01` and `CLEAR-02`. Verify the proposed product, catalog revision, and source excerpts. Approve one and reject the other. Reload, reopen both, and verify the original reviewer and UTC timestamp. These decisions are stored in the same MongoDB message documents the dashboard reads. The review endpoint returns HTTP 409 for a second decision and also rejects the loser of a simultaneous pair.
4. Open `NOFIT-08`. Expect **Documentation produit insuffisante**, with no product recommendation or coverage statement. Open `AMBIG-01` and verify **Besoins à préciser**. A full round has 24 cases. Record each case and decision before stopping the runner, which removes the disposable database. [Cases and scoring rubric](STAGING_EVALUATION.md)

## Reproduce the automated checks

Use the [Wave 2 clean-checkout commands](DRAFT_REVIEW_DEMO.md) to verify the baseline. From the Wave 3 checkout, run:

```sh
pilot_python=../.next-bh-wave3-venv/bin/python
"$pilot_python" -m pip check
env -i PATH="$PATH" "$pilot_python" -B scripts/check_grounded_recommendation.py
npm install --prefix ../.next-bh-wave3-browser --ignore-scripts --no-audit --no-fund playwright@1.62.1
../.next-bh-wave3-browser/node_modules/.bin/playwright install chromium
docker pull mongo:7.0@sha256:884c055bff8b7144ca44830d01826facd3083b33c4dea44b94a1476c62de3c32
NODE_PATH=../.next-bh-wave3-browser/node_modules \
  bash scripts/check_dashboard_review.sh "$pilot_python" --staging-ci
```

CI uses FastAPI, real Chroma retrieval, disposable MongoDB, and Chromium. It substitutes deterministic LangChain model responses. The browser signs in, sees generated drafts and sources, records both decisions, reloads, verifies HTTP 409 on retry and concurrent decisions, and checks that the ambiguous and insufficient-evidence cases are visible. It also verifies that the delivery endpoint returns HTTP 404 and that no browser request leaves the pilot origin.

## Pilot results

| Evidence | Cases and observed outcomes |
| --- | --- |
| Automated | [Wave 3 staging CI on master](https://github.com/naderite/Next-BH/actions/runs/44643141739/attempts/2) passed on `4bfca36`: 24/24 expected outcomes (8 recommendations, 8 clarification requests, 8 insufficient-evidence notes) and zero outbound customer messages. The model responses were deterministic. |
| Actual staging | On hold pending a suitable host. Capture the launcher summary and browser outcomes for the pinned catalog and model on a host with `gemma3n:e4b` available. |
| Human review | Pending. Record the authorized reviewer's date, case count, fit, grounding, and usability totals, plus examples for any scores below 2. |

[BH-12](https://maiteai.atlassian.net/browse/BH-12) tracks the milestone. The [dashboard integration](https://github.com/naderite/Next-BH/pull/11), [staging implementation](https://github.com/naderite/Next-BH/pull/12), and [CI and checkout fixes](https://github.com/naderite/Next-BH/pull/13) are merged. Run actual staging from clean `master` and record the commit, model digest, results, and human scores in [BH-16](https://maiteai.atlassian.net/browse/BH-16). The [project progress record](AVANCEMENT.md) links the remaining acceptance evidence.
