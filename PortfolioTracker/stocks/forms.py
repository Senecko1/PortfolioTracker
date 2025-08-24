from django import forms
from django.forms import ModelForm

from .models import Holding, Portfolio, Transaction


class PortfolioForm(ModelForm):
    class Meta:
        model = Portfolio
        fields = ["name", "description"]


class TransactionForm(ModelForm):
    class Meta:
        model = Transaction
        fields = [
            "stock",
            "transaction_date",
            "quantity",
            "price",
            "fees",
            "transaction_type",
            "notes",
        ]
        widgets = {"transaction_date": forms.DateInput(attrs={"type": "date"})}

    def __init__(self, *args, **kwargs):
        self.portfolio = kwargs.pop("portfolio", None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        transaction_type = cleaned_data.get("transaction_type")
        stock = cleaned_data.get("stock")
        quantity = cleaned_data.get("quantity")

        if transaction_type == "SELL" and stock and quantity and self.portfolio:
            try:
                holding = Holding.objects.get(portfolio=self.portfolio, stock=stock)
            except Holding.DoesNotExist:
                self.add_error(
                    "stock",
                    f"You cannot sell {stock.ticker} because you don't own any shares.",
                )
                return cleaned_data

            if holding.quantity < quantity:
                self.add_error(
                    "quantity",
                    f"You cannot sell {quantity} shares of {stock.ticker}. You only have {holding.quantity} shares.",
                )

        return cleaned_data

