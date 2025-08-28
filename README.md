# PortfolioTracker

PortfolioTracker is a web application for managing and tracking investment portfolios. It allows users to record their stocks, transactions, and portfolio value trends with visualizations. The project uses Django as the backend framework, TailwindCSS for responsive frontend styling, and JavaScript for interactive features.

---

## Features

### Backend

- User registration, login, and session management.
- Portfolio management: create, view, and delete portfolios.
- Add stocks (tickers) with name and currency information.
- Record buy and sell transactions within portfolios.
- Calculate and update holdings, including average purchase price.
- Compute current portfolio value and profit/loss.
- Retrieve real-time stock prices via Yahoo Finance.
- JSON API endpoints for ticker and tag autocomplete.
- Provide time-series data for portfolio value visualizations.

### Frontend

- **Clearly organized templates:**
  - Login page (`login.html`)
  - Registration page (`register.html`)
  - Home page (`home.html`)
  - User portfolios overview (`user_portfolios.html`)
  - Portfolio details with holdings summary (`portfolio_details.html`)
  - Make a transaction (`transaction.html`)
  - Transactions listing (`all_transactions.html`)
  - Holdings breakdown view (`holdings.html`)
  - Portfolio time-series chart (`line_chart.html`)
- **TailwindCSS styling** for a clean, modern, and responsive UI
- **JavaScript interactivity:**
  - Autocomplete for stock tickers
  - Autocomplete for tags with multi-value support
  - Modal windows for forms (open/close animations) (`main.js`)
  - Interactive line charts for portfolio value over time (`line_chart.js`)
  - Doughnut charts for holdings distribution (`doughnut_chart.js`)
  - Chart.js library for chart rendering

---

## Technologies

- **Backend:** Python 3.x, Django 5.2.4
- **Database:** PostgreSQL
- **Frontend:** HTML + Django templating, TailwindCSS, JavaScript (ES6+)
- **Visualization:** Chart.js
- **Data:** yfinance for Yahoo Finance stock data
- **Styling:** TailwindCSS utility classes with custom components

---

## Project Structure

```
PortfolioTracker/
├── PortfolioTracker/
│   ├── settings.py
│   ├── urls.py
├── stocks/
│   ├── management/
│   │   └── commands/
│   │       └── seed.py
│   ├── migrations/
│   ├── static/
│   │   ├── css/
│   │   │   ├── custom.css
│   │   │   └── style.css
│   │   └── js/
│   │       ├── doughnut_chart.js
│   │       ├── line_chart.js
│   │       └── main.js
│   ├── templates/
│   │   ├── base.html
│   │   ├── home.html
│   │   ├── registration/
│   │   │   └── login.html
│   │   └── stocks/
│   │       ├── all_transactions.html
│   │       ├── holdings.html
│   │       ├── line_chart.html
│   │       ├── portfolio_details.html
│   │       ├── register.html
│   │       ├── transaction.html
│   │       └── user_portfolios.html
│   ├── admin.py
│   ├── config.py
│   ├── forms.py
│   ├── models.py
│   └── views.py
├── manage.py
└── requirements.txt
```

---

## Installation & Setup

1. Clone the repository.
2. Create and activate a virtual environment:

   ```bash
   python -m venv venv
   source venv/bin/activate     # macOS/Linux
   venv\Scripts\activate        # Windows
   ```

3. Install dependencies:

   ```bash
   cd PortfolioTracker/
   pip install -r requirements.txt
   ```

4. Configure the PostgreSQL database in `settings.py` (DB name, user, password, host).
5. Apply migrations:

   ```bash
   python manage.py migrate
   ```

6. Load demo data (recommended for first run):

   ```bash
   python manage.py seeds
   ```

   This command creates:
   - A demo user (`demo_user` / `demo1234`)
   - "Demo portfolio" with sample data
   - 7 stocks (AAPL, MSFT, TSLA, GOOGL, AMZN, META, PFE)
   - 9 demo transactions
   - Precomputed holdings with average purchase prices

7. Start the development server:

   ```bash
   python manage.py runserver
   ```

8. Open your browser at:

   ```
   http://localhost:8000
   ```

9. Use the demo account to explore:
   - Username: `demo_user`
   - Password: `demo1234`

---

## Demo Data Details

### Stocks in Demo Portfolio:
- **Apple Inc. (AAPL)**: 21 shares, avg. price ~$204
- **Microsoft Corp. (MSFT)**: 14 shares, avg. price ~$427
- **Tesla Inc. (TSLA)**: 13 shares, price $284
- **Alphabet Inc. (GOOGL)**: 21 shares, price $167
- **Amazon.com Inc. (AMZN)**: 16 shares, price $200
- **Meta Platforms Inc. (META)**: 5 shares, price $522
- **Pfizer Inc. (PFE)**: 112 shares, price $31

### Transactions:
- 9 sample transactions ranging from Feb to Aug 2024
- Various quantities and fees

Use demo data to **immediately** explore all features without manual entry.

---

## Data Management

### Reset Demo Data

To reset and reload demo data:

```bash
python manage.py flush      # Deletes all data
python manage.py migrate    # Reapply migrations
python manage.py seeds      # Reload demo data
```

### Custom Data

Register a new user via the registration form and start adding your own portfolios and transactions.

---

## JavaScript Functionality

### Autocomplete System
- **Ticker autocomplete:** Fetches suggestions from Yahoo Finance API
- **Tag autocomplete:** Supports multiple tags separated by commas
- **Real-time suggestions** as you type

### Interactive Charts
- **Time-series line charts** for portfolio value using Chart.js
- **Doughnut charts** for holdings distribution
- **Responsive design** adapts charts to screen size

### Modal Windows
- **Smooth animations** for opening/closing
- **Close on ESC key** and **click outside**

---

## User Guide

- Home page links to login or registration.
- Quick access via demo account: `demo_user` / `demo1234`
- After login, view your portfolios list.
- Create new portfolios using the provided form.
- Add new stock with ticker autocomplete.
- Portfolio detail page shows holdings summary and profit/loss.
- Add transactions (BUY/SELL)
- View all transactions separately.
- View holdings breakdown with an interactive doughnut chart.
- Monitor portfolio value over time with an interactive line chart.

---

## Dependencies

### Python packages
- Django 5.2.4
- psycopg2 (PostgreSQL adapter)
- yfinance
- pandas

### Frontend libraries
- TailwindCSS 4.1.12
- Chart.js
- Vanilla JavaScript (no additional frameworks)

---

## License

MIT License — free to use and modify with attribution.

---

## Contact & Further Information

For questions or collaboration, contact the project author.
- **GitHub:** Senecko1
- **Email:** slamajakub@email.cz
