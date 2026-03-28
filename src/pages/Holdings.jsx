import { useState } from 'react';
import HoldingsTable from '../components/HoldingsTable';
import {
  holdings,
  enrichHoldingsData,
  formatIndianCurrency,
  formatNumber
} from '../data/mockData';

export default function Holdings() {
  const [selectedAccount, setSelectedAccount] = useState('all');

  const filteredHoldings = selectedAccount === 'all'
    ? holdings
    : holdings.filter(h => h.accountId === selectedAccount);

  const enrichedHoldings = enrichHoldingsData(filteredHoldings);

  const totalInvested = enrichedHoldings.reduce((sum, h) => sum + h.investedValue, 0);
  const totalCurrent = enrichedHoldings.reduce((sum, h) => sum + h.currentValue, 0);
  const totalPNL = enrichedHoldings.reduce((sum, h) => sum + h.pnl, 0);

  return (
    <div className="holdings-page">
      <div className="page-header">
        <h1>Holdings</h1>
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

      <HoldingsTable holdings={enrichedHoldings} />
    </div>
  );
}
