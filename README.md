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
| `ENVIRONMENT`, `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS` | `ENVIRONMENT` est obligatoire (`development`, `test` ou `production`); `DEBUG` est désactivé par défaut et doit être explicitement `False` en production; la clé secrète est obligatoire en production |
| `CORS_ALLOWED_ORIGINS`, `FRONTEND_URL`, `PUBLIC_FRONTEND_URL`, `VITE_API_URL` | Communication navigateur/API et base du lien public de vérification des reçus |
| `DATABASE_URL` | URL PostgreSQL de Django (`postgresql://utilisateur:mot_de_passe@hôte:5432/base`) |
| `REDIS_URL` | Optionnelle. Si elle est absente en production, les compteurs partagés utilisent la table `nobi_cache` dans PostgreSQL ; cela ajoute de la charge à la base. Redis pourra être activé plus tard en fournissant son URL partagée. |
| `BACKUP_ENCRYPTION_KEY`, `BACKUP_S3_BUCKET` | Optionnelles au démarrage. Configurez-les ensemble pour activer les sauvegardes chiffrées vers S3 ; sinon, la sauvegarde distante est désactivée. La commande échoue explicitement en production et ne crée pas de copie locale éphémère. |
| `BACKUP_S3_PREFIX`, `AWS_REGION`, `AWS_ENDPOINT_URL`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` | Réglages du stockage S3 lorsque celui-ci est activé. Les identifiants AWS doivent être disponibles via l'environnement ou un mécanisme d'identité AWS. |
| `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` | Identifiants du service PostgreSQL Docker Compose ; garder ces valeurs alignées sur `DATABASE_URL` |
| `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET` | Accès privé du stockage de preuves Cloudinary, backend uniquement |
| `FEDAPAY_SECRET_KEY` | Clé secrète FedaPay, backend uniquement. Ne jamais la mettre dans le frontend, Git ou un message. |
| `FEDAPAY_ENVIRONMENT` | `sandbox` pour les essais (défaut) ou `live` pour les encaissements réels. |
| `FEDAPAY_WEBHOOK_SECRET` | Secret `wh_...` propre au webhook FedaPay et à son environnement, utilisé pour vérifier la signature. |
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

En développement local (`ENVIRONMENT=development`), si Cloudinary n'est pas configuré, les **logos de profil uniquement** sont stockés dans `backend/media/` et servis par Django, avec un avertissement au démarrage. Ce repli local n'est jamais utilisé en production ; les identifiants Cloudinary sont nécessaires pour y téléverser et conserver les logos. Les preuves de paiement restent sur Cloudinary.

### Paiement manuel de l'abonnement

Les paiements d'abonnement utilisent FedaPay. Le backend crée la transaction en XOF et n'active l'abonnement qu'après avoir relu son statut auprès de l'API FedaPay et vérifié son montant et sa référence locale. En local, utilisez une clé secrète Sandbox et `FEDAPAY_ENVIRONMENT=sandbox`. En production, définissez `FEDAPAY_SECRET_KEY` dans les variables privées du backend Railway et choisissez `FEDAPAY_ENVIRONMENT=live` uniquement après validation du parcours Sandbox. Le webhook FedaPay à enregistrer est `https://<domaine-api>/api/webhooks/fedapay/`; ajoutez dans Railway le secret de signature `wh_...` correspondant dans `FEDAPAY_WEBHOOK_SECRET`. Les clés API et webhook diffèrent selon Sandbox et Live. La confirmation de retour utilisateur relit aussi l'état chez FedaPay. Les demandes manuelles existantes sont conservées pour l'historique administratif.

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

Sur Railway, créez un service **Cron** relié au même dépôt, configuré sur l'image/backend du service `backend`, avec la commande `python manage.py expirer_abonnements` et le calendrier `0 0 * * *` (minuit UTC). Réutilisez les variables backend, notamment la référence `DATABASE_URL` vers PostgreSQL. Railway planifie les tâches en UTC ; la commande doit se terminer pour permettre les exécutions suivantes. [Documentation officielle Railway Cron](https://docs.railway.com/cron-jobs)

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

Pour l'exécuter chaque jour sur Railway, créer un service **Cron** depuis le dépôt, définir la commande `python manage.py notifier_echeances_abonnement` et le cron `0 6 * * *` (UTC, soit 07:00 au Bénin). Partager les mêmes variables d'environnement backend, y compris les clés Vonage. Laisser `SMS_SIMULATION=True` jusqu'à validation des messages en environnement de test.

Les dettes ne sont pas modifiables directement. `POST /api/dettes/{id}/correction/` demande `nouveau_montant` et `raison`; chaque correction conserve l'ancien montant et apparaît dans l'historique et l'audit. Le reçu PDF complet est téléchargeable dans l'espace authentifié du commerçant, depuis `GET /api/dettes/{id}/recu/` ou la fiche client. Au premier téléchargement, il reçoit un UUID aléatoire persistant, une date de génération et un QR code ; les téléchargements suivants gardent le même code. Scanner le QR ouvre `/verifier/{code}` et ne révèle publiquement que l'authenticité et la date. Le PDF financier est réservé au commerçant connecté propriétaire ; le code seul ne donne pas accès aux montants ni aux identités. Un code devient invalide si le document associé est supprimé. Le solde imprimé est le solde total du client, car les paiements actuels ne sont pas affectés à une dette particulière. Les reçus d'abonnement validés suivent le même principe.

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
- En production, définissez `ENVIRONMENT=production`. Le démarrage échoue si `DEBUG` est absent, vide ou vrai, ou si `SECRET_KEY` est absente/vide. `DEBUG` vaut `False` par défaut en développement; activez-le explicitement avec `DEBUG=True` dans votre `.env` local si nécessaire. `ALLOWED_HOSTS` et `CORS_ALLOWED_ORIGINS` doivent contenir des valeurs exactes sans joker. HTTPS, HSTS, cookies sécurisés, `X-Content-Type-Options` et `X-Frame-Options` sont activés.
- Les créations de vente, dette et paiement exigent `Idempotency-Key` en production. Le frontend fournit et réutilise une clé lors d'un renvoi identique après une coupure réseau; les autres clients API doivent également envoyer une clé unique d'au moins 8 caractères.
- Les compteurs DRF et Axes utilisent Redis lorsque `REDIS_URL` est défini. Sans Redis en production, ils utilisent la table PostgreSQL `nobi_cache`, partagée entre les workers. Un avertissement de démarrage signale ce mode de repli et la charge supplémentaire sur PostgreSQL. La migration crée cette table. En développement/test sans Redis, le cache mémoire local reste utilisé.
- Les JWT commerçant et back-office sont transportés par cookies `HttpOnly`; les écritures exigent le jeton CSRF. Les jetons d'accès durent 5 minutes, les refresh durent 7 jours, tournent à chaque renouvellement et sont inscrits dans une liste noire. Le logout et la réinitialisation du mot de passe révoquent la session côté serveur. Configurez `CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS`, `AUTH_COOKIE_SECURE=True` et `AUTH_COOKIE_SAMESITE=None` avec les domaines HTTPS exacts avant production.
- Les listes de l'API sont paginées avec `?page=1&page_size=20`; la taille est plafonnée à 100. Les réponses ont les champs `count`, `next`, `previous` et `results`.
- La suppression d'un client ou d'un produit via l'application archive l'enregistrement. Les ventes, dettes, paiements et rapports historiques restent consultables; un client ou produit archivé ne peut pas être réutilisé pour une nouvelle opération.
- Le journal d'audit est filtré par commerçant, paginé et en lecture seule dans l'API et l'administration. Les champs téléphones, mots de passe, jetons et clés sont exclus ou masqués.
- Sentry est inactif quand le DSN est vide. Les événements sont filtrés avant envoi; les logs de production sont des lignes JSON sans valeurs de requête.
- La CI audite les dépendances JavaScript livrées au navigateur avec `npm audit --omit=dev --audit-level=high`. Le graphe complet de développement signale actuellement l'avis [GHSA-fc5q-39xc-vjpf](https://github.com/advisories/GHSA-fc5q-39xc-vjpf) dans `picomatch`, utilisé par la chaîne Vite/Tailwind; l'avis officiel ne publie pas encore de version corrigée. Ces outils ne sont pas inclus dans les fichiers statiques servis en production. L'audit complet reste à surveiller et cette exception doit être retirée dès qu'un correctif compatible est disponible.
- L'export contient les données de la boutique sans hash de mot de passe. La suppression exige le mot de passe et efface les données métier, l'audit associé et les traces Axes liées au compte.
- Les pages Conditions et Confidentialité portent la mention **MODÈLE À FAIRE VALIDER PAR UN JURISTE**. Compléter et faire valider les textes et coordonnées avant ouverture publique.

## Sauvegarde et restauration

Depuis `backend/`, créez une sauvegarde logique JSON compressée et chiffrée avec Fernet :

```bash
python manage.py sauvegarde_db
# copie locale chiffrée facultative, utile pour un exercice contrôlé
python manage.py sauvegarde_db --sortie backups/avant-maintenance.json.gz.fernet
```

La commande exige `BACKUP_ENCRYPTION_KEY`. En production, `BACKUP_ENCRYPTION_KEY` et `BACKUP_S3_BUCKET` doivent être configurées ensemble pour envoyer une sauvegarde chiffrée vers un stockage objet externe. Ces variables ne bloquent pas le démarrage : sans configuration complète, un avertissement indique que les sauvegardes distantes ne sont pas assurées et la commande `sauvegarde_db` échoue sans créer une copie locale éphémère. Le contenu est chiffré avant transfert, vérifié par Fernet et accompagné d'une empreinte SHA-256. Configurez une règle de cycle de vie dans le bucket pour la rétention voulue et protégez les droits de lecture/suppression. Générez une clé Fernet puis conservez-la comme secret dans l'hébergeur, jamais dans Git :

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Pour restaurer, téléchargez un fichier chiffré vers une nouvelle base PostgreSQL isolée, définissez la même clé de déchiffrement, exécutez `python manage.py migrate`, puis `python manage.py restaure_db chemin/backup.json.gz.fernet`. Cette commande refuse par défaut une cible production; la confirmation `--confirmer-production` doit rester exceptionnelle. Validez les comptes, produits, clients, ventes, dettes, paiements, stocks et abonnements avant de basculer le service. Le test `test_sauvegarde_chiffree_peut_etre_restauree` couvre le chiffrement et la restauration locale; il ne remplace pas un exercice réel sur PostgreSQL et le stockage distant.

### Objectifs RPO/RTO et exercice de restauration

Objectifs provisoires à confirmer selon le plan d'hébergement : **RPO cible 24 h** avec une sauvegarde logique quotidienne externalisée, et **RTO cible 4 h**. Le code chiffre et dépose une copie externe si le bucket est configuré; le cron, ses secrets, sa rétention et le premier exercice de restauration restent à créer dans les comptes d'hébergement.

Pour tester une restauration sans toucher à la base de production : créez une base PostgreSQL temporaire isolée, configurez `DATABASE_URL` vers cette base, exécutez les migrations et `python manage.py restaure_db`, puis vérifiez les données financières et les relations attendues. Supprimez ensuite uniquement cette base temporaire après validation.

### Sauvegardes de la base Railway

Railway fournit des sauvegardes et une restauration de PostgreSQL selon le plan choisi. Activez-les depuis le service de base de données, vérifiez la politique de rétention et réalisez un exercice de restauration vers une base isolée avant de fixer le RPO/RTO. [Documentation officielle Railway sur la restauration PostgreSQL](https://docs.railway.com/volumes/point-in-time-recovery)

La copie applicative chiffrée vers S3 reste une option distincte. Si elle est activée, créez un service **Cron** Railway avec les mêmes variables backend et exécutez `python manage.py sauvegarde_db` selon une cadence définie. Sans bucket et clé Fernet, aucune sauvegarde S3 ne sera produite ; les sauvegardes natives PostgreSQL et cette copie S3 ne se remplacent pas mutuellement.


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

## Déploiement en production sur Railway

L'architecture Railway prévoit deux services applicatifs nommés exactement `backend` et `frontend`, plus un service PostgreSQL. Le frontend Nginx sert React et transmet `/api/` au backend via le réseau privé Railway (`backend.railway.internal:8000`) ; les appels navigateur restent sur le même domaine. Le backend n'a donc pas besoin d'un domaine public. La configuration de ces services et le transfert de la base existante sont des opérations à effectuer dans Railway avant le basculement DNS.

### Préparer les services Railway

1. Créez les services `backend` et `frontend` dans Railway. Utilisez la racine du dépôt comme contexte et indiquez respectivement `backend/Dockerfile` et `frontend/Dockerfile` comme Dockerfile. Désactivez leurs déploiements automatiques déclenchés directement par GitHub : la CI les publiera après validation. Le backend écoute sur le port `8000`; le frontend Nginx écoute sur `80` et doit recevoir un domaine public.
2. Créez un service PostgreSQL. Dans les variables du backend, définissez `DATABASE_URL` comme référence Railway vers la variable de connexion PostgreSQL. Configurez les variables habituelles de production documentées plus haut (`ENVIRONMENT=production`, `DEBUG=False`, `SECRET_KEY`, domaines exacts dans `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS`, URLs frontend, Cloudinary et Brevo selon les fonctions activées). Aucune variable Redis ou S3 n'est requise au démarrage.
3. Après attribution du domaine frontend, utilisez son URL HTTPS exacte dans `FRONTEND_URL`, `PUBLIC_FRONTEND_URL`, `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS` et `CSRF_TRUSTED_ORIGINS` selon les usages de chaque réglage. Configurez `DEPLOYMENT_MAINTENANCE_TOKEN` avec le même secret dédié (au moins 32 caractères) dans Railway et les secrets GitHub.
4. Exportez la base PostgreSQL Render et importez-la dans la base Railway avant de modifier le domaine public. Faites une sauvegarde vérifiable, contrôlez les migrations/données et testez le parcours d'écriture sur Railway. Gardez l'ancien hébergement disponible pendant la validation ; ne supprimez Render/Vercel qu'après validation du trafic, des fichiers Cloudinary, des emails et des reçus.
5. Pour le premier déploiement, configurez manuellement les trois services, les variables, le domaine frontend et la base. Laissez la variable GitHub `PRODUCTION_DEPLOY_ENABLED` absente ou différente de `true` pendant cet amorçage.

### Déploiements automatiques après amorçage

Après réussite de la CI sur un push `main`, le workflow active le mode maintenance, transmet le SHA testé dans la variable optionnelle `APP_RELEASE_SHA`, déploie d'abord `backend`, puis `frontend` avec Railway CLI, vérifie `/api/sante/`, `/api/version/`, `/version.json` et la page d'accueil. Cette variable n'est pas nécessaire au démarrage ; elle sert uniquement à vérifier le commit publié. Le workflow restaure l'état de maintenance antérieur uniquement après confirmation du SHA et des réponses HTTP. Si la vérification échoue, la maintenance reste active pour permettre une vérification manuelle.

Dans GitHub, configurez le secret `RAILWAY_TOKEN` avec un **Project Token** Railway limité au projet/environnement de production, le secret `DEPLOYMENT_MAINTENANCE_TOKEN`, et la variable Actions `RAILWAY_FRONTEND_URL` avec l'URL HTTPS publique du frontend. Après le déploiement manuel initial et un test réussi de l'endpoint de maintenance, définissez `PRODUCTION_DEPLOY_ENABLED=true` pour activer le déploiement depuis la CI. Les nouvelles versions sont publiées par le workflow ; le bouton Maintenance ne fait qu'activer ou arrêter l'accès pendant l'opération.

Aucun paquet Python ou JavaScript supplémentaire n'est ajouté pour Railway. Les variables `RAILWAY_TOKEN` et `RAILWAY_FRONTEND_URL` servent uniquement au workflow GitHub ; elles ne doivent pas être ajoutées au runtime Django.
