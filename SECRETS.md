# 🔐 Gestion des clés secrètes

Toutes les variables sensibles sont stockées dans un fichier `.env` **non commit dans Git**.

## Variables essentielles

| Nom | Utilité |
|-----|---------|
| DJANGO_SECRET_KEY | Clé secrète de l’application |
| ALGOD_ADDRESS | Endpoint API Algorand |
| ALGOD_TOKEN | Token d’accès Algorand |
| SUBCHAIN_TREASURY_WALLET_ADDRESS | Wallet principal SubChain |
| PLATFORM_FEE_WALLET_ADDRESS | Wallet pour les commissions |
| PLATFORM_FEE_PERCENT | Pourcentage prélevé sur chaque transaction |
| TINYSWAP_ROUTER_ADDRESS | Adresse du contrat Tinyman |

## 🔒 Comment récupérer les clés Algorand

1. Créez un wallet sur [https://wallet.myalgo.com](https://wallet.myalgo.com)
2. Récupérez la **clé mnémotechnique** (à ne jamais exposer publiquement)
3. Utilisez `algosdk` pour signer les transactions localement

Ne jamais versionner `.env` ou votre clé privée Algorand dans Git.



Très bien Laurent — voici un **guide détaillé** pour chaque variable `.env` de ton projet SubChain, ainsi que les liens utiles pour récupérer ou configurer les clés Algorand. Ce guide sera ton `SECRETS.md` bien structuré 👇

---

# 🔐 Gestion des clés secrètes – SubChain

Toutes les variables sensibles sont stockées dans le fichier `.env`. **Ne jamais le versionner** dans Git (ajouté dans `.gitignore`).

---

## 📦 Variables essentielles et comment les obtenir/configurer

| **Variable**                       | **Utilité**                                                           | **Comment la récupérer/configurer**                                                                                                                                                                                |
| ---------------------------------- | --------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `DJANGO_SECRET_KEY`                | Clé secrète utilisée par Django pour signer les cookies, tokens, etc. | Générer avec :<br>`python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`<br>💡 À stocker dans `.env` sous `DJANGO_SECRET_KEY=...`                            |
| `ALGOD_ADDRESS`                    | URL de l’API publique Algorand (TestNet ou MainNet)                   | Utiliser un nœud public stable :<br>🔗 [https://docs.algonode.io](https://docs.algonode.io)<br>Ex pour testnet :<br>`ALGOD_ADDRESS=https://testnet-api.algonode.cloud`                                             |
| `ALGOD_TOKEN`                      | Token d’accès API à ton nœud Algorand                                 | Pour Algonode public, tu peux utiliser une chaîne de 64 `a` :<br>`ALGOD_TOKEN=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa`<br>Si tu utilises ton propre nœud : récupère-le dans `algod.token` |
| `SUBCHAIN_TREASURY_WALLET_ADDRESS` | Adresse publique du wallet qui reçoit tous les paiements en ALGO      | Crée un wallet (voir section ci-dessous) et colle l’adresse ici.<br>Format : `ALGO_...`                                                                                                                            |
| `PLATFORM_FEE_WALLET_ADDRESS`      | Adresse publique du wallet où sont envoyés les frais de commission    | Même méthode que pour le treasury wallet. Tu peux créer un second wallet ou utiliser une autre clé du même compte.                                                                                                 |
| `PLATFORM_FEE_PERCENT`             | Pourcentage de frais de plateforme prélevé à chaque paiement          | Ex : `5.0` pour 5 %<br>À modifier selon ton business model.                                                                                                                                                        |
| `TINYSWAP_ROUTER_ADDRESS`          | Adresse du smart contract Tinyman utilisé pour les swaps ALGO → USDC  | Pour testnet, tu peux simuler. Pour la version live : voir [https://docs.tinyman.org](https://docs.tinyman.org) pour obtenir l'adresse du router (en fonction de la version V1/V2/V3).                             |

---

## 🔒 Créer un wallet Algorand sécurisé (pour testnet ou mainnet)

### 🔧 Étape 1 – Créer le wallet

1. Va sur [https://wallet.myalgo.com](https://wallet.myalgo.com)
2. Clique sur **Create Wallet**
3. Note soigneusement la **mnemonic phrase** (25 mots)
4. Tu verras ensuite ton **wallet address** (commence par `ALGO_...` ou `X...`)

> 💡 **Conseil** : pour testnet, utilise aussi [https://testnet.algoexplorer.io/dispenser](https://testnet.algoexplorer.io/dispenser) pour récupérer des ALGO de test gratuitement.

---

## 🔑 Utiliser la clé mnémotechnique pour signer des transactions

Ne jamais inclure ta clé privée ou mnémotechnique dans le code source. Utilise les outils `algosdk` pour importer ta clé en local :

```python
from algosdk import account, mnemonic

mnemo = os.getenv("WALLET_MNEMONIC")
private_key = mnemonic.to_private_key(mnemo)
address = account.address_from_private_key(private_key)
```

Dans ton fichier `.env` local uniquement :

```env
WALLET_MNEMONIC="paddle shadow lucky ... "  # 25 mots
```

---

## 🚨 Sécurité absolue

* **NE STOCKE JAMAIS** ta mnemonic phrase dans Git, même dans un fichier oublié.
* Ajoute bien `.env` à ton `.gitignore`
* Ne loggue **jamais** une clé privée ou un mnemonic dans une console ou un fichier de log
* En production, stocke toutes les clés dans un **vault** sécurisé :
  🔐 AWS Secrets Manager, Google Secret Manager, Railway, Heroku Config Vars...

---

## 📎 Liens utiles

* 🧠 Docs Algorand : [https://developer.algorand.org](https://developer.algorand.org)
* 🔐 Créer un wallet : [https://wallet.myalgo.com](https://wallet.myalgo.com)
* 💧 Faucet testnet : [https://testnet.algoexplorer.io/dispenser](https://testnet.algoexplorer.io/dispenser)
* 🔁 Tinyman SDK : [https://docs.tinyman.org](https://docs.tinyman.org)
* 🔗 Algonode (nœuds publics) : [https://docs.algonode.io](https://docs.algonode.io)

---

Souhaites-tu aussi que je génère un `make_wallet.py` simple pour créer un wallet en CLI avec sauvegarde sécurisée ?
