import { useState } from 'react';
import PositionsTable from '../components/PositionsTable';
import LoadingSpinner from '../components/LoadingSpinner';
import ErrorBanner from '../components/ErrorBanner';
import TokenExpiredModal from '../components/TokenExpiredModal';
import { usePositions } from '../hooks/usePositions';
import { useAccounts } from '../hooks/useAccounts';
import { formatIndianCurrency, formatNumber } from '../services/api';

export default function Positions() {
  const [selectedAccount, setSelectedAccount] = useState('all');
  const [showTokenModal, setShowTokenModal] = useState(false);
  const [tokenAccountId, setTokenAccountId] = useState(null);
  const [squaringOff, setSquaringOff] = useState(null);

  const { data: positions, loading, error, refetch, squareoff, squareoffAll } = usePositions();
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

  const handleSquareOff = async (position) => {
    if (!window.confirm(`Square off ${position.stock} position?`)) {
      return;
    }

    try {
      setSquaringOff(position.id);
      await squareoff({
        tradingsymbol: position.stock,
        exchange: position.exchange,
        order_type: 'MARKET',
        product: position.product,
      });
    } catch (err) {
      alert(err.message || 'Failed to square off position');
    } finally {
      setSquaringOff(null);
    }
  };

  const handleSquareOffAll = async () => {
    if (selectedAccount === 'all') {
      alert('Please select a specific account to square off all positions');
      return;
    }

    const accountPositions = positions.filter(p => p.account_id === parseInt(selectedAccount));
    if (accountPositions.length === 0) {
      alert('No positions to square off');
      return;
    }

    if (!window.confirm(`Square off all ${accountPositions.length} positions?`)) {
      return;
    }

    try {
      setSquaringOff('all');
      await squareoffAll();
    } catch (err) {
      alert(err.message || 'Failed to square off all positions');
    } finally {
      setSquaringOff(null);
    }
  };

  const filteredPositions = selectedAccount === 'all'
    ? positions
    : positions.filter(p => p.account_id === parseInt(selectedAccount));

  // Enrich positions data
  const enrichedPositions = filteredPositions.map(position => ({
    ...position,
    id: position.id.toString(),
    accountId: position.account_id.toString(),
    accountName: accounts.find(a => a.id === position.account_id)?.name || 'Unknown',
    symbol: position.stock,
    product: position.product,
    qty: position.qty,
    avgPrice: position.avg_price,
    ltp: position.ltp,
    pnl: position.pnl,
    dayChange: position.pnl_percent || 0,
  }));

  const totalPNL = enrichedPositions.reduce((sum, p) => sum + p.pnl, 0);
  const totalValue = enrichedPositions.reduce((sum, p) => sum + (p.qty * p.ltp), 0);

  return (
    <div className="positions-page">
      <ErrorBanner error={error !== 'TOKEN_EXPIRED' ? error : null} onDismiss={() => refetch()} />

      <TokenExpiredModal
        isOpen={showTokenModal}
        onClose={handleTokenModalClose}
        accountId={tokenAccountId}
      />

      <div className="page-header">
        <h1>Positions</h1>
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
            className="btn-danger"
            onClick={handleSquareOffAll}
            disabled={selectedAccount === 'all' || squaringOff === 'all'}
          >
            {squaringOff === 'all' ? 'Squaring Off...' : 'Square Off All'}
          </button>
        </div>
      </div>

      {loading && positions.length === 0 ? (
        <div className="flex items-center justify-center h-96">
          <LoadingSpinner size="large" text="Loading positions..." />
        </div>
      ) : (
        <>
          <div className="positions-summary">
            <div className="summary-card">
              <div className="summary-label">Total P&L</div>
              <div className={`summary-value ${totalPNL >= 0 ? 'positive' : 'negative'}`}>
                {formatIndianCurrency(Math.abs(totalPNL))}
              </div>
            </div>
            <div className="summary-card">
              <div className="summary-label">Total Value</div>
              <div className="summary-value">{formatIndianCurrency(totalValue)}</div>
            </div>
            <div className="summary-card">
              <div className="summary-label">Position Count</div>
              <div className="summary-value">{formatNumber(enrichedPositions.length)}</div>
            </div>
          </div>

          {enrichedPositions.length > 0 ? (
            <PositionsTable
              positions={enrichedPositions}
              onSquareOff={handleSquareOff}
              squaringOff={squaringOff}
            />
          ) : (
            <div className="flex flex-col items-center justify-center h-64 text-center">
              <div className="text-gray-400 mb-4">
                <svg className="w-16 h-16 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
                </svg>
                <p className="text-lg">No open positions</p>
                <p className="text-sm mt-2">
                  {accounts.length === 0
                    ? 'Add an account first to see positions'
                    : 'Positions will appear here once you have open trades'}
                </p>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
