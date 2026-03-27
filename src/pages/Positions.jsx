import { useState } from 'react';
import PositionsTable from '../components/PositionsTable';
import { positions, formatIndianCurrency, formatNumber } from '../data/mockData';

export default function Positions() {
  const [selectedAccount, setSelectedAccount] = useState('all');

  const filteredPositions = selectedAccount === 'all'
    ? positions
    : positions.filter(p => p.accountId === selectedAccount);

  const totalPNL = filteredPositions.reduce((sum, p) => sum + p.pnl, 0);
  const totalValue = filteredPositions.reduce((sum, p) => sum + (p.qty * p.ltp), 0);

  const handleSquareOff = (position) => {
    if (window.confirm(`Square off ${position.symbol} position?`)) {
      console.log('Squaring off position:', position);
    }
  };

  return (
    <div className="positions-page">
      <div className="page-header">
        <h1>Positions</h1>
        <div className="account-filter">
          <select
            value={selectedAccount}
            onChange={(e) => setSelectedAccount(e.target.value)}
            className="filter-select"
          >
            <option value="all">All Accounts</option>
            <option value="ACC001">Main Account</option>
            <option value="ACC002">Wife Account</option>
            <option value="ACC003">HUF Account</option>
          </select>
        </div>
      </div>

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
          <div className="summary-value">{formatNumber(filteredPositions.length)}</div>
        </div>
      </div>

      <PositionsTable positions={filteredPositions} onSquareOff={handleSquareOff} />
    </div>
  );
}
