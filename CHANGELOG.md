# Historique des changements

Les changements notables du projet sont consignés dans ce fichier.

## [Préparation de livraison] — 2026-11-18

- L'audit de CI vérifie les vulnérabilités hautes des dépendances JavaScript de production. L'avis `GHSA-fc5q-39xc-vjpf` sur `picomatch` reste connu dans les outils de build (Vite/Tailwind) sans version corrigée annoncée; il est documenté et suivi séparément.
- Les tests ciblés de concurrence PostgreSQL ne comptent plus leur couverture isolée contre le seuil global de 80 %; la suite complète garde le seuil.

## [0.5.0] — 2026-09-30

- Dette technique connue : vulnérabilité DoS faible impact dans braces (dépendance transitive de Tailwind 3). Aucun correctif publié à ce jour. Migration vers Tailwind 4 à planifier séparément, hors urgence, car impact limité au build et sans correctif disponible pour corriger autrement.
- PostgreSQL est désormais la base de données attendue en développement et en production via `DATABASE_URL`.
- Les preuves de paiement sont stockées sur Cloudinary comme ressources authentifiées, avec validation des formats et de la taille.
- Le paiement automatique et son webhook ont été retirés; l'historique antérieur est conservé sous un modèle générique.
- Ajout des commandes interactives de création du premier Super Admin et d'expiration planifiée des abonnements.

## [0.4.0] — 2026-09-29

- Validation stricte des numéros béninois au format `+229` et migration des anciens numéros compatibles.
- Récupération du mot de passe par lien Django à usage unique expirant après 15 minutes (journalisé en développement, sans envoi SMS).
- Ajout des corrections de dettes historisées et auditées, ainsi que des reçus PDF privés par commerçant.

## [0.3.0] — 2026-09-28

- Renforcement de l'authentification : limitation des requêtes sensibles, verrouillage temporaire après échecs et validation stricte des mots de passe.
- Ajout du journal d'audit en lecture seule, filtré par commerçant, et des événements liés aux ventes, au stock, aux dettes et aux paiements.
- Ajout du contrôle de santé, de l'export et de la suppression complète du compte, et du consentement enregistré à l'inscription.
- Ajout du filtrage Sentry, des journaux JSON en production et de la commande de sauvegarde de la base.
- Ajout des pages de confidentialité, des conditions et de l'historique d'activité.

## [0.2.0] — 2026-09-28

- Ajout des abonnements Mobile Money soumis à vérification administrative et de l'accès en lecture seule après expiration.
- Ajout de la documentation OpenAPI, de la couverture pytest, de Docker Compose et de la CI.
- Ajout des données de démonstration et de la documentation de contribution.

## [0.1.0] — 2026-09-28

- Première version du MVP : produits, stock, ventes, clients, dettes et tableau de bord.
