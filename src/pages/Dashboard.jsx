import { useState, useEffect } from 'react';
import MetricCard from '../components/MetricCard';
import LoadingSpinner from '../components/LoadingSpinner';
import ErrorBanner from '../components/ErrorBanner';
import TokenExpiredModal from '../components/TokenExpiredModal';
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
import { useStats } from '../hooks/useStats';
import { useAccounts } from '../hooks/useAccounts';
import { formatIndianCurrency, formatNumber } from '../services/api';

export default function Dashboard() {
  const [selectedAccount, setSelectedAccount] = useState('all');
  const [showTokenModal, setShowTokenModal] = useState(false);
  const [tokenAccountId, setTokenAccountId] = useState(null);

  const { summary, equityData, allocation, topGainers, topLosers, loading, error, refetch } = useStats();
  const { data: accounts } = useAccounts();

  // Handle token expired error
  useEffect(() => {
    if (error === 'TOKEN_EXPIRED') {
      // Use the first account if available
      if (accounts.length > 0) {
        setTokenAccountId(accounts[0].id);
        setShowTokenModal(true);
      }
    }
  }, [error, accounts]);

  const handleTokenModalClose = () => {
    setShowTokenModal(false);
    setTokenAccountId(null);
    refetch();
  };

  const chartData = equityData.map(item => ({
    name: new Date(item.date).toLocaleDateString('en-IN', { day: '2-digit', month: 'short' }),
    value: item.total_value,
    dayPnl: item.day_pnl
  }));

  const COLORS = ['#6366f1', '#22c55e', '#ef4444', '#f59e0b', '#8b5cf6', '#06b6d4', '#f97316', '#84cc16'];

  if (loading && summary.total_value === 0) {
    return (
      <div className="dashboard">
        <div className="flex items-center justify-center h-96">
          <LoadingSpinner size="large" text="Loading dashboard..." />
        </div>
      </div>
    );
  }

  return (
    <div className="dashboard">
      <ErrorBanner error={error !== 'TOKEN_EXPIRED' ? error : null} onDismiss={() => refetch()} />

      <TokenExpiredModal
        isOpen={showTokenModal}
        onClose={handleTokenModalClose}
        accountId={tokenAccountId}
      />

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

      {accounts.length === 0 ? (
        <div className="flex flex-col items-center justify-center h-96 text-center">
          <div className="text-gray-400 mb-4">
            <svg className="w-16 h-16 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 4v16m8-8H4" />
            </svg>
            <p className="text-lg">No accounts added yet</p>
            <p className="text-sm mt-2">Add your first Zerodha account in Settings to get started</p>
          </div>
        </div>
      ) : (
        <>
          <div className="metrics-row">
            <MetricCard
              title="Portfolio Value"
              value={formatIndianCurrency(summary.total_value)}
            />
            <MetricCard
              title="Day P&L"
              value={formatIndianCurrency(Math.abs(summary.day_pnl))}
              subtitle={summary.day_pnl >= 0 ? 'Profit' : 'Loss'}
              positive={summary.day_pnl >= 0}
            />
            <MetricCard
              title="Overall P&L"
              value={formatIndianCurrency(Math.abs(summary.day_pnl))}
              subtitle={summary.day_pnl >= 0 ? 'Profit' : 'Loss'}
              positive={summary.day_pnl >= 0}
            />
          </div>

          <div className="dashboard-grid">
            <div className="chart-container">
              <h3>Portfolio Growth (30 Days)</h3>
              <div className="chart-wrapper">
                {equityData.length > 0 ? (
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
                        formatter={(value, name) => [
                          name === 'value' ? formatIndianCurrency(value) : formatIndianCurrency(value),
                          name === 'value' ? 'Portfolio Value' : 'Day P&L'
                        ]}
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
                ) : (
                  <div className="flex items-center justify-center h-64 text-gray-500">
                    No equity data available
                  </div>
                )}
              </div>
            </div>

            <div className="chart-container">
              <h3>Portfolio Allocation</h3>
              <div className="chart-wrapper">
                {allocation.length > 0 ? (
                  <ResponsiveContainer width="100%" height={300}>
                    <PieChart>
                      <Pie
                        data={allocation}
                        dataKey="value"
                        nameKey="stock"
                        cx="50%"
                        cy="50%"
                        outerRadius={100}
                      >
                        {allocation.map((entry, index) => (
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
                ) : (
                  <div className="flex items-center justify-center h-64 text-gray-500">
                    No allocation data available
                  </div>
                )}
              </div>
            </div>
          </div>

          <div className="dashboard" style={{ marginTop: '30px' }}>
            <div className="top-lists">
              <div className="top-section">
                <h3 className="section-title">Top Gainers 💚</h3>
                {topGainers.length > 0 ? (
                  <div className="stock-list">
                    {topGainers.map((stock, index) => (
                      <div key={index} className="stock-item">
                        <div>
                          <div className="stock-symbol">{stock.stock}</div>
                        </div>
                        <div className="stock-metrics">
                          <div className="stock-pnl">{formatIndianCurrency(stock.pnl)}</div>
                          <div className="stock-percent positive">+{stock.pnl_percent.toFixed(2)}%</div>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-gray-500 text-sm">No gainers today</div>
                )}
              </div>

              <div className="top-section">
                <h3 className="section-title">Top Losers ❤️</h3>
                {topLosers.length > 0 ? (
                  <div className="stock-list">
                    {topLosers.map((stock, index) => (
                      <div key={index} className="stock-item">
                        <div>
                          <div className="stock-symbol">{stock.stock}</div>
                        </div>
                        <div className="stock-metrics">
                          <div className="stock-pnl">{formatIndianCurrency(stock.pnl)}</div>
                          <div className="stock-percent negative">{stock.pnl_percent.toFixed(2)}%</div>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-gray-500 text-sm">No losers today</div>
                )}
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
