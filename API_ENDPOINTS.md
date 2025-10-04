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
| POST | /api/subscriptions/subscribe/ | S'abonner à un plan |
| POST | /api/subscriptions/change-plan/ | Changer de plan |
| GET | /api/subscriptions/me/ | Voir mon abonnement |

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


