import { useEffect, useState } from 'react';
import { formatIndianCurrency, calculateMarketStatus, niftyData } from '../data/mockData';

export default function TopBar() {
  const [marketStatus, setMarketStatus] = useState(calculateMarketStatus());
  const [currentTime, setCurrentTime] = useState(new Date());

  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentTime(new Date());
      setMarketStatus(calculateMarketStatus());
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
        <div className="market-status">
          Market: <span className={`status ${marketStatus.toLowerCase()}`}>{marketStatus}</span>
        </div>
      </div>

      <div className="topbar-center">
        <div className="nifty-info">
          <span className="nifty-label">NIFTY 50</span>
          <span className="nifty-value">{formatIndianCurrency(niftyData.current)}</span>
          <span className={`nifty-change ${niftyData.change >= 0 ? 'positive' : 'negative'}`}>
            {niftyData.change >= 0 ? '+' : ''}{niftyData.change.toFixed(2)} ({niftyData.changePercent >= 0 ? '+' : ''}{niftyData.changePercent.toFixed(2)}%)
          </span>
        </div>
      </div>

      <div className="topbar-right">
        <div className="header-time">
          <span className="date">{formatDate(currentTime)}</span>
          <span className="time">{formatTime(currentTime)} IST</span>
        </div>
      </div>
    </div>
  );
}
