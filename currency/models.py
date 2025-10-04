# currency/models.py

from django.db import models

class Currency(models.Model):
    code = models.CharField(max_length=10, unique=True)  # ex: 'ALGO', 'USDC', 'EUR'
    name = models.CharField(max_length=100)              # ex: 'Algorand', 'US Dollar Coin'
    symbol = models.CharField(max_length=10, blank=True) # ex: '₳', '$'
    is_crypto = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.code} ({self.name})"

class ExchangeRate(models.Model):
    base_currency = models.ForeignKey(Currency, related_name="base_rates", on_delete=models.CASCADE)
    target_currency = models.ForeignKey(Currency, related_name="target_rates", on_delete=models.CASCADE)
    rate = models.DecimalField(max_digits=20, decimal_places=8)  # taux de conversion
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('base_currency', 'target_currency')

    def __str__(self):
        return f"1 {self.base_currency.code} = {self.rate} {self.target_currency.code}"
