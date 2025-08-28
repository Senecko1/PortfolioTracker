import pytest

from ..forms import PortfolioForm, TransactionForm
from ..models import Portfolio


@pytest.mark.django_db
class TestPortfolioForm:
    """Test cases for PortfolioForm."""

    def test_portfolio_form_valid_data(self):
        """Test portfolio form with valid data."""
        form_data = {
            "name": "Investment Portfolio",
            "description": "My investment portfolio",
        }
        form = PortfolioForm(data=form_data)
        # Form should be valid with proper data
        assert form.is_valid()

    def test_portfolio_form_invalid_data(self):
        """Test portfolio form with invalid data."""
        form_data = {"name": "", "description": "Description"}
        form = PortfolioForm(data=form_data)
        # Form should be invalid if name is empty
        assert not form.is_valid()

    def test_portfolio_form_save(self, user):
        """Test saving portfolio form."""
        form_data = {"name": "New Portfolio", "description": "Description"}
        form = PortfolioForm(data=form_data)
        assert form.is_valid()

        # Save with commit=False to assign user before saving
        portfolio = form.save(commit=False)
        portfolio.user = user
        portfolio.save()

        # Verify the portfolio was saved successfully
        assert Portfolio.objects.filter(name="New Portfolio").exists()


@pytest.mark.django_db
class TestTransactionForm:
    """Test cases for TransactionForm."""

    def test_transaction_form_valid_buy(self, portfolio, stock):
        """Test transaction form with valid BUY data."""
        form_data = {
            "stock": stock.id,
            "transaction_date": "2025-08-27",
            "quantity": 5,
            "price": 100.00,
            "fees": 1.00,
            "transaction_type": "BUY",
            "notes": "Test buy",
        }
        form = TransactionForm(data=form_data, portfolio=portfolio)
        # Form should validate properly when buying
        assert form.is_valid()

    def test_transaction_form_invalid_buy(self, portfolio, stock):
        """Test transaction form with invalid BUY data."""
        form_data = {
            "stock": stock.id,
            "transaction_date": "2025-08-27",
            "quantity": 0,  # Invalid quantity: zero
            "price": 100.00,
            "fees": 1.00,
            "transaction_type": "BUY",
            "notes": "Test buy",
        }
        form = TransactionForm(data=form_data, portfolio=portfolio)
        # Form should be invalid due to quantity = 0
        assert not form.is_valid()
        assert "quantity" in form.errors

    def test_transaction_form_valid_sell(self, portfolio, stock, holding):
        """Test transaction form with valid SELL data."""
        form_data = {
            "stock": stock.id,
            "transaction_date": "2025-08-27",
            "quantity": 5,
            "price": 100.00,
            "fees": 1.00,
            "transaction_type": "SELL",
            "notes": "Test sell",
        }
        form = TransactionForm(data=form_data, portfolio=portfolio)
        # Form should be valid when selling stock that is owned
        assert form.is_valid()

    def test_transaction_form_invalid_sell_no_holding(self, portfolio, stock):
        """Test transaction form validation for selling stock not owned."""
        form_data = {
            "stock": stock.id,
            "transaction_date": "2025-08-27",
            "quantity": 5,
            "price": 100.00,
            "fees": 1.00,
            "transaction_type": "SELL",
            "notes": "Test sell",
        }
        form = TransactionForm(data=form_data, portfolio=portfolio)
        # Expect invalid form because no holding exists for this stock
        assert not form.is_valid()
        assert "stock" in form.errors

    def test_transaction_form_invalid_sell_insufficient_quantity(
        self, portfolio, stock, holding
    ):
        """Test transaction form validation for selling more than owned."""
        form_data = {
            "stock": stock.id,
            "transaction_date": "2024-08-26",
            "quantity": 20,  # More than holding quantity (10)
            "price": 100.00,
            "fees": 1.00,
            "transaction_type": "SELL",
            "notes": "Test sell too much",
        }
        form = TransactionForm(data=form_data, portfolio=portfolio)
        # Form should be invalid because quantity exceeds owned holdings
        assert not form.is_valid()
        assert "quantity" in form.errors
