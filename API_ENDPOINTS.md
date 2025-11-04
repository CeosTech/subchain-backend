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

> ℹ️ Certains endpoints peuvent répondre `402 Payment Required` si le middleware x402 est activé (voir `config/settings.py`).

---

## Micropaiements x402

| Méthode | Endpoint | Description |
|--------|----------|-------------|
| GET/POST/PUT/PATCH/DELETE | /api/integrations/x402/pricing-rules/ | Gérer les règles de tarification par endpoint |
| GET | /api/integrations/x402/receipts/ | Consulter les reçus de paiement validés |
| GET/POST/PUT/PATCH/DELETE | /api/integrations/x402/links/ | Créer et maintenir des liens de paiement x402 |
| GET/POST/PUT/PATCH/DELETE | /api/integrations/x402/widgets/ | Générer des widgets embarqués protégés par x402 |
| GET/POST/PUT/PATCH/DELETE | /api/integrations/x402/credit-plans/ | Configurer des packs/crédits x402 |
| GET | /api/integrations/x402/credit-subscriptions/ | Suivre les consommateurs et leurs crédits restants |
| GET | /api/integrations/x402/credit-usage/ | Historique des top-ups et consommations de crédits |
| POST | /api/integrations/x402/credit-subscriptions/{id}/consume/ | Décrémenter manuellement le solde d'un abonné |

Endpoints publics (paywall) générés automatiquement :
- `GET /paywall/tenant/{tenant_id}/links/{slug}/`
- `GET /paywall/tenant/{tenant_id}/widgets/{slug}/`
- `GET /paywall/tenant/{tenant_id}/credits/{slug}/`

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
