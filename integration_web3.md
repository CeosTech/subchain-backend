# 📦 Web3 Integration Guide – SubChain (BSC + Starknet)

Bienvenue dans la documentation d'intégration Web3 pour le projet **SubChain**. Ce guide couvre l'écosystème hybride avec support à la fois pour **Binance Smart Chain (BEP-20)** et **Starknet (receipts, ZK-proof)**.

---

## ✅ Objectifs

* Gérer des abonnements Web3 (plans, paiements, récépissés)
* Accepter des paiements en **BNB / BUSD (BSC)**
* Générer des preuves et certificats d'abonnement sur **Starknet**
* Tester en local avec faux wallets (mock)
* Activer le testnet ou le mainnet plus tard sans reconfiguration majeure

---

## 🌱 Modes d’intégration supportés

| Mode         | Description                      | Usage                           |
| ------------ | -------------------------------- | ------------------------------- |
| `local-mock` | Faux wallets pour dev local      | Dev rapide sans RPC             |
| `testnet`    | Connexion à RPC de test          | Test de réseaux publics         |
| `mainnet`    | Intégration réelle en production | À activer après audit + go-live |

---

## 🔐 Variables d’environnement

Ajoute ces lignes à ton fichier `.env` ou `.env.local` pour démarrer :

```env
# Mode
WEB3_MODE=local-mock

# Fake wallets (dev only)
FAKE_USER_WALLET=0xFAKE123456789
FAKE_TREASURY_WALLET=0xFAKETREASURY

# Binance Smart Chain
BSC_CHAIN_ID=97
BSC_RPC_URL=https://data-seed-prebsc-1-s1.binance.org:8545
BNB_TOKEN_ADDRESS=0x...
USDC_TOKEN_ADDRESS=0x...

# Starknet
STARKNET_RPC_URL=https://alpha4.starknet.io
STARKNET_CONTRACT_ADDRESS=0x...
```

---

## 🧪 Structure de test local (mock)

### 1. Python - `scripts/mock_wallet.py`

Simule un wallet local (sans appel RPC)

```python
# scripts/mock_wallet.py
from eth_account import Account
Account.enable_unaudited_hdwallet_features()
w = Account.create()
print(f"Wallet address: {w.address}")
print(f"Private key: {w.key.hex()}")
```

### 2. Python - `scripts/test_subscription.py`

```python
import requests

response = requests.post("http://localhost:8000/api/subscriptions/subscribe/", json={
    "wallet_address": "0xFAKE123456789",
    "plan_id": 1
})
print(response.json())
```

### 3. TypeScript - `lib/starknet-client.ts`

```ts
export async function issueReceipt(user: string, planId: number) {
  return fetch("/api/starknet/issue_receipt/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user, plan_id: planId })
  }).then(res => res.json())
}
```

---

## 🚀 Passage en Testnet (Starknet + BSC)

1. Modifie `.env` :

```env
WEB3_MODE=testnet
```

2. Utilise des wallets Metamask + Starknet Wallet (Braavos / Argent X)

3. Configure les bonnes adresses de contrat dans `.env`

4. Active le swap token sur testnet si nécessaire (Tinyman, PancakeSwap)

---

## 🔄 Passage en Mainnet

* Webhooks signés + vérifiés
* Audit des smart contracts
* Système de multisig (Gnosis Safe)
* Télémétrie + alertes (Sentry / Prometheus)

---

## 🛠 Smart Contract à connecter

* [ ] Starknet: `SubscriptionReceipt` (cairo)
* [ ] BSC: `PaymentProcessor` (solidity, BNB/USDC)
* [ ] Bridge prévu : `receipt_to_nft`

---

## 📍 Roadmap

* [x] Mock wallet + test local
* [x] Appels Django backend
* [x] Client Next.js
* [ ] Testnet sur Starknet
* [ ] Testnet sur BSC
* [ ] Intégration Tinyman / PancakeSwap
* [ ] Mint d’un NFT de récépissé
* [ ] Passage mainnet avec multisig

---

Tu peux maintenant démarrer le test sans dépendance externe.

Souhaite-tu que je génère les 3 fichiers suivants ?

* `.env.local`
* `mock_wallet.py`
* `test_subscription.py`

Ou préfères-tu un package ZIP de démo ?
