# Next-BH 2.0 — Mise en route et exploitation

Complète `AUDIT.md` (état initial), `INTEGRATION.md` (backend / dashboard) et
`VERIFICATION_LOCALE.md` (exécution vérifiée de bout en bout).
Résultats RL = **simulation** : ils ne prouvent pas un gain de conversion réel.

## Arborescence ajoutée

```
mlops/
  common/        schemas (contrats), manifest (latest.json, rollback), storage, mlflow_tracking, events
  data_rag/      prepare → ingest_documents → index_chroma → evaluate → publish   (run.py)
  rl/            export_events, features, actions, env, policies, train, evaluate, publish  (run.py)
  feedback/      verdict_relay (verdict admin → Kafka, outbox)
  orchestration/ DAGs Airflow optionnels
  configs/       rag.yaml, rl.yaml, validation.yaml (seuils des gates)
  promote.py     promotion / rollback contrôlés
policy_service/  FastAPI /policy/act, /health, /policy/reload, /metrics + Dockerfile
agent/orchestrator.py, agent/compliance.py, agent/feature_flags.py,
agent/utils/policy_client.py, agent/utils/event_publisher.py
docker-compose.mlops.yaml, dvc.yaml, .github/workflows/{ci,mlops}.yml, scripts/smoke_policy_service.py
```

## Articulation avec le pilote de `master`

Le pilote des vagues 1 à 3 (`docs/AVANCEMENT.md`, `docs/STAGING_PILOT.md`) couvre la
recommandation PM avec sources vérifiées et la revue humaine ; il exclut volontairement le RL.
Cette branche ajoute le périmètre MLOps / RL **derrière des feature flags désactivés par défaut** :
le lanceur du pilote, `grounded_recommendation.py`, `draft_review.py` et les workflows
`draft-review.yml` / `staging-pilot.yml` ne sont pas modifiés. Les deux CI coexistent :
`ci.yml` et `mlops.yml` ne lintent ni ne testent les scripts du pilote.

## Installation

En local, `scripts/nextbh.py` installe et lance tout (voir [DEMARRAGE_LOCAL.md](../DEMARRAGE_LOCAL.md)) :

```bash
python scripts/nextbh.py setup               # .venv (requirements-local.txt) + données synthétiques
python scripts/nextbh.py test                # tests sans infrastructure + lint
```

Installation manuelle équivalente :

```bash
pip install -r requirements-local.txt        # agent, pipelines, policy-service, pilote, tests
python scripts/generate_synthetic_datasets.py
dvc init && dvc remote add -d storage $DVC_REMOTE
```

## Pipeline A — Data & RAG

1. Déposer les documents dans `data/rag_docs/<n>-CG-<Catégorie>/` (PDF, CSV, TXT, MD), avec un
   `<fichier>.meta.yaml` optionnel (`date_effet`, `produit`, `version`).
2. Compléter `mlops/data_rag/reference_questions.yaml` avec des questions validées métier.
3. `python -m mlops.data_rag.run` → collection candidate `legal_docs__rag-…`, rapport, manifeste
   (`approved` seulement si Recall@K, MRR, présence des sources passent).
4. `python -m mlops.promote rag promote <version> --by <nom>` puis `RAG_INDEX_MANIFEST=artifacts/rag/latest.json`.

## Pipeline B — RL

```bash
python -m mlops.rl.export_events --kafka-topic decision_events   # optionnel : rapport de calibration
python -m mlops.rl.run                                            # LinUCB + MaskablePPO, 5 graines
python -m mlops.promote rl promote <version> --by <nom>
```

Le champion est le modèle approuvé courant, sinon la **baseline règles** (logique actuelle de
`api_datasets`). Les gates (`validation.yaml`) sont évaluées sur des graines holdout : 0 action
interdite, uplift relatif, graines gagnées, contacts par épisode, robustesse aux multiplicateurs.

## Activation progressive (feature flags)

| Étape | Variables |
|---|---|
| 0. Legacy | aucune |
| 1. Graphe seul | `NEXTBH_USE_ORCHESTRATOR=true` |
| 2. Shadow | `+ NEXTBH_POLICY_MODE=shadow`, policy-service démarré |
| 3. Événements | `+ NEXTBH_PUBLISH_EVENTS=true`, `python -m mlops.feedback.verdict_relay` |
| 4. Actif | `NEXTBH_POLICY_MODE=active` après revue des décisions shadow |
| RAG validé | `RAG_INDEX_MANIFEST=artifacts/rag/latest.json` |

```bash
docker compose -f docker-compose.yaml -f docker-compose.mlops.yaml up -d policy-service mlflow prometheus
python scripts/smoke_policy_service.py --url http://localhost:8010 --expect-model
```

## Défaillances et rollback

| Incident | Comportement |
|---|---|
| policy-service indisponible / timeout | Stratégie legacy appliquée, `fallback_reason=policy_service_unavailable:*` |
| Aucun manifeste approuvé, bundle illisible, schéma ≠ v1 | Service en baseline règles, `/health.fallback_only=true` |
| Mauvais modèle en production | `python -m mlops.promote rl rollback --by <nom>` puis `POST /policy/reload` |
| Index RAG approuvé absent de Chroma | L'agent refuse de démarrer sur une collection vide (pas de création implicite) |
| Kafka indisponible | Événements conservés dans `event_outbox`, ré-émis par le relais |

Traçabilité : `trace_id` / `decision_id` de l'appel policy → champ `decision` du message →
événements `decision_made` / `admin_verdict` → lignes de `export_events`.

## Monitoring minimal

`/metrics` du policy-service (Prometheus) : requêtes, replis, `policy_invalid_action_total`,
répartition des actions, latence p50/p95, version servie. Le rapport de calibration
(`artifacts/rl/datasets/calibration_report.json`) suit le taux d'approbation admin par action.
Grafana / Evidently restent à brancher sur ces sources ; une alerte de drift crée un challenger,
jamais une promotion automatique.

## Limites connues

- Dashboard : seul le pilote reconstruit (`a18e1e0` + correctifs) est disponible ; il n'affiche
  pas encore le champ `decision`. Voir `INTEGRATION.md`.
- Aucune donnée réelle de conversion : `customer_outcome` défini mais non émis.
- La première contact (`agent_initiate`) ne peut que confirmer l'action de l'endpoint ou différer
  le contact : les données récupérées sont propres à l'endpoint tiré.
