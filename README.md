<p><strong>English</strong>: Nobi is a mobile-first shop management MVP for small retailers. Track sales, stock, customers and customer debts with a Django REST API and a lightweight React application.</p>

# Nobi — Gestion simple de commerce

> Gérer ventes, stock et dettes depuis un téléphone, avec une interface conçue pour les petits commerçants francophones.

[![CI](https://github.com/[À_COMPLÉTER]/[À_COMPLÉTER]/actions/workflows/ci.yml/badge.svg)](https://github.com/[À_COMPLÉTER]/[À_COMPLÉTER]/actions/workflows/ci.yml)
[![Couverture](https://img.shields.io/badge/couverture-[À_COMPLÉTER]-gray)](backend/htmlcov/index.html)
[![Licence MIT](https://img.shields.io/badge/licence-MIT-green.svg)](LICENSE)

**Démo :** [À COMPLÉTER] · **Documentation API :** `http://localhost:8000/api/docs/`

## Problème et solution

Les petits commerçants suivent souvent ventes, quantités et crédits clients de mémoire ou dans des cahiers. Nobi rassemble ces opérations dans une application lisible sur téléphone : le commerçant saisit les ventes et les mouvements de dettes, puis consulte ses stocks et récapitulatifs.

Nobi est un MVP en construction. Toute donnée de démonstration créée par `seed_demo` est synthétique ; aucun chiffre d'utilisation ou résultat commercial n'est revendiqué.

## Fonctionnalités

- Inscription et connexion par email avec jetons JWT; téléphone de contact facultatif.
- Catalogue produits et quantités en stock, avec seuil d'alerte.
- Enregistrement de ventes avec contrôle de stock et décrément atomique.
- Fiches clients, dettes, paiements et soldes calculés.
- Tableau de bord jour/semaine/mois et alertes de stock.
- Essai de 14 jours, paiement Mobile Money manuel vérifié depuis l'administration et lecture seule après expiration.
- Accès aux données limité au commerçant authentifié.
- Journal d'activité en lecture seule, export PDF lisible et suppression confirmée par mot de passe.
- Consentement enregistré à l'inscription et documents juridiques modèles dans l'application.
- Limitation des tentatives, verrouillage temporaire des connexions et health check.
- Validation stricte du numéro béninois, récupération à usage unique du mot de passe et reçus PDF de dettes avec corrections historisées.

## Stack technique

| Partie | Technologies |
| --- | --- |
| API | Django, Django REST Framework, JWT, drf-spectacular |
| Données | PostgreSQL avec `DATABASE_URL` en développement et en production |
| Interface | React, Vite, Tailwind CSS, React Router, Axios |
| Qualité | pytest, pytest-django, pytest-cov, Ruff, ESLint |
| Conteneurs | Docker, Docker Compose, Gunicorn, Nginx |

### Architecture

```mermaid
flowchart LR
    U[Commerçant sur Android] -->|HTTPS / JSON| F[React + Vite servi par Nginx]
    F -->|JWT / REST| A[Django REST Framework]
    A --> D[(PostgreSQL)]
    A -->|Preuves privées| C[Cloudinary]
    G[GitHub Actions] -->|Lint, tests, couverture, build| A
    G --> F
```

## Captures d'écran

Ajouter les captures dans `docs/screenshots/` :

- Tableau de bord : `docs/screenshots/tableau-de-bord.png`
- Produits et stock : `docs/screenshots/produits.png`
- Saisie d'une vente : `docs/screenshots/ventes.png`
- Clients et dettes : `docs/screenshots/clients.png`
- Abonnement : `docs/screenshots/abonnement.png`

## Installation en 5 minutes

### Avec Docker Compose

Prérequis : Docker Desktop avec Docker Compose v2.24 ou supérieur.

```bash
cp .env.example .env
docker compose up --build
```

Sous PowerShell, utilisez `Copy-Item .env.example .env`, puis renseignez `NUMERO_MTN`, `NUMERO_MOOV` et/ou `NUMERO_CELTIIS` dans ce `.env` à la racine. Docker Compose transmet ces valeurs au backend. Après une modification, recréez le backend avec `docker compose up -d --build backend`. Modifiez `SECRET_KEY`, `POSTGRES_PASSWORD` et `DATABASE_URL` avant tout déploiement. L'interface s'ouvre sur `http://localhost:8080`, l'API sur `http://localhost:8000`.

### Sans Docker

Prérequis : Python 3.12 ou plus récent, Node.js 22 et npm.

```bash
cd backend
python -m venv .venv
# Windows : .venv\Scripts\Activate.ps1
# macOS / Linux : source .venv/bin/activate
python -m pip install -r requirements-dev.txt
Copy-Item .env.example .env  # PowerShell; sous macOS/Linux : cp .env.example .env
# Renseignez les variables NUMERO_MTN, NUMERO_MOOV et/ou NUMERO_CELTIIS dans backend/.env.
python manage.py migrate
python manage.py runserver
```

Dans un second terminal :

```bash
cd frontend
npm ci
Copy-Item .env.example .env.local  # PowerShell; sous macOS/Linux : cp .env.example .env.local
npm run dev
```

PostgreSQL est requis en développement comme en production. Installez PostgreSQL localement (Windows : installateur PostgreSQL officiel, Linux : paquet `postgresql`), démarrez le service, puis créez une base et un utilisateur depuis `psql` ou pgAdmin. Exemple SQL :

```sql
CREATE USER nobi WITH PASSWORD 'choisir-un-secret-local';
CREATE DATABASE nobi OWNER nobi;
```

Dans `backend/.env`, configurez `DATABASE_URL=postgresql://nobi:choisir-un-secret-local@127.0.0.1:5432/nobi`. Une URL locale dans Docker Compose doit utiliser le nom de service `db` au lieu de `127.0.0.1`. Si le mot de passe contient des caractères réservés d'URL (`@`, `:`, `/`, `#`), encodez-les en pourcentage. Puis lancez `python manage.py migrate`.

## Variables d'environnement

Le fichier `.env.example` à la racine documente la configuration Docker Compose. Pour un lancement Django sans Docker, les variables vont dans `backend/.env` (modèle : `backend/.env.example`). Ces fichiers `.env` ne doivent pas être commités. Django doit être redémarré après leur modification.

| Variable | Rôle |
| --- | --- |
| `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS` | Sécurité et mode Django |
| `CORS_ALLOWED_ORIGINS`, `FRONTEND_URL`, `PUBLIC_FRONTEND_URL`, `VITE_API_URL` | Communication navigateur/API et base du lien public de vérification des reçus |
| `DATABASE_URL` | URL PostgreSQL de Django (`postgresql://utilisateur:mot_de_passe@hôte:5432/base`) |
| `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` | Identifiants du service PostgreSQL Docker Compose ; garder ces valeurs alignées sur `DATABASE_URL` |
| `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET` | Accès privé du stockage de preuves Cloudinary, backend uniquement |
| `NUMERO_MTN`, `NUMERO_MOOV`, `NUMERO_CELTIIS` | Numéros Mobile Money privés affichés selon l'opérateur configuré; une option vide est masquée |
| `SENTRY_DSN`, `VITE_SENTRY_DSN` | DSN Sentry facultatifs, aucun événement transmis si vides |
| `SECURE_SSL_REDIRECT`, `SECURE_HSTS_SECONDS`, `CSRF_TRUSTED_ORIGINS` | Réglages HTTPS et origine CSRF en production |
| `LOG_LEVEL` | Niveau des logs JSON en production |
| `SMS_SIMULATION` | Simule les SMS sans appel payant (`True` par défaut) |
| `VONAGE_API_KEY`, `VONAGE_API_SECRET` | Identifiants privés du compte Vonage, backend uniquement |
| `VONAGE_SMS_SENDER` | Nom d'expéditeur déclaré dans Vonage et autorisé par les opérateurs |
| `EMAIL_SIMULATION` | Simule les emails sans appel fournisseur (`True` par défaut) |
| `BREVO_API_KEY` | Clé privée Brevo, uniquement dans l'environnement backend |
| `BREVO_SENDER_EMAIL`, `BREVO_SENDER_NAME` | Adresse et nom de l'expéditeur Brevo vérifié |

Ne commitez jamais les fichiers `.env`. Les identifiants Cloudinary restent exclusivement côté backend.

### Paiement manuel de l'abonnement

Le paiement d'abonnement est manuel. Configurez au moins un des numéros `NUMERO_MTN`, `NUMERO_MOOV` ou `NUMERO_CELTIIS`. Le commerçant transfère le montant exact du plan, puis transmet la référence reçue par SMS et une capture d'écran facultative (JPEG, PNG ou WEBP, maximum 5 Mo). Les preuves sont envoyées à Cloudinary comme ressources authentifiées ; le backend produit un téléchargement signé temporaire seulement après contrôle de l'accès commerçant ou administrateur. Le disque éphémère de Render n'est ainsi pas utilisé pour les fichiers reçus.

Dans l'administration Django, ouvrez **Demandes de paiement manuel**. Les actions « Valider les demandes sélectionnées » et « Rejeter les demandes sélectionnées » enregistrent l'administrateur et la date dans le journal d'audit. Le rejet demande un motif, envoyé au commerçant par email. Une validation active le plan pour sa durée, envoie un email de confirmation et permet au commerçant de télécharger un reçu PDF certifié avec QR code.

### Preuves déjà enregistrées sur disque

Avant de retirer l'ancien volume `media` ou de déployer la version Cloudinary, configurez les identifiants Cloudinary, gardez l'ancien répertoire accessible et exécutez depuis `backend/` :

```bash
python manage.py migrer_preuves_cloudinary --repertoire-source /chemin/vers/ancien-media
```

Sous PowerShell, le chemin peut être `D:\\...\\gestion-commerçants\\backend\\media` ou la racine du volume média Docker monté. La commande migre les preuves locales encore présentes, met à jour leurs chemins, puis supprime les copies locales migrées. Elle affiche un compte des fichiers absents afin de signaler les pertes déjà survenues sur un disque éphémère. Créez un compte Cloudinary et renseignez les trois variables ci-dessus avant l'exécution.

## API

- Schéma OpenAPI : [`/api/schema/`](http://localhost:8000/api/schema/)
- Swagger UI : [`/api/docs/`](http://localhost:8000/api/docs/)
- Redoc : [`/api/redoc/`](http://localhost:8000/api/redoc/)

Les routes sont regroupées par domaines : Auth, Tableau de bord, Produits, Ventes, Clients et Abonnement. Les opérations protégées utilisent `Authorization: Bearer <access-token>`.

Routes de sécurité et de données : `GET /api/sante/`, `GET /api/audit/`, `GET /api/compte/export/` (téléchargement d'un PDF paginé des données du compte) et `DELETE /api/compte/` (confirmation par `mot_de_passe`). Le journal accepte `action`, `date_debut`, `date_fin`, `page` et `taille_page`.

### Administration de la plateforme

#### Premier déploiement

Avant cette commande, appliquez les migrations et créez la base. Historiquement, le premier Super Admin était créé par `python manage.py createsuperuser` : Django demandait interactivement l'email, le nom de boutique et le mot de passe via le gestionnaire personnalisé `CommercantManager`. Aucun mot de passe par défaut n'est nécessaire à cette méthode. La commande dédiée ci-dessous applique en plus les validateurs de mot de passe et masque la saisie du secret :

```bash
cd backend
python manage.py migrate
python manage.py creer_super_admin
```

Elle demande l'email, le nom de l'administration, puis le mot de passe deux fois. Elle ne prend aucun mot de passe en argument et n'a aucune valeur par défaut. N'exécutez cette commande qu'une fois, puis connectez-vous au back-office.

L'administration Django (`/admin/`) et toutes les permissions de l'API sont réservées aux super-admins. Les sous-admins utilisent une liste individuelle de droits et accèdent uniquement à `/api/admin/`; leur profil et leur statut actif sont relus à chaque requête. Leur désactivation invalide immédiatement les requêtes JWT suivantes.

La connexion du back-office est `POST /api/admin/auth/connexion/` (limite de 3 tentatives par minute). Les principales routes protégées sont `/api/admin/statistiques/`, `/api/admin/utilisateurs/`, `/api/admin/paiements-en-attente/`, `/api/admin/audit/` et `/api/admin/sous-admins/`. Les cinq droits attribuables sont `voir_utilisateurs`, `suspendre_utilisateur`, `valider_paiements`, `voir_audit` et `voir_statistiques`. Seul un super-admin peut créer un sous-admin ou modifier ses droits et son état. L'invitation réutilise le lien de définition du mot de passe, valable 15 minutes. Les suspensions, décisions de paiement et opérations de gestion des sous-admins sont enregistrées dans le journal d'audit avec l'administrateur responsable.

Connexion commerçant : l'adresse email est l'identifiant unique. Le téléphone reste un contact facultatif au format `+229` suivi de huit chiffres; il permet encore de recevoir le rappel SMS d'échéance d'abonnement.

Mot de passe oublié : `POST /api/auth/mot-de-passe/oublie/` avec `email`, puis `POST /api/auth/mot-de-passe/reinitialiser/` avec `uid`, `token` et `nouveau_mot_de_passe`. Le lien expire après 15 minutes et le changement de mot de passe le rend inutilisable une seconde fois. Les adresses inconnues reçoivent la même réponse que les adresses existantes. `EMAIL_SIMULATION=True` empêche l'envoi réel et les logs masquent adresse et lien secret.

### Migration de l'ancienne base SQLite vers PostgreSQL

Les versions précédentes utilisaient SQLite en développement. Avant la bascule, arrêtez l'ancienne application et faites une copie de `backend/db.sqlite3` ainsi que de l'ancien répertoire/volume `media`. Avec la nouvelle version, vous pouvez effectuer une exportation de transition en pointant temporairement `DATABASE_URL` vers cette copie SQLite :

```bash
# Depuis backend/ sous PowerShell; adaptez le chemin de db.sqlite3
$env:DATABASE_URL = "sqlite:///D:/chemin/gestion-commerçants/backend/db.sqlite3"
python manage.py migrate
python manage.py dumpdata commerce --natural-foreign --natural-primary -o migration-commerce.json
```

Créez ensuite une base PostgreSQL vide, configurez `DATABASE_URL` vers celle-ci, puis :

```bash
python manage.py migrate
python manage.py flush --noinput
python manage.py loaddata migration-commerce.json
```

`flush` supprime tout le contenu de la base PostgreSQL cible : n'exécutez ces commandes que sur la nouvelle base vide. Ce passage conserve les comptes et données métier de l'ancienne base, y compris l'historique de paiement renommé. Gardez la sauvegarde SQLite et le fichier d'export jusqu'à vérification des comptes et des volumes de données. Terminez en migrant les preuves locales vers Cloudinary avec la commande de la section précédente.

### Expiration automatique des abonnements

L'application bloque déjà les écritures lorsque `date_fin` est passée. La commande suivante met également à jour le statut stocké, peut être relancée sans effet secondaire et écrit son bilan dans les logs :

```bash
cd backend
python manage.py expirer_abonnements
```

Sur Render, créez un service **Cron Job** relié au même dépôt et à la même base, avec le répertoire backend, la commande `python manage.py expirer_abonnements` et le calendrier `0 0 * * *` (minuit UTC). Partagez les variables de l'API, notamment `DATABASE_URL`. Render interprète les calendriers de Cron Jobs en UTC et permet de configurer des variables par service. [Documentation officielle Render Cron Jobs](https://render.com/docs/cronjobs)

### Migration des comptes existants vers email

Une ancienne base locale pouvait contenir des comptes sans adresse email. Les migrations ne leur attribuent aucune adresse inventée et ne modifient ni leurs mots de passe ni leurs données commerciales. Pour ces déploiements, sauvegardez d'abord la base et gardez l'API hors ligne pendant cette transition, puis :

1. Appliquez seulement la migration de préparation : `python manage.py migrate commerce 0007_email_commercant_nullable`.
2. Créez hors du dépôt un CSV UTF-8 `telephone,email` associant chaque ancien téléphone à une adresse confirmée par son propriétaire. Ne partagez pas ce fichier publiquement.
3. Vérifiez-le avec `python manage.py importer_emails_commercants emails-commercants.csv --dry-run`, puis importez-le sans `--dry-run`.
4. Appliquez la contrainte finale avec `python manage.py migrate`. La migration `0008` s'arrête explicitement si un compte n'a pas d'email valide ou si un doublon existe.
5. Remettez l'application en ligne. Les commerçants se connecteront avec email et leur mot de passe actuel.

Pour une nouvelle base sans anciens comptes, `python manage.py migrate` applique les migrations dans l'ordre et l'import CSV n'est pas nécessaire.

### Emails transactionnels Brevo

Créer un compte Brevo, valider le domaine et l'adresse expéditeur dans le tableau de bord, puis ajouter `BREVO_API_KEY`, `BREVO_SENDER_EMAIL` et `BREVO_SENDER_NAME` au `.env` backend (ou aux variables privées de l'hébergeur). L'API utilise l'en-tête `api-key`; la clé ne doit jamais être intégrée au frontend ni commitée. Garder `EMAIL_SIMULATION=True` en développement et tests. Passer à `False` uniquement dans l'environnement où le compte et l'expéditeur sont validés. L'inscription envoie un email de bienvenue avec le rappel des 14 jours d'essai ; une panne email ne bloque pas la création du compte.

### Configuration des SMS Vonage

1. Créer et créditer un compte Vonage, récupérer l'API Key et l'API Secret dans le tableau de bord.
2. Configurer dans l'environnement backend `VONAGE_API_KEY`, `VONAGE_API_SECRET` et `VONAGE_SMS_SENDER`. Ne jamais mettre ces valeurs dans le frontend ou dans Git.
3. Garder `SMS_SIMULATION=True` pour le développement et les tests. Pour envoyer réellement, définir explicitement `SMS_SIMULATION=False` sur le backend et redémarrer le service.
4. Vérifier le nom d'expéditeur pour le Bénin : la prise en charge varie selon les opérateurs et un expéditeur alphanumérique doit être enregistré au préalable sur MTN. N'utiliser aucun expéditeur générique tel que « INFO » ou « SMS ».

Le format téléphone actuellement accepté par l'application reste `+229` suivi de huit chiffres. La validation locale ne garantit pas à elle seule l'acheminement par un opérateur ou l'acceptation du format par un compte fournisseur réel ; effectuer un essai contrôlé avant l'ouverture du service.

### Rappels d'échéance d'abonnement

La commande `python manage.py notifier_echeances_abonnement` envoie un rappel aux essais et abonnements qui expirent dans les trois prochains jours. Elle peut être relancée sans renvoyer le rappel déjà accepté pour la même échéance. Un échec n'est pas marqué comme envoyé et sera retenté lors de l'exécution suivante.

Pour l'exécuter chaque jour sur Render, créer un service **Cron Job** depuis le dépôt, définir la commande `python manage.py notifier_echeances_abonnement`, le répertoire racine `backend`, et le cron `0 6 * * *` (Render interprète les horaires en UTC, soit 07:00 au Bénin). Partager les mêmes variables d'environnement backend, y compris les clés Vonage. Laisser `SMS_SIMULATION=True` jusqu'à validation des messages en environnement de test.

Les dettes ne sont pas modifiables directement. `POST /api/dettes/{id}/correction/` demande `nouveau_montant` et `raison`; chaque correction conserve l'ancien montant et apparaît dans l'historique et l'audit. Le reçu PDF est disponible à `GET /api/dettes/{id}/recu/` et depuis la fiche client. Au premier téléchargement, il reçoit un UUID persistant, une date de génération et un QR code ; les téléchargements suivants gardent le même code. Le PDF présente un en-tête de marque, les informations du reçu hiérarchisées, le montant mis en évidence et un QR code. Scanner celui-ci ouvre `/verifier/{code}` sur le frontend, qui vérifie le code puis affiche le reçu PDF public via `GET /api/verifier/{code}/recu/`. Toute personne possédant le QR/code peut donc consulter ce reçu et les informations qu'il contient (boutique, client, montant et solde) ; ne partagez le document qu'avec ses destinataires. L'endpoint JSON `GET /api/verifier/{code}/` reste limité au statut d'authenticité et à la date. Les routes publiques de vérification sont limitées à 10 requêtes par minute et par adresse IP. Un code devient invalide si le document associé est supprimé. Le solde imprimé est le solde total du client, car les paiements actuels ne sont pas affectés à une dette particulière. Les reçus d'abonnement validés suivent le même design et possèdent également un QR code public.

## Tests, couverture et lint

Depuis `backend/` :

```bash
python -m pip install -r requirements-dev.txt
pytest
ruff check .
```

`pytest` génère un rapport console par fichier, vérifie le seuil minimal de **80 %** et écrit le rapport HTML dans `backend/htmlcov/`.

Depuis `frontend/` :

```bash
npm ci
npm run lint
npm run build
```

Les mêmes contrôles tournent dans GitHub Actions à chaque push et pull request.

Audits de dépendances à lancer après installation :

```bash
# Depuis backend/
python -m pip install pip-audit
pip-audit

# Depuis frontend/
npm audit
```

## Sécurité, audit et données personnelles

- `django-axes` bloque une combinaison email/adresse IP après 5 échecs pendant 15 minutes. La connexion est aussi limitée à 5 requêtes/minute par IP, l'inscription à 3/heure et le refresh JWT à 30/minute.
- Les preuves de transfert sont des ressources Cloudinary authentifiées. Leur téléchargement passe par une vue protégée qui contrôle le commerçant ou le compte administratif avant de produire une URL signée très courte.
- L'email est l'identifiant de connexion et est masqué dans Sentry et les logs. Les clés Brevo restent côté backend et la simulation est active par défaut.
- En production, `DEBUG=False`, `ALLOWED_HOSTS` et `CORS_ALLOWED_ORIGINS` doivent contenir des valeurs exactes sans joker. HTTPS, HSTS, cookies sécurisés, `X-Content-Type-Options` et `X-Frame-Options` sont activés.
- Le journal d'audit est filtré par commerçant, paginé et en lecture seule dans l'API et l'administration. Les champs téléphones, mots de passe, jetons et clés sont exclus ou masqués.
- Sentry est inactif quand le DSN est vide. Les événements sont filtrés avant envoi; les logs de production sont des lignes JSON sans valeurs de requête.
- L'export contient les données de la boutique sans hash de mot de passe. La suppression exige le mot de passe et efface les données métier, l'audit associé et les traces Axes liées au compte.
- Les pages Conditions et Confidentialité portent la mention **MODÈLE À FAIRE VALIDER PAR UN JURISTE**. Compléter et faire valider les textes et coordonnées avant ouverture publique.

## Sauvegarde et restauration

Depuis `backend/`, créez une sauvegarde JSON logique portable :

```bash
python manage.py sauvegarde_db
# ou choisir le fichier de sortie
python manage.py sauvegarde_db --sortie backups/avant-maintenance.json
```

Le fichier comprend les données utilisateur et les hashes de mots de passe : stockez-le dans un emplacement privé et chiffré, avec des accès limités. Pour restaurer une sauvegarde dans une base vide, installez les dépendances, configurez la base, puis :

```bash
python manage.py migrate
python manage.py loaddata backups/avant-maintenance.json
```

Le test `test_sauvegarde_json_peut_etre_restauree` vérifie la création et la restauration d'un enregistrement depuis ce format.

### Sauvegardes automatiques Render PostgreSQL

Render effectue une sauvegarde continue avec restauration à un instant donné (PITR) pour les bases PostgreSQL payantes. La fenêtre de restauration indiquée par la documentation actuelle est de **3 jours pour Hobby** et **7 jours pour Pro ou supérieur**; les bases Free n'ont pas ces capacités de restauration. Un export logique déclenché depuis le tableau de bord est conservé 7 jours. Pour une rétention plus longue, téléchargez l'export dans un stockage privé ou automatisez `pg_dump` vers un stockage externe.

Consulter la [documentation Render sur la récupération et les sauvegardes PostgreSQL](https://render.com/docs/postgresql-backups) avant de choisir le plan. Après une restauration PITR, Render crée une nouvelle instance : validez son contenu, puis remplacez la connexion de l'application par celle de l'instance restaurée.

## Données de démonstration

Dans `backend/`, après les migrations :

```bash
python manage.py seed_demo
```

La première exécution demande un mot de passe masqué pour le compte `demo@nobi.example`. Ce mot de passe n'est pas fourni par le code et n'est pas modifié lors des exécutions suivantes. Les produits, clients, ventes, dettes et règlements générés sont fictifs. Une autre boutique ne peut pas être écrasée ; choisir une adresse différente en modifiant le code ou les options locales si nécessaire.

## Décisions techniques

- **Django et DRF** : modèles relationnels et API JSON, avec permissions explicites côté serveur.
- **JWT** : authentification adaptée à une interface React séparée.
- **Transactions atomiques** : la vente et la décrémentation du stock réussissent ou échouent ensemble.
- **Isolation par commerçant** : les querysets et validations de relations sont limités au compte courant.
- **PostgreSQL partout** : les tests et l'exécution utilisent le même moteur relationnel; `dj-database-url` interprète `DATABASE_URL`.
- **Cloudinary pour les preuves** : les fichiers persistent hors du disque éphémère et sont stockés comme ressources authentifiées.
- **Nginx et Vite** : build statique du frontend, sans serveur Node en production.

## Sécurité

- Ne jamais accepter le commerçant propriétaire depuis les données envoyées par le navigateur.
- Vérifier les permissions, l'isolation inter-commerçants et les règles de stock dans les tests.
- Remplacer les secrets locaux, activer HTTPS et désactiver `DEBUG` avant publication.
- Le webhook de test devra pointer vers `/api/abonnement/webhook/` sur une URL backend accessible en HTTPS.

## Feuille de route

- Démo publique : [À COMPLÉTER]
- Captures d'écran : [À COMPLÉTER]
- Déploiement public : [À COMPLÉTER]

## Licence

Distribué sous licence MIT. Compléter l'année et le titulaire dans [`LICENSE`](LICENSE) avant publication.
