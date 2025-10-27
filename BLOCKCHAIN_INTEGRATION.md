Voici un fichier `BLOCKCHAIN_INTEGRATION.md` 📄 en **Markdown** pour documenter clairement comment ajouter la **Binance Smart Chain (BNB Chain)** et créer un **token BEP-20 (comme BNB ou ton propre coin)** dans un projet comme `SubChain`.

---

````md
# 📦 BLOCKCHAIN_INTEGRATION.md

## 🔗 Intégration Blockchain – Binance Smart Chain (BNB)

Ce document explique comment intégrer la BNB Chain (ex Binance Smart Chain) dans un projet Django (comme SubChain) pour :
- Ajouter un token BEP-20 (BNB ou token personnalisé)
- Suivre des paiements en BNB
- Déclencher des actions backend (webhooks, swaps, enregistrements…)

---

## ✅ Prérequis

- Python 3.10+
- Web3.py (`pip install web3`)
- Un **nœud BSC RPC** : ex. `https://bsc-dataseed.binance.org/`
- Un wallet BNB (Metamask, Ledger…)
- Un compte BSCScan (facultatif pour l’API)

---

## 📍 Étapes d'intégration

### 1. 📁 Créer un fichier `bnb_config.py` dans une app (ex. `bnb/`)

```python
from web3 import Web3
import os

BSC_RPC_URL = os.getenv("BSC_RPC_URL", "https://bsc-dataseed.binance.org/")
w3 = Web3(Web3.HTTPProvider(BSC_RPC_URL))

# Ton token personnalisé (ou BNB natif)
TOKEN_CONTRACT_ADDRESS = Web3.to_checksum_address("0x...")  # adresse du token BEP-20
TOKEN_ABI = [...]  # ABI du token (copié depuis BscScan)

def get_balance(address):
    address = Web3.to_checksum_address(address)
    contract = w3.eth.contract(address=TOKEN_CONTRACT_ADDRESS, abi=TOKEN_ABI)
    balance = contract.functions.balanceOf(address).call()
    return balance / 10**18  # dépend des décimales du token
````

---

### 2. 🔍 Vérifier les transactions entrantes

Dans une `management command` ou un `cron job`, tu peux détecter les transferts :

```python
def check_incoming_transactions(wallet_address):
    latest = w3.eth.get_block('latest')
    for tx_hash in latest.transactions:
        tx = w3.eth.get_transaction(tx_hash)
        if tx.to and tx.to.lower() == wallet_address.lower():
            print(f"💰 Paiement reçu en BNB : {tx.value / 10**18} BNB")
```

---

### 3. 🔁 Gérer les swaps vers USDT/USDC (via PancakeSwap)

Utilise l'**ABI du Router PancakeSwap** :

```python
ROUTER_ADDRESS = Web3.to_checksum_address("0x...")  # PancakeSwap Router V2
ROUTER_ABI = [...]  # Copier depuis BscScan

router = w3.eth.contract(address=ROUTER_ADDRESS, abi=ROUTER_ABI)

# Exemple : swapExactETHForTokens
tx = router.functions.swapExactETHForTokens(
    0,  # min amount
    [BNB_ADDRESS, USDC_ADDRESS],
    RECEIVER_WALLET,
    int(time.time()) + 300
).build_transaction({
    'from': WALLET_ADDRESS,
    'value': w3.to_wei(0.01, 'ether'),
    'gas': 300000,
    'nonce': w3.eth.get_transaction_count(WALLET_ADDRESS),
})
```

---

## 🧠 Astuces Dev

* Utiliser `dotenv` pour sécuriser les clés privées.
* Toujours convertir en `Web3.to_checksum_address(addr)`
* Vérifie le `nonce`, `gas`, et `chainId=56` (mainnet BSC)
* Pour testnet : `https://data-seed-prebsc-1-s1.binance.org:8545`

---

## 🔒 Sécurité

* Ne jamais hardcoder les **private keys** dans le code.
* Utiliser un wallet dédié pour recevoir les paiements.
* Mettre en place un système de **confirmation par webhook + retries**.

---

## 🚀 Pour aller plus loin

* 🔁 Swaps automatisés avec Web3 + PancakeSwap
* 📩 Webhooks pour notifier le backend (ex : `/api/payments/confirm/`)
* 🧾 Génération automatique de factures après paiement BNB
* 💬 Intégration avec Telegram ou Discord (alertes paiements)
* 🛠️ DAO + staking (via smart contracts custom)

---

## 📚 Ressources utiles

* [Docs Web3.py](https://web3py.readthedocs.io/en/stable/)
* [BSCScan](https://bscscan.com/)
* [PancakeSwap Router ABI](https://bscscan.com/address/0x...#code)
* [Créer un token BEP-20](https://docs.binance.org/smart-chain/developer.html)

---

```

Souhaites-tu que je te génère le code du smart contract BEP-20 aussi, ou uniquement la partie backend Django ?
```
Voici un **smart contract BEP-20** simple et propre pour créer ton propre token sur **Binance Smart Chain** (BNB Chain).
✅ Compatible avec **mainnet** ou **testnet**, écrit en Solidity 0.8+.

---

## 📄 `MyToken.sol` — BEP-20 Token Standard

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// Interface ERC20 standard
interface IERC20 {
    function totalSupply() external view returns (uint256);
    function balanceOf(address account) external view returns (uint256);
    function transfer(address recipient, uint256 amount) external returns (bool);
    
    function allowance(address owner, address spender) external view returns (uint256);
    function approve(address spender, uint256 amount) external returns (bool);
    function transferFrom(address sender, address recipient, uint256 amount) external returns (bool);
    
    event Transfer(address indexed from, address indexed to, uint256 value);
    event Approval(address indexed owner, address indexed spender, uint256 value);
}

// Contexte d'exécution
abstract contract Context {
    function _msgSender() internal view virtual returns (address) {
        return msg.sender;
    }
}

// Implémentation de base de l'ERC20
contract MyToken is Context, IERC20 {
    string public name = "My Token";
    string public symbol = "MTK";
    uint8 public decimals = 18;
    uint256 private _totalSupply;

    address public owner;

    mapping(address => uint256) private _balances;
    mapping(address => mapping(address => uint256)) private _allowances;

    modifier onlyOwner() {
        require(_msgSender() == owner, "Not owner");
        _;
    }

    constructor(uint256 initialSupply) {
        owner = _msgSender();
        _mint(owner, initialSupply * 10 ** uint256(decimals));
    }

    function totalSupply() public view override returns (uint256) {
        return _totalSupply;
    }

    function balanceOf(address account) public view override returns (uint256) {
        return _balances[account];
    }

    function transfer(address recipient, uint256 amount) public override returns (bool) {
        _transfer(_msgSender(), recipient, amount);
        return true;
    }

    function allowance(address owner_, address spender) public view override returns (uint256) {
        return _allowances[owner_][spender];
    }

    function approve(address spender, uint256 amount) public override returns (bool) {
        _approve(_msgSender(), spender, amount);
        return true;
    }

    function transferFrom(address sender, address recipient, uint256 amount) public override returns (bool) {
        _transfer(sender, recipient, amount);
        _approve(sender, _msgSender(), _allowances[sender][_msgSender()] - amount);
        return true;
    }

    // 🔒 Mint tokens (owner only)
    function mint(address account, uint256 amount) public onlyOwner {
        _mint(account, amount);
    }

    // 🔒 Burn tokens (owner only)
    function burn(address account, uint256 amount) public onlyOwner {
        _burn(account, amount);
    }

    // 🔁 Internal logic

    function _transfer(address sender, address recipient, uint256 amount) internal {
        require(sender != address(0) && recipient != address(0), "Invalid address");
        require(_balances[sender] >= amount, "Insufficient balance");
        
        _balances[sender] -= amount;
        _balances[recipient] += amount;
        
        emit Transfer(sender, recipient, amount);
    }

    function _mint(address account, uint256 amount) internal {
        require(account != address(0), "Mint to zero");
        _totalSupply += amount;
        _balances[account] += amount;
        emit Transfer(address(0), account, amount);
    }

    function _burn(address account, uint256 amount) internal {
        require(account != address(0), "Burn from zero");
        require(_balances[account] >= amount, "Burn exceeds balance");
        _balances[account] -= amount;
        _totalSupply -= amount;
        emit Transfer(account, address(0), amount);
    }

    function _approve(address owner_, address spender, uint256 amount) internal {
        require(owner_ != address(0) && spender != address(0), "Zero address");
        _allowances[owner_][spender] = amount;
        emit Approval(owner_, spender, amount);
    }
}
```

---

## 🚀 Déploiement rapide (Hardhat)

### 1. Créer un projet Hardhat

```bash
npm init -y
npm install --save-dev hardhat
npx hardhat
```

Choisis **"Create a basic sample project"**.

### 2. Ajouter le contrat dans `contracts/MyToken.sol`

Puis compile :

```bash
npx hardhat compile
```

### 3. Script de déploiement (`scripts/deploy.js`)

```js
async function main() {
  const [deployer] = await ethers.getSigners();

  const MyToken = await ethers.getContractFactory("MyToken");
  const token = await MyToken.deploy(1000000);  // 1M tokens

  console.log("Token deployed to:", token.address);
}

main()
  .then(() => process.exit(0))
  .catch((err) => {
    console.error(err);
    process.exit(1);
  });
```

### 4. Déployer sur testnet BSC

Ajoute `bscTestnet` dans `hardhat.config.js` :

```js
require("@nomiclabs/hardhat-ethers");

module.exports = {
  networks: {
    bscTestnet: {
      url: "https://data-seed-prebsc-1-s1.binance.org:8545",
      chainId: 97,
      accounts: ["0xTON_PRIVATE_KEY"], // ⚠️ Ne JAMAIS exposer ta vraie clé
    },
  },
  solidity: "0.8.20",
};
```

Puis :

```bash
npx hardhat run scripts/deploy.js --network bscTestnet
```

---

## 🪙 Résultat

Tu auras un **token BEP-20** fonctionnel, avec :

* ✅ Transferts
* ✅ Approve / Allowance
* ✅ Mint / Burn (owner only)
* 📦 Compatible PancakeSwap

---

Souhaite-tu que je te génère maintenant ce contrat depuis **Vercel v0**, ou l’ajouter dans un `.sol` et `.md` dans ton repo GitHub ?
