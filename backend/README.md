# pyPortMan Backend

FastAPI backend for pyPortMan - Zerodha KiteConnect multi-account portfolio management.

## Features

- Multi-account Zerodha integration
- Real-time portfolio tracking
- Automated data refresh during market hours
- SQLite database for data persistence
- REST API for React frontend
- Order placement and cancellation
- Position management
- Portfolio analytics and equity curve

## Installation

1. **Clone the repository**
   ```bash
   cd pyPortMan/backend
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   ```

3. **Activate virtual environment**

   Windows:
   ```bash
   venv\Scripts\activate
   ```

   Linux/Mac:
   ```bash
   source venv/bin/activate
   ```

4. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

5. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

## Usage

### Start the server

**Windows:**
```bash
start_backend.bat
```

**Linux/Mac:**
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

### API Documentation

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## First-Time Setup

1. **Add your Zerodha account**
   ```bash
   POST /accounts
   {
     "name": "My Account",
     "account_id": "ZERODHA_USER_ID",
     "api_key": "YOUR_API_KEY",
     "api_secret": "YOUR_API_SECRET"
   }
   ```

2. **Get login URL**
   ```bash
   GET /accounts/{id}/token-url
   ```

3. **Complete Zerodha login** - Open the returned URL in your browser and login

4. **Get request token** - After login, you'll be redirected with `request_token` in the URL

5. **Generate access token**
   ```bash
   POST /auth/callback
   {
     "account_id": 1,
     "request_token": "REQUEST_TOKEN_FROM_URL"
   }
   ```

6. **Your account is now ready!** - Fetch holdings, positions, and place orders

## API Endpoints

### Accounts
- `GET /accounts` - Get all accounts
- `POST /accounts` - Add new account
- `PUT /accounts/{id}` - Update account
- `DELETE /accounts/{id}` - Remove account
- `GET /accounts/{id}/token-url` - Get Zerodha login URL

### Holdings
- `GET /holdings` - Get all holdings
- `GET /holdings/{account_id}` - Get holdings for one account
- `POST /holdings/refresh` - Fetch fresh from Zerodha API

### Positions
- `GET /positions` - Get all open positions
- `GET /positions/{account_id}` - Get positions for one account
- `POST /positions/{account_id}/squareoff-all` - Square off all positions
- `POST /positions/squareoff` - Square off single position

### Orders
- `GET /orders` - Get all orders
- `GET /orders/{account_id}` - Get orders for one account
- `POST /orders` - Place new order
- `DELETE /orders/{order_id}` - Cancel order

### Stats
- `GET /stats/summary` - Combined portfolio stats
- `GET /stats/equity` - 30-day portfolio value history
- `GET /stats/allocation` - Sector/stock allocation breakdown
- `GET /stats/top-gainers` - Top 5 gaining stocks
- `GET /stats/top-losers` - Top 5 losing stocks

### Auth
- `GET /auth/login-url/{account_id}` - Generate Zerodha login URL
- `POST /auth/callback` - Handle access token after login

## Important Notes

### Token Expiration
- KiteConnect access tokens expire daily at 6 AM IST
- You need to re-login each day to get a new token
- The scheduler will not refresh data if token is expired

### Market Hours
- Data auto-refreshes every 5 minutes during market hours (9:15 AM - 3:30 PM IST)
- Portfolio snapshots are saved every 15 minutes
- No refresh on weekends

### Error Handling
- If access token expired → Returns 401 with message
- If Zerodha API down → Returns cached data from database
- All errors are logged to `app.log`

## Project Structure

```
backend/
├── main.py              # FastAPI app entry point
├── kite_manager.py      # Multi-account KiteConnect manager
├── database.py          # SQLite setup using SQLAlchemy
├── models.py            # DB models
├── scheduler.py         # Auto-refresh data every 5 minutes
├── requirements.txt     # Python dependencies
├── .env.example         # API keys template
├── .env                 # Your environment variables
├── start_backend.bat    # Windows startup script
└── pyportman.db         # SQLite database (created on first run)
```

## Development

### Run with hot reload
```bash
uvicorn main:app --reload
```

### Reset database
```python
from database import reset_db
reset_db()
```

## License

MIT License
