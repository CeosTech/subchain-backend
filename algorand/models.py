from django.db import models

class SwapLog(models.Model):
    transaction = models.OneToOneField("payments.Transaction", on_delete=models.CASCADE)
    from_currency = models.CharField(max_length=10, default="ALGO")
    to_currency = models.CharField(max_length=10, default="USDC")
    amount_in = models.DecimalField(max_digits=20, decimal_places=8)
    amount_out = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)
    rate = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)
    slippage = models.DecimalField(max_digits=5, decimal_places=2, default=0.03)
    tx_id = models.CharField(max_length=128, null=True, blank=True)
    status = models.CharField(max_length=20, default="pending")  # success, failed, etc.
    created_at = models.DateTimeField(auto_now_add=True)
    error_message = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Swap {self.amount_in} ALGO → {self.amount_out or '...'} USDC"

