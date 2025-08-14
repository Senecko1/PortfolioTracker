from django.core.exceptions import ValidationError
from django.forms import ModelForm

from .models import Portfolio, Transaction, Holding

class PortfolioForm(ModelForm):
    class Meta:
        model = Portfolio
        fields = ['name', 'description']


class TransactionForm(ModelForm):
    class Meta:
        model = Transaction
        fields = [
            'stock',
            'transaction_date',
            'quantity',
            'price',
            'fees',
            'transaction_type',
            'notes',
        ]

    def __init__(self, *args, **kwargs):
        # We are waiting for the portfolio instance to be handed over for sales validation.
        self.portfolio = kwargs.pop('portfolio', None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        transaction_type = cleaned_data.get('transaction_type')
        stock = cleaned_data.get('stock')
        quantity = cleaned_data.get('quantity')

        # Validation: you cannot sell more shares than you have
        if transaction_type == 'SELL' and stock and quantity and self.portfolio:
            try:
                holding = Holding.objects.get(portfolio=self.portfolio, stock=stock)
            except Holding.DoesNotExist:
                raise ValidationError(
                    f"You cannot sell {stock.ticker} because you don't own any shares."
                )

            if holding.quantity < quantity:
                raise ValidationError(
                    f"You cannot sell {quantity} shares of {stock.ticker}. "
                    f"You only have {holding.quantity} shares."
                )

        return cleaned_data

