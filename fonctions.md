✅ Fonctions clés

Paiement en $ALGO avec conversion automatique

Webhooks de renouvellement

Auth par email + vérification + reset

Notifications personnalisées (email / in-app)

Gestion des plans et périodes d’essai

🔐 Admin
email: admin@subchain.app
mot de passe : admin123


---

### 📚 3. `DOC_MODELS.md`

```markdown
# 📘 Documentation des modèles

## 👤 accounts.User
- email
- is_active / is_staff
- wallet_address

## 📧 accounts.EmailVerification
- token
- user (FK)
- expiration

## 💳 subscriptions.SubscriptionPlan
- name / description
- price / currency
- trial_days
- is_active

## 📥 subscriptions.Subscriber
- user (FK)
- plan (FK)
- status (trialing / active / cancelled)
- renewal_date
- trial_end_date

## 🔄 subscriptions.PlanChangeLog
- subscriber (FK)
- previous_plan (FK)
- new_plan (FK)

## 💰 payments.Transaction
- subscriber (FK)
- algo_amount / usdc_amount
- status (pending / swapped)
- platform_fee
- timestamps

## 🌐 algorand.swap (util)
- `perform_swap_algo_to_usdc()` : simule le swap ALGO → USDC avec slippage

## 🔁 webhooks.renewal
- Appelle le swap + renouvelle automatiquement l’abonnement

## 📩 notifications.NotificationTemplate
- slug / subject / content
- is_active