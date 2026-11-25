# Next-BH 2.0 — Intégration backend Node et dashboard (PR 6)

Le gitlink `web/BH-Assurance` pointe sur une révision indisponible. Depuis la vague 2 de `master`,
le dashboard est reconstruit hors du dépôt à partir de la révision `a18e1e0` et des correctifs
`web/review-pilot/dashboard.patch` et `staging.patch` (`docs/DASHBOARD_SOURCE.md`,
`scripts/run_dashboard_review_pilot.sh`). La boucle de feedback fonctionne **sans modifier ce
code** ; ce document décrit les évolutions optionnelles côté web.

### Raccordement avec le pilote de revue (vagues 2 et 3)

| Pilote `master` | Next-BH 2.0 (cette branche) |
|---|---|
| Décision admin : `status` + `reviewed_by` + `reviewed_at` dans la même écriture (Express ou `agent/utils/draft_review.py`) | `verdict_relay` lit ces champs ; `reviewed_at` devient l'horodatage de l'événement `admin_verdict`, l'identité du relecteur n'est pas copiée dans Kafka |
| Brouillons du lanceur : `recommendation_outcome`, `recommendation_product`, `recommendation_sources`, `catalog_revision` | Les messages de l'agent portent `decision` (action, version de modèle, sources RAG, conformité) et `argumentation`. Ils n'ont pas de `decision.decision_id` côté pilote : le relais les ignore |
| L'écran **Validation** du pilote n'affiche que `subject`, `body`, statut, relecteur et champs `recommendation_*` | Pour y voir la décision RL, étendre `staging.patch` avec les champs du §3 ci-dessous. Les sources RAG de l'agent ne sont pas des extraits vérifiés au sens du pilote : ne pas les écrire dans `recommendation_sources` |

## 1. Ce qui fonctionne déjà sans toucher au web

| Besoin | Mise en œuvre côté Python |
|---|---|
| Afficher action, justification, version de modèle, sources | Ajoutés au champ `argumentation` du message, déjà affiché par le dashboard (sections 4 à 6) |
| Conserver la décision avec le message | Champ `decision` du document `messages` (decision_id, action, model_version, fallback_reason, reason_codes, sources, conformité, trace_id) |
| Événement `decision_made` | Publié par l'agent après l'écriture MongoDB réussie (`NEXTBH_PUBLISH_EVENTS=true`) |
| Événement `admin_verdict` | `python -m mlops.feedback.verdict_relay` lit les messages passés `pending → validated/rejected` (édition = `is_modified`) et publie un événement idempotent par message |
| Aucune perte | Outbox MongoDB `event_outbox` : écrit avant l'envoi Kafka, ré-émis tant que non acquitté |
| Aucun envoi client sans verdict | Inchangé : l'agent n'écrit que des messages `pending` |

Mapping du verdict : `rejected → rejected`, `validated + is_modified → edited`, `validated → approved`.
Si le backend stocke un motif de rejet dans `rejection_reason`, il est repris en `reason_code`.

## 2. Option A — publier le verdict depuis le backend (commit DB puis événement)

À placer dans la fonction qui fait passer le message de `pending` à `validated/rejected`, **après**
l'écriture réussie. L'`event_id` est le même UUIDv5 que celui du relais Python, donc les deux
chemins peuvent coexister sans doublon.

```js
// npm i kafkajs uuid
const { Kafka } = require('kafkajs');
const { v5: uuidv5 } = require('uuid');
const NS = '6f1c2a8e-4d0b-4c7a-9f5e-2b1d3c4e5f60';            // mlops/common/events.py
const producer = new Kafka({ brokers: [process.env.KAFKA_BOOTSTRAP_SERVERS] }).producer();

async function publishVerdict(message) {                       // message = document mis à jour
  if (!message.decision?.decision_id) return;                 // messages legacy : rien à publier
  const verdict = message.status === 'rejected' ? 'rejected'
                : message.is_modified ? 'edited' : 'approved';
  const id = message._id.toString();
  const event = {
    event_id: uuidv5(`admin_verdict:${message.decision.decision_id}:${id}:${verdict}`, NS),
    event_type: 'admin_verdict', schema_version: 'v1',
    decision_id: message.decision.decision_id, message_id: id,
    conversation_id: message.conversation_id?.toString() ?? null,
    timestamp: new Date().toISOString(), model_version: message.decision.model_version,
    action: message.decision.action, admin_verdict: verdict,
    reason_code: message.rejection_reason ?? null,
    customer_outcome: null, reward_status: 'provisional', trace_id: message.decision.trace_id,
  };
  await producer.send({ topic: 'decision_events',
                        messages: [{ key: event.decision_id, value: JSON.stringify(event) }] });
}
```

## 3. Option B — affichage structuré dans le dashboard

Le champ `argumentation` suffit pour la démonstration. Pour un affichage dédié, lire
`message.decision` :

| Élément | Champ |
|---|---|
| Action appliquée / proposée (shadow) | `decision.action`, `decision.policy_action`, `decision.mode` |
| Justification | `decision.reason_codes`, `decision.fallback_reason` |
| Limites | `decision.allowed_actions` |
| Version du modèle et de l'index | `decision.model_version`, `decision.rag_index.index_version` |
| Documents cités | `decision.sources[]` (`source`, `document_version`, `page`) |
| Conformité | `decision.compliance.passed`, `decision.compliance.issues` |

## 4. Résultat client (`customer_outcome`)

Aucun signal d'achat ou de renouvellement n'existe aujourd'hui dans le dépôt. L'événement est
défini (`DecisionEvent`, `event_type="customer_outcome"`) mais il ne doit être émis qu'à partir
d'une source réelle (souscription, renouvellement constaté) avec sa fenêtre d'attribution ;
il n'est jamais déduit du verdict administratif.
