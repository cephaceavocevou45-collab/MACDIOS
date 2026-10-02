# NOBI — RAPPORT PHASE 5B

Date : 2 octobre 2026. Les vérifications ci-dessous distinguent les contrôles réellement exécutés des simples inspections statiques. Aucun secret n’est reproduit. Le virtualenv ignoré par Git a été réparé et ses dépendances installées. Au moment de l’audit initial, le seul changement ciblé était la contrainte `cryptography>=50,<51`, suite à `pip-audit`; les corrections ultérieures sont signalées dans la mise à jour en tête du rapport. Aucun push, purge Git, suppression de branche ou force-push n’a été effectué.

## 1. Résumé exécutif

Cette phase a permis de relancer les contrôles locaux : Django check, migrations (détection de changements), pytest, Ruff, validation OpenAPI stricte, npm lint/build. Résultat backend relancé : 112 tests réussis, 4 ignorés, couverture 89,97 % sur SQLite. `pip-audit` avait relevé une vulnérabilité de `cryptography`; la contrainte a été corrigée. `npm audit` avait révélé deux avis modérés React Router; voir la mise à jour initiale pour la correction et ses vérifications.

Un run GitHub Actions réel est consultable et réussi sur le commit `018e6a3` du 1er octobre 2026 : jobs backend et frontend, étapes consultables toutes réussies. La définition distante de ce run utilise PostgreSQL 15 et exécute pytest/Ruff ainsi que ESLint/build. Ce run ne valide pas les changements actuellement non commités : le code de tests de concurrence et le workflow local étendu sont absents du commit testé. Le workflow de ce commit ne contient pas de service Redis ni d’étapes pip-audit/OpenAPI stricte/npm audit. Aucun PostgreSQL local, Redis local ou staging n’est disponible. Les secrets historiques n’ont été ni rotés ni révoqués.

## 2. Environnement réel

| Outil/service | Détection dans cette session |
|---|---|
| Git | `git version 2.55.0.windows.5` |
| Python dans PATH | Absent ; `py -0p` indique aucun Python enregistré |
| Python du projet (`backend/.venv`) | `3.14.5`; Django `5.2.17`; pytest `9.1.1`; exécutable utilisable avec exécution hors sandbox |
| Dépendances | `pip install -r requirements-dev.txt` complété dans `.venv`; `pip check` : aucune dépendance cassée |
| pip-audit | Exécutable présent dans `.venv`; audit final réussi après correction cryptography |
| Node.js | `v24.15.0` |
| npm | `11.12.0` |
| Docker / Docker Compose | Docker absent ; Compose non disponible |
| Client PostgreSQL (`psql`) | Absent |
| Client Redis (`redis-cli`) | Absent |
| GitHub CLI (`gh`) | Absent ; accès API en lecture obtenu via credential helper Git, sans afficher son jeton |
| PostgreSQL local | `127.0.0.1:5432` non joignable |
| Redis local | `127.0.0.1:6379` non joignable |

**État Git :** branche `main`, HEAD local `018e6a3ccafbd7ca359d8f73a3f9067d0630570f`. `git ls-remote origin refs/heads/main`, exécuté en lecture seule hors sandbox, a confirmé le même SHA sur GitHub. Le working tree reste modifié (58 entrées suivies/non suivies au dernier relevé), notamment le workflow CI et les tests, et ces modifications ne sont pas sur le commit distant. Rien n’a été poussé ni écrasé.

Commandes de contrôle : versions des outils, `py -0p`, `Get-Service`, tests de ports TCP locaux, `git status -sb`, `git branch --show-current`, `git log --oneline -10`, `git remote -v`, `git ls-remote`, API GitHub Actions en lecture. Aucun staging accessible n’a été révélé.

## 3. PostgreSQL

| Contrôle | Résultat |
|---|---|
| PostgreSQL 15 local | NON VÉRIFIÉ — Docker et `psql` absents, port local 5432 fermé |
| PostgreSQL 15 CI | CONFIRMÉ pour le commit `018e6a3` : l’étape de création des conteneurs et le job backend ont réussi ; workflow distant définit `postgres:15` et `DATABASE_URL` PostgreSQL |
| Code du working tree actuel sur PostgreSQL | NON VÉRIFIÉ — changements locaux non commités absents du run CI |
| Django check / migrations | `manage.py check` et `makemigrations --check --dry-run` réussis localement en configuration SQLite mémoire ; pas de `migrate` explicite sur PostgreSQL |
| Suite pytest locale | 112 réussis, 4 ignorés, couverture 89,97 % ; SQLite |

Cause : aucun moteur PostgreSQL local ou staging accessible. Le run CI prouve l’exécution de la version commitée, pas les modifications locales. Action nécessaire : exécuter la branche de travail actuelle sur un service PostgreSQL 15 via CI après intégration autorisée, ou sur un staging isolé, puis lancer `check`, `migrate` et pytest. Criticité : **CRITIQUE pour la version de travail non commitée**.

## 4. Concurrence

Les tests dans `backend/commerce/tests.py` sont inspectés :

| Test | DB / requêtes | Résultat Phase 5B | Statut |
|---|---|---|---|
| `test_deux_paiements_simultanes_sont_serialises_par_client` | `select_for_update`, 2 threads | Test absent du commit CI ; présent dans le working tree non testé sur PostgreSQL | NON VÉRIFIÉ |
| `test_ventes_simultanees_ne_peuvent_pas_depasser_le_stock` | verrouillage produit, 2 threads | Test absent du commit CI ; présent dans le working tree non testé sur PostgreSQL | NON VÉRIFIÉ |
| `test_idempotence_simultanee_ne_cree_qu_une_vente` | clé identique, 2 threads | Test absent du commit CI ; présent dans le working tree non testé sur PostgreSQL | NON VÉRIFIÉ |
| Correction de dette concurrente | Aucun test simultané dédié trouvé ; seul un test de correction de solde est présent | Test manquant à concevoir et exécuter sur PostgreSQL | NON VÉRIFIÉ |

Les trois tests de concurrence dans le working tree sont ignorés par `skipUnlessDBFeature("has_select_for_update")` sur SQLite. Le run CI réussi est sur un commit antérieur où ces tests n’existent pas. La quatrième exclusion est le test Redis conditionné par `REDIS_URL`. Les assertions de solde/stock dans le code des tests n’équivalent pas à une exécution sur cette version.

## 5. Redis

Redis 7 local non démarré ; `redis-cli` absent et `localhost:6379` non joignable. Le dernier workflow distant au commit `018e6a3` ne contient pas de service Redis ni `REDIS_URL`; le test du throttling partagé n’est pas prouvé. Le workflow local modifié déclare Redis 7, mais il n’est pas commité ni exécuté.

**NON VÉRIFIÉ.** Élément manquant : Redis réel partagé. Action : exécuter le test sous deux processus/workers pointant sur le même service Redis de staging/CI. Criticité : **CRITIQUE**.

## 6. Idempotence

Le test de vente avec clé idempotente simultanée existe dans le working tree, mais il n’a pas été exécuté sur cette version avec PostgreSQL. Le commit CI réussi ne contient pas ce test. Aucune preuve actuelle ne démontre une seule écriture métier pour deux requêtes concurrentes de la version de travail.

**NON VÉRIFIÉ. Criticité : CRITIQUE.**

## 7. CI GitHub

Run réel : [Qualité et intégration continue — run 36855898072](https://github.com/cephaceavocevou45-collab/gestions-commer-ants/actions/runs/36855898072), créé le 1er octobre 2026, commit `018e6a3ccafbd7ca359d8f73a3f9067d0630570f`. API GitHub : les jobs backend « Tests, couverture et Ruff » et frontend « ESLint et build Vite » sont `success`; chaque étape exposée dans ces jobs est `success`. Le détail stdout des logs n’a pas pu être téléchargé, donc nombre exact de tests/couverture du run distant non disponible.

Le workflow du commit distant utilise PostgreSQL 15 et lance pytest/Ruff ainsi que ESLint/build. Il ne déclare pas Redis et ne lance pas `pip-audit`, OpenAPI strict, le contrôle de migrations ou `npm audit`. Le workflow local modifié prévoit ces étapes, mais il est non commité et non testé par ce run.

**CONFIRMÉ pour le commit distant ; PARTIEL pour l’état actuel du working tree.** Criticité : **CRITIQUE pour obtenir un run de la version courante**.

## 8. OpenAPI strict

Commande réellement exécutée dans le virtualenv restauré : `python manage.py spectacular --validate --file <fichier temporaire>`. Résultat : succès, schéma de 111 830 octets. Le contrôle strict est également prévu dans le workflow local modifié, non présent dans le run CI distant.

**CONFIRMÉ localement ; CI du workflow courant NON VÉRIFIÉE.**

## 9. npm audit

Commande réellement exécutée avec réseau : `npm audit`. Résultat : **2 vulnérabilités modérées** dans `react-router` transitivement utilisé par `react-router-dom@6.30.6` : GHSA-wrjc-x8rr-h8h6 (open redirect via chemins de navigation contrôlés) et GHSA-337j-9hxr-rhxg (injection de constructeur en hydratation SSR). Les deux avis sont corrigés upstream à partir de React Router 7.18.0; npm propose `react-router-dom@7.18.4` et signale le saut majeur (`npm audit fix --force`). Le projet utilise `BrowserRouter`/`Routes` en mode déclaratif : l’avis SSR indique que son scénario ne s’applique pas au mode déclaratif. L’avis open redirect reste dans la dépendance et nécessite une revue des chemins de navigation. [Avis open redirect](https://github.com/advisories/GHSA-wrjc-x8rr-h8h6), [avis SSR](https://github.com/advisories/GHSA-337j-9hxr-rhxg).

**ÉTAT INITIAL : ÉCHEC de l’audit npm (2 avis modérés).** Correctif appliqué ensuite : `react-router-dom@7.18.4`, avec mise à jour de `package.json` et du lockfile. ESLint et le build Vite passent, puis `npm audit` confirme **0 vulnérabilité**. Les API de navigation déclarative existantes sont conservées.

## 10. pip-audit

Premier audit : `cryptography 49.0.0` signalé pour `PYSEC-2026-3552`, correction disponible en 50.0.0. Le projet n’utilise que Fernet, tandis que l’avis concerne les fonctions de déchiffrement PKCS#7 EnvelopedData ; le paquet était néanmoins dans une version vulnérable et la contrainte `<50` empêchait la correction. La contrainte a été portée à `cryptography>=50,<51`; l’environnement ignoré par Git utilise `50.0.2`. Second audit : `pip-audit -r requirements.txt` → **No known vulnerabilities found**. `pip check` → aucune dépendance cassée. L’avis officiel classe le problème Moderate et indique 50.0.0 comme version corrigée [advisory pyca/cryptography](https://github.com/pyca/cryptography/security/advisories/GHSA-g6cj-pr64-35w5).

**CONFIRMÉ : audit final propre après correction ciblée.**

## 11. Secrets

Les commits historiques `74d20cd`, `c7a6c23`, `018e6a3` contiennent des valeurs non vides dans les fichiers d’exemple. Les valeurs ne sont pas affichées. L’état d’accès fournisseur ne permet pas de confirmer une révocation ou une rotation. `git-filter-repo` n’a pas été détecté. Aucune purge n’a été tentée.

| Secret | Historique détecté | Rotation | Révocation | Nouveau secret actif |
|---|---|---|---|---|
| Django `SECRET_KEY` | CONFIRMÉ | NON VÉRIFIÉ | NON VÉRIFIÉ | NON VÉRIFIÉ |
| Identifiants PostgreSQL / `DATABASE_URL` | CONFIRMÉ | NON VÉRIFIÉ | NON VÉRIFIÉ | NON VÉRIFIÉ |
| Cloudinary | CONFIRMÉ | NON VÉRIFIÉ | NON VÉRIFIÉ | NON VÉRIFIÉ |
| Brevo/API email | CONFIRMÉ | NON VÉRIFIÉ | NON VÉRIFIÉ | NON VÉRIFIÉ |
| Signature JWT | Utilise la `SECRET_KEY` Django par défaut dans `SIMPLE_JWT` (aucun `SIGNING_KEY` spécifique configuré) | NON VÉRIFIÉ | NON VÉRIFIÉ | NON VÉRIFIÉ |

Cause : aucun accès fournisseur ni preuve de rotation avec les nouveaux credentials. Le `ls-remote` confirme que `main` et `origin/main` pointent au même commit, mais les blobs historiques restent présents. Action : rotation/révocation fournisseur, validation de service, copie miroir, puis purge préparée sans force-push automatique. Criticité : **CRITIQUE**.

## 12. Backup

Le code de `sauvegarde_db` a été inspecté : export Django, compression gzip, chiffrement Fernet, empreinte SHA-256 et envoi S3 avec chiffrement serveur si bucket configuré. En production, le bucket est exigé. Ces propriétés proviennent de la lecture du code, pas d’un backup réel. Aucune date, taille, empreinte ou destination d’un objet distant n’est disponible ; automatisation, rétention, fréquence et notification d’échec ne sont pas prouvées.

**NON VÉRIFIÉ.** Action : exécuter la commande avec une base PostgreSQL et stockage distant de test, puis vérifier l’objet, sa métadonnée de hash et sa politique de rétention. Criticité : **CRITIQUE**.

## 13. Restauration

La commande `restaure_db` a été inspectée ; elle déchiffre, décompresse et charge dans une transaction. Aucun backup PostgreSQL réel ni serveur PostgreSQL de staging/local n’étant disponible, aucune restauration réelle ni comparaison d’entités n’a été faite. La restauration SQLite de la phase précédente n’est pas une preuve PostgreSQL.

**NON VÉRIFIÉ.** Action : restaurer un backup de test dans une base PostgreSQL temporaire et comparer commerçants, clients, produits, ventes, dettes, paiements, abonnements et journaux d’audit. Criticité : **CRITIQUE**.

## 14. Cloudinary

Aucun accès à un compte Cloudinary de staging ni aucune preuve d’upload/récupération/remplacement/suppression réel dans cette session. Les clés historiques restent à traiter comme compromises.

**NON VÉRIFIÉ.** Action : effectuer les scénarios de fichiers valides, invalides, trop volumineux, erreur fournisseur, remplacement, suppression et recherche de fichiers orphelins. Criticité : **CRITIQUE**.

## 15. Staging

**STAGING NON DISPONIBLE / NON IDENTIFIÉ.** Aucun URL frontend/API de staging, service de base/Redis, bucket de test, ni domaine n’a été fourni ou rendu accessible. Aucun domaine ne sera supposé à partir d’une configuration ou d’un ancien déploiement.

Élément manquant : accès à un environnement isolé de staging et à ses comptes de test. Action : fournir/configurer les URLs et services staging, puis exécuter les validations qui suivent. Impact : bloque HTTPS, CORS/CSRF, cookies, headers, Cloudinary, E2E, XSS et tests multi-commerçants réels. Criticité : **CRITIQUE**.

## 16. HTTPS

Aucun endpoint staging n’étant disponible, certificat TLS, redirection HTTP, chaîne de certificat et transport du navigateur n’ont pas été vérifiés. Les réglages Django/Vercel ne constituent pas une preuve HTTP.

**NON VÉRIFIÉ.** Criticité : **CRITIQUE**.

## 17. CORS / CSRF

Aucune requête navigateur depuis une origine staging autorisée ou interdite, aucun preflight, et aucun essai de jeton CSRF valide/absent/invalide en environnement réel n’ont été exécutés.

**NON VÉRIFIÉ.** Criticité : **CRITIQUE**.

## 18. Cookies

Les tests/configurations locaux de la phase précédente ne prouvent pas l’émission réelle des cookies `Secure`, `HttpOnly`, `SameSite`, leurs durées, le refresh, la rotation ou le logout sur le domaine cible. Aucun DevTools navigateur de staging.

**NON VÉRIFIÉ.** Criticité : **CRITIQUE**.

## 19. Security Headers

Les configurations CSP/frame/nosniff existent dans le frontend, mais aucune réponse HTTP staging n’a été obtenue. Les valeurs réellement reçues pour CSP, HSTS, `X-Content-Type-Options`, `Referrer-Policy`, `Permissions-Policy` et clickjacking sont donc inconnues.

**NON VÉRIFIÉ en réel.** Criticité : **MAJEURE**.

## 20. XSS navigateur

La recherche statique et une sonde de rendu React sont des contrôles antérieurs, pas un test navigateur de champs client/produit/notes/QR/reçu. Aucun payload de test n’a été soumis à une application staging.

**NON VÉRIFIÉ en navigateur.** Criticité : **MAJEURE**.

## 21. Multi-tenancy réelle

Des tests backend locaux d’isolation et mass assignment sont documentés dans le rapport Phase 5. Aucun environnement réel avec commerces A et B n’a été accessible pour tester les verbes GET/POST/PUT/PATCH/DELETE et statistiques/audit par l’API déployée.

**PARTIEL (tests locaux antérieurs) ; NON VÉRIFIÉ en staging.** Criticité : **CRITIQUE**.

## 22. Parcours E2E

Aucun parcours navigateur login → produit → client → vente → dette → paiement → reçu → refresh → logout n’a été exécuté, faute de staging et d’accès navigateur vers le service déployé.

**NON VÉRIFIÉ.** Criticité : **CRITIQUE**.

## 23. Mobile

Aucun appareil réel ni émulation navigateur à 320, 375, 768 px n’a été testé durant cette phase.

**NON VÉRIFIÉ.** Action : parcourir les vues et opérations principales sur ces largeurs et appareil Android. Criticité : **MAJEURE**.

## 24. Accessibilité

Aucun contrôle clavier, focus, labels, contraste, titres, Axe ou Lighthouse n’a pu être conduit sur une interface déployée.

**NON VÉRIFIÉ.** Criticité : **MAJEURE**.

## 25. Performance PostgreSQL

Sans PostgreSQL et jeu de données de staging, aucun `EXPLAIN ANALYZE`, plan d’index, durée réelle ou mesure N+1 sur moteur cible n’est disponible. La pagination du dashboard et les tests locaux antérieurs ne démontrent pas la performance de production.

**NON VÉRIFIÉ.** Action : capturer les requêtes critiques tenant/date/statut sur des données représentatives et analyser leurs plans avant d’ajouter des index. Criticité : **MAJEURE**.

## 26. Tableau des 52 domaines

Les domaines sont repris de la grille Phase 5. Le rapport Phase 4 détaillé avec ses 52 statuts individuels reste indisponible dans les fichiers consultés ; aucun ancien statut n’est inventé. La preuve Phase 5B concerne les tests exécutés dans cette phase.

| # | Domaine | Test réel / preuve Phase 5B | Statut |
|---:|---|---|---|
| 1 | Transparence et règle absolue | Aucun push, force-push ou valeur sensible affichée | CONFIRMÉ |
| 2 | Périmètre produit | Aucun ajout fonctionnel commercial pendant la phase | CONFIRMÉ |
| 3 | Secrets et variables | Valeurs historiques identifiées, rotation non prouvée | ÉCHEC |
| 4 | Authentification | Suite actuelle relancée sur SQLite ; staging absent | PARTIEL |
| 5 | Autorisations et isolation | Tests backend locaux relancés ; API réelle indisponible | PARTIEL |
| 6 | Archivage/suppression clients | Suite locale passée sur SQLite ; PostgreSQL/staging absent | PARTIEL |
| 7 | Dettes et corrections | Suite locale passée ; correction concurrente non prouvée | PARTIEL |
| 8 | Paiements atomiques | Test de paiement concurrent identifié, non lancé sur PostgreSQL | NON VÉRIFIÉ |
| 9 | Idempotence financière | Test simultané identifié, non lancé sur PostgreSQL | NON VÉRIFIÉ |
| 10 | Ventes | Aucun parcours réel navigateur | NON VÉRIFIÉ |
| 11 | Stock et concurrence | Test identifié mais DB PostgreSQL inaccessible | NON VÉRIFIÉ |
| 12 | Archivage produits | Aucune validation DB dans 5B | NON VÉRIFIÉ |
| 13 | Pagination API | Suite locale actuelle réussie ; aucun test sur données PostgreSQL réelles | PARTIEL |
| 14 | Performance clients/N+1 | PostgreSQL indisponible, aucune mesure | NON VÉRIFIÉ |
| 15 | Index PostgreSQL | Aucun EXPLAIN possible | NON VÉRIFIÉ |
| 16 | QR et reçus | Aucun reçu staging scanné | NON VÉRIFIÉ |
| 17 | En-têtes de sécurité | Pas de réponse staging à relever | NON VÉRIFIÉ |
| 18 | CORS / CSRF | Contrôles backend locaux rejoués ; aucun domaine staging | PARTIEL |
| 19 | Rate limiting | Tests locaux passés sauf Redis partagé ; pas de Redis réel | PARTIEL |
| 20 | Validation des données | Suite backend locale actuelle réussie | PARTIEL |
| 21 | Calculs financiers | Tests locaux SQLite réussis ; pas de preuve PostgreSQL actuelle | PARTIEL |
| 22 | Concurrence financière | Quatre scénarios requis non prouvés ; test correction concurrente absent | NON VÉRIFIÉ |
| 23 | Abonnements | Tests backend locaux réussis ; aucune échéance staging suivie | PARTIEL |
| 24 | Journal d’audit | Tests d’audit backend locaux réussis ; pas d’événement staging | PARTIEL |
| 25 | Sauvegarde/restauration | Scripts inspectés seulement, aucun backup/restore exécuté | NON VÉRIFIÉ |
| 26 | Cloudinary | Tests locaux/mocks dans la suite ; aucun compte réel testé | PARTIEL |
| 27 | Token frontend | Tests locaux backend/session ; aucun test navigateur staging | PARTIEL |
| 28 | Dates/fuseaux | Tests locaux passés ; aucun test de DB/staging | PARTIEL |
| 29 | Décimales | Tests locaux SQLite passés ; PostgreSQL courant non testé | PARTIEL |
| 30 | Refresh après opération | Pas de parcours staging/browser | NON VÉRIFIÉ |
| 31 | Erreurs et UX | Aucun test des réponses API déployées | NON VÉRIFIÉ |
| 32 | Back-office et permissions | Tests backend locaux actuels réussis ; aucun compte admin staging | PARTIEL |
| 33 | Gestion des produits | Tests locaux passés ; parcours E2E non exécuté | PARTIEL |
| 34 | Suite de tests | 112 pass, 4 skip, 89,97 % sur SQLite après restauration Python | PARTIEL |
| 35 | Tests de sécurité | Suite sécurité locale passée ; aucun test navigateur staging | PARTIEL |
| 36 | Déploiement | Aucun staging accessible | NON VÉRIFIÉ |
| 37 | Dépendances | `pip-audit` précédemment propre après correction ciblée ; `npm audit` propre après mise à jour React Router | PARTIEL |
| 38 | Performance générale | Aucun test de charge ni plan PostgreSQL | NON VÉRIFIÉ |
| 39 | Accessibilité | Aucun audit navigateur | NON VÉRIFIÉ |
| 40 | Mobile | Aucun appareil ou viewport testé | NON VÉRIFIÉ |
| 41 | Liens/contenu publics | Aucun domaine public confirmé en staging | NON VÉRIFIÉ |
| 42 | Page publique / QR | Aucun endpoint déployé vérifié | NON VÉRIFIÉ |
| 43 | Architecture | Audits locaux exécutés sans changement d’architecture | CONFIRMÉ |
| 44 | Discipline de modification | Pas de refonte ni de changement applicatif 5B | CONFIRMÉ |
| 45 | Migrations | `makemigrations --check` local sans changement ; run CI ancien réussi ; pas de `migrate` courant en PG | PARTIEL |
| 46 | Données existantes | Aucune copie/restauration d’un dataset réel | NON VÉRIFIÉ |
| 47 | Contrat API/OpenAPI | `spectacular --validate` réussi localement ; CI actuelle non exécutée | PARTIEL |
| 48 | Absence d’invention | Limites et résultats non vérifiés explicitement indiqués | CONFIRMÉ |
| 49 | Priorisation des risques | Blocages classés par criticité technique ci-dessous | CONFIRMÉ |
| 50 | Tests finaux | pytest, Ruff, ESLint, build, migrations et OpenAPI relancés localement | PARTIEL |
| 51 | Critère production | Critères critiques encore non prouvés | CONFIRMÉ |
| 52 | Inspection initiale | Outils, branche, historique, statut et workflow inspectés | CONFIRMÉ |

## 27. Blocages critiques

### CRITIQUE

1. Rotation/révocation des secrets historiques non confirmée ; traiter les valeurs comme compromises.
2. Modifications présentes dans le working tree non exécutées dans un run PostgreSQL ; le CI réussi teste le commit antérieur.
3. Les nouveaux tests paiement/vente/idempotence concurrents ne sont pas dans le commit CI ; ils restent ignorés sur SQLite. Le test de correction concurrente manque.
4. Redis partagé et throttling multi-worker non vérifiés.
5. Backup distant et restauration PostgreSQL non exécutés.
6. Pas de run CI sur le workflow et les tests actuellement modifiés localement.
7. Aucun staging accessible pour HTTPS, cookies, CORS/CSRF, Cloudinary, isolation réelle et parcours E2E.

### MAJEUR

1. Le run CI du commit distant ne comprend pas pip-audit ni OpenAPI strict ; ces validations ont réussi localement, mais ne sont pas encore confirmées par le workflow courant.
2. En-têtes réels, XSS navigateur, mobile et accessibilité non contrôlés.
3. Plans de requêtes/performance PostgreSQL non mesurés.

### MINEUR

Aucun problème isolé classé mineur sur preuve suffisante durant cette phase ; les éléments non vérifiés ne sont pas reclassés mineurs par défaut.

## 28. Actions restantes

1. Faire tourner/révoquer les credentials historiques chez Django, PostgreSQL, Cloudinary et Brevo ; confirmer le résultat sans communiquer les valeurs.
2. Rendre accessibles PostgreSQL 15 et Redis 7 pour le working tree courant (Docker Desktop ou staging isolé). Les services locaux sont absents.
3. Autoriser ensuite un run CI de la version modifiée, ou exécuter les tests PostgreSQL/Redis dans l’environnement staging ; intégrer le test manquant de correction concurrente.
4. Effectuer un backup réel chiffré vers stockage distant, vérifier hash/rétention, puis restaurer dans PostgreSQL temporaire et comparer les entités.
5. La dépendance React Router a été mise à jour vers 7.18.4 ; lint, build et `npm audit` passent. Les parcours navigateur staging restent à exécuter.
6. Fournir les domaines et accès staging par variables d’environnement sécurisées (ne pas coller de secrets dans le chat), puis tester HTTPS, cookies, CORS/CSRF, headers, Cloudinary, XSS, isolation, E2E, mobile et accessibilité.
7. Après rotation seulement, préparer une copie miroir et une purge Git documentée. `git-filter-repo` n’a pas été trouvé ; aucun historique n’a été réécrit. Ne pas force-push sans autorisation explicite.

## 29. Verdict final

# NON PRÊT POUR LA PRODUCTION

Les contrôles locaux relancés sont positifs : pytest (SQLite), Ruff, migrations sans changement, OpenAPI strict, ESLint, build et `npm audit` (0 vulnérabilité). `pip-audit` avait confirmé l'absence d'avis après correction cryptography, mais le dernier relancement n'a pas pu aboutir faute de réponse du service d'audit. Le CI GitHub réussi sur `018e6a3` utilise PostgreSQL 15 mais ne teste pas le working tree actuel ni Redis. PostgreSQL/Redis courants, secrets, staging, sauvegarde/restauration et les contrôles navigateur restent ouverts. Le projet n'est donc pas encore prêt pour la production.
