from __future__ import annotations

import json
import logging
import secrets
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, Iterable, Optional

from django.conf import settings
from django.core.cache import caches
from django.core.cache.backends.base import InvalidCacheBackendError
from django.db import IntegrityError
from django.core.exceptions import ImproperlyConfigured
from django.http import HttpRequest
from django.utils.module_loading import import_string

from .models import (
    EndpointPricingRule,
    PaymentLink,
    PaymentReceipt,
    PaymentReceiptStatus,
    X402CreditPlan,
)
from .services import apply_credit_top_up, record_payment_link_event


logger = logging.getLogger(__name__)

_PRICING_RULES_CACHE: tuple[str, list["PricingRule"]] = ("", [])
_DEFAULT_PRICE_CACHE: tuple[str, Decimal] = ("", Decimal("0"))

_NONCE_CACHE_ALIAS = getattr(settings, "X402_CACHE_ALIAS", "default")
_NONCE_TEMPLATE = "x402:nonce:{nonce}"
_NONCE_TTL_SECONDS = max(1, int(getattr(settings, "X402_NONCE_TTL_SECONDS", 300)))
_AMOUNT_QUANT = Decimal("0.00000001")


@dataclass(frozen=True)
class PricingRule:
    pattern: str
    amount: Decimal
    methods: Optional[frozenset[str]] = None
    currency: Optional[str] = None
    network: Optional[str] = None
    source: Any | None = None
    owner_id: Optional[int] = None

    def matches(self, path: str, method: str) -> bool:
        method = method.upper()
        if self.methods and method not in self.methods:
            return False

        normalized_path = _normalize_path(path)
        normalized_pattern = self.pattern.strip()

        if not normalized_pattern:
            normalized_pattern = "/"

        if not normalized_pattern.startswith("/"):
            normalized_pattern = f"/{normalized_pattern}"

        if normalized_pattern == "/*":
            return True

        if normalized_pattern.endswith("*"):
            prefix = normalized_pattern[:-1]
            prefix_normalized = _normalize_path(prefix)
            return (
                normalized_path == prefix_normalized
                or normalized_path.startswith(f"{prefix_normalized}/")
            )

        return normalized_path == _normalize_path(normalized_pattern)


def initialize() -> None:
    """
    Preload configuration at startup.
    """
    if not is_enabled():
        return

    if not get_payto_address():
        raise ImproperlyConfigured(
            "X402_PAYTO_ADDRESS must be set when X402_ENABLED is true."
        )

    _get_pricing_rules()
    _get_default_price()


def is_enabled() -> bool:
    return getattr(settings, "X402_ENABLED", False)


def get_payto_address() -> str:
    return getattr(settings, "X402_PAYTO_ADDRESS", "") or ""


def _get_currency() -> str:
    return getattr(settings, "X402_CURRENCY", "USDC")


def _get_network() -> str:
    return getattr(settings, "X402_NETWORK", "algorand")


def match_price(path: str, method: str, request: Optional[HttpRequest] = None) -> Optional[Decimal]:
    """
    Return the Decimal price for the given request, or None if not paywalled.
    """
    if not is_enabled():
        return None

    matched_rule: PricingRule | None = None
    for rule in _iter_pricing_rules(request):
        if rule.matches(path, method):
            matched_rule = rule
            break

    if matched_rule:
        if request is not None:
            setattr(request, "x402_rule", matched_rule)
        return matched_rule.amount

    price = _get_default_price()

    if price is None or price <= Decimal("0"):
        return None

    return price


def build_challenge(request: HttpRequest, price: Decimal) -> Dict[str, str]:
    """
    Build the 402 response headers instructing the client how to pay.
    """
    default_payto = get_payto_address()
    if not default_payto:
        raise ImproperlyConfigured(
            "X402_PAYTO_ADDRESS must be configured to issue x402 challenges."
        )

    nonce = _generate_nonce()
    _register_nonce(nonce, request, price)

    rule = getattr(request, "x402_rule", None)
    currency = rule.currency if rule and rule.currency else _get_currency()
    network = rule.network if rule and rule.network else _get_network()
    pay_to = _resolve_payto_address(rule, default_payto)
    setattr(request, "x402_payto_address", pay_to)

    challenge = {
        "X-402-PayTo": pay_to,
        "X-402-Amount": _format_amount(price),
        "X-402-Nonce": nonce,
        "X-402-Protocol": "x402",
        "X-402-Currency": currency,
        "X-402-Network": network,
    }

    callback = getattr(settings, "X402_CALLBACK_URL", "")
    if callback:
        challenge["X-402-Callback"] = callback

    return challenge


def verify_receipt(receipt: str, price: Decimal, request: HttpRequest) -> Optional[Dict[str, Any]]:
    """
    Validate a receipt header and return metadata if payment is accepted.
    """
    verifier = _get_verifier()
    if verifier is None:
        logger.error(
            "x402 receipt verifier is not configured. Set X402_RECEIPT_VERIFIER to enable verification."
        )
        return None

    try:
        result = verifier(receipt=receipt, price=price, request=request)
    except Exception:  # pragma: no cover - defensive logging
        logger.exception("x402 receipt verifier raised an unexpected error.")
        return None

    if not result:
        return None

    nonce = result.get("nonce")
    if not nonce:
        logger.warning("x402 verifier did not return a nonce; rejecting receipt.")
        return None

    if _nonce_consumed(nonce):
        logger.warning("x402 nonce replay detected for nonce=%s", nonce)
        return None

    try:
        receipt_record = _ensure_receipt_record(nonce, request, price, rule=getattr(request, "x402_rule", None))
    except Exception:  # pragma: no cover - defensive logging
        logger.exception("Unable to ensure receipt record for nonce=%s", nonce)
        receipt_record = None

    if receipt_record and receipt_record.status != PaymentReceiptStatus.PENDING:
        logger.warning(
            "x402 receipt nonce=%s already processed with status=%s",
            nonce,
            receipt_record.status,
        )
        return None

    amount_value = result.get("amount")
    amount_decimal: Optional[Decimal]
    if amount_value is not None:
        try:
            amount_decimal = _quantize_amount(_to_decimal(amount_value))
        except InvalidOperation:
            logger.warning("x402 verifier returned invalid amount: %s", amount_value)
            amount_decimal = None
    else:
        amount_decimal = _quantize_amount(price)

    if amount_decimal is not None and amount_decimal < price:
        logger.warning("x402 receipt amount %s is below required price %s", amount_decimal, price)
        if receipt_record:
            receipt_record.mark_rejected(
                reason="amount_below_required",
                metadata={
                    "expected_amount": _format_amount(price),
                    "received_amount": _format_amount(amount_decimal),
                },
                receipt_token=receipt,
            )
        return None

    payer = result.get("payer") or result.get("from") or result.get("sender")

    status_value = str(result.get("status", "")).lower()
    accepted_flag = result.get("accepted")
    success_statuses = {"confirmed", "success", "paid", "completed"}
    if accepted_flag is None:
        accepted = status_value in success_statuses or status_value == ""
    else:
        accepted = bool(accepted_flag)
    if status_value and status_value not in success_statuses:
        accepted = False

    metadata_payload = _extract_metadata(result)
    expected_receiver = getattr(request, "x402_payto_address", None)
    if expected_receiver:
        metadata_payload.setdefault("expected_receiver", expected_receiver)

    if not accepted:
        reason = result.get("reason") or (status_value or "verification_failed")
        if receipt_record:
            receipt_record.mark_rejected(
                reason=reason,
                metadata=metadata_payload,
                receipt_token=receipt,
            )
        return None

    if receipt_record:
        receipt_record.mark_confirmed(
            metadata=metadata_payload,
            payer=payer,
            receipt_token=receipt,
            amount=amount_decimal or _quantize_amount(price),
        )
        result["receipt_id"] = receipt_record.id

    _post_process_receipt(request, receipt_record, metadata_payload, payer)

    _mark_nonce_consumed(nonce)

    if payer:
        result.setdefault("payer", payer)
    if amount_decimal is not None:
        result["amount"] = _format_amount(amount_decimal)
    return result


def attach_payment_metadata(request: HttpRequest, metadata: Dict[str, Any]) -> None:
    """
    Attach verification metadata to the request for downstream handlers.
    """
    setattr(request, "x402_payment", metadata)


def refresh_configuration() -> None:
    """
    Clear cached config to force a reload from settings.
    """
    global _PRICING_RULES_CACHE, _DEFAULT_PRICE_CACHE
    _PRICING_RULES_CACHE = ("", [])
    _DEFAULT_PRICE_CACHE = ("", Decimal("0"))


def _get_pricing_rules() -> list[PricingRule]:
    global _PRICING_RULES_CACHE
    raw_rules = getattr(settings, "X402_PRICING_RULES", "{}") or "{}"

    if raw_rules == _PRICING_RULES_CACHE[0]:
        return _PRICING_RULES_CACHE[1]

    try:
        parsed = json.loads(raw_rules)
    except (TypeError, ValueError) as exc:
        logger.warning("Invalid JSON for X402_PRICING_RULES: %s", exc)
        _PRICING_RULES_CACHE = (raw_rules, [])
        return []

    if not isinstance(parsed, dict):
        logger.warning("X402_PRICING_RULES must be a JSON object.")
        _PRICING_RULES_CACHE = (raw_rules, [])
        return []

    rules: list[PricingRule] = []
    for pattern, entry in parsed.items():
        amount, methods = _parse_rule(entry)
        if amount is None:
            continue
        rules.append(PricingRule(pattern=str(pattern), amount=amount, methods=methods))

    _PRICING_RULES_CACHE = (raw_rules, rules)
    return rules


def _iter_pricing_rules(request: Optional[HttpRequest]) -> Iterable[PricingRule]:
    yield from _get_user_pricing_rules(request)
    yield from _get_pricing_rules()


def _get_user_pricing_rules(request: Optional[HttpRequest]) -> list[PricingRule]:
    path = _normalize_path(request.path) if request else ""
    owner_ids: set[int] = set()

    if request is not None:
        user = getattr(request, "user", None)
        if getattr(user, "is_authenticated", False) and user.id:
            owner_ids.add(user.id)

    path_owner_id = _extract_owner_id(path)
    if path_owner_id:
        owner_ids.add(path_owner_id)

    if not owner_ids:
        return []

    rules: list[PricingRule] = []
    queryset = EndpointPricingRule.objects.filter(user_id__in=owner_ids, is_active=True).order_by("priority", "pattern")
    for entry in queryset:
        amount = _sanitize_amount(entry.amount)
        if amount is None:
            continue
        rules.append(
            PricingRule(
                pattern=entry.pattern,
                amount=amount,
                methods=entry.normalized_methods(),
                currency=entry.currency,
                network=entry.network,
                source=entry,
                owner_id=entry.user_id,
            )
        )
    return rules


def _get_default_price() -> Decimal:
    global _DEFAULT_PRICE_CACHE
    raw_default = getattr(settings, "X402_DEFAULT_PRICE", "0") or "0"

    if raw_default == _DEFAULT_PRICE_CACHE[0]:
        return _DEFAULT_PRICE_CACHE[1]

    try:
        value = _to_decimal(raw_default)
    except InvalidOperation:
        logger.warning("Invalid Decimal for X402_DEFAULT_PRICE: %s", raw_default)
        value = Decimal("0")

    _DEFAULT_PRICE_CACHE = (raw_default, value)
    return value


def _parse_rule(entry: Any) -> tuple[Optional[Decimal], Optional[frozenset[str]]]:
    if isinstance(entry, (str, int, float, Decimal)):
        return _sanitize_amount(entry), None

    if isinstance(entry, dict):
        amount = _sanitize_amount(entry.get("amount"))
        methods = entry.get("methods")
        if methods is not None:
            methods_set = _parse_methods(methods)
        else:
            methods_set = None
        return amount, methods_set

    logger.warning("Unsupported x402 pricing rule format: %s", entry)
    return None, None


def _sanitize_amount(value: Any) -> Optional[Decimal]:
    if value is None:
        return None
    try:
        amount = _to_decimal(value)
    except InvalidOperation:
        logger.warning("Ignoring invalid x402 amount value: %s", value)
        return None
    if amount < Decimal("0"):
        logger.warning("Ignoring negative x402 amount value: %s", value)
        return None
    return amount


def _parse_methods(value: Any) -> Optional[frozenset[str]]:
    if value is None:
        return None
    if isinstance(value, str):
        methods = [value]
    elif isinstance(value, Iterable):
        methods = list(value)
    else:
        logger.warning("Invalid methods collection in x402 pricing rules: %s", value)
        return None

    normalized = {str(method).upper() for method in methods if str(method).strip()}
    return frozenset(normalized) if normalized else None


def _format_amount(amount: Decimal) -> str:
    quantized = amount.normalize()
    if "E" in str(quantized):
        quantized = quantized.quantize(Decimal("0.00000001"))
    return format(quantized, "f")


def _quantize_amount(amount: Decimal) -> Decimal:
    try:
        return amount.quantize(_AMOUNT_QUANT)
    except (InvalidOperation, AttributeError):
        return amount


def _generate_nonce() -> str:
    return secrets.token_urlsafe(32)


def _register_nonce(nonce: str, request: HttpRequest, price: Decimal) -> None:
    cache = _get_nonce_cache()
    rule = getattr(request, "x402_rule", None)
    payload = {
        "status": "pending",
        "path": _normalize_path(request.path),
        "method": request.method.upper(),
        "price": _format_amount(price),
        "rule_owner_id": getattr(rule, "owner_id", None),
        "pay_to": getattr(request, "x402_payto_address", None),
    }
    cache.set(_NONCE_TEMPLATE.format(nonce=nonce), payload, timeout=_NONCE_TTL_SECONDS)
    try:
        _ensure_receipt_record(nonce, request, price, metadata=payload, rule=rule)
    except Exception:  # pragma: no cover - defensive logging
        logger.exception("Unable to persist x402 receipt placeholder for nonce=%s", nonce)


def _nonce_consumed(nonce: str) -> bool:
    cache = _get_nonce_cache()
    entry = cache.get(_NONCE_TEMPLATE.format(nonce=nonce))
    if entry is not None:
        return entry.get("status") == "consumed"
    receipt = PaymentReceipt.objects.filter(nonce=nonce).first()
    if receipt is None:
        return True
    return receipt.status != PaymentReceiptStatus.PENDING


def _mark_nonce_consumed(nonce: str) -> None:
    cache = _get_nonce_cache()
    key = _NONCE_TEMPLATE.format(nonce=nonce)
    cache.set(key, {"status": "consumed"}, timeout=_NONCE_TTL_SECONDS)


def _ensure_receipt_record(
    nonce: str,
    request: HttpRequest,
    price: Decimal,
    metadata: Optional[Dict[str, Any]] = None,
    rule: PricingRule | None = None,
) -> PaymentReceipt:
    request_user = getattr(request, "user", None)
    auth_user = request_user if getattr(request_user, "is_authenticated", False) else None
    path = _normalize_path(request.path)
    method = request.method.upper()
    amount = _quantize_amount(price)
    request_meta = _build_request_metadata(request)
    metadata_payload: Dict[str, Any] = {}
    if metadata:
        metadata_payload["challenge"] = metadata
    if request_meta:
        metadata_payload["request"] = request_meta
    owner_user = None
    if rule and rule.source is not None and hasattr(rule.source, "user"):
        owner_user = getattr(rule.source, "user", None)
    if owner_user is None and rule and rule.owner_id:
        from django.contrib.auth import get_user_model  # local import to avoid circular

        owner_user = get_user_model().objects.filter(id=rule.owner_id).first()

    if owner_user is None:
        owner_user = auth_user

    currency = rule.currency if rule and rule.currency else _get_currency()
    network = rule.network if rule and rule.network else _get_network()

    defaults = {
        "user": owner_user,
        "amount": amount,
        "currency": currency,
        "network": network,
        "request_path": path,
        "request_method": method,
        "metadata": metadata_payload,
    }

    try:
        receipt, created = PaymentReceipt.objects.get_or_create(nonce=nonce, defaults=defaults)
    except IntegrityError:
        receipt = PaymentReceipt.objects.get(nonce=nonce)
        created = False

    updates: list[str] = []
    if not created:
        if owner_user and receipt.user_id != getattr(owner_user, "id", None):
            receipt.user = owner_user
            updates.append("user")
        if receipt.request_path != path:
            receipt.request_path = path
            updates.append("request_path")
        if receipt.request_method != method:
            receipt.request_method = method
            updates.append("request_method")
        if receipt.currency != defaults["currency"]:
            receipt.currency = defaults["currency"]
            updates.append("currency")
        if receipt.network != defaults["network"]:
            receipt.network = defaults["network"]
            updates.append("network")
        if receipt.amount != amount:
            receipt.amount = amount
            updates.append("amount")
        if metadata_payload:
            combined = receipt.metadata.copy()
            if "request" in metadata_payload:
                combined["last_request"] = metadata_payload["request"]
            if "challenge" in metadata_payload:
                combined["last_challenge"] = metadata_payload["challenge"]
            receipt.metadata = combined
            updates.append("metadata")
        if updates:
            receipt.save(update_fields=updates + ["updated_at"])
    return receipt


def _build_request_metadata(request: HttpRequest) -> Dict[str, Any]:
    data: Dict[str, Any] = {}
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded_for:
        data["ip"] = forwarded_for.split(",")[0].strip()
    else:
        remote_addr = request.META.get("REMOTE_ADDR")
        if remote_addr:
            data["ip"] = remote_addr
    user_agent = request.META.get("HTTP_USER_AGENT")
    if user_agent:
        data["user_agent"] = user_agent[:512]
    try:
        host = request.get_host()
    except Exception:
        host = None
    if host:
        data["host"] = host
    if request.GET:
        query: Dict[str, Any] = {}
        for key in request.GET.keys():
            values = request.GET.getlist(key)
            query[key] = values if len(values) > 1 else values[0]
        data["query_params"] = query
    return data


def _extract_metadata(result: Dict[str, Any]) -> Dict[str, Any]:
    metadata: Dict[str, Any] = {}
    embedded = result.get("metadata")
    if isinstance(embedded, dict):
        metadata.update(embedded)

    for key in ("transaction_id", "txid", "payment_reference", "receiver", "raw_receipt"):
        value = result.get(key)
        if value is not None:
            metadata.setdefault(key, value)

    for key, value in result.items():
        if key in {"nonce", "amount", "payer", "from", "status", "metadata"}:
            continue
        if key.startswith("_"):
            continue
        metadata.setdefault(key, value)

    return metadata


def _get_nonce_cache():
    alias = getattr(settings, "X402_CACHE_ALIAS", _NONCE_CACHE_ALIAS)
    try:
        return caches[alias]
    except InvalidCacheBackendError:
        logger.warning("Cache alias %s not found for x402, falling back to default.", alias)
        return caches["default"]
    except KeyError:
        logger.warning("Cache alias %s not configured for x402, falling back to default.", alias)
        return caches["default"]


def _normalize_path(path: str) -> str:
    if not path:
        return "/"
    if not path.startswith("/"):
        path = f"/{path}"
    if len(path) > 1 and path.endswith("/"):
        path = path[:-1]
    return path


def _extract_owner_id(path: str) -> Optional[int]:
    if not path:
        return None
    parts = path.split("/")
    for idx, part in enumerate(parts):
        if part == "tenant" and idx + 1 < len(parts):
            try:
                return int(parts[idx + 1])
            except (TypeError, ValueError):
                return None
    return None


def _resolve_payto_address(rule: PricingRule | None, default_payto: str) -> str:
    if rule is not None:
        source = rule.source
        if source is not None:
            pay_to = getattr(source, "pay_to_address", "")
            if pay_to:
                return pay_to
            metadata = getattr(source, "metadata", None)
            if isinstance(metadata, dict):
                pay_to_meta = metadata.get("pay_to_address")
                if pay_to_meta:
                    return pay_to_meta
    return default_payto


def _get_verifier():
    backend_path = getattr(settings, "X402_RECEIPT_VERIFIER", "")
    if not backend_path:
        return None
    return import_string(backend_path)


def _to_decimal(value: Any) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _post_process_receipt(
    request: HttpRequest,
    receipt: Optional[PaymentReceipt],
    metadata: Dict[str, Any],
    payer: Optional[str],
) -> None:
    if receipt is None:
        return
    try:
        path = _normalize_path(request.path)
        rule = getattr(request, "x402_rule", None)
        owner_id = getattr(rule, "owner_id", None)
        pay_to = getattr(request, "x402_payto_address", None)
        meta_base = dict(metadata)
        if pay_to and "pay_to" not in meta_base:
            meta_base["pay_to"] = pay_to

        link = None
        if owner_id:
            link = PaymentLink.objects.filter(user_id=owner_id, pattern=path, is_active=True).first()
        if link is None:
            link = PaymentLink.objects.filter(pattern=path, is_active=True).first()

        if link is not None:
            record_payment_link_event(link=link, receipt=receipt, payer=payer, metadata=meta_base)
            return

        plan = None
        if owner_id:
            plan = X402CreditPlan.objects.filter(user_id=owner_id, pattern=path, is_active=True).first()
        if plan is None:
            plan = X402CreditPlan.objects.filter(pattern=path, is_active=True).first()

        if plan is not None:
            consumer = None
            if request.GET:
                consumer = request.GET.get("consumer") or request.GET.get("customer")
            if not consumer:
                consumer = request.headers.get("X-Consumer-ID") or request.headers.get("X-Customer-ID")
            if not consumer:
                consumer = metadata.get("consumer") or metadata.get("customer")
            if not consumer:
                consumer = payer or "anonymous"
            consumer = str(consumer)
            meta = dict(meta_base)
            meta.setdefault("consumer", consumer)
            apply_credit_top_up(plan=plan, consumer_ref=consumer, receipt=receipt, metadata=meta)
    except Exception:  # pragma: no cover - ensure failures don't break request flow
        logger.exception("x402 post-processing failed for receipt %s", receipt.id if receipt else "unknown")
