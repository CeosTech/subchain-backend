# algorand/utils.py
from __future__ import annotations

import logging
import base64
from typing import Iterable, List, Optional

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from algosdk.atomic_transaction_composer import (
    AccountTransactionSigner,
    AtomicTransactionComposer,
    TransactionWithSigner,
)
from algosdk.future.transaction import (
    ApplicationCreateTxn,
    OnComplete,
    StateSchema,
    wait_for_confirmation,
)
from algosdk.v2client import algod
from rest_framework.exceptions import APIException
from tinyman.v1.client import TinymanMainnetClient, TinymanTestnetClient

from algorand.contracts.subscription_contract import (
    SubscriptionContractConfig,
    get_teal_sources,
)

logger = logging.getLogger(__name__)


class TinymanSwapError(Exception):
    """Raised when the Tinyman swap cannot be executed."""


def _assert_setting(value: str, setting_name: str) -> str:
    if not value:
        raise ImproperlyConfigured(f"{setting_name} must be configured before using Algorand services.")
    return value


def get_algod_client() -> algod.AlgodClient:
    """Instantiate an Algod client using project settings."""
    api_token = settings.ALGO_API_TOKEN
    headers = {"X-API-Key": api_token} if api_token else {}
    return algod.AlgodClient(api_token, settings.ALGO_NODE_URL, headers)


def compile_teal_source(teal_source: str, algod_client: Optional[algod.AlgodClient] = None) -> bytes:
    """Compile TEAL source code using the configured Algod client."""
    algod_client = algod_client or get_algod_client()
    response = algod_client.compile(teal_source)
    return base64.b64decode(response["result"])


def compile_subscription_contract(
    cfg: SubscriptionContractConfig,
    algod_client: Optional[algod.AlgodClient] = None,
) -> dict:
    """Compile subscription contract approval and clear programs to binary."""
    sources = get_teal_sources(cfg)
    algod_client = algod_client or get_algod_client()
    approval = compile_teal_source(sources["approval"], algod_client)
    clear = compile_teal_source(sources["clear"], algod_client)
    return {"approval": approval, "clear": clear, "sources": sources}


def deploy_subscription_contract(
    cfg: SubscriptionContractConfig,
    algod_client: Optional[algod.AlgodClient] = None,
) -> int:
    """Deploy the subscription smart contract and return the app ID."""
    algod_client = algod_client or get_algod_client()
    compiled = compile_subscription_contract(cfg, algod_client)

    params = algod_client.suggested_params()
    params.flat_fee = True
    params.fee = params.min_fee * 2

    txn = ApplicationCreateTxn(
        sender=settings.ALGORAND_ACCOUNT_ADDRESS,
        sp=params,
        on_complete=OnComplete.NoOpOC,
        approval_program=compiled["approval"],
        clear_program=compiled["clear"],
        global_schema=StateSchema(num_uints=4, num_byte_slices=1),
        local_schema=StateSchema(num_uints=1, num_byte_slices=1),
    )

    private_key = getattr(settings, "ALGORAND_DEPLOYER_PRIVATE_KEY", None)
    if not private_key:
        raise ImproperlyConfigured("ALGORAND_DEPLOYER_PRIVATE_KEY must be set to deploy contracts.")

    signed_txn = txn.sign(private_key)
    tx_id = algod_client.send_transaction(signed_txn)
    wait_rounds = getattr(settings, "ALGORAND_APP_WAIT_ROUNDS", 4)
    wait_for_confirmation(algod_client, tx_id, wait_rounds)
    response = algod_client.pending_transaction_info(tx_id)
    app_id = response.get("application-index")
    if not app_id:
        raise RuntimeError("Failed to deploy subscription contract")
    return app_id


def _resolve_usdc_asset_id() -> int:
    network = getattr(settings, "ALGORAND_NETWORK", "testnet").lower()
    if network == "mainnet":
        return int(getattr(settings, "ALGORAND_USDC_ASSET_ID_MAINNET", 31566704))
    return int(getattr(settings, "ALGORAND_USDC_ASSET_ID_TESTNET", 10458941))


def get_tinyman_client(user_address: str, algod_client: algod.AlgodClient | None = None):
    """Return the proper Tinyman client according to the configured network."""
    if not user_address:
        raise ImproperlyConfigured("user_address is required to instantiate the Tinyman client.")

    network = getattr(settings, "ALGORAND_NETWORK", "testnet").lower()
    algod_client = algod_client or get_algod_client()

    if network == "mainnet":
        return TinymanMainnetClient(user_address=user_address, algod_client=algod_client)
    return TinymanTestnetClient(user_address=user_address, algod_client=algod_client)


def _extract_transactions(group) -> List[TransactionWithSigner]:
    if isinstance(group, (list, tuple)):
        items: Iterable = group
    elif hasattr(group, "transactions"):
        items = group.transactions
    else:
        raise TinymanSwapError("Unexpected Tinyman transaction group format.")

    transactions: List = []
    for item in items:
        if isinstance(item, TransactionWithSigner):
            transactions.append(item)
        elif hasattr(item, "transaction"):  # Tinyman wrapper exposing transaction attribute
            signer = getattr(item, "signer", None)
            if signer is not None:
                transactions.append(TransactionWithSigner(item.transaction, signer))
            else:
                transactions.append(item.transaction)
        else:
            transactions.append(item)
    return transactions


def _execute_transaction_group(group, private_key: str, algod_client: algod.AlgodClient):
    signer = AccountTransactionSigner(private_key)
    composer = AtomicTransactionComposer()

    for element in _extract_transactions(group):
        if isinstance(element, TransactionWithSigner):
            composer.add_transaction(element)
        else:
            composer.add_transaction(TransactionWithSigner(element, signer))

    wait_rounds = getattr(settings, "ALGORAND_SWAP_WAIT_ROUNDS", 4)
    result = composer.execute(algod_client, wait_rounds)
    return {"tx_ids": result.tx_ids, "confirmed_round": result.confirmed_round}


def _ensure_user_setup(client, private_key: str, algod_client: algod.AlgodClient, usdc_asset):
    """Ensure the Tinyman user is opted-in to the protocol and the USDC asset."""
    try:
        is_opted_in = getattr(client, "is_opted_in")
        if callable(is_opted_in) and not is_opted_in():
            logger.info("Opting Tinyman account into the protocol.")
            tx_group = client.prepare_opt_in_transactions()
            _execute_transaction_group(tx_group, private_key, algod_client)
    except AttributeError:
        logger.debug("Tinyman client does not expose opt-in helper.")

    try:
        is_asset_opted = getattr(client, "is_opted_in_to_asset")
        if callable(is_asset_opted) and not is_asset_opted(usdc_asset):
            logger.info("Opting Tinyman account into USDC asset %s.", usdc_asset)
            tx_group = client.prepare_asset_opt_in_transactions(usdc_asset)
            _execute_transaction_group(tx_group, private_key, algod_client)
    except AttributeError:
        logger.debug("Tinyman client does not expose asset opt-in helper.")


def get_algo_to_usdc_rate() -> float:
    """Fetch the ALGO→USDC quote using Tinyman."""
    address = _assert_setting(getattr(settings, "ALGORAND_ACCOUNT_ADDRESS", ""), "ALGORAND_ACCOUNT_ADDRESS")
    algod_client = get_algod_client()
    client = get_tinyman_client(address, algod_client)
    try:
        algo_asset = client.fetch_asset(0)
        usdc_asset = client.fetch_asset(_resolve_usdc_asset_id())
        pool = client.fetch_pool(algo_asset, usdc_asset)
        quote = pool.fetch_fixed_input_swap_quote(algo_asset(1_000_000), slippage=settings.TINYMAN_SWAP_SLIPPAGE)
        return round(quote.amount_out.amount / 1_000_000, 6)
    except Exception as exc:
        logger.exception("Unable to fetch ALGO→USDC rate via Tinyman.")
        raise APIException(f"Failed to fetch swap rate from Tinyman: {exc}") from exc


def perform_swap_algo_to_usdc(
    sender_address: str,
    sender_private_key: str,
    amount_algo: int,
    transaction_id: int | None = None,
):
    """
    Execute an ALGO ➜ USDC swap via Tinyman using the provided credentials.

    :param sender_address: Algorand address funding the swap (must be Tinyman ready)
    :param sender_private_key: Private key matching the sender address
    :param amount_algo: Amount in microAlgos to swap
    :param transaction_id: Optional SubChain transaction identifier used for logging
    """
    if sender_address is None or sender_private_key is None:
        raise ImproperlyConfigured("Sender credentials are required to perform a Tinyman swap.")
    if amount_algo is None:
        raise ValueError("amount_algo is required to perform the swap.")

    algod_client = get_algod_client()
    client = get_tinyman_client(sender_address, algod_client)
    usdc_asset = client.fetch_asset(_resolve_usdc_asset_id())

    try:
        _ensure_user_setup(client, sender_private_key, algod_client, usdc_asset)

        algo_asset = client.fetch_asset(0)  # ALGO native asset
        pool = client.fetch_pool(algo_asset, usdc_asset)
        quote = pool.fetch_fixed_input_swap_quote(
            algo_asset(amount_algo),
            slippage=settings.TINYMAN_SWAP_SLIPPAGE,
        )

        logger.info(
            "Executing Tinyman swap for transaction=%s amount=%sµALGO expected=%sµUSDC",
            transaction_id,
            amount_algo,
            quote.amount_out.amount,
        )

        tx_group = client.prepare_swap_transactions_from_quote(
            quote, slippage=settings.TINYMAN_SWAP_SLIPPAGE
        )
        submission = _execute_transaction_group(tx_group, sender_private_key, algod_client)

        return {
            "status": "success",
            "algo_sent": amount_algo,
            "usdc_received": quote.amount_out.amount,
            "transaction_id": transaction_id,
            "tx_ids": submission["tx_ids"],
            "confirmed_round": submission["confirmed_round"],
        }
    except Exception as exc:  # pragma: no cover - unexpected Tinyman/Algorand errors
        logger.exception("Tinyman swap failed for transaction=%s", transaction_id)
        raise TinymanSwapError(str(exc)) from exc
