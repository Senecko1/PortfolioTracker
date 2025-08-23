from django.contrib import admin
from django.urls import path
from django.contrib.auth.views import LoginView, LogoutView

from stocks.views import (
    home,
    RegisterView,
    UserPortfoliosView,
    PortfolioDetailView,
    PortfolioDeleteView,
    AddStockView,
    TransactionCreateView,
    AllTransactionsView,
    HoldingsView,
    PortfolioChartData,
    LineChartView,
    TagAutocompleteView,
    StockAutocompleteView,
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home, name='home'),
    path('login/', LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', LogoutView.as_view(next_page='home'), name='logout'),
    path('register/', RegisterView.as_view(), name='register'),
    path('portfolios/', UserPortfoliosView.as_view(), name='user-portfolios'),
    path('portfolios/<int:portfolio_id>/', PortfolioDetailView.as_view(), name='portfolio-details'),
    path('portfolios/<int:portfolio_id>/delete/', PortfolioDeleteView.as_view(), name='delete-portfolio'),
    path('stocks/add/', AddStockView.as_view(), name='add-stock'),
    path('portfolios/<int:portfolio_id>/transactions/add/', TransactionCreateView.as_view(), name='transaction'),
    path('portfolios/<int:portfolio_id>/transactions/', AllTransactionsView.as_view(), name='all-transactions'),
    path('portfolios/<int:portfolio_id>/holdings/', HoldingsView.as_view(), name='holdings'),
    path('portfolios/<int:portfolio_id>/line-chart/data/', PortfolioChartData.as_view(), name='line-chart-data'),
    path('portfolios/<int:portfolio_id>/line-chart/', LineChartView.as_view(), name='line-chart'),




    path('tag_autocomplete/', TagAutocompleteView.as_view(), name='tag-autocomplete'),
    path('stock_autocomplete/', StockAutocompleteView.as_view(), name='stock-autocomplete'),
]
