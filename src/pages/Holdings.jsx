import { useState } from 'react';
import HoldingsTable from '../components/HoldingsTable';
import LoadingSpinner from '../components/LoadingSpinner';
import ErrorBanner from '../components/ErrorBanner';
import TokenExpiredModal from '../components/TokenExpiredModal';
import { useHoldings } from '../hooks/useHoldings';
import { useAccounts } from '../hooks/useAccounts';
import { formatIndianCurrency, formatNumber } from '../services/api';

export default function Holdings() {
  const [selectedAccount, setSelectedAccount] = useState('all');
  const [showTokenModal, setShowTokenModal] = useState(false);
  const [tokenAccountId, setTokenAccountId] = useState(null);
  const [refreshing, setRefreshing] = useState(false);

  const { data: holdings, loading, error, refetch, refresh } = useHoldings();
  const { data: accounts } = useAccounts();

  // Handle token expired error
  if (error === 'TOKEN_EXPIRED' && accounts.length > 0) {
    setTokenAccountId(accounts[0].id);
    setShowTokenModal(true);
  }

  const handleTokenModalClose = () => {
    setShowTokenModal(false);
    setTokenAccountId(null);
    refetch();
  };

  const handleRefresh = async () => {
    if (selectedAccount === 'all') {
      alert('Please select a specific account to refresh holdings');
      return;
    }

    try {
      setRefreshing(true);
      await refresh();
    } catch (err) {
      alert(err.message || 'Failed to refresh holdings');
    } finally {
      setRefreshing(false);
    }
  };

  const filteredHoldings = selectedAccount === 'all'
    ? holdings
    : holdings.filter(h => h.account_id === parseInt(selectedAccount));

  // Enrich holdings data with calculated values
  const enrichedHoldings = filteredHoldings.map(holding => {
    const currentValue = holding.qty * holding.ltp;
    const investedValue = holding.qty * holding.avg_price;
    const pnl = currentValue - investedValue;
    const pnlPercent = investedValue > 0 ? (pnl / investedValue) * 100 : 0;

    return {
      ...holding,
      accountId: holding.account_id.toString(),
      accountName: accounts.find(a => a.id === holding.account_id)?.name || 'Unknown',
      symbol: holding.stock,
      qty: holding.qty,
      avgBuyPrice: holding.avg_price,
      ltp: holding.ltp,
      currentValue,
      investedValue,
      pnl,
      pnlPercent,
      dayChange: pnlPercent, // Using pnl_percent as day change for now
    };
  });

  const totalInvested = enrichedHoldings.reduce((sum, h) => sum + h.investedValue, 0);
  const totalCurrent = enrichedHoldings.reduce((sum, h) => sum + h.currentValue, 0);
  const totalPNL = enrichedHoldings.reduce((sum, h) => sum + h.pnl, 0);

  return (
    <div className="holdings-page">
      <ErrorBanner error={error !== 'TOKEN_EXPIRED' ? error : null} onDismiss={() => refetch()} />

      <TokenExpiredModal
        isOpen={showTokenModal}
        onClose={handleTokenModalClose}
        accountId={tokenAccountId}
      />

      <div className="page-header">
        <h1>Holdings</h1>
        <div className="flex items-center gap-3">
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
          <button
            className="btn-secondary"
            onClick={handleRefresh}
            disabled={refreshing || selectedAccount === 'all'}
          >
            {refreshing ? 'Refreshing...' : 'Refresh'}
          </button>
        </div>
      </div>

      {loading && holdings.length === 0 ? (
        <div className="flex items-center justify-center h-96">
          <LoadingSpinner size="large" text="Loading holdings..." />
        </div>
      ) : (
        <>
          <div className="holdings-summary">
            <div className="summary-card">
              <div className="summary-label">Total Invested</div>
              <div className="summary-value">{formatIndianCurrency(totalInvested)}</div>
            </div>
            <div className="summary-card">
              <div className="summary-label">Current Value</div>
              <div className="summary-value">{formatIndianCurrency(totalCurrent)}</div>
            </div>
            <div className="summary-card">
              <div className="summary-label">Total P&L</div>
              <div className={`summary-value ${totalPNL >= 0 ? 'positive' : 'negative'}`}>
                {formatIndianCurrency(Math.abs(totalPNL))}
              </div>
            </div>
            <div className="summary-card">
              <div className="summary-label">Stock Count</div>
              <div className="summary-value">{formatNumber(enrichedHoldings.length)}</div>
            </div>
          </div>

          {enrichedHoldings.length > 0 ? (
            <HoldingsTable holdings={enrichedHoldings} />
          ) : (
            <div className="flex flex-col items-center justify-center h-64 text-center">
              <div className="text-gray-400 mb-4">
                <svg className="w-16 h-16 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
                </svg>
                <p className="text-lg">No holdings found</p>
                <p className="text-sm mt-2">
                  {accounts.length === 0
                    ? 'Add an account first to see holdings'
                    : 'Holdings will appear here once you have positions'}
                </p>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
