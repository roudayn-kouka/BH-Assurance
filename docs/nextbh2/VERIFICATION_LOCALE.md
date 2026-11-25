# Vérification locale de bout en bout — 25 novembre 2026

Exécution sur un poste Windows, depuis la branche `feature/nextbh-2.0` (commit `bb20e86` pour le
code exécuté). Toutes les commandes passent par `scripts/nextbh.py` sauf mention contraire.
Données : uniquement synthétiques (`scripts/generate_synthetic_datasets.py`, fixtures de la vague 3).

## Environnement

| Élément | Version |
|---|---|
| OS / matériel | Windows 11 Pro, 16 Go de RAM, NVIDIA RTX 3050 6 Go (portable) |
| Python | 3.12.15 (`.venv`, `requirements-local.txt`) |
| Docker | Docker Desktop 29.9.3, VM de 2 Go |
| Node.js / npm | 24.19.0 / 11.17.0 |
| Ollama | 0.40.18 portable, `gemma3n:e4b` digest `0a377808afeaafcbf5dcc2b1844594a1b60a50cd18e7e3e469cfd64e7bb7faa5` |
| Modèles Hugging Face | `intfloat/multilingual-e5-large`, `joeddav/xlm-roberta-large-xnli`, `Qwen/Qwen2.5-1.5B-Instruct` |

## Résultats

| Vérification | Commande | Résultat observé |
|---|---|---|
| Tests unitaires et lint | `nextbh.py test` | 53 tests réussis, ruff sans erreur |
| Infrastructure | `nextbh.py up --events` | MongoDB, mongo-express, ChromaDB, Zipkin, OTel, Kafka, AKHQ, API (8083), policy-service (8010) actifs |
| API de recommandation | 6 routes + `/features` | 200 sur les six routes avec les CSV synthétiques |
| Pipeline Data & RAG | `nextbh.py rag` | `rag-c80433850c-3a60fe` approuvé et promu : Recall@5 = 1,0, MRR = 1,0, présence des sources = 1,0 (12 extraits) |
| Pipeline RL | `nextbh.py rl` | 5 graines ; LinUCB 0,445 ± 0,028, MaskablePPO 0,421 ± 0,030 ; champion règles −0,03 ; `rl-20261125-003448-linucb` approuvé (toutes les gates), promu, rechargé à chaud |
| Policy-service | `scripts/smoke_policy_service.py --expect-model` | modèle servi, trace propagée, masque respecté, `/metrics` exposé |
| Agent — premier contact | `nextbh.py agent --once` (orchestrateur, politique `active`, index validé, événements) | brouillon `pending` en MongoDB, action `recommend_product` (LinUCB), 3 sources citées, objet et corps nettoyés |
| Agent — réponse client | réponse client simulée puis `nextbh.py agent --once` | intention `devis`, réponse au message du client, conformité « conforme », conversation repassée en `pending` |
| Boucle d'événements | revue via `agent/utils/draft_review.py`, `nextbh.py relay --once`, `mlops.rl.export_events` | `decision_made` puis `admin_verdict` (`approved`, horodatage `reviewed_at`) dans Kafka ; export : 6 événements, 5 décisions, aucune issue client inventée |
| Démo de revue (vague 2) | `nextbh.py demo` | décisions `validated` / `rejected` horodatées, deuxième décision refusée, « Outbound requests: 0 » |
| Dashboard (vague 2) | `nextbh.py dashboard` | build React/Express, connexion, deux brouillons `pending`, 409 sur seconde décision, 401 sans connexion |
| Recette vague 3, mode CI | `scripts/run_staging_recommendations.py --ci` | 24/24 résultats attendus, 0 message client |
| **Recette vague 3 avec Gemma** | `nextbh.py dashboard --staging` | **24/24 résultats attendus** (8 recommandations, 8 clarifications, 8 preuves insuffisantes), 0 message client, empreintes du catalogue et du modèle vérifiées |
| Revue dans le dashboard (vague 3) | API du pilote | 24 brouillons ; CLEAR-01 approuvé et CLEAR-02 rejeté (relecteur et horodatage UTC) ; 409 sur une seconde décision ; NOFIT-08 sans produit (« Le catalogue ne documente pas tous les besoins indiqués… ») |

## Restant à faire hors de cette vérification

- **Notation humaine** des 24 cas (grille de `docs/STAGING_EVALUATION.md`) par un évaluateur
  autorisé : non réalisée ici, elle ne peut pas être automatisée.
- Captures du dashboard dans un navigateur pour le rapport (le parcours a été vérifié par l'API).
- Résultats RL **simulés** : ils ne mesurent pas un gain de conversion réel.
