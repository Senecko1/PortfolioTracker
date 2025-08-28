from decimal import Decimal

import pytest
from django.db import IntegrityError

from ..models import Portfolio, Stock, Tag


@pytest.mark.django_db
class TestTag:
    """Test cases for Tag model."""

    def test_tag_creation(self):
        """Test creating a tag instance."""
        tag = Tag.objects.create(name="Finance")
        # Verify tag name is set correctly
        assert tag.name == "Finance"
        # Check string representation returns tag name
        assert str(tag) == "Finance"

    def test_tag_unique_constraint(self):
        """Test uniqueness constraint on tag names."""
        Tag.objects.create(name="Tech")
        # Creating duplicate name should raise IntegrityError
        with pytest.raises(IntegrityError):
            Tag.objects.create(name="Tech")


@pytest.mark.django_db
class TestStock:
    """Test cases for Stock model."""

    def test_stock_creation(self):
        """Test creating a stock instance."""
        stock = Stock.objects.create(
            ticker="MSFT", name="Microsoft Corporation", currency="USD"
        )
        # Verify stock fields values
        assert stock.ticker == "MSFT"
        assert stock.name == "Microsoft Corporation"

    def test_stock_str_representation(self, stock):
        """Test string representation of a stock instance."""
        expected = f"{stock.ticker} ({stock.name})"
        # Check __str__ returns ticker and name concat
        assert str(stock) == expected

    def test_stock_many_to_many_tags(self, stock, tag):
        """Test the many-to-many relation between stock and tags."""
        # Verify tag is linked to stock
        assert tag in stock.tags.all()
        # Verify stock is linked to tag (reverse relation)
        assert stock in tag.stock_set.all()


@pytest.mark.django_db
class TestPortfolio:
    """Test cases for Portfolio model."""

    def test_portfolio_creation(self, user):
        """Test creating a portfolio instance."""
        portfolio = Portfolio.objects.create(
            user=user, name="Growth Portfolio", description="Long-term growth focused"
        )
        # Verify portfolio fields match input
        assert portfolio.user == user
        assert portfolio.name == "Growth Portfolio"

    def test_portfolio_str_representation(self, portfolio):
        """Test string representation of a portfolio instance."""
        expected = f"{portfolio.name} ({portfolio.user.username})"
        # Check __str__ returns name and username
        assert str(portfolio) == expected

    def test_unique_portfolio_name_per_user(self, user):
        """Test uniqueness constraint on portfolio name per user."""
        Portfolio.objects.create(user=user, name="Portfolio1")
        # Creating duplicate name for same user should raise integrity error
        with pytest.raises(IntegrityError):
            Portfolio.objects.create(user=user, name="Portfolio1")


@pytest.mark.django_db
class TestHolding:
    """Test cases for Holding model."""

    def test_holding_creation(self, holding):
        """Test creating a holding instance."""
        # Verify fields from fixture
        assert holding.quantity == 10
        assert holding.buy_price == Decimal("100.00")

    def test_holding_str_representation(self, holding):
        """Test string representation of a holding."""
        expected = f"{holding.quantity} × {holding.stock.ticker}"
        # Check __str__ with quantity and ticker
        assert str(holding) == expected

    def test_holding_current_value_calculation(self, holding):
        """Test method calculating the holding's current value."""
        current_price = 150.00
        expected_value = holding.quantity * current_price
        # Call method and verify calculation
        assert holding.current_value(current_price) == expected_value


@pytest.mark.django_db
class TestTransaction:
    """Test cases for Transaction model."""

    def test_transaction_creation(self, transaction):
        """Test creating a transaction instance."""
        # Verify fields from fixture
        assert transaction.quantity == 5
        assert transaction.price == Decimal("120.00")
        assert transaction.transaction_type == "BUY"

    def test_transaction_str_representation(self, transaction):
        """Test string representation of a transaction."""
        expected = f"{transaction.transaction_type} {transaction.quantity}×{transaction.stock.ticker}"
        # Check __str__ returns expected formatted string
        assert str(transaction) == expected
