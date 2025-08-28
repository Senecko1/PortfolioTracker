import json

import pytest
from django.urls import reverse
from django.utils import timezone

from ..models import Holding, Portfolio, Stock, Transaction


@pytest.mark.django_db
class TestHomeView:
    """Test cases for home view."""

    def test_home_view_anonymous_user(self, client):
        """Test home view for anonymous user."""
        # Send GET request to home URL without authentication
        response = client.get(reverse("home"))
        # Verify response is HTTP 200 OK
        assert response.status_code == 200
        # Confirm "home.html" template was used to render response
        assert "home.html" in [t.name for t in response.templates]

    def test_home_view_authenticated_user(self, client, user):
        """Test home view redirects authenticated user."""
        # Log in user to simulate authenticated request
        client.force_login(user)
        response = client.get(reverse("home"))
        # Expect redirect (302) to user-portfolios page
        assert response.status_code == 302
        assert response.url == reverse("user-portfolios")


@pytest.mark.django_db
class TestRegisterView:
    """Test cases for register view."""

    def test_register_view_valid_register(self, client):
        """Test register view with valid data."""
        data = {
            "username": "testuser",
            "password1": "testpassword",
            "password2": "testpassword",
        }
        # Send POST request with valid registration data
        response = client.post(reverse("register"), data)
        # Expect redirect on successful registration
        assert response.status_code == 302
        assert response.url == reverse("user-portfolios")

    def test_register_view_invalid_register(self, client):
        """Test register view with invalid data."""
        data = {
            "username": "testuser",
            "password1": "testpassword",
            "password2": "wrongpassword",
        }
        # Send POST request with mismatched passwords
        response = client.post(reverse("register"), data)
        # Expect page re-render (status 200) with form errors
        assert response.status_code == 200


@pytest.mark.django_db
class TestUserPortfoliosView:
    """Test cases for UserPortfoliosView."""

    def test_user_portfolios_view_authenticated(self, client, user, portfolio):
        """Test portfolios view for authenticated user."""
        # Authenticate user to access portfolios
        client.force_login(user)
        response = client.get(reverse("user-portfolios"))
        assert response.status_code == 200
        # Verify that the portfolio fixture is in the context data
        assert portfolio in response.context["portfolios"]

    def test_user_portfolios_view_anonymous(self, client):
        """Test portfolios view redirects anonymous user to login."""
        response = client.get(reverse("user-portfolios"))
        # Expect redirect (302) to login page
        assert response.status_code == 302
        assert "/login" in response.url

    def test_create_portfolio_post(self, client, user):
        """Test creating portfolio via POST request."""
        client.force_login(user)
        data = {"name": "New Test Portfolio", "description": "Created via POST"}
        response = client.post(reverse("user-portfolios"), data)
        # Expect redirect on success
        assert response.status_code == 302
        # Verify new portfolio was created in the database
        assert Portfolio.objects.filter(name="New Test Portfolio").exists()

    def test_create_portfolio_invalid_post(self, client, user):
        """Test creating portfolio with invalid data via POST request."""
        client.force_login(user)
        data = {"name": "", "description": "Created via POST"}
        response = client.post(reverse("user-portfolios"), data)
        # Expect re-render with validation errors (200 OK)
        assert response.status_code == 200


@pytest.mark.django_db
class TestPortfolioDetailDeleteView:
    """Test cases for PortfolioDetailDeleteView."""

    def test_portfolio_detail_view_authenticated(self, client, user, portfolio):
        """Test portfolio detail view for authenticated user."""
        client.force_login(user)
        url = reverse("portfolio-details", kwargs={"portfolio_id": portfolio.id})
        response = client.get(url)
        assert response.status_code == 200
        # Verify portfolio returned in context
        assert response.context["portfolio"] == portfolio

    def test_portfolio_detail_view_anonymous(self, client, portfolio):
        """Test portfolio detail view redirects anonymous user."""
        url = reverse("portfolio-details", kwargs={"portfolio_id": portfolio.id})
        response = client.get(url)
        # Expect redirect to login
        assert response.status_code == 302
        assert "/login" in response.url

    def test_portfolio_delete_view_authenticated(self, client, user, portfolio):
        """Test portfolio delete view."""
        client.force_login(user)
        url = reverse("portfolio-details", kwargs={"portfolio_id": portfolio.id})
        # Send POST to delete with action parameter set
        response = client.post(url, data={"action": "delete"})
        # Expect redirect after deletion
        assert response.status_code == 302
        assert "/portfolios" in response.url


@pytest.mark.django_db
class TestAddStockView:
    """Test cases for AddStockView."""

    def test_portfolio_add_new_ticker_creates_stock(self, client, user, mocker):
        """Test adding stock with new ticker."""
        client.force_login(user)
        url = reverse("add-stock")

        # Prepare mocked info to simulate external API response
        mock_info = {
            "shortName": "Test Stock Inc.",
            "currency": "USD",
            "currentPrice": 123.45,
        }
        # Create a mock yf.Ticker instance with .info attribute
        mock_yf_ticker = mocker.Mock()
        mock_yf_ticker.info = mock_info

        # Patch the yf.Ticker constructor to return mock object
        mocker.patch("stocks.views.yf.Ticker", return_value=mock_yf_ticker)

        response = client.post(url, data={"ticker": "TEST"})
        assert response.status_code == 302
        assert response.url == reverse("user-portfolios")

        # Check stock was created correctly with mocked data
        stock = Stock.objects.filter(ticker="TEST").first()
        assert stock is not None
        assert stock.name == mock_info["shortName"][:100]
        assert stock.currency == "$"
        assert stock.last_price == mock_info["currentPrice"]

    def test_portfolio_add_existing_ticker(self, client, user, stock):
        """Test adding stock with existing ticker."""
        client.force_login(user)
        url = reverse("add-stock")
        response = client.post(url, data={"ticker": stock.ticker})
        assert response.status_code == 302
        assert response.url == reverse("user-portfolios")

    def test_portfolio_add_no_ticker(self, client, user):
        """Test adding stock with no ticker."""
        client.force_login(user)
        url = reverse("add-stock")
        response = client.post(url, data={"ticker": ""})
        assert response.status_code == 302
        assert response.url == reverse("user-portfolios")


@pytest.mark.django_db
class TestTransactionCreateView:
    """Test cases for TransactionCreateView."""

    def test_transaction_create_post_validbuy(self, client, user, portfolio, stock):
        """Test POST request to create BUY transaction."""
        client.force_login(user)
        url = reverse("transaction", kwargs={"portfolio_id": portfolio.id})
        data = {
            "stock": stock.id,
            "transaction_date": "2024-08-26",
            "quantity": 5,
            "price": 100.00,
            "fees": 1.00,
            "transaction_type": "BUY",
            "notes": "Test transaction",
        }
        # Post valid buy transaction data
        response = client.post(url, data)
        assert response.status_code == 302
        # Verify transaction exists in DB
        assert Transaction.objects.filter(portfolio=portfolio, stock=stock).exists()

    def test_transaction_create_post_valid_sell(
        self, client, user, portfolio, stock, holding
    ):
        """Test POST request to create SELL transaction."""
        client.force_login(user)
        url = reverse("transaction", kwargs={"portfolio_id": portfolio.id})
        data = {
            "stock": stock.id,
            "transaction_date": "2025-01-01",
            "quantity": 5,
            "price": 110.00,
            "fees": 1.20,
            "transaction_type": "SELL",
            "notes": "Selling part of holding",
        }
        # Post sell transaction data
        response = client.post(url, data)
        assert response.status_code == 302
        # Verify sell transaction exists
        assert Transaction.objects.filter(
            portfolio=portfolio, stock=stock, transaction_type="SELL"
        ).exists()
        # Refresh holding and check quantity updated
        holding.refresh_from_db()
        assert holding.quantity == 5

    def test_transaction_create_post_invalid_data(self, client, user, portfolio):
        """Test POST request with invalid data."""
        client.force_login(user)
        url = reverse("transaction", kwargs={"portfolio_id": portfolio.id})
        data = {
            "stock": "",
            "transaction_date": "invalid-date",
            "quantity": -5,
            "price": -100,
            "fees": -1,
            "transaction_type": "BUY",
            "notes": "",
        }
        # Post invalid data should return to form with errors
        response = client.post(url, data)
        assert response.status_code == 200
        form = response.context["form"]
        # Verify form contains errors on invalid fields
        assert form.errors
        assert (
            "stock" in form.errors
            or "transaction_date" in form.errors
            or "quantity" in form.errors
        )


@pytest.mark.django_db
class TestAllTransactionsView:
    """Test cases for AllTransactionsView."""

    def test_user_sees_transactions(self, client, user, portfolio, transaction):
        """Test that user sees their transactions."""
        client.force_login(user)
        url = reverse("all-transactions", kwargs={"portfolio_id": portfolio.id})
        response = client.get(url)
        assert response.status_code == 200
        # Confirm transaction in context
        transactions = response.context["transactions"]
        assert transaction in transactions
        # Confirm portfolio information
        assert response.context["portfolio"] == portfolio
        assert response.context["portfolio_id"] == portfolio.id

    def test_anonymous_user_redirects_to_login(self, client, portfolio):
        """Test that anonymous user is redirected to login."""
        url = reverse("all-transactions", kwargs={"portfolio_id": portfolio.id})
        response = client.get(url)
        # Expect redirect status code 302
        assert response.status_code == 302
        # Confirm redirect to login page
        assert "/login" in response.url


@pytest.mark.django_db
class TestHoldingsView:
    """Test cases for HoldingsView."""

    def test_holdings(self, client, user, portfolio, holding):
        """Test that user sees their holdings."""
        client.force_login(user)
        url = reverse("holdings", kwargs={"portfolio_id": portfolio.id})
        response = client.get(url)
        assert response.status_code == 200
        # Check holdings queryset contains holding
        holdings = response.context["holdings"]
        assert holding in holdings
        # Check portfolio context is correct
        assert response.context["portfolio"] == portfolio
        # Check chart data exists and is consistent
        labels = response.context["chart_labels"]
        values = response.context["chart_values"]
        assert isinstance(labels, list)
        assert isinstance(values, list)
        assert len(labels) == len(values)
        assert holding.stock.ticker in labels

    def test_holdings_filtered_by_user(self, client, user, portfolio, holding):
        """Test that holdings are filtered by user."""
        # Create holding in a different portfolio for the user
        other_user = user
        other_portfolio = Portfolio.objects.create(
            user=other_user, name="Other Portfolio"
        )
        Holding.objects.create(
            portfolio=other_portfolio,
            stock=holding.stock,
            quantity=100,
            buy_price=50,
            buy_date="2024-01-01",
        )
        client.force_login(user)
        url = reverse("holdings", kwargs={"portfolio_id": portfolio.id})
        response = client.get(url)
        holdings = response.context["holdings"]
        # Verify holdings belong only to the logged-in user
        assert all(holding.portfolio.user == user for holding in holdings)


@pytest.mark.django_db
class TestPortfolioChartDataView:
    """Test cases for PortfolioChartDataView."""

    def test_get_chart_data_authenticated(self, client, user, portfolio):
        """Test getting chart data."""
        client.force_login(user)
        url = reverse("line-chart-data", kwargs={"portfolio_id": portfolio.id})
        response = client.get(url)
        assert response.status_code == 200
        # Ensure content type is JSON
        assert response["Content-Type"] == "application/json"
        data = json.loads(response.content)
        # Check JSON response type
        assert isinstance(data, dict)

    def test_get_chart_data_forbidden_other_user(
        self, client, user, portfolio, django_user_model
    ):
        """Test getting chart data for other user."""
        # Create different user and login
        other_user = django_user_model.objects.create_user(
            username="other", password="pass"
        )
        client.force_login(other_user)
        url = reverse("line-chart-data", kwargs={"portfolio_id": portfolio.id})
        response = client.get(url)
        # Should return 404 Not Found for unauthorized user
        assert response.status_code == 404


@pytest.mark.django_db
class TestLineChartView:
    """Test cases for LineChartView."""

    def test_line_chart_view_authenticated(self, client, user, portfolio):
        """Test line chart view."""
        client.force_login(user)
        url = reverse("line-chart", kwargs={"portfolio_id": portfolio.id})
        response = client.get(url)
        assert response.status_code == 200
        # Confirm correct portfolio in context
        assert response.context["portfolio"] == portfolio
        assert response.context["portfolio_id"] == portfolio.id
        # Confirm current date is in context formatted as ISO string
        today_iso = timezone.now().date().isoformat()
        assert response.context["today"] == today_iso

    def test_line_chart_view_invalid_portfolio(self, client, user):
        """Test line chart view for invalid portfolio."""
        client.force_login(user)
        url = reverse("line-chart", kwargs={"portfolio_id": 999999})
        response = client.get(url)
        # Should return 404 Not Found for non-existing portfolio
        assert response.status_code == 404


@pytest.mark.django_db
class TestTickerAutocompleteView:
    """Test cases for TickerAutocompleteView."""

    def test_get_empty_query(self, client):
        """Test getting empty query."""
        url = reverse("api-ticker-autocomplete")
        response = client.get(url, data={"q": ""})
        assert response.status_code == 200
        assert response.json() == []

    def test_get_external_api_success(self, client, mocker):
        """Test getting external API success."""
        mock_response = mocker.Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "quotes": [{"symbol": "AAPL", "shortname": "Apple Inc.", "currency": "USD"}]
        }
        mocker.patch("stocks.views.requests.get", return_value=mock_response)
        url = reverse("api-ticker-autocomplete")
        response = client.get(url, data={"q": "AAPL"})
        assert response.status_code == 200
        data = response.json()
        assert any(item["ticker"] == "AAPL" for item in data)
        assert any("Apple Inc." in item["label"] for item in data)

    def test_get_external_api_failure(self, client, stock, mocker):
        """Test getting external API failure."""
        mocker.patch("stocks.views.requests.get", side_effect=Exception("API down"))
        url = reverse("api-ticker-autocomplete")
        response = client.get(url, data={"q": stock.ticker[:2]})
        assert response.status_code == 200
        data = response.json()
        assert any(item["ticker"] == stock.ticker for item in data)


@pytest.mark.django_db
class TestTagAutocompleteView:
    """Test cases for TagAutocompleteView."""

    def test_get_empty_query(self, client, tag):
        """Test getting empty query."""
        url = reverse("api-tag-autocomplete")
        response = client.get(url, data={"q": ""})
        assert response.status_code == 200
        data = response.json()
        assert any(item["label"] == tag.name for item in data)

    def test_get_query_filters_tags(self, client, tag):
        """Test getting query filters tags."""
        url = reverse("api-tag-autocomplete")
        query = tag.name[:3]
        response = client.get(url, data={"q": query})
        assert response.status_code == 200
        data = response.json()
        assert all(query.lower() in item["label"].lower() for item in data)
        assert any(item["label"] == tag.name for item in data)

    def test_get_no_matching_tags(self, client):
        """Test getting no matching tags."""
        url = reverse("api-tag-autocomplete")
        response = client.get(url, data={"q": "nonexistenttagxyz"})
        assert response.status_code == 200
        data = response.json()
        assert data == []
