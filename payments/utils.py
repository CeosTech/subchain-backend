# payments/utils.py

import qrcode
from io import BytesIO
import base64
from decimal import Decimal
from django.conf import settings
from typing import Tuple

def generate_algo_payment_qr(wallet_address, amount):
    uri = f"algorand://pay?amount={int(amount * 1e6)}&receiver={wallet_address}"
    qr = qrcode.make(uri)
    buffer = BytesIO()
    qr.save(buffer, format="PNG")
    buffer.seek(0)
    return base64.b64encode(buffer.read()).decode("utf-8")

def calculate_fees(amount: Decimal) -> Tuple[Decimal, Decimal]:
    """Calcule les frais de plateforme et le net_amount"""
    fee_percent = Decimal(settings.PLATFORM_FEE_PERCENT) / 100
    platform_fee = (amount * fee_percent).quantize(Decimal("0.01"))
    net_amount = amount - platform_fee
    return platform_fee, net_amount
    
