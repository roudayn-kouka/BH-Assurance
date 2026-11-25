# Wave 3 staging dependencies

Start from a clean Next-BH checkout. Use Python 3.12, Git, Node.js 22 or newer, npm, and Docker. The pilot uses the company route `GET /recommend_pm/`, embedded Chroma, a dedicated local Ollama process, and the historical dashboard with disposable MongoDB. The opportunity input is a per-case CSV in a temporary directory. The FastAPI route scores two synthetic rows and the workflow uses the winning company and candidate product. The adapter replaces generated contact fields with a case-specific address under `example.invalid`.

```sh
python3.12 -m venv ../.next-bh-wave3-venv
../.next-bh-wave3-venv/bin/python -m pip install -r scripts/staging-requirements.txt
../.next-bh-wave3-venv/bin/python -m pip check
```

Provision the repository's configured `gemma3n:e4b` in a dedicated Ollama process bound to loopback. The runtime reads the tag and digest from `/api/tags` and refuses to run with a different digest. Match the digest against the local model manifest. Use a machine sized for the Ollama model and record its runtime version. One way to provision it is:

```sh
OLLAMA_HOST=127.0.0.1:11434 OLLAMA_NO_CLOUD=1 ollama serve
# From a second terminal
OLLAMA_HOST=127.0.0.1:11434 ollama pull gemma3n:e4b
curl --fail --silent http://127.0.0.1:11434/api/tags
curl --fail --silent http://127.0.0.1:11434/api/version
```

The pilot uses Chroma for vector indexing and retrieval. It builds normalized lexical vectors from product names, excerpts, need codes, and the synthetic opportunity context. This keeps staging reproducible without downloading a second model. Chroma runs in process with telemetry disabled and uses a dedicated collection.

The catalog is a JSON object with a `revision` and an `entries` array. Each entry contains a unique `id`, the exact API `product` name, `document` and `locator` fields, the verbatim `excerpt`, and `supports` codes for the needs that the excerpt substantiates. Keep enough surrounding text to preserve qualifications. The pilot requires the approved SHA-256 of the catalog file. Use an approved catalog whose excerpts can be shown in the pilot dashboard.

Both indexing and lookup use Chroma. Lookup ranks passages for the candidate and filters on its exact product name. Code checks all stated needs against the returned source metadata before the model can select evidence for the draft. The pilot process permits only its dedicated local MongoDB and Ollama endpoints. It starts no inbound-message, Kafka, or email services.
