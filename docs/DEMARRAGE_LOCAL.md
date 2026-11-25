# Démarrage local de Next-BH

Toutes les parties du dépôt se lancent depuis un seul point d'entrée, `scripts/nextbh.py`
(bibliothèque standard uniquement, Windows / Linux / macOS). Vérifié sur Windows 11 avec
Docker Desktop (VM de 2 Go), Git for Windows, Node.js 24 et `uv`.

## Prérequis

| Outil | Rôle | Remarque |
|---|---|---|
| Python ≥ 3.10 (pour lancer le script) | `py scripts\nextbh.py …` sous Windows | L'environnement du projet est créé en Python 3.12 |
| [uv](https://docs.astral.sh/uv/) | crée `.venv` et télécharge Python 3.12 | sinon `python -m venv` + `pip` |
| Docker Desktop | MongoDB, ChromaDB, Zipkin, Kafka, MongoDB jetables des démos | 2 Go de VM suffisent sans le profil `sql` |
| Git for Windows (Git Bash) | lanceur du dashboard | |
| Node.js 22+ et npm | dashboard React / Express | |
| [Ollama](https://ollama.com) | LLM de l'agent (`gemma3n:e4b`) | version portable possible, voir plus bas |

Espace disque : environ 8 Go pour `.venv`, 7,6 Go pour `gemma3n:e4b`, 7 Go pour les modèles
Hugging Face, 1 Go de node_modules temporaires pour le dashboard.

## Installation

```powershell
py scripts\nextbh.py setup      # .venv (requirements-local.txt) + données synthétiques
py scripts\nextbh.py models     # e5-large, XLM-R, Qwen 1.5B, gemma3n:e4b — reprend après coupure
py scripts\nextbh.py doctor     # état des prérequis, services et artefacts
```

`setup` génère des données **fictives** : les six CSV lus par `api_datasets/app.py`
(`catboost_pm.csv`, …, avec des échéances de renouvellement proches d'aujourd'hui) et un corpus de
conditions générales par branche dans `data/rag_docs/`. Ces fichiers sont ignorés par Git ;
`scripts/generate_synthetic_datasets.py` les régénère à l'identique.

## Lancer la plateforme

```powershell
py scripts\nextbh.py up            # Docker + API recommandation + policy-service + Ollama
py scripts\nextbh.py rag           # indexe data/rag_docs, évalue, promeut rag/latest.json
py scripts\nextbh.py rl            # entraîne LinUCB + MaskablePPO, compare, promeut rl/latest.json
py scripts\nextbh.py agent --once  # un cycle de l'agent (sans --once : boucle continue)
py scripts\nextbh.py status        # URLs
py scripts\nextbh.py down          # arrête tout (--keep-infra garde Docker)
```

| Interface | URL |
|---|---|
| API recommandation (Swagger) | http://127.0.0.1:8083/docs |
| Policy-service (Swagger, `/metrics`) | http://127.0.0.1:8010/docs |
| mongo-express (`admin` / `secret` par défaut) | http://127.0.0.1:8081 |
| ChromaDB | http://127.0.0.1:8000/api/v2/heartbeat |
| Zipkin | http://127.0.0.1:9411 |
| AKHQ (avec `up --events`) | http://127.0.0.1:8090 |

Les services lancés en arrière-plan écrivent dans `.run/<service>.log`.

### Activer Next-BH 2.0 dans l'agent

Copier `.env.example` en `.env` puis, progressivement :

```ini
NEXTBH_USE_ORCHESTRATOR=true
NEXTBH_POLICY_MODE=shadow          # puis active
RAG_INDEX_MANIFEST=artifacts/rag/latest.json
NEXTBH_PUBLISH_EVENTS=true         # outbox MongoDB ; Kafka avec `up --events`
```

`py scripts\nextbh.py relay` publie ensuite les verdicts admin (`--once` pour un passage).

## Démos et dashboard

```powershell
py scripts\nextbh.py demo                 # recommandation + revue des brouillons (MongoDB jetable)
py scripts\nextbh.py dashboard            # dashboard React/Express avec deux brouillons de démo
py scripts\nextbh.py dashboard --staging  # 24 cas de la vague 3 rédigés par gemma3n:e4b
py scripts\nextbh.py test                 # tests unitaires + lint
```

Le dashboard affiche son URL et un mot de passe temporaire. `Ctrl-C` l'arrête et supprime la base
et les sources temporaires.

## Ollama sans installation

L'archive officielle `ollama-windows-amd64.zip`
(https://github.com/ollama/ollama/releases) peut être décompressée dans un dossier voisin du
dépôt, `..\tools\ollama\`. Sans Ollama installé, `nextbh.py models` y télécharge le modèle et
`nextbh.py up` y démarre le serveur (modèles dans `..\tools\ollama\models`, journal dans
`.run\ollama.log`) ; `down` l'arrête. Une installation classique d'Ollama est utilisée en priorité.

## Dépannage

| Symptôme | Cause et solution |
|---|---|
| `docker compose up` reste bloqué à « Creating » | un autre `docker compose` est encore en cours : l'arrêter puis relancer |
| ChromaDB s'arrête avec « readonly database » | ancienne version du compose avec `./chroma_data` monté : les volumes sont maintenant nommés |
| Téléchargement interrompu (DNS, connexion réinitialisée) | relancer `nextbh.py models` : les téléchargements reprennent |
| `llama-server … CUDA error` dans `.run/ollama.log` | échec ponctuel au premier chargement GPU du modèle ; Ollama le relance et l'agent réessaie l'appel automatiquement |
| Mémoire insuffisante pour l'agent | modèles plus légers dans `.env` (`NEXTBH_LLM_MODEL=gemma3n:e2b`, …) |
| SQL Server / Kafka Connect | profils optionnels `sql` et `events` (`docker compose --profile sql up -d`), à réserver à une VM Docker de 4 Go ou plus |
