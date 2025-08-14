from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from django.utils import timezone
from datetime import timedelta
import yfinance as yf


class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)

    class Meta:
        verbose_name = 'Tag'
        verbose_name_plural = 'Tags'

    def __str__(self):
        return self.name


class Stock(models.Model):
    ticker = models.CharField(max_length=10, unique=True, help_text="Stock ticker symbol, e.g. AAPL")
    name = models.CharField(max_length=100, blank=True)
    currency = models.CharField(max_length=10, blank=True, null=True)
    last_price = models.FloatField(blank=True, null=True)
    last_update = models.DateTimeField(auto_now=True)
    tags = models.ManyToManyField(Tag, blank=True)

    class Meta:
        verbose_name = 'Stock'
        verbose_name_plural = 'Stocks'

    def __str__(self):
        return f"{self.ticker} ({self.name})" if self.name else self.ticker


    def fetch_current_price(self):
        try:
            ticker = yf.Ticker(self.ticker)
            price = ticker.fast_info.last_price
            self.last_price = price
            self.save(update_fields=['last_price', 'last_update'])
            return price
        except Exception:
            return self.last_price


class Portfolio(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    description = models.TextField(null=True, blank=True, help_text="Optional description")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'name'], name='unique_user_name')
        ]

    def __str__(self):
        return f"{self.name} ({self.user.username})"

    def get_holdings_with_prices(self):
        holdings = Holding.objects.filter(portfolio=self).select_related('stock')
        holdings_with_prices = []
        cutoff = timezone.now() - timedelta(minutes=15)
        
        for holding in holdings:
            stock = holding.stock
            if not stock.last_price or stock.last_update < cutoff:
                stock.fetch_current_price()

            current_price = stock.last_price
            if current_price is None:
                holdings_with_prices.append({
                    'holding': holding,
                    'current_price': None,
                    'current_value': None,
                    'currency': None,
                    'gain_loss': None,
                    'gain_loss_percent': None
                })
                continue

            current_value = holding.quantity * current_price
            cost_basis = holding.quantity * float(holding.buy_price)
            gain_loss = current_value - cost_basis
            gain_loss_percent = (gain_loss / cost_basis * 100) if cost_basis else 0

            holdings_with_prices.append({
                'holding': holding,
                'current_price': round(current_price, 2),
                'current_value': round(current_value, 2),
                'currency': stock.currency,
                'gain_loss': round(gain_loss, 2),
                'gain_loss_percent': round(gain_loss_percent, 2)
            })

        return holdings_with_prices


class Holding(models.Model):
    portfolio = models.ForeignKey(Portfolio, on_delete=models.CASCADE)
    stock = models.ForeignKey(Stock, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    buy_price = models.DecimalField(max_digits=10, decimal_places=2)
    buy_date = models.DateField()

    class Meta:
        unique_together = [('portfolio', 'stock')]

    def __str__(self):
        return f"{self.quantity} × {self.stock.ticker}"

    def current_value(self, current_price):
        return self.quantity * current_price

    def average_price(self):
        return self.buy_price


class Transaction(models.Model):
    TRANSACTION_TYPES = (
    ('BUY', 'Buy'),
    ('SELL', 'Sell'),
)

    portfolio = models.ForeignKey(Portfolio, on_delete=models.CASCADE)
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE)
    transaction_date = models.DateField(help_text="YYYY-MM-DD")
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    fees = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    transaction_type = models.CharField(max_length=4, choices=TRANSACTION_TYPES)
    notes = models.TextField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.transaction_type} {self.quantity}×{self.stock.ticker}"

    class Meta:
        ordering = ['-transaction_date', '-timestamp']