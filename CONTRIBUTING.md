# Contribuer

Merci de contribuer à MACDIOS. Les changements doivent préserver l'isolation des données de chaque commerçant et l'interface française mobile-first.

1. Créez une branche dédiée et décrivez brièvement le changement.
2. Installez `backend/requirements-dev.txt` et les dépendances frontend avec `npm ci`.
3. Avant une demande de fusion, lancez `ruff check .`, `pytest` dans `backend/`, puis `npm run lint` et `npm run build` dans `frontend/`.
4. Ajoutez ou adaptez les tests pour tout comportement modifié, notamment les permissions et les paiements.
5. N'ajoutez jamais de clé, mot de passe ou fichier `.env` au dépôt.
