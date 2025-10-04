## 🧠 Prompt pour Vercel v0 — Frontend connecté à SubChain (Django REST + Algorand)

Build a full frontend with Next.js (App Router) using Tailwind CSS, and connect it to my Django REST API for a crypto subscription SaaS called SubChain.

---

### 🔐 Authentification (JWT)
- **POST** `/api/auth/login/`
  - Body: `{ "email": "", "password": "" }`
  - Response: `{ "access": "", "refresh": "" }`

- **GET** `/api/auth/profile/`
  - Header: `Authorization: Bearer <access_token>`
  - Response: user object

> Token must be stored in `localStorage` and added to `Authorization` header for all protected routes.

---

### 🧾 Plans & Abonnements

- **GET** `/api/subscriptions/plans/`  
  → Liste des plans disponibles

- **POST** `/api/subscriptions/subscribe/`  
  Body: `{ "plan_id": int }`  
  → Souscrit à un plan

- **GET** `/api/subscriptions/status/`  
  → Récupère le statut de l’abonnement en cours

---

### 💸 Paiements & Swap Algorand

- **GET** `/api/payments/history/`  
  → Historique des paiements ALGO/USDC

- **POST** `/api/payments/trigger-swap/`  
  Body: `{ "payment_id": int }`  
  → Lance automatiquement le swap ALGO → USDC via Tinyman

- **GET** `/api/payments/qrcode/<amount>/`  
  → Génère un QR code à afficher côté frontend pour que l’utilisateur puisse payer en ALGO

---

### 🔔 Notifications

- **GET** `/api/notifications/`  
  → Liste des notifications de l’utilisateur

- **PATCH** `/api/notifications/<id>/`  
  → Marque comme lue

---

### 📈 Analytics internes

- **POST** `/api/analytics/track/`  
  Body: `{ "event_type": "login", "payload": {...} }`  
  → Permet de traquer les événements (connexion, souscription, etc.)

---

### ⚙️ Intégrations Webhooks

- **POST** `/api/webhooks/payment-received/`  
  Body: `{ "transaction_id": "...", "amount": ..., "wallet": "..." }`  
  → Appelé par le front ou un service tiers pour notifier un paiement ALGO

---

### 🧱 Structure souhaitée du frontend

- `/login` → Formulaire de connexion
- `/dashboard` → Abonnement actif + historique + QR code paiement
- `/subscribe` → Liste des plans avec bouton "Souscrire"
- `/notifications` → Liste de notifications
- `/settings` → Paramètres utilisateur (optionnel)

---

### 🧑‍🎨 Design UI

- Sombre par défaut
- Responsive (mobile-friendly)
- TailwindCSS 3+
- Boutons arrondis, cartes animées
- Icônes modernes (Lucide ou Heroicons)

---

### 🌍 Langue
Multilingue (français par défaut, puis anglais si possible)

---

### 🔗 API Base
