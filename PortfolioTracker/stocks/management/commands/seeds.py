from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from stocks.models import Holding, Portfolio, Stock, Transaction


class Command(BaseCommand):
    help = "Seed initial data for demo portfolio with stock purchases and holdings"

    def handle(self, *args, **options):
        user, created = User.objects.get_or_create(username="demo_user")
        if created:
            user.set_password("demo1234")
            user.save()
            self.stdout.write(
                self.style.SUCCESS(
                    f'Created demo user "{user.username}" with password "demo1234"'
                )
            )

        portfolio, created = Portfolio.objects.get_or_create(
            user=user,
            name="Demo portfolio",
            defaults={"description": "Demo portfolio for presentation purposes"},
        )
        if created:
            self.stdout.write(self.style.SUCCESS("Created demo portfolio"))

        stocks_data = [
            {"ticker": "AAPL", "name": "Apple Inc.", "currency": "$"},
            {"ticker": "MSFT", "name": "Microsoft Corporation", "currency": "$"},
            {"ticker": "TSLA", "name": "Tesla Inc.", "currency": "$"},
            {"ticker": "GOOGL", "name": "Alphabet Inc.", "currency": "$"},
            {"ticker": "AMZN", "name": "Amazon.com, Inc.", "currency": "$"},
            {"ticker": "META", "name": "Meta Platforms, Inc.", "currency": "$"},
            {"ticker": "PFE", "name": "Pfizer Inc. ", "currency": "$"},
        ]
        stocks = []
        for stock_data in stocks_data:
            stock, created = Stock.objects.get_or_create(
                ticker=stock_data["ticker"],
                defaults={
                    "name": stock_data["name"],
                    "currency": stock_data["currency"],
                },
            )
            stocks.append(stock)

        transactions_data = [
            {
                "stock": stocks[0],
                "transaction_date": date(2024, 6, 24),
                "quantity": 14,
                "price": Decimal("208.63"),
                "fees": Decimal("1.00"),
                "transaction_type": "BUY",
            },
            {
                "stock": stocks[1],
                "transaction_date": date(2024, 2, 19),
                "quantity": 8,
                "price": Decimal("409.87"),
                "fees": Decimal("1.50"),
                "transaction_type": "BUY",
            },
            {
                "stock": stocks[2],
                "transaction_date": date(2024, 7, 10),
                "quantity": 13,
                "price": Decimal("284.02"),
                "fees": Decimal("2.00"),
                "transaction_type": "BUY",
            },
            {
                "stock": stocks[0],
                "transaction_date": date(2024, 8, 5),
                "quantity": 7,
                "price": Decimal("196.32"),
                "fees": Decimal("1.20"),
                "transaction_type": "BUY",
            },
            {
                "stock": stocks[3],
                "transaction_date": date(2024, 5, 13),
                "quantity": 21,
                "price": Decimal("167.24"),
                "fees": Decimal("5.00"),
                "transaction_type": "BUY",
            },
            {
                "stock": stocks[4],
                "transaction_date": date(2024, 7, 1),
                "quantity": 16,
                "price": Decimal("200.32"),
                "fees": Decimal("3.00"),
                "transaction_type": "BUY",
            },
            {
                "stock": stocks[5],
                "transaction_date": date(2024, 6, 24),
                "quantity": 5,
                "price": Decimal("521.92"),
                "fees": Decimal("2.00"),
                "transaction_type": "BUY",
            },
            {
                "stock": stocks[1],
                "transaction_date": date(2024, 6, 24),
                "quantity": 6,
                "price": Decimal("455.10"),
                "fees": Decimal("1.50"),
                "transaction_type": "BUY",
            },
            {
                "stock": stocks[6],
                "transaction_date": date(2024, 7, 22),
                "quantity": 112,
                "price": Decimal("30.74"),
                "fees": Decimal("1.50"),
                "transaction_type": "BUY",
            },
        ]

        for tx_data in transactions_data:
            transaction, created = Transaction.objects.get_or_create(
                portfolio=portfolio,
                stock=tx_data["stock"],
                transaction_date=tx_data["transaction_date"],
                quantity=tx_data["quantity"],
                price=tx_data["price"],
                fees=tx_data["fees"],
                transaction_type=tx_data["transaction_type"],
            )

            holding, _ = Holding.objects.get_or_create(
                portfolio=portfolio,
                stock=tx_data["stock"],
                defaults={
                    "quantity": 0,
                    "buy_price": tx_data["price"],
                    "buy_date": tx_data["transaction_date"],
                },
            )

            total_old_value = holding.quantity * float(holding.buy_price)
            total_new_value = tx_data["quantity"] * float(tx_data["price"])
            new_quantity = holding.quantity + tx_data["quantity"]
            new_avg_price = (total_old_value + total_new_value) / new_quantity

            holding.quantity = new_quantity
            holding.buy_price = round(new_avg_price, 2)
            holding.buy_date = tx_data["transaction_date"]
            holding.save()

        self.stdout.write(
            self.style.SUCCESS(
                "Demo portfolio, stocks, transactions, and holdings inserted successfully"
            )
        )
