import requests
import yfinance as yf
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import IntegrityError
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import (
    CreateView,
    DetailView,
    ListView,
)

from .config import CURRENCY_SYMBOLS, DATE_FORMAT_DISPLAY
from .forms import PortfolioForm, TransactionForm
from .models import Holding, Portfolio, Stock, Tag, Transaction


def home(request: HttpRequest) -> HttpResponse:
    """
    Render the home page if the user is not authenticated.

    If the user is authenticated, redirect to the user portfolios page.

    Args:
        request (HttpRequest): The HTTP request object.

    Returns:
        HttpResponse: Rendered home page for unauthenticated
        users or redirect response for authenticated users.
    """
    # If the user is logged in, redirect to the user portfolios page
    if request.user.is_authenticated:
        return redirect("user-portfolios")

    # Otherwise, show the general home page
    return render(request, "home.html")


class RegisterView(CreateView):
    """
    Display user registration form and handle user creation.

    On successful form submission, the user is created, logged in,
    and redirected to the user portfolios page.

    Attributes:
        template_name (str): Path to the registration template.
        form_class (UserCreationForm): Form used for user registration.
        success_url (str): URL to redirect after successful registration.
    """

    template_name = "stocks/register.html"
    form_class = UserCreationForm
    success_url = reverse_lazy("user-portfolios")

    def form_valid(self, form) -> HttpResponse:
        """
        If the form is valid, save the new user, log them in,
        and return the successful response.

        Args:
            form (UserCreationForm): The valid registration form.

        Returns:
            HttpResponse: Redirect response after user registration and login.
        """
        response = super().form_valid(form)
        # Log in the newly created user
        login(self.request, self.object)
        return response


class UserPortfoliosView(LoginRequiredMixin, ListView):
    """
    Display the list of portfolios belonging to the logged-in user
    and handle creation of new portfolios via POST requests.

    Attributes:
        model (Portfolio): The Portfolio model to be listed.
        template_name (str): Template used to render the portfolio list.
        context_object_name (str): The context variable name for portfolios in the template.
    """

    model = Portfolio
    template_name = "stocks/user_portfolios.html"
    context_object_name = "portfolios"

    def get_queryset(self):
        """
        Return portfolios filtered by the current logged-in user.

        Returns:
            QuerySet: A queryset of Portfolio instances for the user.
        """
        return self.model.objects.filter(user=self.request.user)

    def post(self, request, *args, **kwargs):
        """
        Handle POST request to create a new portfolio.

        Validates the submitted form, associates the portfolio with the logged-in user,
        handles potential uniqueness conflicts, and provides feedback messages.

        If form is invalid or an error occurs, re-renders the page with the form and modal open.

        Returns:
            HttpResponse: Redirects to the portfolios list on success,
            or re-renders the portfolio page on failure.
        """
        form = PortfolioForm(request.POST)
        form.instance.user = request.user  # Associate portfolio with logged-in user

        if form.is_valid():
            try:
                form.save()
                messages.success(
                    request, f'Portfolio "{form.instance.name}" was created.'
                )
                return redirect("user-portfolios")
            except IntegrityError:
                messages.error(
                    request, f'Portfolio "{form.instance.name}" already exists.'
                )
        else:
            messages.error(request, "Please correct the errors below.")

        # Re-render the page with the form errors and open the portfolio modal
        return self.get(request, form=form, open_modal="portfolioModal")

    def get_context_data(self, **kwargs):
        """
        Add extra context to the template, including the portfolio creation form
        and a flag indicating whether to open the modal.

        Returns:
            dict: Context data for template rendering.
        """
        context = super().get_context_data(**kwargs)
        context["portfolio_form"] = kwargs.get("form", PortfolioForm())
        context["open_modal"] = kwargs.get("open_modal")
        return context


class PortfolioDetailDeleteView(LoginRequiredMixin, DetailView):
    """
    Display detailed information for a specific portfolio and handle deletion requests.

    Allows viewing portfolio details including holdings with prices, portfolio summary,
    and related transactions. Supports deletion of the portfolio via POST request.

    Attributes:
        model (Portfolio): The Portfolio model.
        pk_url_kwarg (str): URL param name to identify the portfolio object.
        template_name (str): Template for rendering portfolio details.
        context_object_name (str): Context name for the portfolio object in the template.
        success_url (str): Redirect URL after successful portfolio deletion.
    """

    model = Portfolio
    pk_url_kwarg = "portfolio_id"
    template_name = "stocks/portfolio_details.html"
    context_object_name = "portfolio"
    success_url = reverse_lazy("user-portfolios")

    def get_context_data(self, **kwargs) -> dict:
        """
        Add additional portfolio-related data to the template context.

        Returns:
            dict: Context including holdings with prices, summary, transactions, and portfolio ID.
        """
        context = super().get_context_data(**kwargs)
        context["holdings_with_prices"] = self.object.get_holdings_with_prices()
        context["summary"] = self.object.get_portfolio_summary()
        context["transactions"] = Transaction.objects.filter(portfolio=self.object)
        context["portfolio_id"] = self.object.id
        return context

    def post(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        """
        Handle POST requests for deleting the portfolio.

        If the POST parameter "action" equals "delete", deletes the portfolio,
        shows a success message, and redirects to the portfolios list.
        Otherwise, re-renders the detail view.

        Args:
            request (HttpRequest): The HTTP request object.

        Returns:
            HttpResponse: Redirect after deletion or detail page render.
        """
        if request.POST.get("action") == "delete":
            portfolio = self.get_object()
            portfolio_name = portfolio.name  # Store before deleting
            portfolio.delete()
            messages.success(
                request, f'Portfolio "{portfolio_name}" was deleted successfully.'
            )
            return redirect(self.success_url)
        # If action is not delete, simply render the portfolio detail view
        return super().get(request, *args, **kwargs)


class AddStockView(LoginRequiredMixin, View):
    """
    Handle POST request to add a stock by its ticker symbol.

    If the stock does not exist, attempt to fetch additional info via yfinance.
    Associates provided tags with the stock, creating new tags if necessary.

    Provides user feedback messages for success, warnings or errors.

    Methods:
        post: Process the stock addition POST request.
    """

    def post(self, request: HttpRequest) -> HttpResponse:
        """
        Process the POST request to add a new stock.

        Args:
            request (HttpRequest): The HTTP request containing form data.

        Returns:
            HttpResponse: Redirect to user portfolios page after processing.
        """
        ticker = request.POST.get("ticker", "").upper().strip()
        raw_tags = request.POST.getlist("tags")

        # Validate ticker input presence
        if not ticker:
            messages.error(request, "Please enter a stock ticker.")
            return redirect("user-portfolios")

        # Create or retrieve existing stock
        stock, created = Stock.objects.get_or_create(ticker=ticker)

        if created:
            try:
                yf_stock = yf.Ticker(ticker)
                info = yf_stock.info
                # Safely extract attributes with truncation and fallback
                stock.name = info.get("shortName", "")[:100]
                currency = info.get("currency", "")
                stock.currency = CURRENCY_SYMBOLS.get(currency, currency)
                stock.last_price = info.get("currentPrice", 0)
                stock.save()
                messages.success(request, f"Stock {ticker} added to the system.")
            except Exception as e:
                # Save stock even if external data fetching fails
                stock.save()
                messages.warning(
                    request, f"Ticker {ticker} added, but fetching data failed: {e}"
                )
        else:
            messages.info(request, f"Stock {ticker} is already available.")

        tags_to_set = []
        for raw in raw_tags:
            if raw.isdigit():
                try:
                    tag = Tag.objects.get(pk=int(raw))
                except Tag.DoesNotExist:
                    continue  # Ignore invalid tag IDs
            else:
                tag, _ = Tag.objects.get_or_create(name=raw.strip())
            tags_to_set.append(tag)

        # Associate tags with the stock
        stock.tags.set(tags_to_set)

        return redirect("user-portfolios")


class TransactionCreateView(LoginRequiredMixin, CreateView):
    """
    Create a new transaction belonging to a specific portfolio.

    Handles transaction creation, associates it with the logged-in user's portfolio,
    and updates the holdings based on the transaction type (BUY or SELL).

    Attributes:
        model (Transaction): The Transaction model.
        form_class (TransactionForm): The form to create a transaction.
        template_name (str): Template to render the transaction form.
    """

    model = Transaction
    form_class = TransactionForm
    template_name = "stocks/transaction.html"

    def dispatch(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        """
        Retrieve the portfolio belonging to the current user, or return 404.

        Args:
            request (HttpRequest): The HTTP request.
            *args: Additional positional arguments.
            **kwargs: Keyword arguments containing 'portfolio_id'.

        Returns:
            HttpResponse: The response from the parent dispatch method.
        """
        self.portfolio = get_object_or_404(
            Portfolio, pk=kwargs["portfolio_id"], user=request.user
        )
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self) -> dict:
        """
        Pass the portfolio instance to the form's kwargs.

        Returns:
            dict: Form keyword arguments including the portfolio.
        """
        kwargs = super().get_form_kwargs()
        kwargs["portfolio"] = self.portfolio
        return kwargs

    def form_valid(self, form) -> HttpResponse:
        """
        Set the portfolio to the transaction instance, save it,
        and update holdings accordingly.

        Args:
            form: Validated TransactionForm instance.

        Returns:
            HttpResponse: Redirect response after successful form submission.
        """
        form.instance.portfolio = self.portfolio
        response = super().form_valid(form)
        self._update_holdings(form.instance)
        return response

    def _update_holdings(self, transaction):
        """
        Update or delete holdings based on the transaction type.

        For BUY transactions, update average buy price and quantity.
        For SELL transactions, decrease quantity or delete holding if zero.

        Args:
            transaction (Transaction): The processed transaction instance.
        """
        holding, _ = Holding.objects.get_or_create(
            portfolio=transaction.portfolio,
            stock=transaction.stock,
            defaults={
                "quantity": 0,
                "buy_price": 0,
                "buy_date": transaction.transaction_date,
            },
        )

        if transaction.transaction_type == "BUY":
            total_old_value = holding.quantity * float(holding.buy_price)
            total_new_value = transaction.quantity * float(transaction.price)
            new_quantity = holding.quantity + transaction.quantity
            new_avg_price = (total_old_value + total_new_value) / new_quantity

            holding.quantity = new_quantity
            holding.buy_price = round(new_avg_price, 2)
            holding.buy_date = transaction.transaction_date
            holding.save()

        elif transaction.transaction_type == "SELL":
            new_quantity = holding.quantity - transaction.quantity
            if new_quantity == 0:
                # Delete holding if quantity becomes zero
                holding.delete()
            else:
                holding.quantity = new_quantity
                holding.save()

    def get_success_url(self) -> str:
        """
        Return the URL to redirect to after successful transaction creation.

        Returns:
            str: URL to the portfolio detail page.
        """
        return reverse_lazy(
            "portfolio-details", kwargs={"portfolio_id": self.portfolio.pk}
        )

    def get_context_data(self, **kwargs) -> dict:
        """
        Add portfolio info to template context.

        Returns:
            dict: Context data for template rendering.
        """
        context = super().get_context_data(**kwargs)
        context["portfolio"] = self.portfolio
        context["portfolio_id"] = self.portfolio.pk
        return context


class AllTransactionsView(LoginRequiredMixin, ListView):
    """
    Display all transactions for a specific portfolio owned by the logged-in user.

    Attributes:
        model (Transaction): The Transaction model to be listed.
        pk_url_kwarg (str): URL param name to identify the portfolio.
        template_name (str): Template used to render the transactions.
        context_object_name (str): Context variable name for transactions in the template.
    """

    model = Transaction
    pk_url_kwarg = "portfolio_id"
    template_name = "stocks/all_transactions.html"
    context_object_name = "transactions"

    def get_queryset(self):
        """
        Return transactions filtered by the portfolio id and owned by the logged-in user.

        Returns:
            QuerySet: A queryset of Transaction instances for the portfolio.
        """
        # Ensure portfolio belongs to the logged-in user to prevent unauthorized data access
        portfolio_id = self.kwargs.get(self.pk_url_kwarg)
        portfolio = get_object_or_404(
            Portfolio, pk=portfolio_id, user=self.request.user
        )
        return Transaction.objects.filter(portfolio=portfolio)

    def get_context_data(self, **kwargs) -> dict:
        """
        Add portfolio details and display settings to the context.

        Returns:
            dict: Context data including portfolio and date format display constant.
        """
        context = super().get_context_data(**kwargs)
        portfolio_id = self.kwargs.get(self.pk_url_kwarg)
        portfolio = get_object_or_404(
            Portfolio, pk=portfolio_id, user=self.request.user
        )
        context["portfolio"] = portfolio
        context["portfolio_id"] = portfolio.id
        context["DATE_FORMAT_DISPLAY"] = DATE_FORMAT_DISPLAY
        return context


class HoldingsView(LoginRequiredMixin, ListView):
    """
    Display all holdings for a specific portfolio owned by the logged-in user,
    including data for visual chart representation of holdings distribution.

    Attributes:
        model (Holding): The Holding model to be listed.
        pk_url_kwarg (str): URL parameter name to identify the portfolio.
        template_name (str): Template used to render the holdings.
        context_object_name (str): Context variable name for holdings in the template.
    """

    model = Holding
    pk_url_kwarg = "portfolio_id"
    template_name = "stocks/holdings.html"
    context_object_name = "holdings"

    def get_queryset(self):
        """
        Return holdings filtered by portfolio ID and portfolio ownership.

        Returns:
            QuerySet: A queryset of Holding instances for the user's portfolio.
        """
        portfolio_id = self.kwargs.get("portfolio_id")
        return self.model.objects.filter(
            portfolio__pk=portfolio_id, portfolio__user=self.request.user
        )

    def get_context_data(self, **kwargs) -> dict:
        """
        Add portfolio and chart data to the template context.

        Calculates each holding's value and its percentage share in the portfolio.

        Returns:
            dict: Context data including portfolio, chart labels, values, and portfolio ID.
        """
        context = super().get_context_data(**kwargs)
        holdings = context["holdings"]

        labels = []
        values = []
        total_value = 0
        fresh_data = []

        # Calculate total portfolio value and individual holdings values
        for holding in holdings:
            price = holding.stock.last_price or 0
            current_value = holding.quantity * price
            total_value += current_value
            fresh_data.append((holding, current_value))

        # Build labels and values for chart
        for holding, current_value in fresh_data:
            labels.append(holding.stock.ticker)
            values.append(
                round((current_value / total_value) * 100, 2) if total_value > 0 else 0
            )

        # Fetch portfolio validating ownership
        portfolio_id = self.kwargs.get(self.pk_url_kwarg)
        portfolio = get_object_or_404(
            Portfolio, pk=portfolio_id, user=self.request.user
        )

        context["portfolio"] = portfolio
        context["chart_labels"] = labels
        context["chart_values"] = values
        context["portfolio_id"] = portfolio.id
        return context


class PortfolioChartData(LoginRequiredMixin, View):
    """
    Provide JSON time series data for a specified portfolio.

    Retrieves time series data for the portfolio over the past year
    and returns it as a JSON response.

    Methods:
        get: Handle GET request and return time series data.
    """

    def get(self, request: HttpRequest, portfolio_id: int) -> HttpResponse:
        """
        Handle GET request to fetch time series data for a portfolio.

        Args:
            request (HttpRequest): The HTTP request object.
            portfolio_id (int): The ID of the portfolio to fetch data for.

        Returns:
            JsonResponse: JSON response containing the portfolio's time series data.
        """
        # Ensure portfolio belongs to the logged-in user for security
        portfolio = get_object_or_404(Portfolio, pk=portfolio_id, user=request.user)

        # Fetch time series data, e.g., last 365 days
        data = portfolio.get_time_series(days=365)

        return JsonResponse(data)


class LineChartView(LoginRequiredMixin, DetailView):
    """
    Display a line chart for a specific portfolio.

    Provides portfolio details and current date to the template for rendering.

    Attributes:
        model (Portfolio): The Portfolio model.
        pk_url_kwarg (str): URL parameter for portfolio ID.
        template_name (str): Template used to render the chart.
        context_object_name (str): Context variable for the portfolio object.
    """

    model = Portfolio
    pk_url_kwarg = "portfolio_id"
    template_name = "stocks/line_chart.html"
    context_object_name = "portfolio"

    def get_context_data(self, **kwargs) -> dict:
        """
        Add additional data to the template context, including the portfolio ID and today's date.

        Returns:
            dict: Context data for template rendering.
        """
        context = super().get_context_data(**kwargs)
        # Use get_object_or_404 with user check to ensure user owns the portfolio
        portfolio = get_object_or_404(
            Portfolio, pk=self.kwargs[self.pk_url_kwarg], user=self.request.user
        )
        context["portfolio_id"] = portfolio.id
        context["today"] = timezone.now().date().isoformat()
        return context


class TickerAutocomplete(View):
    """
    Provide autocomplete suggestions for stock tickers based on user query.

    Queries local database and Yahoo Finance API to retrieve matching tickers,
    marking whether each ticker is already available in the local system.

    Methods:
        get: Handle GET request and return ticker suggestions as JSON.
    """

    def get(self, request: HttpRequest) -> HttpResponse:
        """
        Process GET request to fetch ticker autocomplete suggestions.

        Args:
            request (HttpRequest): The HTTP request with 'q' query parameter.

        Returns:
            JsonResponse: List of suggestions containing tickers and labels.
        """
        q = request.GET.get("q", "").strip()
        if not q:
            # Return empty list if query is empty
            return JsonResponse([], safe=False)

        # Get existing tickers from local database matching query (case-insensitive)
        stocks_in_db = set(
            Stock.objects.filter(ticker__icontains=q).values_list("ticker", flat=True)
        )

        try:
            # Query Yahoo Finance search API for ticker suggestions
            url = "https://query1.finance.yahoo.com/v1/finance/search"
            params = {"q": q, "quotesCount": 10, "newsCount": 0}
            headers = {"User-Agent": "Mozilla/5.0"}
            resp = requests.get(url, params=params, headers=headers, timeout=5)

            results = []
            if resp.status_code == 200:
                data = resp.json().get("quotes", [])
                for item in data:
                    symbol = item.get("symbol")
                    # Fetch stock name favoring shortname, fallback to longname or empty
                    name = item.get("shortname") or item.get("longname") or ""
                    if symbol:
                        exists = symbol in stocks_in_db
                        label = (
                            f"{symbol} — {name} ({'Available' if exists else 'New'})"
                        )
                        results.append(
                            {
                                "ticker": symbol,
                                "label": label,
                            }
                        )
            return JsonResponse(results, safe=False)

        except Exception:
            # On API failure, fallback to local database suggestions
            stocks = Stock.objects.filter(ticker__icontains=q)[:10]
            results = []
            for stock in stocks:
                results.append(
                    {
                        "ticker": stock.ticker,
                        "label": f"{stock.ticker} — {stock.name or 'No name'} (Available)",
                    }
                )
            return JsonResponse(results, safe=False)


class TagAutocomplete(View):
    """
    Provide autocomplete suggestions for tags based on user query.

    Searches tags by case-insensitive containment of query string and returns
    up to 10 matching tags as JSON.

    Methods:
        get: Handle GET request and return tag suggestions as JSON.
    """

    def get(self, request: HttpRequest) -> HttpResponse:
        """
        Process GET request to fetch tag autocomplete suggestions.

        Args:
            request (HttpRequest): The HTTP request with 'q' query parameter.

        Returns:
            JsonResponse: List of tag suggestions with id and label.
        """
        q = request.GET.get("q", "").strip()
        # Search tags with names containing the query string (case-insensitive)
        tags = Tag.objects.filter(name__icontains=q)[:10]

        results = [{"id": t.id, "label": t.name} for t in tags]
        return JsonResponse(results, safe=False)
