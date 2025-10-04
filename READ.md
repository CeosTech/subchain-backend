# SubChain Backend 🛠️

SubChain est une solution API-first pour la gestion d’abonnements Web3 avec paiements en ALGO convertis automatiquement en USDC.

## ⚙️ Stack principale

- Django 4 / DRF
- SimpleJWT pour l'authentification
- SQLite (dev) / PostgreSQL (prod)
- Algorand SDK / Tinyman
- Webhooks / Notifications / Seeders

## 📦 Applications Django

- `accounts` — gestion des utilisateurs
- `subscriptions` — plans & abonnements
- `payments` — transactions & frais
- `algorand` — swaps ALGO → USDC
- `currency` — simulateur taux change
- `webhooks` — écouteurs auto (renouvellement)
- `notifications` — templates + envois
- `integrations` — connexions externes (à venir)
- `analytics` — suivi usage (à venir)

## 🚀 Démarrage local

```bash
git clone ...
cd subchain_backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py seed_accounts
python manage.py runserver
