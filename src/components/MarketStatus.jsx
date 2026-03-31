import React from 'react';
import { isMarketOpen } from '../services/api';

/**
 * MarketStatus component
 * Displays current market status (OPEN/CLOSED)
 */
export default function MarketStatus() {
  const [isOpen, setIsOpen] = React.useState(isMarketOpen());
  const [lastUpdated, setLastUpdated] = React.useState(new Date());

  React.useEffect(() => {
    const interval = setInterval(() => {
      setIsOpen(isMarketOpen());
      setLastUpdated(new Date());
    }, 60000); // Check every minute

    return () => clearInterval(interval);
  }, []);

  const timeString = lastUpdated.toLocaleTimeString('en-IN', {
    hour: '2-digit',
    minute: '2-digit',
  });

  return (
    <div className="flex items-center gap-2">
      <span
        className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium ${
          isOpen
            ? 'bg-green-900/30 text-green-400 border border-green-700'
            : 'bg-red-900/30 text-red-400 border border-red-700'
        }`}
      >
        <span className={`w-2 h-2 rounded-full ${isOpen ? 'bg-green-400' : 'bg-red-400'}`} />
        {isOpen ? 'OPEN' : 'CLOSED'}
      </span>
      <span className="text-gray-500 text-xs">Updated: {timeString}</span>
    </div>
  );
}
