import { formatIndianCurrency } from '../services/api';

export default function AccountCard({ account, onClick, onEdit, onDelete, onRefreshToken }) {
  return (
    <div className="account-card" onClick={() => onClick && onClick(account)}>
      <div className="account-header">
        <div className="account-title">
          <h3>{account.name}</h3>
          <span className={`account-status ${account.status}`}>{account.status}</span>
        </div>
        <div className="account-actions">
          <button
            className="btn-icon"
            onClick={(e) => {
              e.stopPropagation();
              onEdit && onEdit(account);
            }}
            title="Edit account"
          >
            ✏️
          </button>
          {onRefreshToken && (
            <button
              className="btn-icon"
              onClick={(e) => {
                e.stopPropagation();
                onRefreshToken && onRefreshToken(account);
              }}
              title="Refresh token"
            >
              🔄
            </button>
          )}
          {onDelete && (
            <button
              className="btn-icon"
              onClick={(e) => {
                e.stopPropagation();
                onDelete && onDelete(account);
              }}
              title="Delete account"
            >
              🗑️
            </button>
          )}
        </div>
      </div>

      <div className="account-details">
        <div className="account-row">
          <span className="account-label">Account ID:</span>
          <span className="account-value">{account.id}</span>
        </div>
        <div className="account-row">
          <span className="account-label">Broker:</span>
          <span className="account-value">{account.broker.toUpperCase()}</span>
        </div>
      </div>

      <div className="account-metrics">
        <div className="account-metric">
          <div className="metric-label">Invested</div>
          <div className="metric-value">{formatIndianCurrency(account.totalInvested)}</div>
        </div>
        <div className="account-metric">
          <div className="metric-label">Current</div>
          <div className="metric-value">{formatIndianCurrency(account.currentValue)}</div>
        </div>
        <div className="account-metric">
          <div className="metric-label">Overall P&L</div>
          <div className={`metric-value ${account.overallPL >= 0 ? 'positive' : 'negative'}`}>
            {formatIndianCurrency(account.overallPL)}
          </div>
        </div>
      </div>

      <div className="account-day-pl">
        <span className="account-label">Day P&L:</span>
        <span className={`day-pl-value ${account.dayPL >= 0 ? 'positive' : 'negative'}`}>
          {account.dayPL >= 0 ? '+' : ''}{formatIndianCurrency(account.dayPL)}
        </span>
      </div>
    </div>
  );
}
