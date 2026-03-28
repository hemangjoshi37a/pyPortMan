export const accounts = [
  {
    id: 'ACC001',
    name: 'Main Account',
    broker: 'zerodha',
    status: 'active',
    totalInvested: 1000000,
    currentValue: 1250000,
    dayPL: 8500,
    overallPL: 250000,
    apiKey: 'abcd1234',
    apiSecret: 'secret123',
    accessToken: 'token123'
  },
  {
    id: 'ACC002',
    name: 'Wife Account',
    broker: 'zerodha',
    status: 'active',
    totalInvested: 700000,
    currentValue: 830000,
    dayPL: -3200,
    overallPL: 130000,
    apiKey: 'efgh5678',
    apiSecret: 'secret456',
    accessToken: 'token456'
  },
  {
    id: 'ACC003',
    name: 'HUF Account',
    broker: 'angel',
    status: 'active',
    totalInvested: 500000,
    currentValue: 670000,
    dayPL: 5400,
    overallPL: 170000,
    apiKey: 'ijkl9012',
    apiSecret: 'secret789',
    accessToken: 'token789'
  }
];

export const holdings = [
  // Main Account Holdings
  { accountId: 'ACC001', accountName: 'Main Account', symbol: 'RELIANCE', qty: 50, avgBuyPrice: 2500, ltp: 2680, dayChange: 2.5 },
  { accountId: 'ACC001', accountName: 'Main Account', symbol: 'TCS', qty: 25, avgBuyPrice: 3200, ltp: 3450, dayChange: 1.8 },
  { accountId: 'ACC001', accountName: 'Main Account', symbol: 'INFY', qty: 100, avgBuyPrice: 1450, ltp: 1520, dayChange: -0.5 },
  { accountId: 'ACC001', accountName: 'Main Account', symbol: 'HDFCBANK', qty: 75, avgBuyPrice: 1600, ltp: 1580, dayChange: -1.2 },
  { accountId: 'ACC001', accountName: 'Main Account', symbol: 'ICICIBANK', qty: 80, avgBuyPrice: 850, ltp: 920, dayChange: 3.1 },
  { accountId: 'ACC001', accountName: 'Main Account', symbol: 'WIPRO', qty: 120, avgBuyPrice: 420, ltp: 445, dayChange: 0.8 },
  { accountId: 'ACC001', accountName: 'Main Account', symbol: 'SBIN', qty: 150, avgBuyPrice: 550, ltp: 580, dayChange: 2.0 },
  { accountId: 'ACC001', accountName: 'Main Account', symbol: 'TATAMOTORS', qty: 200, avgBuyPrice: 480, ltp: 465, dayChange: -2.5 },
  { accountId: 'ACC001', accountName: 'Main Account', symbol: 'BAJFINANCE', qty: 30, avgBuyPrice: 7000, ltp: 7250, dayChange: 1.5 },
  { accountId: 'ACC001', accountName: 'Main Account', symbol: 'HCLTECH', qty: 60, avgBuyPrice: 1100, ltp: 1150, dayChange: 1.2 },

  // Wife Account Holdings
  { accountId: 'ACC002', accountName: 'Wife Account', symbol: 'RELIANCE', qty: 30, avgBuyPrice: 2450, ltp: 2680, dayChange: 2.5 },
  { accountId: 'ACC002', accountName: 'Wife Account', symbol: 'TCS', qty: 20, avgBuyPrice: 3150, ltp: 3450, dayChange: 1.8 },
  { accountId: 'ACC002', accountName: 'Wife Account', symbol: 'INFY', qty: 80, avgBuyPrice: 1480, ltp: 1520, dayChange: -0.5 },
  { accountId: 'ACC002', accountName: 'Wife Account', symbol: 'HDFCBANK', qty: 60, avgBuyPrice: 1580, ltp: 1580, dayChange: -1.2 },
  { accountId: 'ACC002', accountName: 'Wife Account', symbol: 'ICICIBANK', qty: 70, avgBuyPrice: 860, ltp: 920, dayChange: 3.1 },
  { accountId: 'ACC002', accountName: 'Wife Account', symbol: 'WIPRO', qty: 100, avgBuyPrice: 425, ltp: 445, dayChange: 0.8 },
  { accountId: 'ACC002', accountName: 'Wife Account', symbol: 'BAJFINANCE', qty: 20, avgBuyPrice: 6900, ltp: 7250, dayChange: 1.5 },
  { accountId: 'ACC002', accountName: 'Wife Account', symbol: 'HCLTECH', qty: 45, avgBuyPrice: 1120, ltp: 1150, dayChange: 1.2 },

  // HUF Account Holdings
  { accountId: 'ACC003', accountName: 'HUF Account', symbol: 'RELIANCE', qty: 40, avgBuyPrice: 2480, ltp: 2680, dayChange: 2.5 },
  { accountId: 'ACC003', accountName: 'HUF Account', symbol: 'INFY', qty: 90, avgBuyPrice: 1460, ltp: 1520, dayChange: -0.5 },
  { accountId: 'ACC003', accountName: 'HUF Account', symbol: 'ICICIBANK', qty: 85, avgBuyPrice: 855, ltp: 920, dayChange: 3.1 },
  { accountId: 'ACC003', accountName: 'HUF Account', symbol: 'WIPRO', qty: 110, avgBuyPrice: 422, ltp: 445, dayChange: 0.8 },
  { accountId: 'ACC003', accountName: 'HUF Account', symbol: 'SBIN', qty: 180, avgBuyPrice: 540, ltp: 580, dayChange: 2.0 },
  { accountId: 'ACC003', accountName: 'HUF Account', symbol: 'TATAMOTORS', qty: 250, avgBuyPrice: 475, ltp: 465, dayChange: -2.5 },
  { accountId: 'ACC003', accountName: 'HUF Account', symbol: 'BAJFINANCE', qty: 35, avgBuyPrice: 6950, ltp: 7250, dayChange: 1.5 },
  { accountId: 'ACC003', accountName: 'HUF Account', symbol: 'HCLTECH', qty: 55, avgBuyPrice: 1110, ltp: 1150, dayChange: 1.2 }
];

export const orders = [
  {
    id: 'ORD001',
    accountId: 'ACC001',
    symbol: 'RELIANCE',
    qty: 50,
    type: 'LIMIT',
    side: 'BUY',
    price: 2650,
    status: 'COMPLETE',
    timestamp: '2024-01-15T10:30:00'
  },
  {
    id: 'ORD002',
    accountId: 'ACC001',
    symbol: 'TCS',
    qty: 25,
    type: 'MARKET',
    side: 'BUY',
    price: 3420,
    status: 'COMPLETE',
    timestamp: '2024-01-15T11:15:00'
  },
  {
    id: 'ORD003',
    accountId: 'ACC002',
    symbol: 'HDFCBANK',
    qty: 60,
    type: 'LIMIT',
    side: 'SELL',
    price: 1600,
    status: 'PENDING',
    timestamp: '2024-01-16T09:30:00'
  },
  {
    id: 'ORD004',
    accountId: 'ACC001',
    symbol: 'INFY',
    qty: 100,
    type: 'LIMIT',
    side: 'BUY',
    price: 1500,
    status: 'OPEN',
    timestamp: '2024-01-16T10:00:00'
  },
  {
    id: 'ORD005',
    accountId: 'ACC003',
    symbol: 'BAJFINANCE',
    qty: 35,
    type: 'LIMIT',
    side: 'BUY',
    price: 7200,
    status: 'COMPLETE',
    timestamp: '2024-01-15T14:30:00'
  }
];

export const positions = [
  {
    id: 'POS001',
    accountId: 'ACC001',
    symbol: 'ICICIBANK',
    product: 'MIS',
    qty: 80,
    avgPrice: 885,
    ltp: 920,
    pnl: 2800,
    dayChange: 3.1
  },
  {
    id: 'POS002',
    accountId: 'ACC002',
    symbol: 'RELIANCE',
    product: 'MIS',
    qty: 30,
    avgPrice: 2650,
    ltp: 2680,
    pnl: 900,
    dayChange: 2.5
  },
  {
    id: 'POS003',
    accountId: 'ACC001',
    symbol: 'TATAMOTORS',
    product: 'CNC',
    qty: 200,
    avgPrice: 480,
    ltp: 465,
    pnl: -3000,
    dayChange: -2.5
  }
];

export const gttOrders = [
  {
    id: 'GTT001',
    accountId: 'ACC001',
    symbol: 'RELIANCE',
    qty: 50,
    buyPrice: 2400,
    sellPrice: 2800,
    stopLoss: 2300,
    status: 'ACTIVE',
    createdAt: '2024-01-10T09:00:00'
  },
  {
    id: 'GTT002',
    accountId: 'ACC002',
    symbol: 'TCS',
    qty: 25,
    buyPrice: 3300,
    sellPrice: 3600,
    stopLoss: 3200,
    status: 'ACTIVE',
    createdAt: '2024-01-11T10:00:00'
  },
  {
    id: 'GTT003',
    accountId: 'ACC003',
    symbol: 'INFY',
    qty: 90,
    buyPrice: 1400,
    sellPrice: 1600,
    stopLoss: 1350,
    status: 'TRIGGERED',
    createdAt: '2024-01-12T11:00:00'
  }
];

export const portfolioHistory = [
  { date: '2024-01-01', value: 2750000 },
  { date: '2024-01-02', value: 2765000 },
  { date: '2024-01-03', value: 2748000 },
  { date: '2024-01-04', value: 2782000 },
  { date: '2024-01-05', value: 2800000 },
  { date: '2024-01-08', value: 2795000 },
  { date: '2024-01-09', value: 2820000 },
  { date: '2024-01-10', value: 2845000 },
  { date: '2024-01-11', value: 2830000 },
  { date: '2024-01-12', value: 2855000 },
  { date: '2024-01-15', value: 2870000 },
  { date: '2024-01-16', value: 2750000 }
];

export const niftyData = {
  current: 21750,
  change: 125.50,
  changePercent: 0.58
};

export function formatIndianCurrency(amount) {
  if (amount >= 10000000) {
    return `₹${(amount / 10000000).toFixed(2)} Cr`;
  } else if (amount >= 100000) {
    return `₹${(amount / 100000).toFixed(2)} L`;
  } else if (amount >= 1000) {
    return `₹${(amount / 1000).toFixed(2)} K`;
  }
  return `₹${amount.toFixed(2)}`;
}

export function formatNumber(amount) {
  if (amount >= 10000000) {
    return `${(amount / 10000000).toFixed(2)} Cr`;
  } else if (amount >= 100000) {
    return `${(amount / 100000).toFixed(2)} L`;
  } else if (amount >= 1000) {
    return `${(amount / 1000).toFixed(2)} K`;
  }
  return amount.toLocaleString('en-IN');
}

export function calculateMarketStatus() {
  const now = new Date();
  const hours = now.getHours();
  const minutes = now.getMinutes();
  const currentTime = hours * 60 + minutes;

  const marketOpen = 9 * 60 + 15;  // 9:15 AM
  const marketClose = 15 * 60 + 30; // 3:30 PM

  return currentTime >= marketOpen && currentTime <= marketClose ? 'OPEN' : 'CLOSED';
}

export function enrichHoldingsData(holdings) {
  return holdings.map(holding => {
    const currentValue = holding.qty * holding.ltp;
    const investedValue = holding.qty * holding.avgBuyPrice;
    const pnl = currentValue - investedValue;
    const pnlPercent = (pnl / investedValue) * 100;

    return {
      ...holding,
      currentValue,
      investedValue,
      pnl,
      pnlPercent
    };
  });
}

export function getTotalPortfolioValue() {
  return accounts.reduce((total, account) => total + account.currentValue, 0);
}

export function getTotalDayPL() {
  return accounts.reduce((total, account) => total + account.dayPL, 0);
}

export function getTotalOverallPL() {
  return accounts.reduce((total, account) => total + account.overallPL, 0);
}

export function getTopGainers() {
  const enriched = enrichHoldingsData(holdings);
  return enriched
    .filter(h => h.pnlPercent > 0)
    .sort((a, b) => b.pnlPercent - a.pnlPercent)
    .slice(0, 5);
}

export function getTopLosers() {
  const enriched = enrichHoldingsData(holdings);
  return enriched
    .filter(h => h.pnlPercent < 0)
    .sort((a, b) => a.pnlPercent - b.pnlPercent)
    .slice(0, 5);
}

export function getPortfolioAllocation() {
  const enriched = enrichHoldingsData(holdings);
  const allocation = {};

  enriched.forEach(holding => {
    allocation[holding.symbol] = (allocation[holding.symbol] || 0) + holding.currentValue;
  });

  return Object.entries(allocation)
    .map(([symbol, value]) => ({ symbol, value }))
    .sort((a, b) => b.value - a.value);
}
