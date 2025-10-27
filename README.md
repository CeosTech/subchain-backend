# SubChain Backend

SubChain is an API-first subscription and billing engine purpose-built for the Algorand ecosystem. It combines recurring billing primitives, automated Tinyman swaps, lifecycle automation, and customer notifications so founders can launch crypto-native SaaS products without reinventing their payments stack.

This codebase underpins our submission to the **Algorand Startup Challenge**. Our thesis: predictable USDC revenue, powered by Algorand, deserves the same level of polish and developer experience that Web2 founders enjoy with services like Stripe Billing.

## Why SubChain for Algorand

- **Stripe-like subscription model** – Plans, tiers, coupons, invoices, payment intents, and checkout sessions map to familiar billing workflows while remaining token-aware.
- **Tinyman at the core** – Every billing cycle can trigger an automated ALGO → USDC swap, with retries, audit trails, and configurable slippage limits.
- **Operational muscle** – Background jobs cover trial expirations, renewals, and payment retries; event logs keep analytics and external systems in sync.
- **Customer-first notifications** – Email notifications (SMS/webhooks ready) communicate state changes to users and operators automatically.
- **Checkout sessions** – Secure, signed sessions allow front-ends to start subscriptions with wallet confirmation handled server-side.

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
- `payments` – Transaction log, Tinyman swap executor, fee calculation utilities.
- `algorand` – SDK utilities, Tinyman clients, rate quoting, ATC helpers.
- `notifications` – Notification templates and dispatcher (email today, SMS/webhooks tomorrow).
- `webhooks` – Endpoints for external confirmations (e.g., Algorand explorers or partner services).
- `currency`, `integrations`, `analytics` – extension points for FX data, partner APIs, and usage dashboards.

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

The `.env.example` file documents all configuration. Notable Algorand settings:

- `ALGORAND_NETWORK` (`testnet` or `mainnet`)
- `ALGORAND_ACCOUNT_ADDRESS` and `ALGORAND_ACCOUNT_MNEMONIC`
- `ALGO_NODE_URL`, `ALGO_INDEXER_URL`
- `ALGORAND_USDC_ASSET_ID_TESTNET` / `ALGORAND_USDC_ASSET_ID_MAINNET`
- `TINYMAN_SWAP_SLIPPAGE`, `ALGORAND_SWAP_MAX_RETRIES`

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
- `POST /api/invoices/{id}/pay/` – Retry a payment manually.
- `GET /api/events/` – Fetch the audit stream (admin only).

Swagger/OpenAPI docs are available at `/swagger/` once the server is running.

## Testing

```bash
python manage.py test subscriptions
```

Tests cover:

- Model invariants (plans, invoices, subscriptions).
- Service orchestration (lifecycle, invoicing, Tinyman payments, notifications).
- REST endpoints (checkout sessions, subscription creation).
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
