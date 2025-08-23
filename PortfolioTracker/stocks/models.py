from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from django.utils import timezone
from datetime import timedelta
import pandas as pd
import yfinance as yf
from .config import (
    TRANSACTION_TYPES,
    PRICE_REFRESH_DELTA_MINUTES,
)

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
        ordering = ['ticker']

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
        cutoff = timezone.now() - timedelta(minutes=PRICE_REFRESH_DELTA_MINUTES)

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
                    'gain_loss_percent': None,
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
                'gain_loss_percent': round(gain_loss_percent, 2),
            })

        return holdings_with_prices

    def get_portfolio_summary(self):
        holdings_with_prices = self.get_holdings_with_prices()

        total_value = 0
        total_cost = 0

        for item in holdings_with_prices:
            if item['current_value'] is not None:
                total_value += item['current_value']
            if item['holding'].buy_price and item['holding'].quantity:
                total_cost += item['holding'].quantity * float(item['holding'].buy_price)

        gain_loss = total_value - total_cost
        gain_loss_percent = (gain_loss / total_cost * 100) if total_cost else 0

        return {
            'total_value': round(total_value, 2),
            'total_cost': round(total_cost, 2),
            'gain_loss': round(gain_loss, 2),
            'gain_loss_percent': round(gain_loss_percent, 2),
        }

    def get_time_series(self, days=365):
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)

        all_transactions = (
            Transaction.objects
            .filter(portfolio=self, transaction_date__lte=end_date)
            .order_by('transaction_date', 'timestamp')
        )
        if not all_transactions.exists():
            return {'labels': [], 'values': []}

        ticker_transaction_changes = {}
        for transaction in all_transactions:
            ticker_changes = ticker_transaction_changes.setdefault(transaction.stock.ticker, [])
            quantity_change = transaction.quantity if transaction.transaction_type == 'BUY' else -transaction.quantity
            ticker_changes.append((transaction.transaction_date, quantity_change))

        ticker_list = list(ticker_transaction_changes.keys())
        price_data_frame = yf.download(
            tickers=ticker_list,
            start=start_date.isoformat(),
            end=(end_date + timedelta(days=1)).isoformat(),
            progress=False,
            group_by='ticker'
        )
        if price_data_frame.empty:
            return {'labels': [], 'values': []}

        holdings_data_frame = pd.DataFrame(index=price_data_frame.index)

        for ticker, transactions_for_ticker in ticker_transaction_changes.items():
            initial_quantity = sum(change for date, change in transactions_for_ticker if date < start_date)
            relevant_events = sorted([(date, change) for date, change in transactions_for_ticker if start_date <= date <= end_date])

            current_quantity = initial_quantity
            daily_quantities = []
            event_index = 0
            for current_date in price_data_frame.index.normalize():
                while event_index < len(relevant_events) and relevant_events[event_index][0] == current_date.date():
                    current_quantity += relevant_events[event_index][1]
                    event_index += 1
                daily_quantities.append(current_quantity)
            holdings_data_frame[ticker] = pd.Series(daily_quantities, index=price_data_frame.index)

        portfolio_value_series = pd.Series(0.0, index=price_data_frame.index)
        for ticker in ticker_list:
            close_prices = price_data_frame[ticker]['Close'] if len(ticker_list) > 1 else price_data_frame['Close']
            portfolio_value_series += holdings_data_frame[ticker].astype(float) * close_prices.astype(float)

        labels = [date.date().isoformat() for date in portfolio_value_series.index]
        values = [round(value, 2) for value in portfolio_value_series.values]

        return {'labels': labels, 'values': values}


class Holding(models.Model):
    portfolio = models.ForeignKey(Portfolio, on_delete=models.CASCADE)
    stock = models.ForeignKey(Stock, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    buy_price = models.DecimalField(max_digits=10, decimal_places=2)
    buy_date = models.DateField()

    class Meta:
        unique_together = [('portfolio', 'stock')]
        ordering = ['stock__ticker']

    def __str__(self):
        return f"{self.quantity} × {self.stock.ticker}"

    def current_value(self, current_price):
        return self.quantity * current_price


class Transaction(models.Model):
    TRANSACTION_TYPES = TRANSACTION_TYPES

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