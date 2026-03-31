import { useState, useEffect } from 'react';
import MarketStatus from './MarketStatus';
import { getSummary, formatIndianCurrency } from '../services/api';

export default function TopBar() {
  const [summary, setSummary] = useState({
    total_value: 0,
    day_pnl: 0,
    accounts_count: 0,
  });
  const [lastUpdated, setLastUpdated] = useState(new Date());
  const [backendOnline, setBackendOnline] = useState(true);
  const [currentTime, setCurrentTime] = useState(new Date());

  useEffect(() => {
    const fetchSummary = async () => {
      try {
        const result = await getSummary();
        setSummary(result);
        setLastUpdated(new Date());
        setBackendOnline(true);
      } catch (err) {
        setBackendOnline(false);
      }
    };

    fetchSummary();

    // Refresh every 60 seconds
    const interval = setInterval(fetchSummary, 60000);

    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentTime(new Date());
    }, 60000); // Update every minute

    return () => clearInterval(timer);
  }, []);

  const formatTime = (date) => {
    return date.toLocaleTimeString('en-IN', {
      hour: '2-digit',
      minute: '2-digit',
      hour12: false
    });
  };

  const formatDate = (date) => {
    return date.toLocaleDateString('en-IN', {
      day: '2-digit',
      month: 'short',
      year: 'numeric'
    });
  };

  return (
    <div className="topbar">
      <div className="topbar-left">
        <div className="logo">
          <span className="logo-icon">📊</span>
          <span className="logo-text">pyPortMan</span>
        </div>
      </div>

      <div className="topbar-center">
        <div className="market-info">
          <MarketStatus />
        </div>
      </div>

      <div className="topbar-right">
        <div className="portfolio-summary">
          <div className="portfolio-item">
            <span className="portfolio-label">Portfolio</span>
            <span className="portfolio-value">{formatIndianCurrency(summary.total_value)}</span>
          </div>
          <div className="portfolio-item">
            <span className="portfolio-label">Day P&L</span>
            <span className={`portfolio-value ${summary.day_pnl >= 0 ? 'positive' : 'negative'}`}>
              {summary.day_pnl >= 0 ? '+' : ''}{formatIndianCurrency(summary.day_pnl)}
            </span>
          </div>
          <div className="portfolio-item">
            <span className="portfolio-label">Accounts</span>
            <span className="portfolio-value">{summary.accounts_count}</span>
          </div>
        </div>

        {!backendOnline && (
          <div className="backend-status offline">
            <span className="status-dot"></span>
            Backend Offline
          </div>
        )}

        <div className="header-time">
          <span className="date">{formatDate(currentTime)}</span>
          <span className="time">{formatTime(currentTime)} IST</span>
        </div>
      </div>
    </div>
  );
}
