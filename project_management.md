Voici un document `README.md` structuré et complet que tu peux inclure dans ton repo `subchain_backend` pour documenter l’état du projet, les modules déjà en place, les intégrations avec Algorand, et ce qu’il reste à faire.

---

## 🧠 SubChain Backend — Architecture Django REST + Algorand

> Plateforme de gestion d’abonnements Web3 avec paiements en $ALGO automatiquement convertis en stablecoin ($USDC) sur la blockchain **Algorand**.

---

## ✅ Fonctionnalités déjà implémentées

### 🔐 Authentification (App `accounts`)

* Utilisateur personnalisé (`CustomUser`)
* Auth via e-mail & mot de passe
* JWT sécurisé (`rest_framework_simplejwt`)
* Endpoints : inscription, login, profil

### 📦 Abonnements (App `subscriptions`)

* Création de **plans d'abonnement**
* Suivi des **utilisateurs abonnés**
* Stockage du nombre de **jours restants**
* Système de **renouvellement automatique prévu** via Webhook

### 💸 Paiements (App `payments`)

* Enregistrement des paiements ALGO
* Statut du paiement + adresse payée + montant
* Détection de paiement par webhook ou tâche planifiée

### 🔁 Swap ALGO → USDC (App `algorand`)

* Utilisation du SDK Algorand pour :

  * Détection de transaction entrante
  * Swap automatique via **Tinyman**
* Configuration dynamique via variables `.env`
* Taux de slippage personnalisable

### 📢 Notifications (App `notifications`)

* Modèle `Notification` lié à chaque utilisateur
* Canaux supportés : `email`, `SMS`, `in_app`, `webhook`
* Templates configurables via `NotificationTemplate`
* Support multi-langues (français, anglais, espagnol)

### 📊 Analytics (App `analytics`)

* Logs d'événements (connexion, abonnement, paiement)
* Deux modèles :

  * `EventLog` : suivi orienté utilisateur
  * `AnalyticsLog` : tracking technique (API calls, events custom)

### 🔗 Webhooks (App `webhooks`)

* Prévu pour recevoir les callbacks (paiement, renouvellement)
* Écoute des événements externes (WalletConnect, Indexer)

### 💱 Devise (App `currency`)

* Conversion, historique de taux, et formatage prévu
* `currency/utils.py` contient les helpers

### 🌐 Intégrations externes (App `integrations`)

* Prêt à accueillir les connexions à :

  * WalletConnect
  * Tinyman
  * AlgoExplorer
  * Email providers (SendGrid, etc.)
  * Stripe si besoin en parallèle

---

## 🔗 Intégration Blockchain Algorand

### ▶️ Utilisation

* SDK officiel `py-algorand-sdk`
* Noeud API : [https://testnet-api.algonode.cloud](https://testnet-api.algonode.cloud)
* Indexer : [https://testnet-idx.algonode.cloud](https://testnet-idx.algonode.cloud)

### 🔁 Fonctionnement du swap

```text
[User envoie ALGO] → [Wallet SubChain reçoit] → [Déclenchement Swap] → [Tinyman] → [USDC]
```

* Swap déclenché automatiquement par webhook ou job CRON
* Conversion sécurisée avec `slippage` max configurable
* Logs complets dans `algorand/utils.py` et `payments/models.py`

---

## 📁 Structure du Projet

```bash
subchain_backend/
├── accounts/              # Auth & user model
├── subscriptions/         # Plans & abonnements
├── payments/              # Paiements ALGO reçus
├── algorand/              # Fonctions blockchain
├── currency/              # Conversion & devises
├── notifications/         # Système de notifications
├── analytics/             # Logs analytics & événements
├── webhooks/              # Réception d'événements externes
├── integrations/          # Connecteurs API externes
├── config/                # Settings Django
└── manage.py
```

---

## ⚙️ Variables d’environnement essentielles

> À renseigner dans `.env` (voir `.env.example`)

| Nom                                | Rôle                             |
| ---------------------------------- | -------------------------------- |
| `DJANGO_SECRET_KEY`                | Clé secrète Django               |
| `ALGO_NODE_URL`                    | Endpoint Algorand                |
| `ALGO_API_TOKEN`                   | Token API Algo (souvent vide)    |
| `ALGO_INDEXER_URL`                 | Endpoint Indexer                 |
| `SUBCHAIN_TREASURY_WALLET_ADDRESS` | Wallet principal SubChain        |
| `PLATFORM_FEE_WALLET_ADDRESS`      | Wallet des commissions           |
| `PLATFORM_FEE_PERCENT`             | Pourcentage pris sur chaque swap |
| `TINYMAN_SWAP_SLIPPAGE`            | Slippage max (ex : 0.03 pour 3%) |
| `FRONTEND_BASE_URL`                | URL du front Next.js             |

---

## 📌 À faire (TODO)

### 🔧 Technique

* [ ] Finaliser Webhook Tinyman / Indexer
* [ ] Ajout CRON fallback si aucun webhook n’arrive
* [ ] Ajout auto-swap par batch (toutes les X minutes)
* [ ] Export RGPD + Audit Trail
* [ ] Activation 2FA / TOTP pour comptes sensibles

### ⚙️ Admin & Dashboard

* [ ] Interface admin pour relancer un swap manuellement
* [ ] Ajout bouton "Voir sur AlgoExplorer"
* [ ] Historique de transactions USDC/ALGO

### 🧪 Tests & Sécurité

* [ ] Tests unitaires (algorand, swap, webhook)
* [ ] Limiter la fréquence des appels (ratelimit API)
* [ ] Captcha sur les formulaires publics

### 📄 Docs Dev

* [ ] `API_ENDPOINTS.md` → Liste des routes REST
* [ ] `SECRETS.md` → Format des clés Algorand
* [ ] `DOC_MODELS.md` → Description des modèles

---

## 🧠 Vision

SubChain vise à **simplifier l'intégration Web3 dans des plateformes SaaS** :

* Paiement en crypto (ALGO)
* Conversion automatique en stablecoin (USDC)
* Abonnements récurrents
* Intégration simple via REST API

---

Souhaite-tu que je te génère ce fichier `README.md` prêt à l’emploi ?
Ou un export PDF avec branding pour doc interne ?
