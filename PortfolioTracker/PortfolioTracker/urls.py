from django.contrib import admin
from django.urls import path
from django.contrib.auth.views import LoginView, LogoutView

from stocks.views import (
    home,
    RegisterView,
    UserPortfoliosView,
    PortfolioDetailDeleteView,
    AddStockView,
    TransactionCreateView,
    AllTransactionsView,
    HoldingsView,
    PortfolioChartData,
    LineChartView,
    TickerAutocomplete,
    TagAutocomplete,
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home, name='home'),
    path('login/', LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', LogoutView.as_view(next_page='home'), name='logout'),
    path('register/', RegisterView.as_view(), name='register'),
    path('portfolios/', UserPortfoliosView.as_view(), name='user-portfolios'),
    path('portfolios/<int:portfolio_id>/', PortfolioDetailDeleteView.as_view(), name='portfolio-details'),
    path('stocks/add/', AddStockView.as_view(), name='add-stock'),
    path('portfolios/<int:portfolio_id>/transactions/add/', TransactionCreateView.as_view(), name='transaction'),
    path('portfolios/<int:portfolio_id>/transactions/', AllTransactionsView.as_view(), name='all-transactions'),
    path('portfolios/<int:portfolio_id>/holdings/', HoldingsView.as_view(), name='holdings'),
    path('portfolios/<int:portfolio_id>/line-chart/data/', PortfolioChartData.as_view(), name='line-chart-data'),
    path('portfolios/<int:portfolio_id>/line-chart/', LineChartView.as_view(), name='line-chart'),
    path('api/autocomplete/tickers/', TickerAutocomplete.as_view(), name='api-ticker-autocomplete'),
    path('api/autocomplete/tags/', TagAutocomplete.as_view(), name='api-tag-autocomplete'),
]