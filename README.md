# SubChain Backend

SubChain is an API-first subscription and billing engine purpose-built for the Algorand ecosystem. It combines recurring billing primitives, automated Tinyman swaps, lifecycle automation, and customer notifications so founders can launch crypto-native SaaS products without reinventing their payments stack.

This codebase underpins our submission to the **Algorand Startup Challenge**. Our thesis: predictable USDC revenue, powered by Algorand, deserves the same level of polish and developer experience that Web2 founders enjoy with services like Stripe Billing.

## Why SubChain for Algorand

- **Stripe-like subscription model** – Plans, tiers, coupons, invoices, payment intents, and checkout sessions map to familiar billing workflows while remaining token-aware.
- **Tinyman at the core** – Every billing cycle can trigger an automated ALGO → USDC swap, with retries, audit trails, and configurable slippage limits.
- **Operational muscle** – Background jobs cover trial expirations, renewals, and payment retries; event logs keep analytics and external systems in sync.
- **Customer-first notifications** – Email notifications (SMS/webhooks ready) communicate state changes to users and operators automatically.
- **Checkout sessions** – Secure, signed sessions allow front-ends to start subscriptions with wallet confirmation handled server-side.
- **x402 micropayments ready** – Optional HTTP 402 paywall lets you charge in USDC per endpoint call while keeping Algorand subscriptions untouched.

## Architecture Overview

| Layer | Highlights |
| --- | --- |
| **Framework** | Django 4, Django REST Framework, SimpleJWT |
| **Ledger & swaps** | Algorand SDK, Tinyman atomic transaction composer |
| **Persistence** | SQLite (dev) / PostgreSQL (prod) |
| **Background ops** | Management commands ready for cron/Celery: trial expiry, renewals, retry queue |
| **Observability** | EventLog for every lifecycle transition, notifications, webhooks |

### Key Django Apps

- `accounts` – Custom user model, profiles, settings, password flows.
- `subscriptions` – Plans, features, price tiers, checkout sessions, invoices, payment intents, lifecycle automation.
  - Coupon management endpoints let operators or merchants mint their own promo codes alongside platform-wide campaigns.
- `payments` – Transaction log, Tinyman swap executor, fee calculation utilities.
- `algorand` – SDK utilities, Tinyman clients, rate quoting, ATC helpers.
  - `contracts/subscription_contract.py` – PyTeal smart contract scaffolding for on-chain subscription state.
- `notifications` – Notification templates and dispatcher (email today, SMS/webhooks tomorrow).
- `webhooks` – Endpoints for external confirmations (e.g., Algorand explorers or partner services).
- `currency`, `integrations`, `analytics` – extension points for FX data, partner APIs, usage dashboards, and now the reusable x402 payment middleware.

## Getting Started

```bash
git clone https://github.com/your-org/subchain_backend.git
cd subchain_backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
python manage.py makemigrations
python manage.py migrate
python manage.py seed_accounts
python manage.py seed_subscriptions
python manage.py runserver
```

### Environment Variables

The `.env.example` file documents all configuration. Key values to review before running the stack:

| Category | Variables |
| --- | --- |
| **Algorand node** | `ALGOD_ADDRESS`, `ALGOD_TOKEN`, `ALGORAND_NETWORK`, `ALGORAND_USDC_ASSET_ID_TESTNET`, `ALGORAND_USDC_ASSET_ID_MAINNET` |
| **Treasury & swaps** | `SUBCHAIN_TREASURY_WALLET_ADDRESS`, `ALGORAND_ACCOUNT_ADDRESS`, `ALGORAND_ACCOUNT_MNEMONIC`, `ALGORAND_DEPLOYER_PRIVATE_KEY`, `PLATFORM_FEE_WALLET_ADDRESS`, `PLATFORM_FEE_PERCENT`, `ALGORAND_SWAP_MAX_RETRIES`, `ALGORAND_SWAP_WAIT_ROUNDS`, `ALGORAND_SWAP_RETRY_DELAY_SECONDS`, `TINYMAN_SWAP_SLIPPAGE` |
| **Micropayments (x402)** | `X402_ENABLED`, `X402_PAYTO_ADDRESS`, `X402_DEFAULT_PRICE`, `X402_PRICING_RULES`, `X402_RECEIPT_VERIFIER`, `X402_CALLBACK_URL`, `X402_NONCE_TTL_SECONDS`, `X402_CURRENCY`, `X402_NETWORK`, `X402_CACHE_ALIAS`, `X402_ASSET_ID`, `X402_ASSET_DECIMALS` |
| **Webhooks** | `WEBHOOK_SECRET` |
| **Celery** | `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`, `CELERY_TASK_ALWAYS_EAGER` (optional for local dev) |
| **NFT minting (optional)** | `NFT_CREATOR_ADDRESS`, `NFT_CREATOR_MNEMONIC` |
| **Frontend / misc.** | `FRONTEND_BASE_URL`, email settings, JWT lifetimes |

Email delivery defaults to the console backend during development. Update `EMAIL_BACKEND` (and credentials) before production launches.

## Operational Commands

| Command | Purpose |
| --- | --- |
| `python manage.py renew_subscriptions` | Process renewals and charge active or past-due subscriptions. |
| `python manage.py retry_failed_payments` | Reattempt Tinyman swaps for invoices stuck in `past_due`. |
| `python manage.py expire_trials` | Convert expired trials to active subs (billing) or mark them `past_due`. |
| `python manage.py seed_accounts` | Populate demo accounts. |
| `python manage.py seed_subscriptions` | Seed Starter/Pro/Enterprise plans for testing. |

These run well under Celery beat, cron, or serverless schedulers.

## API Highlights

- `POST /api/subscriptions/checkout-sessions/` – Issue a signed checkout session for the front-end.
- `POST /api/subscriptions/checkout-sessions/{id}/confirm` – Finalize a session into a subscription/invoice/payment-intent trio.
- `POST /api/subscriptions/` – Direct server-side creation (for trusted services or admin flows).
- `GET/POST /api/subscriptions/coupons/` – Authenticated users can manage their own coupons; staff can manage every campaign.
- `POST /api/invoices/{id}/pay/` – Retry a payment manually.
- `GET /api/events/` – Fetch the audit stream (admin only).

Swagger/OpenAPI docs are available at `/swagger/` once the server is running.

### Developer Tooling

- **Postman collection** – Import `docs/postman/SubChain.postman_collection.json`, set the `base_url`, `email`, and `password` variables, then run the requests in order (login → checkout session → confirm).
- **OpenAPI artifacts** – `python manage.py generateschema --format openapi-json > docs/OpenAPI/openapi.json` (and the YAML variant) keeps the schema current; optional SDKs can be generated with `openapi-generator-cli` into `docs/OpenAPI/client/`.
- **Founder Insights dashboard** – Visit `/admin/founder-insights/` for MRR, churn, and swap volume snapshots (admin login required).
- **Smart contract artifacts** – Generate TEAL for a plan via `python manage.py shell -c "from algorand.contracts.subscription_contract import SubscriptionContractConfig, get_teal_sources; print(get_teal_sources(SubscriptionContractConfig(plan_id=1, price_micro_algo=1000000, renew_interval_rounds=1000, treasury_address='YOURADDRESS')))"` then compile/deploy with the helpers in `algorand.utils`.
- **Celery worker** – Background tasks (webhook swap processing) require `celery -A config worker -l info`; set `CELERY_BROKER_URL`/`CELERY_RESULT_BACKEND` in `.env` (Redis recommended).

### x402 Micropayments

- Manage pay-per-call pricing via `/api/integrations/x402/pricing-rules/` (CRUD) and inspect receipts with `/api/integrations/x402/receipts/`.
- Middleware `integrations.middleware.x402.X402PaymentMiddleware` issues HTTP 402 challenges, validates receipts, and records `PaymentReceipt` entries for replay protection.
- `integrations/verifiers/algorand.verify_receipt` validates USDC transfers on Algorand against your treasury wallet, ready to customize for mainnet/testnet.
- Django admin surfaces pricing rules and receipts so operators can audit payments without leaving the dashboard.
- Front-ends can listen for `402 Payment Required`, trigger a wallet payment, then retry the request with the `X-402-Receipt` header for a seamless user experience.
- Tenants peuvent maintenant créer leurs propres liens (`/api/integrations/x402/links/`) et widgets (`/api/integrations/x402/widgets/`) avec `pay_to_address` et `platform_fee_percent` personnalisés : chaque ressource génère automatiquement une route publique `/paywall/tenant/{id}/links|widgets/{slug}/` et un `PaymentLinkEvent` détaillant commission et net reversé.
- Les packs de crédits sont gérés via `/api/integrations/x402/credit-plans/`, avec suivi des abonnés (`/credit-subscriptions/`) et de la consommation (`/credit-usage/`). L’endpoint public `/paywall/tenant/{id}/credits/{slug}/` crédite automatiquement les comptes clients après paiement tout en appliquant la commission plateforme.
- Une fois les crédits attribués, les équipes peuvent décrémenter le solde via `POST /api/integrations/x402/credit-subscriptions/{id}/consume/` pour tracer la consommation réelle côté backend.

## Testing

```bash
python manage.py test subscriptions
```

Tests cover:

- Model invariants (plans, invoices, subscriptions).
- Service orchestration (lifecycle, invoicing, Tinyman payments, notifications).
- REST endpoints (checkout sessions, subscription creation).
- Coupon access control & authoring.
- Management commands (trial expiry, renewals, payment retries).

Tinyman interactions are mocked so the suite runs offline.

## Roadmap for the Algorand Startup Challenge

1. **Security hardening** – Integrate secret managers (Vault/KMS) for mnemonics, add swap signature monitoring.
2. **Mainnet benchmarks** – Stress-test swaps under load, slippage, and contested rounds.
3. **Developer portal** – Publish SDK snippets, Postman collection, and onboarding guides for Algorand builders.
4. **Usage analytics** – Ship dashboards and webhooks showcasing recurring revenue metrics powered by on-chain data.
5. **Compliance-ready accounting** – Exportable ledgers and reconciliation flows for USDC conversions.

## Contributing & Contact

Issues and pull requests are welcome. For partnership inquiries or to learn more about SubChain’s participation in the Algorand Startup Challenge, reach out at **hello@subchain.xyz**.

Let’s prove that world-class subscription infrastructure can live entirely on Algorand.
### Collecting Customer Details Up Front

Both `/api/subscriptions/` and `/api/subscriptions/checkout-sessions/` now accept rich billing metadata so the checkout form can adapt to individuals or businesses:

```json
{
  "plan_id": 1,
  "wallet_address": "SOMETHING123",
  "customer_type": "business",
  "company_name": "ACME Labs",
  "vat_number": "EU123456789",
  "billing_email": "billing@acme.io",
  "billing_phone": "+33 1 23 45 67 89",
  "billing_address": "15 rue de Rivoli, 75001 Paris",
  "billing_same_as_shipping": false,
  "shipping_address": "Entrepôt ACME, 10 bd Voltaire, 75011 Paris"
}
```

If `customer_type` is `business`, both `company_name` and `vat_number` are required. Set `billing_same_as_shipping` to `false` to capture a dedicated delivery address. Telephone numbers remain optional.
