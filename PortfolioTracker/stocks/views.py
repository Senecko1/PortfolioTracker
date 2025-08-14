import requests
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import IntegrityError
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
)

import yfinance as yf
from .forms import PortfolioForm, TransactionForm
from .models import Portfolio, Stock, Holding, Transaction, Tag

def home(request):
    if request.user.is_authenticated:
        return redirect('user-portfolios')
    return render(request, 'home.html')


class RegisterView(CreateView):
    template_name = 'stocks/register.html'
    form_class = UserCreationForm
    success_url = reverse_lazy('user-portfolios')

    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object)
        return response


class UserPortfoliosView(LoginRequiredMixin, ListView):
    model = Portfolio
    template_name = 'stocks/user_portfolios.html'
    context_object_name = 'portfolios'

    def get_queryset(self):
        return self.model.objects.filter(user=self.request.user)

    def post(self, request, *args, **kwargs):
        form = PortfolioForm(request.POST)
        form.instance.user = request.user
        if form.is_valid():
            try:
                form.save()
                return redirect('user-portfolios')
            except IntegrityError:
                messages.error(request, f'Portfolio "{form.instance.name}" already exists.')
        else:
            messages.error(request, 'Please correct the errors below.')
        return self.get(request, form=form, open_modal='portfolioModal')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['portfolio_form'] = kwargs.get('form', PortfolioForm())
        context['open_modal'] = kwargs.get('open_modal')
        return context



class PortfolioDetailView(LoginRequiredMixin, DetailView):
    model = Portfolio
    pk_url_kwarg = 'portfolio_id'
    template_name = 'stocks/portfolio_details.html'
    context_object_name = 'portfolio'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['holdings_with_prices'] = self.object.get_holdings_with_prices()
        context['transactions'] = Transaction.objects.filter(portfolio=self.object)
        context['portfolio_id'] = self.object.id
        return context


class PortfolioDeleteView(LoginRequiredMixin, DeleteView):
    model = Portfolio
    pk_url_kwarg = 'portfolio_id'
    success_url = reverse_lazy('user-portfolios')


class AddStockView(LoginRequiredMixin, View):
    def post(self, request):
        ticker = request.POST.get('ticker', '').upper().strip()
        raw_tags = request.POST.getlist('tags')

        if not ticker:
            messages.error(request, 'Please enter a stock ticker.')
            return redirect('user-portfolios')

        stock, created = Stock.objects.get_or_create(ticker=ticker)
        if created:
            try:
                yf_stock = yf.Ticker(ticker)
                info = yf_stock.info
                stock.name = info.get('shortName', '')[:100]
                currency_symbols = {
                    'USD': '$',
                    'EUR': '€',
                    'GBP': '£',
                    'CZK': 'Kč',
                }
                currency = info.get('currency', '')
                stock.currency = currency_symbols.get(currency, currency)

                stock.last_price = info.get('currentPrice', 0)
                stock.save()
                messages.success(request, f"Stock {ticker} added to the system.")
            except Exception as e:
                stock.save()
                messages.warning(request, f"Ticker {ticker} added, but fetching data failed: {e}")
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

        return redirect('user-portfolios')



class TransactionCreateView(LoginRequiredMixin, CreateView):
    model = Transaction
    form_class = TransactionForm
    template_name = 'stocks/transaction.html'

    def dispatch(self, request, *args, **kwargs):
        self.portfolio = get_object_or_404(Portfolio, pk=kwargs['portfolio_id'], user=request.user)
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['portfolio'] = self.portfolio
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
                'quantity': 0, 
                'buy_price': 0, 
                'buy_date': transaction.transaction_date
            }
        )

        if transaction.transaction_type == 'BUY':
            total_old_value = holding.quantity * float(holding.buy_price)
            total_new_value = transaction.quantity * float(transaction.price)
            new_quantity = holding.quantity + transaction.quantity
            new_avg_price = (total_old_value + total_new_value) / new_quantity

            holding.quantity = new_quantity
            holding.buy_price = round(new_avg_price, 2)
            holding.buy_date = transaction.transaction_date
            holding.save()

        elif transaction.transaction_type == 'SELL':
            new_quantity = holding.quantity - transaction.quantity
            if new_quantity == 0:
                holding.delete()
            else:
                holding.quantity = new_quantity
                holding.save()

    def get_success_url(self):
        return reverse_lazy('portfolio-details', kwargs={'portfolio_id': self.portfolio.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['portfolio'] = self.portfolio
        context['portfolio_id'] = self.portfolio.pk
        return context




class AllTransactionsView(LoginRequiredMixin, ListView):
    model = Transaction
    pk_url_kwarg = 'portfolio_id'
    template_name = 'stocks/all_transactions.html'
    context_object_name = 'transactions'

    def get_queryset(self):
        return Transaction.objects.filter(portfolio=self.kwargs['portfolio_id'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        portfolio = Portfolio.objects.get(pk=self.kwargs['portfolio_id'])
        context['portfolio'] = portfolio
        context['portfolio_id'] = portfolio.id
        return context



class HoldingsView(LoginRequiredMixin, ListView):
    model = Holding
    pk_url_kwarg = 'portfolio_id'
    template_name = 'stocks/holdings.html'
    context_object_name = 'holdings'

    def get_queryset(self):
        portfolio_id = self.kwargs.get('portfolio_id')
        return self.model.objects.filter(portfolio__pk=portfolio_id, portfolio__user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        holdings = context['holdings']
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
            values.append(round((current_value / total_value) * 100, 2) if total_value > 0 else 0)
        portfolio = Portfolio.objects.get(pk=self.kwargs['portfolio_id'])
        context['portfolio'] = portfolio
        context['chart_labels'] = labels
        context['chart_values'] = values
        if holdings:
            context['portfolio_id'] = holdings[0].portfolio.id
        return context


















class TagAutocompleteView(LoginRequiredMixin, View):
    def get(self, request):
        q = request.GET.get('q', '').strip()
        results = []
        if q:
            tags = Tag.objects.filter(name__icontains=q).order_by('name')[:20]
            for tag in tags:
                results.append({'id': tag.name, 'text': tag.name})
        return JsonResponse({'results': results})



class StockAutocompleteView(View):
    def get(self, request):
        q = request.GET.get('q', '').strip().upper()
        results = []

        if not q:
            return JsonResponse({'results': results})

        local_stocks = Stock.objects.filter(ticker__icontains=q).order_by('ticker')[:5]
        for stock in local_stocks:
            display_name = f"{stock.ticker}"
            if stock.name:
                display_name += f" – {stock.name}"
            display_name += " (Local)"
            results.append({
                'id': stock.ticker,
                'text': display_name
            })

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        response = requests.get(
            "https://query2.finance.yahoo.com/v1/finance/search",
            params={
                'q': q,
                'quotesCount': 15,
                'newsCount': 0,
                'listsCount': 0,
                'quotesQueryId': 'tss_match_phrase_query'
            },
            headers=headers,
            timeout=3
        )

        if response.status_code == 200:
            data = response.json()
            quotes = data.get('quotes', [])
            seen_tickers = {result['id'] for result in results}

            for quote in quotes:
                symbol = quote.get('symbol', '')
                if not symbol or symbol in seen_tickers:
                    continue

                if '.' in symbol or len(symbol) > 5:
                    continue

                short_name = quote.get('shortname', '')
                long_name = quote.get('longname', '')
                exchange = quote.get('exchDisp', '')

                company_name = short_name or long_name
                display_parts = [symbol]
                if company_name:
                    display_parts.append(company_name)
                if exchange:
                    display_parts.append(f"({exchange})")

                display_text = " – ".join(display_parts)

                results.append({
                    'id': symbol,
                    'text': display_text
                })

                seen_tickers.add(symbol)

                if len(results) >= 20:
                    break

        local_results = [r for r in results if 'Local' in r['text']]
        yahoo_results = [r for r in results if 'Local' not in r['text']]
        yahoo_results.sort(key=lambda x: x['text'])

        final_results = local_results + yahoo_results

        return JsonResponse({
            'results': final_results,
            'total_count': len(final_results)
        })
