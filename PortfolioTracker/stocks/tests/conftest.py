import pytest
from django.contrib.auth.models import User
from django.test import Client

from ..models import Holding, Portfolio, Stock, Tag, Transaction


@pytest.fixture
def user(db):
    """Creates and returns a test user."""
    # Create standard test user
    return User.objects.create_user(
        username="testuser",
        password="testpass123",
    )


@pytest.fixture
def admin_user(db):
    """Creates and returns an admin user."""
    # Create superuser for admin-specific tests
    return User.objects.create_superuser(
        username="admin",
        password="adminpass123",
    )


@pytest.fixture
def tag(db):
    """Creates and returns a test tag."""
    # Create a sample tag for linking with stocks or other tests
    return Tag.objects.create(name="Technology")


@pytest.fixture
def stock(db, tag):
    """Creates and returns a test stock with tags."""
    # Create a stock instance and assign the tag
    stock = Stock.objects.create(
        ticker="AAPL", name="Apple Inc.", currency="USD", last_price=230.00
    )
    stock.tags.add(tag)
    return stock


@pytest.fixture
def portfolio(db, user):
    """Creates and returns a test portfolio."""
    # Create a portfolio owned by the test user
    return Portfolio.objects.create(
        user=user, name="Test Portfolio", description="Test portfolio description"
    )


@pytest.fixture
def holding(db, portfolio, stock):
    """Creates and returns a test holding."""
    # Create a holding representing stock quantity owned in portfolio
    return Holding.objects.create(
        portfolio=portfolio,
        stock=stock,
        quantity=10,
        buy_price=100.00,
        buy_date="2024-01-01",
    )


@pytest.fixture
def transaction(db, portfolio, stock):
    """Creates and returns a test transaction."""
    # Create a stock transaction linked to portfolio and stock
    return Transaction.objects.create(
        portfolio=portfolio,
        stock=stock,
        transaction_date="2025-08-26",
        quantity=5,
        price=120.00,
        fees=1.50,
        transaction_type="BUY",
        notes="Test transaction",
    )


@pytest.fixture
def client():
    """Returns Django test client."""
    # Provides a Django test client instance for sending HTTP requests in tests
    return Client()
