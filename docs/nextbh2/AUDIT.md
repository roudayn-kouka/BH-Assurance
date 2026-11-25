# Next-BH 2.0 — Audit des appels et schémas (PR 1)

Audit du dépôt `naderite/Next-BH` (master `49167ad`) avant la migration décrite dans le
*Guide d'implémentation orienté dépôt*. Tout ce qui suit a été lu dans le code, pas déduit du README.

## 1. Graphe d'appels temps réel

```
agent/app.py  (boucle infinie)
├── get_conversations_with_open_status()            utils/mongodb_conn.py
├── generate_response(agent)                        agent/agent.py
│   ├── get_first_open_status_conversation()
│   ├── SalesAgent.respond(user_message, user_data, conversation_history)
│   │   ├── analyze_intent()  → intent_analysis.analyse_message()   (regex puis zero-shot XLM-R)
│   │   ├── SALES_STRATEGIES[label]                 agent/config.py
│   │   ├── [use_rag] llm.query_rag_llm() → query_rag() → rag.retrieve_context(q, 3)
│   │   ├── llm.query_llm(True, user_data, rag_context, system_prompt=…)
│   │   └── generate_explanation("respond", …)
│   ├── append_message_to_conversation(statut="pending", argumentation=explanation)
│   └── update_conversation_status(conv_id, "pending")
└── fetch_new_user_data()  → user_profile_conn.fetch_new_user()  (endpoint api_datasets tiré au hasard)
    └── generate_initial_message(agent, user_data)
        ├── classify_user_type()
        ├── SalesAgent.agent_initiate(user_data)
        │   ├── endpoint_strategy / recommended_action  ← api_datasets
        │   ├── llm.query_small_rag_llm(product) → query_rag()
        │   └── llm.query_scenario_llm(endpoint_strategy, …)
        ├── create_or_get_client()
        └── append_message_to_conversation(statut="pending", conversation_status=…)
```

La décision commerciale est aujourd'hui prise **hors de l'agent** : `api_datasets/app.py` choisit
l'endpoint (au hasard côté agent) et `recommended_action` (règle de seuil sur le score CatBoost).

## 2. Schémas MongoDB écrits par l'agent

| Collection | Champs écrits par `mongodb_conn.py` |
|---|---|
| `conversations` | `client_id`, `status` (nouvelle_opportunite, renouvellement, payment_facture, upsell_cross_sell), `conversation_status` (open/pending), `is_completed`, `started_at`, `last_activity_at` |
| `messages` | `conversation_id`, `sender` (client/ai/agent), `direction`, `subject`, `body`, `status` (pending/validated/rejected), `is_modified`, `argumentation`, `created_at` |

Le passage `pending → validated/rejected` (verdict admin) est effectué par le backend Node
(voir §4). Depuis la vague 2 de `master`, la même écriture enregistre `reviewed_by` et
`reviewed_at` (`agent/utils/draft_review.py`, pilote `web/review-pilot`). `argumentation` est le
champ affiché par le dashboard historique : la PR 5 y ajoute action, justification, version de
modèle et sources sans modifier le frontend.

## 3. Contrats existants conservés

| Point d'entrée | Signature à préserver |
|---|---|
| `SalesAgent.respond` | `(user_message, user_data, conversation_history) -> (response, explanation)` |
| `SalesAgent.agent_initiate` | `(user_data) -> (response, explanation, subject)` |
| `generate_initial_message` / `generate_response` | inchangés, appelés par `agent/app.py` |
| `GET /recommend_pm/` … `/renouvellement_pp/` | `UserResponse` (user_id, user_type, endpoint_strategy, endpoint_key, profile, recommended_action) |

## 4. Constats à corriger ou à connaître

| # | Constat | Traitement |
|---|---|---|
| 1 | `web/BH-Assurance` pointe sur `394df01`, indisponible en amont. Depuis `master` (BH-8/BH-17), `.gitmodules` est déclaré et le dashboard est reconstruit à partir de la révision `a18e1e0` + `web/review-pilot/*.patch` (`docs/DASHBOARD_SOURCE.md`) | Verdict admin publié côté Python par `mlops/feedback/verdict_relay.py` (lit les changements de statut des messages, horodatage `reviewed_at`) ; snippet backend fourni dans `docs/nextbh2/INTEGRATION.md` |
| 2 | `rag.py` : `logger.exception("…" + e)` lève `TypeError` dans le `except` | Corrigé en PR 3 |
| 3 | `/recommend_pm/` renvoie le meilleur score **global** du CSV et des noms aléatoires | Endpoint `/features/{endpoint_key}/{ref}` ajouté (PR 3/5), endpoints existants inchangés |
| 4 | `generate_response` code en dur `endpoint_strategy="product_recommendation"` et `produits_recommandes=AUTOMOBILE` | Conservé en legacy ; le graphe reconstruit l'état à partir du profil disponible |
| 5 | `user_profile_conn.BASE_URL` = `localhost:8083`, port aussi publié par `kafka-connect` dans le compose | À arbitrer ; rendu configurable via `RECO_API_URL` |
| 6 | Healthcheck MongoDB utilise `mongo` (absent de `mongo:6.0`, remplacé par `mongosh`) | Corrigé dans `docker-compose.yaml` |
| 7 | Secrets de démonstration en clair (mongo-express, SQL Server, sqlpad) | Paramétrés par variables d'environnement, `.env.example` ajouté |
| 8 | Aucun `requirements.txt` | Ajoutés pour `mlops`, `policy_service` et les tests |
| 9 | Tests racine `test_*.py` = scripts d'intégration nécessitant MongoDB/API | Conservés ; tests unitaires stubés dans `agent/tests` |

## 5. Feature flags (`agent/feature_flags.py`)

| Variable | Défaut | Effet |
|---|---|---|
| `NEXTBH_USE_ORCHESTRATOR` | `false` | `SalesAgent.respond()` délègue à `AgentOrchestrator` |
| `NEXTBH_POLICY_MODE` | `off` | `off` / `shadow` (appel journalisé, décision legacy) / `active` |
| `POLICY_SERVICE_URL` | `http://localhost:8010` | URL du policy-service |
| `RAG_INDEX_MANIFEST` | vide | Chemin de `rag/latest.json` ; vide = collection legacy `legal_docs` |
| `NEXTBH_PUBLISH_EVENTS` | `false` | Publication des `decision_events` (Kafka + outbox MongoDB) |

Tous à leur valeur par défaut, le comportement est identique au legacy, ce que vérifient
`agent/tests/test_legacy_respond.py` et `agent/tests/test_orchestrator.py`.
