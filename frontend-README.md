# pyPortMan React Dashboard

A production-ready React dashboard for managing multiple Zerodha trading accounts.

## Features

- 📊 **Dashboard**: Portfolio overview with charts and metrics
- 👤 **Accounts**: Multi-account management with credential storage
- 📈 **Holdings**: Detailed portfolio holdings with P&L tracking
- 📋 **Orders**: Order management (pending, completed, GTT)
- 🎯 **Positions**: Real-time position monitoring with square-off
- ⚙️ **Settings**: Account configuration and API management

## Tech Stack

- **Frontend**: React 18 + Vite
- **Routing**: React Router v6
- **Charts**: Recharts
- **Styling**: Custom CSS (Dark Theme)

## Design

Dark theme optimized for trading with:
- Background: `#0b0f1a`
- Cards: `#111827`
- Primary accent: `#6366f1` (Indigo)
- Profit: `#22c55e` (Green)
- Loss: `#ef4444` (Red)

## Getting Started

1. **Install dependencies:**
```bash
npm install
```

2. **Start development server:**
```bash
npm run dev
```

3. **Open browser:**
Navigate to `http://localhost:3000`

## Project Structure

```
src/
├── components/          # Reusable UI components
│   ├── Sidebar.jsx      # Navigation sidebar
│   ├── TopBar.jsx       # Market status bar
│   ├── MetricCard.jsx   # Metric display cards
│   ├── HoldingsTable.jsx # Holdings data table
│   ├── OrdersTable.jsx  # Orders data table
│   ├── AccountCard.jsx  # Account cards
│   └── PositionsTable.jsx # Positions data table
├── pages/               # Page components
│   ├── Dashboard.jsx    # Main dashboard
│   ├── Accounts.jsx     # Account management
│   ├── Holdings.jsx     # Portfolio holdings
│   ├── Orders.jsx       # Order management
│   ├── Positions.jsx    # Current positions
│   └── Settings.jsx     # Settings page
├── data/
│   └── mockData.js      # Mock data and utilities
├── App.jsx              # Main app component
├── main.jsx             # App entry point
├── App.css              # App-specific styles
└── index.css            # Global styles
```

## Mock Data

The dashboard uses realistic Indian stock market data:

- **Accounts**: 3 accounts (Main, Wife, HUF) with 5-15L values
- **Stocks**: RELIANCE, TCS, INFY, HDFC BANK, ICICI, etc.
- **Markets**: Realistic P&L with mix of gains and losses
- **Currency**: Indian Rupees (₹) with lakh/crore formatting

## Features Implemented

✅ Responsive design (mobile, tablet, desktop)
✅ Dark theme throughout
✅ Interactive charts with Recharts
✅ Sortable, searchable tables
✅ Indian number formatting (₹1.5L not ₹150,000)
✅ Market status tracking (9:15 AM - 3:30 PM IST)
✅ Realistic P&L calculations
✅ Account management with add/edit forms
✅ Order placement forms
✅ GTT order tracking
✅ Position square-off functionality

## Customization

To integrate with real Zerodha Kite API:

1. Replace mock data in `src/data/mockData.js` with API calls
2. Implement authentication flow
3. Add WebSocket for live market data
4. Add error handling and loading states

## Building for Production

```bash
npm run build
```

Static files will be in `dist/` directory.

## Deployment

Serve the `dist/` folder using any static file server or integrate with Python backend.

## Screenshots

_Dashboard with portfolio charts_
_Detailed holdings table with P&L_
_Account management interface_
_Order placement form_

## Contributing

This dashboard is designed for the pyPortMan project. For issues or feature requests, create an issue on GitHub.

## License

MIT License - same as pyPortMan project
