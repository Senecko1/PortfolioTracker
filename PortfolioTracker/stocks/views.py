import requests
import yfinance as yf
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import IntegrityError
from django.http import JsonResponse
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


def home(request):
    if request.user.is_authenticated:
        return redirect("user-portfolios")
    return render(request, "home.html")


class RegisterView(CreateView):
    template_name = "stocks/register.html"
    form_class = UserCreationForm
    success_url = reverse_lazy("user-portfolios")

    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object)
        return response


class UserPortfoliosView(LoginRequiredMixin, ListView):
    model = Portfolio
    template_name = "stocks/user_portfolios.html"
    context_object_name = "portfolios"

    def get_queryset(self):
        return self.model.objects.filter(user=self.request.user)

    def post(self, request, *args, **kwargs):
        form = PortfolioForm(request.POST)
        form.instance.user = request.user
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
        return self.get(request, form=form, open_modal="portfolioModal")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["portfolio_form"] = kwargs.get("form", PortfolioForm())
        context["open_modal"] = kwargs.get("open_modal")
        return context


class PortfolioDetailDeleteView(LoginRequiredMixin, DetailView):
    model = Portfolio
    pk_url_kwarg = "portfolio_id"
    template_name = "stocks/portfolio_details.html"
    context_object_name = "portfolio"
    success_url = reverse_lazy("user-portfolios")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["holdings_with_prices"] = self.object.get_holdings_with_prices()
        context["summary"] = self.object.get_portfolio_summary()
        context["transactions"] = Transaction.objects.filter(portfolio=self.object)
        context["portfolio_id"] = self.object.id
        return context

    def post(self, request, *args, **kwargs):
        if request.POST.get("action") == "delete":
            portfolio = self.get_object()
            portfolio.delete()
            messages.success(
                request, f'Portfolio "{portfolio.name}" was deleted successfully.'
            )
            return redirect(self.success_url)
        else:
            return super().get(request, *args, **kwargs)


class AddStockView(LoginRequiredMixin, View):
    def post(self, request):
        ticker = request.POST.get("ticker", "").upper().strip()
        raw_tags = request.POST.getlist("tags")

        if not ticker:
            messages.error(request, "Please enter a stock ticker.")
            return redirect("user-portfolios")

        stock, created = Stock.objects.get_or_create(ticker=ticker)
        if created:
            try:
                yf_stock = yf.Ticker(ticker)
                info = yf_stock.info
                stock.name = info.get("shortName", "")[:100]
                currency = info.get("currency", "")
                stock.currency = CURRENCY_SYMBOLS.get(currency, currency)

                stock.last_price = info.get("currentPrice", 0)
                stock.save()
                messages.success(request, f"Stock {ticker} added to the system.")
            except Exception as e:
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
                    continue
            else:
                tag, _ = Tag.objects.get_or_create(name=raw.strip())
            tags_to_set.append(tag)

        stock.tags.set(tags_to_set)

        return redirect("user-portfolios")


class TransactionCreateView(LoginRequiredMixin, CreateView):
    model = Transaction
    form_class = TransactionForm
    template_name = "stocks/transaction.html"

    def dispatch(self, request, *args, **kwargs):
        self.portfolio = get_object_or_404(
            Portfolio, pk=kwargs["portfolio_id"], user=request.user
        )
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["portfolio"] = self.portfolio
        return kwargs

    def form_valid(self, form):
        form.instance.portfolio = self.portfolio
        response = super().form_valid(form)
        self._update_holdings(form.instance)
        return response

    def _update_holdings(self, transaction):
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
                holding.delete()
            else:
                holding.quantity = new_quantity
                holding.save()

    def get_success_url(self):
        return reverse_lazy(
            "portfolio-details", kwargs={"portfolio_id": self.portfolio.pk}
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["portfolio"] = self.portfolio
        context["portfolio_id"] = self.portfolio.pk
        return context


class AllTransactionsView(LoginRequiredMixin, ListView):
    model = Transaction
    pk_url_kwarg = "portfolio_id"
    template_name = "stocks/all_transactions.html"
    context_object_name = "transactions"

    def get_queryset(self):
        return Transaction.objects.filter(portfolio=self.kwargs["portfolio_id"])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        portfolio = Portfolio.objects.get(pk=self.kwargs["portfolio_id"])
        context["portfolio"] = portfolio
        context["portfolio_id"] = portfolio.id
        context["DATE_FORMAT_DISPLAY"] = DATE_FORMAT_DISPLAY
        return context


class HoldingsView(LoginRequiredMixin, ListView):
    model = Holding
    pk_url_kwarg = "portfolio_id"
    template_name = "stocks/holdings.html"
    context_object_name = "holdings"

    def get_queryset(self):
        portfolio_id = self.kwargs.get("portfolio_id")
        return self.model.objects.filter(
            portfolio__pk=portfolio_id, portfolio__user=self.request.user
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        holdings = context["holdings"]
        labels = []
        values = []
        total_value = 0
        fresh_data = []
        for holding in holdings:
            price = holding.stock.last_price or 0
            current_value = holding.quantity * price
            total_value += current_value
            fresh_data.append((holding, current_value))
        for holding, current_value in fresh_data:
            labels.append(holding.stock.ticker)
            values.append(
                round((current_value / total_value) * 100, 2) if total_value > 0 else 0
            )
        portfolio = Portfolio.objects.get(pk=self.kwargs["portfolio_id"])
        context["portfolio"] = portfolio
        context["chart_labels"] = labels
        context["chart_values"] = values
        context["portfolio_id"] = portfolio.id
        return context


class PortfolioChartData(LoginRequiredMixin, View):
    def get(self, request, portfolio_id):
        portfolio = get_object_or_404(Portfolio, pk=portfolio_id, user=request.user)
        data = portfolio.get_time_series(days=365)
        return JsonResponse(data)


class LineChartView(LoginRequiredMixin, DetailView):
    model = Portfolio
    pk_url_kwarg = "portfolio_id"
    template_name = "stocks/line_chart.html"
    context_object_name = "portfolio"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        portfolio = Portfolio.objects.get(pk=self.kwargs["portfolio_id"])
        context["portfolio_id"] = portfolio.id
        context["today"] = timezone.now().date().isoformat()
        return context


class TickerAutocomplete(View):
    def get(self, request):
        q = request.GET.get("q", "").strip()
        if not q:
            return JsonResponse([], safe=False)

        try:
            url = "https://query1.finance.yahoo.com/v1/finance/search"
            params = {"q": q, "quotesCount": 10, "newsCount": 0}
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            resp = requests.get(url, params=params, headers=headers, timeout=5)

            if resp.status_code == 200:
                try:
                    data = resp.json().get("quotes", [])
                    results = []
                    for item in data:
                        symbol = item.get("symbol")
                        name = item.get("shortname") or item.get("longname") or ""
                        currency = item.get("currency") or ""
                        if symbol:
                            results.append(
                                {
                                    "ticker": symbol,
                                    "label": f"{symbol} — {name} ({currency})",
                                }
                            )
                    return JsonResponse(results, safe=False)
                except ValueError:
                    pass
        except:
            pass

        stocks = Stock.objects.filter(ticker__icontains=q)[:10]
        results = []
        for stock in stocks:
            results.append(
                {
                    "ticker": stock.ticker,
                    "label": f"{stock.ticker} — {stock.name or 'No name'}",
                }
            )
        return JsonResponse(results, safe=False)


class TagAutocomplete(View):
    def get(self, request):
        q = request.GET.get("q", "").strip()
        tags = Tag.objects.filter(name__icontains=q)[:10]
        results = [{"id": t.id, "label": t.name} for t in tags]
        return JsonResponse(results, safe=False)
