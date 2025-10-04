# algorand/utils.py
import os
from algosdk.v2client import algod
from algosdk import account, mnemonic
from algosdk.transaction import PaymentTxn
from algosdk.atomic_transaction_composer import *
from dotenv import load_dotenv
from tinyman.v1.client import TinymanTestnetClient
from rest_framework.exceptions import APIException


load_dotenv()

ALGOD_ADDRESS = os.getenv("ALGOD_ADDRESS")
ALGOD_TOKEN = os.getenv("ALGOD_TOKEN")
SWAP_ROUTER_ADDRESS = os.getenv("TINYSWAP_ROUTER_ADDRESS")
PLATFORM_WALLET = os.getenv("PLATFORM_WALLET")

algod_client = algod.AlgodClient(ALGOD_TOKEN, ALGOD_ADDRESS)

# ⚠️ ID de l’asset USDC sur TESTNET (à ajuster si tu passes sur mainnet plus tard)
USDC_ASSET_ID_TESTNET = 10458941

def get_algo_to_usdc_rate():
    try:
        client = TinymanTestnetClient(user_address=os.getenv("SUBCHAIN_TREASURY_WALLET_ADDRESS"))
        algo = client.fetch_asset(0)  # ALGO
        usdc = client.fetch_asset(USDC_ASSET_ID_TESTNET)
        pool = client.fetch_pool(algo, usdc)
        quote = pool.fetch_fixed_input_swap_quote(algo, 1_000_000)  # 1 ALGO
        return round(quote.amount_out.amount / 1_000_000, 6)  # Convert to float
    except Exception as e:
        raise APIException(f"Failed to fetch swap rate from Tinyman: {str(e)}")
    
    
def perform_swap_algo_to_usdc(sender_address, sender_private_key, amount_algo, transaction_id=None):
    """
    Effectue le swap de ALGO vers USDC via Tinyman.
    :param sender_address: L'adresse qui envoie les ALGO
    :param sender_private_key: La clé privée de l'expéditeur (gérée en sécurité)
    :param amount_algo: Montant en microAlgos
    :param transaction_id: Optionnel, ID de transaction SubChain
    :return: dict avec les infos du swap ou erreur
    """
    try:
        # Ici on simule l'appel à Tinyman - dans une vraie implémentation on utilise leur SDK
        print(f"🔁 Swapping {amount_algo} microALGO to USDC...")
        
        # ⚠️ À remplacer par logique réelle d'intégration Tinyman
        usdc_received = int(amount_algo * 0.95)  # exemple simple : 5% slippage/frais

        return {
            "status": "success",
            "algo_sent": amount_algo,
            "usdc_received": usdc_received,
            "transaction_id": transaction_id
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
