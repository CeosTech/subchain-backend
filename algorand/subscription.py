from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from algosdk import account
try:
    from algosdk.future import transaction  # Compat with older SDKs
except ModuleNotFoundError:  # pragma: no cover - py-algorand-sdk >=2.0
    from algosdk import transaction
from algosdk.v2client import algod

from django.conf import settings

from subscriptions.models import Plan, Subscription

from .contracts.subscription_contract import SubscriptionContractConfig
from .utils import deploy_subscription_contract, get_algod_client


@dataclass
class SubscriptionAccount:
    address: str
    private_key: str


def get_subscription_config(plan: Plan, interval_rounds: int) -> SubscriptionContractConfig:
    return SubscriptionContractConfig(
        plan_id=plan.id,
        price_micro_algo=int(plan.amount * 1_000_000),
        renew_interval_rounds=interval_rounds,
        treasury_address=settings.ALGORAND_ACCOUNT_ADDRESS,
    )


def deploy_plan_contract(plan: Plan, interval_rounds: int = 30 * 60) -> int:
    cfg = get_subscription_config(plan, interval_rounds)
    app_id = deploy_subscription_contract(cfg)
    plan.contract_app_id = app_id
    plan.save(update_fields=["contract_app_id"])
    return app_id


def opt_in_subscription(subscription: Subscription, subscription_account: SubscriptionAccount, interval_rounds: int = 30 * 60):
    if not subscription.plan.contract_app_id:
        deploy_plan_contract(subscription.plan, interval_rounds)

    algod_client = get_algod_client()
    params = algod_client.suggested_params()
    txn = transaction.ApplicationOptInTxn(
        sender=subscription_account.address,
        sp=params,
        index=subscription.plan.contract_app_id,
        app_args=[b"register"],
    )
    signed = txn.sign(subscription_account.private_key)
    tx_id = algod_client.send_transaction(signed)
    transaction.wait_for_confirmation(algod_client, tx_id, 4)


def renew_subscription_app(subscription: Subscription, subscription_account: SubscriptionAccount):
    if not subscription.plan.contract_app_id:
        raise ValueError("Plan does not have a deployed contract")

    algod_client = get_algod_client()
    params = algod_client.suggested_params()
    txn = transaction.ApplicationNoOpTxn(
        sender=subscription_account.address,
        sp=params,
        index=subscription.plan.contract_app_id,
        app_args=[b"renew"],
    )
    signed = txn.sign(subscription_account.private_key)
    tx_id = algod_client.send_transaction(signed)
    transaction.wait_for_confirmation(algod_client, tx_id, 4)
