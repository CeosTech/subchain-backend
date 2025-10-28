"""PyTeal smart contract primitives for subscription management."""
from __future__ import annotations

from dataclasses import dataclass

from pyteal import (
    Addr,
    And,
    App,
    Bytes,
    Cond,
    Global,
    Int,
    Mode,
    OnComplete,
    Return,
    Seq,
    Txn,
    compileTeal,
)


PLAN_KEY = Bytes("plan_id")
PRICE_KEY = Bytes("price")
INTERVAL_KEY = Bytes("interval")
TREASURY_KEY = Bytes("treasury")

STATUS_KEY = Bytes("status")
NEXT_RENEWAL_KEY = Bytes("next")

STATUS_ACTIVE = Bytes("active")
STATUS_CANCELLED = Bytes("cancelled")


@dataclass
class SubscriptionContractConfig:
    plan_id: int
    price_micro_algo: int
    renew_interval_rounds: int
    treasury_address: str


def approval_program(cfg: SubscriptionContractConfig):
    """Approval program storing plan metadata and user status."""

    is_creator = Txn.sender() == Global.creator_address()

    on_create = Seq(
        App.globalPut(PLAN_KEY, Int(cfg.plan_id)),
        App.globalPut(PRICE_KEY, Int(cfg.price_micro_algo)),
        App.globalPut(INTERVAL_KEY, Int(cfg.renew_interval_rounds)),
        App.globalPut(TREASURY_KEY, Addr(cfg.treasury_address)),
        Return(Int(1)),
    )

    opt_in = Seq(renew_user_state(), Return(Int(1)))

    register = Seq(renew_user_state(), Return(Int(1)))

    renew = Seq(
        App.localPut(Txn.sender(), STATUS_KEY, STATUS_ACTIVE),
        App.localPut(
            Txn.sender(),
            NEXT_RENEWAL_KEY,
            Global.round() + App.globalGet(INTERVAL_KEY),
        ),
        Return(Int(1)),
    )

    cancel = Seq(
        App.localPut(Txn.sender(), STATUS_KEY, STATUS_CANCELLED),
        Return(Int(1)),
    )

    has_args = Txn.application_args.length() > Int(0)

    return Cond(
        [Txn.application_id() == Int(0), on_create],
        [Txn.on_completion() == OnComplete.OptIn, opt_in],
        [Txn.on_completion() == OnComplete.CloseOut, Return(Int(1))],
        [Txn.on_completion() == OnComplete.UpdateApplication, Return(is_creator)],
        [Txn.on_completion() == OnComplete.DeleteApplication, Return(is_creator)],
        [And(has_args, Txn.application_args[0] == Bytes("register")), register],
        [And(has_args, Txn.application_args[0] == Bytes("renew")), renew],
        [And(has_args, Txn.application_args[0] == Bytes("cancel")), cancel],
    )


def renew_user_state():
    return Seq(
        App.localPut(Txn.sender(), STATUS_KEY, STATUS_ACTIVE),
        App.localPut(
            Txn.sender(),
            NEXT_RENEWAL_KEY,
            Global.round() + App.globalGet(INTERVAL_KEY),
        ),
    )


def clear_state_program():
    return Return(Int(1))


def get_teal_sources(cfg: SubscriptionContractConfig, version: int = 8) -> dict[str, str]:
    """Compile PyTeal to TEAL source strings."""
    approval_teal = compileTeal(approval_program(cfg), mode=Mode.Application, version=version)
    clear_teal = compileTeal(clear_state_program(), mode=Mode.Application, version=version)
    return {"approval": approval_teal, "clear": clear_teal}
