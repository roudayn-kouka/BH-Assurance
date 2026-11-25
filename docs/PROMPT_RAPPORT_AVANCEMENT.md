# Prompt · Rapport d’avancement Next-BH

Copier le texte ci-dessous dans une session disposant d’un accès au dépôt et, si possible, à Jira.

---

Tu es chargé de rédiger un **rapport d’avancement de Next-BH entièrement en français** pour l’encadrement académique et l’équipe technique. Produis un fichier Word éditable `Rapport_avancement_Next-BH.docx` et un PDF de diffusion `Rapport_avancement_Next-BH.pdf`. Présente le travail réalisé, le périmètre architectural exact, les résultats observés, les limites et le plan de reprise. Indique la date réelle de la revue (fuseau Africa/Tunis) et le commit Git étudié. Utilise « 20 novembre 2026 » comme date du point de référence ci-dessous, puis actualise ce point si des preuves plus récentes sont accessibles.

## Sources à consulter

- Dans le [dépôt Next-BH](https://github.com/naderite/Next-BH), lire le [suivi d’avancement](https://github.com/naderite/Next-BH/blob/master/docs/AVANCEMENT.md), le README, le [guide de recette](https://github.com/naderite/Next-BH/blob/master/docs/STAGING_PILOT.md), les [prérequis](https://github.com/naderite/Next-BH/blob/master/docs/STAGING_SETUP.md), la [grille de notation](https://github.com/naderite/Next-BH/blob/master/docs/STAGING_EVALUATION.md) et le [guide de la source du tableau de bord](https://github.com/naderite/Next-BH/blob/master/docs/DASHBOARD_SOURCE.md). Vérifie dans le code les composants représentés sur le schéma.
- Dans [Jira BH](https://maiteai.atlassian.net/browse/BH-12), vérifier BH-1 à BH-17, les relations parent-enfant et les statuts. Vérifier les PR #1 à #13 et leurs commits de fusion sur `master`. Présenter une matrice concise reliant chaque ticket à son livrable et à la PR correspondante, avec des liens cliquables. Si Jira est inaccessible, dater la dernière vérification documentée et signaler les statuts qui restent à confirmer.
- Lire les logs du [workflow de revue](https://github.com/naderite/Next-BH/actions/runs/44643141682) et de la [CI vague 3](https://github.com/naderite/Next-BH/actions/runs/44643141739/attempts/2), notamment le [job Chromium](https://github.com/naderite/Next-BH/actions/runs/44643141739/job/135981926388). Ces exécutions correspondent au commit `4bfca3682be42a1f52011a7111d648ed9f83553e`. Vérifier le SHA et le mode avant de citer d’autres exécutions.

## Contenu du rapport

1. **Résumé exécutif.** Donner le périmètre et l’état des trois vagues. Au point de référence, BH-1 à BH-11, BH-13 à BH-15 et BH-17 sont Done. BH-12 et BH-16 restent In Progress dans Jira. La recette BH-16 est en pause, avec son implémentation fusionnée.
2. **Travaux réalisés.** Expliquer ce qu’apporte chaque vague et la fiabilisation BH-17. Présenter les PR et les résultats de vérification. Indiquer que la revue technique et la fusion des PR #11 à #13 ont été réalisées sous la direction de Mohamed Kallel. Attribuer les revues humaines uniquement si une trace explicite les confirme.
3. **Architecture du pilote.** Créer un schéma lisible à partir du flux vérifié. Montrer l’entrée PM synthétique, la route FastAPI `GET /recommend_pm/`, le produit candidat, le catalogue approuvé contrôlé par SHA-256, la récupération Chroma, la vérification des besoins et des preuves, la sélection des identifiants par le scénario LangChain, le document `pending` dans MongoDB, puis l’entrée de revue Express et l’écran React **Validation**. Montrer le retour de la décision vers le document MongoDB, avec auteur et horodatage. Indiquer que le code compose le brouillon à partir des citations validées. Identifier les branches « Besoins à préciser » et « Documentation produit insuffisante », ainsi que la note interne si le modèle renvoie une sélection invalide. Sur le schéma, préciser que Gemma via Ollama est la configuration de recette et que la CI utilise une sélection déterministe. Si tu reproduis les schémas historiques du README, légende-les comme tels et indique la zone couverte par le pilote. Situer Gmail, Kafka, les parcours de facturation et de renouvellement, les particuliers et MaskablePPO hors du périmètre testé ici.
4. **Intégration du tableau de bord.** Expliquer pourquoi la recette utilise l’export historique qui reste disponible, `a18e1e0fc402af64d63a16fba5532bc357d077e1`, et les deux correctifs versionnés. Consigner la limite du gitlink `394df01b2ce3fb5575a828049928885c76f3c31a`, toujours épinglé et indisponible à l’upstream lors de la vérification.
5. **Tests et résultats.** Présenter une matrice avec objectif, environnement, commande ou job, résultat, commit et source. Décrire la démonstration Wave 1, les deux chemins de revue Wave 2, les vérifications Git/Bash sous Windows et le scénario de bout en bout Wave 3. Consigner les 24 résultats attendus sur 24 en CI (8 recommandations, 8 clarifications, 8 preuves insuffisantes), la persistance des deux décisions après rechargement, le conflit HTTP 409, la route d’envoi absente (404) et zéro message client. Identifier l’exécution annulée et la relance réussie sur le même SHA si tu les mentionnes. Pour la recette Gemma ou les notes humaines, renseigner uniquement les résultats effectivement disponibles et leur source.
6. **Reste à faire.** Présenter les dépendances et critères de sortie dans l’ordre. Identifier un hôte Linux adapté et une session de revue privée. Exécuter la recette avec le modèle `gemma3n:e4b` sur un `master` propre. Relever le digest du modèle, la version d’Ollama, le digest du catalogue et l’issue de chaque cas. Capturer les décisions après rechargement et l’absence d’envoi. Faire noter les 24 cas par l’évaluateur autorisé (pertinence, appui factuel et utilisabilité, chacun de 0 à 2 par cas, total sur 48 par dimension). Consigner la date, l’évaluateur et les exemples pour chaque note inférieure à 2. Publier les preuves puis vérifier les critères de fermeture de BH-16 et BH-12. Ne fixe aucune date ni note qui n’a été confirmée.
7. **Annexes.** Donner les liens vers Jira, les PR, les logs, les chemins source et les commandes officielles. Inclure une table des figures et des preuves avec leur contexte de collecte. Indiquer la date de consultation pour les sources dont le contenu peut changer.

## Captures et données probantes

Collecter les captures depuis les systèmes ou depuis une exécution reproductible du dépôt. Privilégier une capture ciblée par état et ajouter à chaque figure un numéro, une légende, la date, le mode d’exécution, le commit quand il s’applique et un lien vers la preuve. Les captures de Jira doivent être recadrées et débarrassées des données d’identité, noms de compte, e-mails et notes internes sans rapport avec le projet. Masquer les jetons, mots de passe, cookies, données personnelles et adresses privées dans toutes les captures et tous les extraits.

| Figure | Écran ou preuve à recueillir | Ce qu’il faut rendre lisible |
| --- | --- | --- |
| 1 | Jira, vue de projet ou fiches BH-12 et BH-16 | Statuts actuels, relation parent-enfant et critères encore ouverts. |
| 2 | GitHub, PR #11 à #13 ou historique de `master` | État fusionné, SHA et contrôles pertinents. |
| 3 | GitHub Actions, résumé et log du job vague 3 | Mode `ci`, SHA, répartition 8/8/8, 24/24 et compteur d’envoi à 0. |
| 4 | Tableau de bord, brouillon `CLEAR-01` ou `CLEAR-02` | Produit candidat, extrait, référence de la source et révision du catalogue. |
| 5 | Tableau de bord après rechargement | Un brouillon `validated`, un `rejected`, identité d’essai et horodatages UTC persistés. |
| 6 | Tableau de bord, cas `AMBIG-01` et `NOFIT-08` | Note de clarification et note de preuves insuffisantes. |
| 7 | Terminal du pilote Gemma et relevé de recette, lorsqu’ils existent | Commit, mode `staging`, version Ollama, digests, résultats observés et synthèse des scores humains. |

Pour les figures 4 à 6, si la recette Gemma est toujours suspendue, tu peux rejouer le pilote déterministe sur un hôte autorisé et capturer le navigateur. Après installation des dépendances selon le guide de recette, utilise la commande suivante depuis la racine du dépôt (`pilot_python` désigne le Python de la venv de recette).

```sh
bash scripts/run_dashboard_review_pilot.sh "$pilot_python" --staging reviewer@example.invalid --ci
```

Ouvre le tableau de bord en boucle locale et identifie les figures par la légende « Pilote synthétique · inférence déterministe ». Si un accès, une capture ou un résultat manque, indique précisément la preuve attendue et ajoute le lien ou le journal disponible. Ne génère aucune imitation de capture. N’exécute aucun service de production et n’utilise que les données d’essai du dépôt.

## Mise en page et contrôle final

Utilise un format A4, une couverture avec le titre et la date, un sommaire, des pieds de page numérotés et une grille typographique cohérente. Donne la priorité au résumé, au schéma architectural et à la matrice des tests. Regroupe les preuves détaillées en annexe. Choisis une palette sobre, des légendes lisibles, des marges régulières et des tableaux qui se lisent à taille réelle. Indique chaque statut en texte pour que sa signification reste claire sans couleur. Garde le nom des services, les routes, les identifiants d’interface et les valeurs des statuts Jira tels qu’ils apparaissent dans les sources. Développe les acronymes utiles à la première occurrence.

Vérifie les statuts et numéros de PR, les SHA, les totaux, les liens, les légendes et la séparation entre CI et recette. Ouvre le DOCX et le PDF et inspecte le rendu de chaque page. Corrige les sauts de page, tableaux tronqués, images floues et liens cassés avant de livrer les deux fichiers avec la liste des preuves encore manquantes.
