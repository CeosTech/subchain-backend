# 🌐 Endpoints API - SubChain

## Auth

| Méthode | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/auth/register/ | Créer un compte |
| POST | /api/auth/login/ | Connexion avec JWT |
| GET | /api/auth/profile/ | Profil utilisateur |
| POST | /api/auth/verify-email/ | Vérification email |
| POST | /api/auth/reset-password/ | Envoi lien reset |
| POST | /api/auth/reset-password/confirm/ | Réinitialisation mot de passe |

---

## Subscriptions

| Méthode | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/subscriptions/plans/ | Liste des plans |
| POST | /api/subscriptions/ | Créer un abonnement (champ `customer_type`, adresse de facturation, etc.) |
| GET | /api/subscriptions/ | Voir mes abonnements |
| GET/POST | /api/subscriptions/coupons/ | Gérer ses coupons (staff = global) |
| POST | /api/subscriptions/checkout-sessions/ | Lancer un checkout sécurisé |
| POST | /api/subscriptions/checkout-sessions/{id}/confirm | Confirmer le checkout |

---

## Payments

| POST | /api/payments/receive/ | Créer une transaction ALGO |
| GET  | /api/payments/history/ | Historique de paiements |

---

## Algorand

| GET | /api/currency/convert/?from=ALGO&to=USDC&amount=10 | Simuler un swap |

---

## Notifications

| GET | /api/notifications/templates/ | Voir tous les templates |
| POST | /api/notifications/send/ | Envoyer une notif avec template |

---

## Webhooks (automatiques)

| POST | /api/webhooks/renew/ | Déclenché après 30j pour renouveler |

