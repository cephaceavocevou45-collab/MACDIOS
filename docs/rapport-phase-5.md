# NOBI — RAPPORT FINAL PHASE 5

Date du bilan : 2 octobre 2026. Ce rapport distingue les contrôles exécutés dans l’environnement local des contrôles qui nécessitent une infrastructure de staging. Aucun déploiement, push ou force-push n’a été effectué.

## 1. Résumé exécutif

Des vérifications locales et des corrections ciblées ont été effectuées : schéma OpenAPI documenté et vérifié par génération, pagination du tableau de bord bornée, tests de mass assignment et d’isolation renforcés, vérification des migrations, et contrôles frontend/backend relancés.

Résultats locaux : **112 tests réussis, 4 ignorés, couverture 89,97 %**, Ruff, ESLint et build Vite réussis. Cette exécution a utilisé SQLite. Les quatre tests ignorés couvrent Redis non configuré et `select_for_update` non pris en charge par SQLite. La génération OpenAPI est réussie, mais la validation stricte locale est bloquée par une erreur de dépendance Python (`rpds.rpds` absent). La CI modifiée n’a pas été exécutée sur GitHub.

Les preuves requises pour PostgreSQL réel, concurrence, Redis partagé, sauvegarde distante/restauration PostgreSQL, Cloudinary réel, staging HTTPS, audit navigateur et domaines réels ne sont pas disponibles. Des valeurs sensibles figurent encore dans l’historique Git des références `main` et `origin/main`; aucune rotation ni purge n’a été effectuée. **Le verdict demeure NON PRÊT POUR LA PRODUCTION.**

## 2. Environnement testé

| Élément | Environnement / résultat |
|---|---|
| Frontend | React/Vite, lint et build locaux réussis |
| Backend | Django, pytest local réussi sur SQLite |
| PostgreSQL | Non testé : aucun serveur PostgreSQL local accessible |
| Redis | Non testé : service non configuré |
| Cloudinary | Tests locaux/mock uniquement ; compte réel non vérifié |
| CI | Workflow modifié, aucun résultat de run GitHub récupéré |
| Staging | Aucun staging réel identifié et testé |
| Navigateur | Aucun parcours de sécurité complet en navigateur/staging |

## 3. Tests exécutés

| Test | Environnement | Résultat | Preuve | Statut |
|---|---|---|---|---|
| `pytest` avec couverture | Python local, SQLite | 112 pass, 4 skip, 89,97 % | Exécution finale : 116 collectés, 32,57 s ; seuil 80 % atteint | CONFIRMÉ (SQLite seulement) |
| Ruff | Local | Réussi | `ruff check --no-cache .` | CONFIRMÉ |
| ESLint | Local | Réussi | `npm run lint` | CONFIRMÉ |
| Build frontend | Local | Réussi | `npm run build`, Vite 6.4.3 | CONFIRMÉ |
| Migrations | Configuration SQLite mémoire | Aucune migration manquante | `manage.py makemigrations --check --dry-run --skip-checks` | CONFIRMÉ (détection locale seulement) |
| Génération OpenAPI | Django local | Générée sans erreur de schéma | Test de schéma ciblé et génération | CONFIRMÉ |
| OpenAPI strict | Django local | Bloqué | `manage.py spectacular --validate` échoue avant validation : `ModuleNotFoundError: rpds.rpds` | ÉCHEC (outil local) |
| `npm audit` | Réseau local | Non abouti | Registre npm inaccessible | NON VÉRIFIÉ |
| `pip-audit` | Local | Non abouti | Outil absent et installation/réseau non disponible | NON VÉRIFIÉ |
| CI GitHub réelle | Distant | Résultat non récupéré | `gh` absent ; consultation web non concluante | NON VÉRIFIÉ |
| Vérification de patch | Local | Réussie | `git diff --check` | CONFIRMÉ |

## 4. PostgreSQL

La suite finale a utilisé SQLite, pas PostgreSQL. L’absence de PostgreSQL 15 accessible empêche de confirmer les migrations et les opérations financières sur le moteur cible. Le workflow CI contient un service PostgreSQL 15, mais le résultat d’un run réel n’a pas été consulté. À exécuter sur staging/CI avant décision : migrations, tests complets, contraintes, données financières et requêtes avec `EXPLAIN ANALYZE`.

**Statut : NON VÉRIFIÉ.**

## 5. Concurrence

Trois tests reposant sur `select_for_update` sont ignorés sous SQLite. Ils doivent être exécutés sur PostgreSQL avec deux requêtes concurrentes de paiement et de vente, puis vérifier solde, stock, absence de doublon et absence de valeur négative. Aucune mesure PostgreSQL n’est disponible.

**Statut : NON VÉRIFIÉ.**

## 6. Redis

Le test nécessitant Redis est ignoré car aucun Redis réel n’est configuré. Le workflow déclare un service Redis 7, mais il n’y a pas de résultat CI prouvant le throttling partagé entre workers/processus.

**Statut : NON VÉRIFIÉ.**

## 7. Idempotence

Les protections et tests locaux sont présents, mais l’idempotence concurrente n’a pas été exercée sur PostgreSQL ni sur plusieurs processus. Une validation exige deux requêtes simultanées avec la même clé et la preuve d’une seule opération comptable.

**Statut : PARTIEL.**

## 8. Sauvegardes

La commande de sauvegarde chiffre et prépare un transfert distant selon la configuration, mais aucun backup distant réel, politique de rétention, fréquence planifiée ni notification d’échec n’a été vérifié dans cette phase.

| Contrôle | Résultat |
|---|---|
| Backup PostgreSQL réel | NON VÉRIFIÉ |
| Stockage distant réel | NON VÉRIFIÉ |
| Chiffrement / intégrité | Présents dans le mécanisme local ; validation de l’objet distant NON VÉRIFIÉE |
| Rétention / fréquence / alerte | NON VÉRIFIÉES |

## 9. Restauration

Une restauration SQLite avait été vérifiée dans la phase précédente. Aucun backup PostgreSQL réel n’a été restauré en base PostgreSQL temporaire durant cette phase ; les données avant/après, taille, hash et durée ne peuvent donc pas être attestés.

**Statut : PARTIEL pour SQLite ; NON VÉRIFIÉ pour PostgreSQL.**

## 10. Sécurité

Les tests locaux couvrent l’authentification, les sessions JWT/CSRF, l’isolation et des tentatives de mass assignment. Le frontend ne lit ni ne stocke les JWT dans `localStorage`/`sessionStorage`; les résultats de recherche montrent seulement la suppression d’anciennes clés et la persistance du profil commerçant. Les cookies et CSRF ont des tests locaux, sans preuve navigateur/staging. Les actions réelles admin, les en-têtes servis et la résistance multi-instance restent à vérifier.

**Statut global : PARTIEL.**

## 11. Secrets

L’inspection de l’historique trouve des affectations non vides dans des fichiers d’exemple aux commits `74d20cd`, `c7a6c23` et `018e6a3`. Types concernés : clé Django, URL/identifiants PostgreSQL, clés Cloudinary et clé Brevo. Les valeurs ne sont pas reproduites ici. Elles doivent être traitées comme compromises jusqu’à rotation et révocation confirmées.

Les `.env.example` du working tree ont des champs de secrets vides/placeholders. Cela ne nettoie pas les blobs des références Git `main` et `origin/main`. Aucun credential n’a été roté, aucun ancien credential n’a été révoqué et aucun historique n’a été réécrit. Les références inspectées sont `main` et `origin/main`; aucune étiquette Git n’a été trouvée. `git-filter-repo` n’est pas installé.

**Statut : ÉCHEC / BLOQUANT.** Aucun secret n’est affiché. La purge ne doit avoir lieu qu’après rotation, vérification des nouveaux credentials et accord explicite pour la réécriture coordonnée des clones. Aucun force-push n’a été fait.

## 12. OpenAPI

Corrections effectuées : schéma d’authentification cookie documenté, sécurité globale excessive retirée au profit d’une extension ciblée, réponses et pagination documentées, refresh précisé comme cookie-only, paramètres de vues et tests de schéma ajoutés. La génération et le test ciblé réussissent. La commande stricte échoue localement avant validation à cause du module `rpds.rpds` manquant. Une étape `spectacular --validate` a été ajoutée à la CI, sans run distant confirmé.

**Génération : CONFIRMÉE. Validation stricte CI : NON VÉRIFIÉE.**

## 13. Dépendances

`npm audit` n’a pas pu joindre le registre npm. `pip-audit` n’a pas été exécuté car l’outil n’est pas disponible et son installation n’a pas pu être vérifiée. Aucune conclusion d’absence de vulnérabilités ne peut être tirée.

**Statut : NON VÉRIFIÉ.**

## 14. Cloudinary

Les tests locaux/mock peuvent vérifier les validations et le code de stockage, mais upload, lecture, suppression, remplacement, échec fournisseur et fichiers orphelins sur un compte staging n’ont pas été testés. Les secrets Cloudinary historiques sont concernés par la rotation requise.

**Statut : NON VÉRIFIÉ en réel.**

## 15. HTTPS / CORS / CSRF / cookies

Les réglages et tests locaux existent. Aucun navigateur sur un domaine staging HTTPS n’a été utilisé pour relever cookies `Secure`, `HttpOnly`, `SameSite`, rotation/révocation, préflight CORS, CSRF valide/invalide et redirection HTTP→HTTPS. Le nom de domaine réel du frontend n’est pas confirmé dans les éléments accessibles.

**Statut : NON VÉRIFIÉ en staging.**

## 16. Security Headers

Les configurations Vercel et Nginx contiennent des directives de protection (CSP, frame denial, nosniff et autres). Aucun relevé de réponse HTTP réelle sur staging n’a été obtenu. La présence de configuration ne prouve pas les en-têtes effectivement servis.

**Statut : PARTIEL.**

## 17. XSS navigateur

La recherche statique n’a trouvé aucun usage de `dangerouslySetInnerHTML`, `innerHTML`, `eval` ou équivalent dans les chemins analysés. Une sonde React isolée a confirmé l’échappement du texte par React. Aucun parcours navigateur réel avec les champs malveillants énumérés n’a été effectué.

**Statut : PARTIEL.**

## 18. Multi-tenancy

Les tests locaux SQLite confirment les lectures protégées, les refus de relations étrangères, des écritures croisées, et des tentatives d’affectation de propriétaire/rôle/solde. Les tests ont été renforcés pour les routes de détail et champs forgés. Ce n’est pas une preuve de test end-to-end sur PostgreSQL ni dans le navigateur.

**Statut : CONFIRMÉ localement, PARTIEL en conditions réelles.**

## 19. Tests frontend

ESLint et build réussis. Aucun test automatisé de composants/parcours frontend n’a été exécuté dans ce bilan.

**Statut : PARTIEL.**

## 20. Mobile

Aucun test réel sur appareil Android, tablette ou tailles d’écran définies n’a été réalisé durant cette phase.

**Statut : NON VÉRIFIÉ.**

## 21. Accessibilité

Aucun audit navigateur avec clavier, contraste ou outil d’accessibilité n’a été exécuté.

**Statut : NON VÉRIFIÉ.**

## 22. CI/CD

Le workflow a été mis à jour avec PostgreSQL 15, Redis 7 et validation OpenAPI stricte. Ruff, tests, audit dépendances, lint et build figurent dans le pipeline. Le run GitHub réel n’a pas pu être récupéré ; le workflow contient des modifications locales non poussées. Il est donc impossible de déclarer la CI verte.

**Statut : NON VÉRIFIÉ.**

## 23. Audit des 52 domaines

Le statut Phase 4 ci-dessous est reconstitué à partir du bilan Phase 4 joint et des résultats résumés qui y figurent. Le rapport détaillé Phase 4 avec ses 52 statuts ligne par ligne n’est pas présent dans les fichiers accessibles du dépôt ; les cellules Phase 4 ne prétendent donc pas reproduire un ancien tableau inaccessible. Les 52 domaines sont conservés et les statuts Phase 5 reposent sur les preuves listées ici. Les mentions « CONFIRMÉ local » ne valent pas preuve de production.

| N° | Domaine | Statut Phase 4 | Preuve Phase 5 | Nouveau statut | Action restante |
|---:|---|---|---|---|---|
| 1 | Règle absolue / transparence | CONFIRMÉ | Limites explicites dans ce rapport ; aucun push | CONFIRMÉ | Maintenir cette discipline |
| 2 | Objectif métier / périmètre | CONFIRMÉ | Aucun ajout fonctionnel commercial | CONFIRMÉ | Aucune |
| 3 | Secrets et variables d’environnement | ÉCHEC | Historique contient des valeurs non vides | ÉCHEC | Rotation puis purge coordonnée |
| 4 | Authentification | CONFIRMÉ local | Tests de session/JWT locaux ; pas de navigateur réel | PARTIEL | Parcours staging complet |
| 5 | Autorisations et isolation | CONFIRMÉ local | Tests étrangers/forgés renforcés, SQLite | PARTIEL | Rejouer PostgreSQL et frontend |
| 6 | Suppression/archivage clients | CONFIRMÉ local | Tests existants, suite locale verte | PARTIEL | Valider PostgreSQL et rétention |
| 7 | Dettes et corrections | CONFIRMÉ local | Couvert par suite locale | PARTIEL | Vérifier sur PostgreSQL |
| 8 | Paiements atomiques | CONFIRMÉ local | Verrouillage testé/ignoré sous SQLite | PARTIEL | Concurrence PostgreSQL |
| 9 | Idempotence financière | CONFIRMÉ local | Tests locaux, pas de concurrence multi-processus | PARTIEL | Test concurrent PostgreSQL |
| 10 | Ventes | CONFIRMÉ local | Suite locale verte | PARTIEL | Parcours staging end-to-end |
| 11 | Stock et concurrence | PARTIEL | Test `select_for_update` ignoré sous SQLite | NON VÉRIFIÉ | Vente simultanée PostgreSQL |
| 12 | Suppression produits | CONFIRMÉ local | Archivage et tests locaux | PARTIEL | Vérifier cohérence PostgreSQL |
| 13 | Pagination API | CONFIRMÉ | Tests de pagination ; liste dashboard plafonnée à 100 + total | CONFIRMÉ local | Vérifier volume réel |
| 14 | Performance clients/N+1 | CONFIRMÉ local | Pas de mesure PostgreSQL durant cette phase | PARTIEL | Mesurer requêtes sur données représentatives |
| 15 | Index PostgreSQL | PARTIEL | Aucun `EXPLAIN ANALYZE` réel | NON VÉRIFIÉ | Audit PostgreSQL avant ajout d’index |
| 16 | QR et reçus | CONFIRMÉ local | Tests locaux ; pas de scan réel en staging | PARTIEL | Vérifier domaine/scan public |
| 17 | En-têtes sécurité | PARTIEL | Configs existent ; headers HTTP non relevés | PARTIEL | `curl`/DevTools staging |
| 18 | CORS / CSRF | CONFIRMÉ local | Tests locaux ; domaine staging absent | PARTIEL | Tester domaines réels et preflight |
| 19 | Rate limiting | CONFIRMÉ local | Pas de Redis partagé réel | PARTIEL | Tester limites multi-instance |
| 20 | Validation des données | CONFIRMÉ local | Tests de validation existants | PARTIEL | Rejouer intégration PostgreSQL |
| 21 | Calculs monétaires | CONFIRMÉ local | Suite locale verte | PARTIEL | Comparer parcours et montants PostgreSQL |
| 22 | Concurrence financière | NON VÉRIFIÉ | 3 tests ignorés sous SQLite | NON VÉRIFIÉ | Exécuter sur PostgreSQL |
| 23 | Abonnements | CONFIRMÉ local | Tests locaux ; tâche réelle non observée | PARTIEL | Tester staging et cron |
| 24 | Journal d’audit | CONFIRMÉ local | Tests locaux, y compris isolation | PARTIEL | Vérifier actions réelles admin |
| 25 | Sauvegarde et restauration | PARTIEL | Restauration SQLite antérieure ; pas de backup PostgreSQL distant | NON VÉRIFIÉ | Backup + restauration PostgreSQL |
| 26 | Cloudinary | PARTIEL | Tests/mock ; aucun compte réel vérifié | NON VÉRIFIÉ | Parcours upload complet sur staging |
| 27 | Frontend / token | CONFIRMÉ local | Aucun JWT lu/stocké dans Web Storage trouvé | PARTIEL | Test navigateur login/refresh/logout |
| 28 | Dates et fuseaux | CONFIRMÉ local | Suite locale seulement | PARTIEL | Tester fuseaux et échéances staging |
| 29 | Décimales | CONFIRMÉ local | Tests locaux seulement | PARTIEL | Valider données/arrondis PostgreSQL |
| 30 | Refresh après vente | CONFIRMÉ local | Tests locaux seulement | PARTIEL | Parcours navigateur réel |
| 31 | Erreurs et expérience utilisateur | CONFIRMÉ local | Pas de tests UI pour chaque statut HTTP | PARTIEL | Tester erreurs API en navigateur |
| 32 | Back-office et permissions | CONFIRMÉ local | Tests backend locaux | PARTIEL | Vérifier rôles en staging |
| 33 | Gestion produits | CONFIRMÉ local | Suite locale + pagination | PARTIEL | Parcours réel mobile/desktop |
| 34 | Suite de tests | CONFIRMÉ | 112 pass, 4 skip, 89,97 % | CONFIRMÉ local | Faire tourner la suite PostgreSQL/Redis |
| 35 | Tests sécurité | CONFIRMÉ local | Mass assignment/isolation renforcés | PARTIEL | DAST et tests staging |
| 36 | Déploiement | NON VÉRIFIÉ | Aucun staging déployé ici | NON VÉRIFIÉ | Déployer et valider staging |
| 37 | Dépendances | NON VÉRIFIÉ | npm audit réseau indisponible ; pip-audit absent | NON VÉRIFIÉ | Exécuter les deux audits |
| 38 | Performance | PARTIEL | Dashboard rupture borné ; pas de charge/SQL plan | PARTIEL | Profilage sous charge représentative |
| 39 | Accessibilité | NON VÉRIFIÉ | Aucun audit clavier/contraste | NON VÉRIFIÉ | Audit WCAG navigateur |
| 40 | Mobile | PARTIEL | Responsive dans le code ; aucun vrai appareil testé | NON VÉRIFIÉ | Android étroit/tablette/desktop |
| 41 | Contenu et liens publics | PARTIEL | Domaine réel non confirmé | PARTIEL | Vérifier liens et coordonnées avant publication |
| 42 | Page publique/QR | PARTIEL | Schéma et tests locaux ; URL réelle non vérifiée | PARTIEL | Scanner QR sur staging |
| 43 | Architecture | CONFIRMÉ | Stack et séparation restent cohérentes | CONFIRMÉ | Aucune |
| 44 | Règles de changement | CONFIRMÉ | Modifications ciblées, aucun historique réécrit | CONFIRMÉ | Revue avant intégration |
| 45 | Migrations | CONFIRMÉ local | `makemigrations --check` sans changement | PARTIEL | Appliquer sur vraie base PostgreSQL |
| 46 | Données existantes | PARTIEL | Aucun dataset production exporté/importé | NON VÉRIFIÉ | Répétition sur copie anonymisée |
| 47 | Format de réponse API | CONFIRMÉ | Pagination et réponses OpenAPI couvertes | PARTIEL | Vérification stricte bloquée localement |
| 48 | Absence de données inventées | CONFIRMÉ | Valeurs historiques masquées, chiffres marqués comme tests | CONFIRMÉ | Maintenir |
| 49 | Priorisation des risques | CONFIRMÉ | Secrets et infrastructure signalés comme bloquants | CONFIRMÉ | Traiter les blocages dans l’ordre |
| 50 | Tests finaux | CONFIRMÉ local | pytest, Ruff, ESLint, build exécutés | PARTIEL | Relancer dans CI PostgreSQL/Redis |
| 51 | Critère de production | CONFIRMÉ | Critères critiques toujours non prouvés | CONFIRMÉ | Ne pas déclarer prêt avant preuves |
| 52 | Démarrage de la phase | CONFIRMÉ | Dépôt, branche, historique et changements inspectés | CONFIRMÉ | Aucune |

## 24. Blocages restants

1. Secrets historiques non rotés et présents dans les refs Git.
2. Aucun run de validation PostgreSQL 15 + Redis 7 consulté.
3. Concurrence réelle et idempotence multi-processus non prouvées.
4. Backup distant et restauration PostgreSQL non testés.
5. `npm audit` et `pip-audit` non aboutis.
6. Validation stricte OpenAPI et CI GitHub non confirmées.
7. Cloudinary réel, staging, domaines, HTTPS, cookies, CORS/CSRF et headers réels non vérifiés.
8. Parcours navigateur, XSS, mobile et accessibilité non audités.

## 25. Actions avant production

1. Révoquer/renouveler les secrets cités, vérifier les nouveaux et confirmer que les anciens ne fonctionnent plus.
2. Préparer une purge avec `git-filter-repo --replace-text` dans un clone miroir après rotation ; coordonner les contributeurs. Ne réécrire/pousser l’historique qu’après validation explicite.
3. Installer un staging avec PostgreSQL 15, Redis 7, Cloudinary, domaines et HTTPS réels.
4. Exécuter migrations et toute la suite sur les vrais services ; retirer les skips dus à SQLite et prouver les scénarios concurrents.
5. Faire un backup PostgreSQL distant chiffré, puis le restaurer dans une base temporaire et comparer les entités listées dans le protocole.
6. Exécuter `npm audit`, `pip-audit` et `manage.py spectacular --validate`; récupérer le run GitHub Actions réel.
7. Tester headers/cookies/CORS/CSRF, QR, upload, XSS, parcours de vente et dette, appareils mobiles et accessibilité dans le navigateur.
8. Ne promouvoir en production qu’après résolution des bloquants et conservation des preuves de staging.

## 26. Verdict final

### NON PRÊT POUR LA PRODUCTION

Les vérifications locales sont encourageantes, mais plusieurs critères critiques de la Phase 5 exigent des preuves réelles absentes, en particulier la rotation des secrets, PostgreSQL, Redis, concurrence financière, sauvegarde/restauration, dépendances auditées et staging HTTPS. La couverture SQLite ne remplace pas ces validations. Aucun secret, jeton ou credential n’est exposé dans ce rapport.
