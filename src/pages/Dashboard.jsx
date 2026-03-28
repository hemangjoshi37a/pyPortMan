import { useState, useEffect } from 'react';
import MetricCard from '../components/MetricCard';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  PieChart,
  Pie,
  Cell,
  Legend
} from 'recharts';
import {
  accounts,
  enrichHoldingsData,
  holdings,
  portfolioHistory,
  getTotalPortfolioValue,
  getTotalDayPL,
  getTotalOverallPL,
  getPortfolioAllocation,
  getTopGainers,
  getTopLosers,
  formatIndianCurrency,
  formatNumber
} from '../data/mockData';

export default function Dashboard() {
  const [selectedAccount, setSelectedAccount] = useState('all');
  const [dashboardData, setDashboardData] = useState({
    portfolioValue: 0,
    dayPL: 0,
    overallPL: 0,
    allocation: [],
    topGainers: [],
    topLosers: []
  });

  useEffect(() => {
    const updateData = () => {
      const filteredHoldings = selectedAccount === 'all'
        ? holdings
        : holdings.filter(h => h.accountId === selectedAccount);

      const enrichedHoldings = enrichHoldingsData(filteredHoldings);
      const selectedAccounts = selectedAccount === 'all'
        ? accounts
        : accounts.filter(a => a.id === selectedAccount);

      setDashboardData({
        portfolioValue: selectedAccounts.reduce((sum, acc) => sum + acc.currentValue, 0),
        dayPL: selectedAccounts.reduce((sum, acc) => sum + acc.dayPL, 0),
        overallPL: selectedAccounts.reduce((sum, acc) => sum + acc.overallPL, 0),
        allocation: selectedAccount === 'all' ? getPortfolioAllocation() : [],
        topGainers: getTopGainers(),
        topLosers: getTopLosers()
      });
    };

    updateData();
  }, [selectedAccount]);

  const chartData = portfolioHistory.map(item => ({
    name: new Date(item.date).toLocaleDateString('en-IN', { day: '2-digit', month: 'short' }),
    value: item.value
  }));

  const COLORS = ['#6366f1', '#22c55e', '#ef4444', '#f59e0b', '#8b5cf6', '#06b6d4', '#f97316', '#84cc16'];

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <h1>Dashboard</h1>
        <div className="account-filter">
          <select
            value={selectedAccount}
            onChange={(e) => setSelectedAccount(e.target.value)}
            className="filter-select"
          >
            <option value="all">All Accounts</option>
            {accounts.map(account => (
              <option key={account.id} value={account.id}>
                {account.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="metrics-row">
        <MetricCard
          title="Portfolio Value"
          value={formatIndianCurrency(dashboardData.portfolioValue)}
        />
        <MetricCard
          title="Day P&L"
          value={formatIndianCurrency(Math.abs(dashboardData.dayPL))}
          subtitle={dashboardData.dayPL >= 0 ? 'Profit' : 'Loss'}
        />
        <MetricCard
          title="Overall P&L"
          value={formatIndianCurrency(Math.abs(dashboardData.overallPL))}
          subtitle={dashboardData.overallPL >= 0 ? 'Profit' : 'Loss'}
        />
      </div>

      <div className="dashboard-grid">
        <div className="chart-container">
          <h3>Portfolio Growth (30 Days)</h3>
          <div className="chart-wrapper">
            <ResponsiveContainer width="100%" height={300}>
              <AreaChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e2535" />
                <XAxis dataKey="name" stroke="#9ca3af" />
                <YAxis stroke="#9ca3af" />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#111827',
                    border: '1px solid #1e2535',
                    borderRadius: '8px'
                  }}
                />
                <Area
                  type="monotone"
                  dataKey="value"
                  stroke="#6366f1"
                  fill="#6366f1"
                  fillOpacity={0.3}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="chart-container">
          <h3>Portfolio Allocation</h3>
          <div className="chart-wrapper">
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={dashboardData.allocation}
                  dataKey="value"
                  nameKey="symbol"
                  cx="50%"
                  cy="50%"
                  outerRadius={100}
                >
                  {dashboardData.allocation.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Legend
                  layout="vertical"
                  align="right"
                  verticalAlign="middle"
                />
                <Tooltip
                  formatter={(value, name) => [
                    formatIndianCurrency(value),
                    name
                  ]}
                  contentStyle={{
                    backgroundColor: '#111827',
                    border: '1px solid #1e2535',
                    borderRadius: '8px'
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      <div className="dashboard" style={{ marginTop: '30px' }}>
        <div className="top-lists">
          <div className="top-section">
            <h3 className="section-title">Top Gainers 💚</h3>
            <div className="stock-list">
              {dashboardData.topGainers.map((stock, index) => (
                <div key={index} className="stock-item">
                  <div>
                    <div className="stock-symbol">{stock.symbol}</div>
                    <div className="stock-account">{stock.accountName}</div>
                  </div>
                  <div className="stock-metrics">
                    <div className="stock-pnl">{formatIndianCurrency(stock.pnl)}</div>
                    <div className="stock-percent positive">+{stock.pnlPercent.toFixed(2)}%</div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="top-section">
            <h3 className="section-title">Top Losers ❤️</h3>
            <div className="stock-list">
              {dashboardData.topLosers.map((stock, index) => (
                <div key={index} className="stock-item">
                  <div>
                    <div className="stock-symbol">{stock.symbol}</div>
                    <div className="stock-account">{stock.accountName}</div>
                  </div>
                  <div className="stock-metrics">
                    <div className="stock-pnl">{formatIndianCurrency(stock.pnl)}</div>
                    <div className="stock-percent negative">{stock.pnlPercent.toFixed(2)}%</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
